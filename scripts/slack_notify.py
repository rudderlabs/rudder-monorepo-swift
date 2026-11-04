"""Slack notifications for releases and PR validation. Never fails a job: a missing webhook or a failed post is a
warning only. Message texts live in release/texts.json; no message links to the workflow run.

  release    one message per released package, after its customer install check passed (publish.yml)
  attention  Tag & Release Packages left something incomplete; silent otherwise (complete-publication.yml)
  pr         every PR validation run, passed or failed (ci.yml)

The webhook comes from SLACK_WEBHOOK_URL; each workflow maps it from its own secret (SLACK_RELEASE_WEBHOOK_URL or
SLACK_PR_WEBHOOK_URL), so releases and PRs can move to different channels without a code change.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
import urllib.request

from common import OWNER, ROOT, inventory, load, run, text
from publication_status import collect, release_key, summarize
from release_notes import display_name

FAILED = ('failure', 'cancelled', 'timed_out')


def escape(value):
    """Slack mrkdwn control characters in user-written text (PR titles, error messages)."""
    return str(value).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def short(value, limit=150):
    line = ' '.join(str(value).split())
    return line if len(line) <= limit else line[:limit - 1] + '…'


def post(message, webhook=None, opener=urllib.request.urlopen):
    """True when Slack accepted the message. Never raises: notifications must not fail a job."""
    webhook = webhook if webhook is not None else os.environ.get('SLACK_WEBHOOK_URL', '')
    if not webhook:
        print('::warning::Slack notification not sent: no webhook configured')
        return False
    request = urllib.request.Request(webhook, data=json.dumps({'text': message}).encode(),
                                     headers={'Content-Type': 'application/json'}, method='POST')
    try:
        with opener(request, timeout=15) as response:
            if 200 <= getattr(response, 'status', 200) < 300:
                return True
            print(f'::warning::Slack notification not sent: HTTP {response.status}')
    except Exception as error:  # noqa: BLE001 - any failure is a warning, never a failed job
        print(f'::warning::Slack notification not sent: {type(error).__name__}')
    return False


def release_message(key, package, version, customer, actor):
    """`package` is the inventory entry of `key`; `customer` is customer-result.json of the passed install check."""
    repository = f"{OWNER}/{package['repository']}"
    return text('slackRelease', title=display_name(key, package), version=version, repository=repository,
                platforms=', '.join(customer.get('platforms', [])) or 'none', actor=actor,
                url=f'https://github.com/{repository}/releases/tag/{version}')


def attention_items(plan, broken, pending_result, jobs, packages):
    """(title, version, reason) for every item Tag & Release Packages left incomplete. `jobs` is keyed by release_key."""
    items = []
    result = summarize([{'package': i['package'], 'version': i['version'], 'sha': i.get('source_sha', i.get('sha'))}
                        for i in plan], {k: v['job'] for k, v in jobs.items()})
    for state in result['packages']:
        if state['status'] != 'incomplete':
            continue
        found = jobs.get(release_key(state), {})
        customer = found.get('customer', {})
        if customer.get('status') == 'failed':
            reason = 'customer install check failed'
        elif found.get('job', {}).get('outputs', {}).get('error'):
            reason = found['job']['outputs']['error']
        else:
            reason = 'publish job ' + state['jobResult']
        key = state['package']
        items.append((display_name(key, packages.get(key)), state['version'], short(reason)))
    for item in broken:
        items.append((display_name(item['package'], packages.get(item['package'])), item['version'],
                      short(item.get('error') or item.get('status', 'incomplete'))))
    if pending_result in FAILED and not items:
        items.append(('Tag & Release Packages', 'queue', 'the queue check failed'))
    return items


def attention_message(items):
    if not items:
        return None
    lines = '\n'.join(text('slackAttentionItem', title=title, version=version, reason=escape(reason))
                      for title, version, reason in items)
    noun = 'package needs' if len(items) == 1 else 'packages need'
    return text('slackAttention', count=len(items), noun=noun, items=lines)


def failed_checks(jobs, own_name):
    """Names of the run's failed, cancelled or timed-out jobs, e.g. `test (firebase)`. The `ci-ok` gate is listed only
    when nothing else failed: otherwise it just repeats the failure that caused it."""
    failed = [job['name'] for job in jobs if job.get('conclusion') in FAILED and job.get('name') != own_name]
    others = [name for name in failed if name != 'ci-ok']
    return others or failed


def pr_message(event, failed):
    pull = event['pull_request']
    message = text('slackPullRequest', status='failed' if failed else 'passed', emoji='❌' if failed else '✅',
                   repository=event['repository']['full_name'], number=pull['number'], title=escape(pull['title']),
                   head=pull['head']['ref'], base=pull['base']['ref'], actor=event.get('sender', {}).get('login', ''),
                   url=pull['html_url'])
    if failed:
        message += '\n\n' + text('slackFailedChecks', checks='\n'.join('• ' + escape(name) for name in failed))
    return message


def run_jobs():
    """This run's jobs (current attempt) from the GitHub API. Raises when they cannot be read, so the caller posts
    nothing: an unread job list must never be announced as a passed run."""
    endpoint = (f"repos/{os.environ['GITHUB_REPOSITORY']}/actions/runs/{os.environ['GITHUB_RUN_ID']}"
                f"/attempts/{os.environ.get('GITHUB_RUN_ATTEMPT', '1')}/jobs?per_page=100")
    jobs = [job for page in json.loads(run(['gh', 'api', '--paginate', '--slurp', endpoint]))
            for job in page.get('jobs', [])]
    if not jobs:
        raise RuntimeError('the run has no readable jobs')
    return jobs


def download_jobs(plan, temp):
    """Each publish leg leaves publication-<key>-<version> (and customer-<key>-<version>) artifacts."""
    def download(name):
        try:
            run(['gh', 'run', 'download', os.environ['GITHUB_RUN_ID'], '--repo', os.environ['GITHUB_REPOSITORY'],
                 '--name', name, '--dir', Path(temp) / name])
        except RuntimeError:
            return None
        return Path(temp) / name
    plan = [{'package': i['package'], 'version': i['version'], 'sha': i.get('source_sha')} for i in plan]
    jobs = {key: {'job': job} for key, job in collect(plan, download).items()}
    for item in plan:
        folder = download(f"customer-{item['package']}-{item['version']}")
        if folder is not None and (folder / 'customer-result.json').exists():
            jobs.setdefault(release_key(item), {'job': {'result': 'missing', 'outputs': {}}})
            jobs[release_key(item)]['customer'] = load(folder / 'customer-result.json')
    return jobs


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest='command', required=True)
    release = commands.add_parser('release')
    release.add_argument('package')
    release.add_argument('version')
    release.add_argument('--customer-result', type=Path, required=True)
    release.add_argument('--actor', default=os.environ.get('GITHUB_ACTOR', ''))
    release.add_argument('--source-root', type=Path, default=ROOT)
    attention = commands.add_parser('attention')
    attention.add_argument('--plan', default='{"include":[]}', help='the pending job matrix')
    attention.add_argument('--broken', default='[]', help='the pending job broken items')
    attention.add_argument('--pending-result', default='success')
    commands.add_parser('pr')
    args = parser.parse_args(argv)
    try:
        if args.command == 'release':
            message = release_message(args.package, inventory(args.source_root)[args.package], args.version,
                                      load(args.customer_result), args.actor)
        elif args.command == 'attention':
            plan = json.loads(args.plan or '{}').get('include', [])
            with tempfile.TemporaryDirectory(prefix='slack-attention-') as temp:
                jobs = download_jobs(plan, temp) if plan else {}
            message = attention_message(attention_items(plan, json.loads(args.broken or '[]'), args.pending_result,
                                                        jobs, inventory()))
        else:
            event = load(os.environ['GITHUB_EVENT_PATH'])
            message = pr_message(event, failed_checks(run_jobs(), os.environ.get('SLACK_JOB_NAME', '')))
    except Exception as error:  # noqa: BLE001 - a notification problem never fails the job
        print(f'::warning::Slack notification not built: {short(error)}')
        return 0
    if message is None:
        print('Nothing needs attention; no Slack message.')
        return 0
    print(message)
    post(message)
    return 0


if __name__ == '__main__':
    sys.exit(main())
