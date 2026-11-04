"""Slack notifications: message texts, and that a missing webhook or a failed post never fails a job."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import inventory_fixture  # noqa: F401,E402  (default package list for tests)
from common import inventory  # noqa: E402
import slack_notify  # noqa: E402
from slack_notify import (attention_items, attention_message, failed_checks, main, post, pr_message,  # noqa: E402
                          release_message)

ROOT = Path(__file__).resolve().parents[1]
SHA = 'a' * 40


class Response:
    def __init__(self, status=200):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def event(title='fix(sprig): handle missing survey id'):
    return {'repository': {'full_name': 'rudderlabs/rudder-monorepo-swift'}, 'sender': {'login': 'SKannaniOS'},
            'pull_request': {'number': 12, 'title': title, 'html_url': 'https://github.com/rudderlabs/rudder-monorepo-swift/pull/12',
                             'head': {'ref': 'fix/sprig-missing-survey-id'}, 'base': {'ref': 'main'}}}


class MessageTests(unittest.TestCase):
    def test_release_message(self):
        sprig = inventory()['sprig']
        message = release_message('sprig', sprig, '2.0.1', {'status': 'passed', 'platforms': ['iOS']}, 'SKannaniOS')
        repository = 'rudderlabs/' + sprig['repository']
        self.assertEqual(message, f"🚀 *{sprig['title']} 2.0.1* released\n\n*Repository:* {repository}\n*Tag:* 2.0.1\n"
                                  "*Customer install check:* passed ✅ (iOS)\n*Released by:* SKannaniOS\n\n"
                                  f"<https://github.com/{repository}/releases/tag/2.0.1|View Release>")
        two = release_message('firebase', inventory()['firebase'], '2.0.1', {'platforms': ['iOS', 'macOS']}, 'x')
        self.assertIn('passed ✅ (iOS, macOS)', two)

    def test_release_message_without_title_uses_the_target(self):
        package = {key: value for key, value in inventory()['sprig'].items() if key != 'title'}
        message = release_message('sprig', package, '2.0.1', {'platforms': ['iOS']}, 'x')
        self.assertTrue(message.startswith(f"🚀 *{package['target']} 2.0.1* released"))

    def test_pr_message_passed_and_failed_without_run_links(self):
        passed = pr_message(event(), [])
        self.assertEqual(passed, "*PR Validation passed ✅*\n*Repository:* rudderlabs/rudder-monorepo-swift\n"
                                 "*PR:* #12 - fix(sprig): handle missing survey id\n"
                                 "*Branch:* fix/sprig-missing-survey-id → main\n*By:* SKannaniOS\n"
                                 "<https://github.com/rudderlabs/rudder-monorepo-swift/pull/12|View PR>")
        failed = pr_message(event('feat: <b> & {x}'), ['test (firebase)', 'lint'])
        self.assertTrue(failed.startswith('*PR Validation failed ❌*'))
        self.assertIn('#12 - feat: &lt;b&gt; &amp; {x}', failed)
        self.assertTrue(failed.endswith('🚨 *Failed Checks:*\n• test (firebase)\n• lint'))
        for message in (passed, failed):
            self.assertNotIn('/actions/runs/', message)
            self.assertNotIn('Workflow Details', message)

    def test_failed_checks_skip_this_job_and_the_gate_when_others_failed(self):
        jobs = [{'name': 'test (firebase)', 'conclusion': 'failure'}, {'name': 'lint', 'conclusion': 'success'},
                {'name': 'ci-ok', 'conclusion': 'failure'}, {'name': 'sonarcloud', 'conclusion': 'cancelled'},
                {'name': 'Slack PR summary', 'conclusion': None}, {'name': 'export (sprig)', 'conclusion': 'skipped'}]
        self.assertEqual(failed_checks(jobs, 'Slack PR summary'), ['test (firebase)', 'sonarcloud'])
        self.assertEqual(failed_checks([{'name': 'ci-ok', 'conclusion': 'failure'}], 'x'), ['ci-ok'])

    def test_attention_lists_incomplete_items_and_is_silent_otherwise(self):
        plan = [{'package': 'sprig', 'version': '2.0.1', 'source_sha': SHA},
                {'package': 'firebase', 'version': '2.0.1', 'source_sha': SHA}]
        published = {'result': 'success', 'outputs': {'status': 'published', 'package': 'sprig', 'version': '2.0.1',
                                                      'tag': '2.0.1', 'sourceCommit': SHA, 'publicationCommit': 'b' * 40}}
        firebase_failed = {'result': 'failure', 'outputs': {**published['outputs'], 'package': 'firebase'}}
        packages = inventory()
        jobs = {('sprig', '2.0.1'): {'job': published},
                ('firebase', '2.0.1'): {'job': firebase_failed, 'customer': {'status': 'failed'}}}
        items = attention_items(plan, [], 'success', jobs, packages)
        self.assertEqual(items, [(packages['firebase']['title'], '2.0.1', 'customer install check failed')])
        message = attention_message(items)
        self.assertEqual(message, f"⚠️ *Tag & Release Packages: 1 package needs attention*\n\n"
                                  f"• *{packages['firebase']['title']} 2.0.1* — incomplete (customer install check failed)\n\n"
                                  "Fix the cause, then run Tag & Release Packages again.")
        self.assertNotIn('/actions/runs/', message)
        self.assertIsNone(attention_message(attention_items(plan[:1], [], 'success', {('sprig', '2.0.1'): {'job': published}},
                                                            packages)))
        broken = [{'package': 'swift-sdk', 'version': '2.0.1', 'error': 'Publication repository contains\nmanual drift'}]
        two = attention_items(plan[:1], broken, 'failure', {('sprig', '2.0.1'): {'job': published}}, packages)
        self.assertEqual(two, [(packages['swift-sdk']['title'], '2.0.1', 'Publication repository contains manual drift')])
        self.assertIn('2 packages need attention', attention_message(two + items))
        self.assertEqual(attention_items([], [], 'failure', {}, packages),
                         [('Tag & Release Packages', 'queue', 'the queue check failed')])
        self.assertEqual(attention_items([], [], 'success', {}, packages), [])
        missing = attention_items(plan[1:], [], 'success', {}, packages)
        self.assertEqual(missing, [(packages['firebase']['title'], '2.0.1', 'publish job missing')])

    def test_attention_reports_a_failed_version_next_to_a_published_one(self):
        # Two versions of one package in one Tag & Release run: the published one must not hide the failed one.
        plan = [{'package': 'sprig', 'version': '2.0.2', 'source_sha': SHA},
                {'package': 'sprig', 'version': '2.1.1', 'source_sha': SHA}]
        outputs = {'status': 'published', 'package': 'sprig', 'sourceCommit': SHA, 'publicationCommit': 'b' * 40}
        jobs = {('sprig', '2.0.2'): {'job': {'result': 'failure', 'outputs': {**outputs, 'version': '2.0.2', 'tag': '2.0.2'}}},
                ('sprig', '2.1.1'): {'job': {'result': 'success', 'outputs': {**outputs, 'version': '2.1.1', 'tag': '2.1.1'}}}}
        packages = inventory()
        self.assertEqual(attention_items(plan, [], 'success', jobs, packages),
                         [(packages['sprig']['title'], '2.0.2', 'publish job failure')])

    def test_texts_live_in_release_texts(self):
        texts = json.loads((ROOT / 'release/texts.json').read_text())
        for name in ('slackRelease', 'slackAttention', 'slackAttentionItem', 'slackPullRequest', 'slackFailedChecks'):
            self.assertIn(name, texts)
            self.assertNotIn('actions/runs', texts[name])


class PostTests(unittest.TestCase):
    def test_no_webhook_is_a_warning(self):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertFalse(post('hello', webhook=''))
        self.assertIn('::warning::Slack notification not sent: no webhook configured', output.getvalue())

    def test_failed_post_is_a_warning_and_never_raises(self):
        def broken(request, timeout):
            raise OSError('network down https://hooks.slack.com/services/SECRET')
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertFalse(post('hello', webhook='https://hooks.slack.com/services/SECRET', opener=broken))
        self.assertIn('::warning::Slack notification not sent: OSError', output.getvalue())
        self.assertNotIn('SECRET', output.getvalue())
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertFalse(post('hello', webhook='https://example.invalid', opener=lambda r, timeout: Response(500)))

    def test_post_sends_json_text(self):
        sent = []

        def opener(request, timeout):
            sent.append((request.full_url, request.get_method(), json.loads(request.data), timeout))
            return Response(200)
        self.assertTrue(post('hello', webhook='https://example.invalid/hook', opener=opener))
        self.assertEqual(sent, [('https://example.invalid/hook', 'POST', {'text': 'hello'}, 15)])


class CommandTests(unittest.TestCase):
    def test_release_command_posts_and_exits_zero(self):
        with tempfile.TemporaryDirectory() as temp:
            result = Path(temp) / 'customer-result.json'
            result.write_text(json.dumps({'status': 'passed', 'platforms': ['iOS']}))
            with patch.object(slack_notify, 'post') as sent, contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(['release', 'sprig', '2.0.1', '--customer-result', str(result),
                                       '--actor', 'SKannaniOS', '--source-root', str(inventory_fixture.ROOT)]), 0)
        self.assertIn('2.0.1* released', sent.call_args.args[0])

    def test_any_error_is_a_warning_and_exit_zero(self):
        with patch.object(slack_notify, 'post') as sent, contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(['release', 'sprig', '2.0.1', '--customer-result', '/nonexistent.json']), 0)
        sent.assert_not_called()
        self.assertIn('::warning::Slack notification not built', output.getvalue())

    def test_attention_command_is_silent_with_nothing_pending(self):
        with patch.object(slack_notify, 'post') as sent, contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(['attention', '--plan', '{"include":[]}', '--broken', '[]']), 0)
        sent.assert_not_called()
        self.assertIn('Nothing needs attention', output.getvalue())

    def test_pr_command_reads_the_event_and_the_run_jobs(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'event.json'
            path.write_text(json.dumps(event()))
            env = {'GITHUB_EVENT_PATH': str(path), 'SLACK_JOB_NAME': 'Slack PR summary'}
            with patch.dict(os.environ, env), patch.object(slack_notify, 'run_jobs',
                                                           return_value=[{'name': 'lint', 'conclusion': 'failure'}]), \
                    patch.object(slack_notify, 'post') as sent, contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(['pr']), 0)
        self.assertTrue(sent.call_args.args[0].startswith('*PR Validation failed ❌*'))
        self.assertIn('• lint', sent.call_args.args[0])


    def test_pr_command_posts_nothing_when_the_run_jobs_cannot_be_read(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'event.json'
            path.write_text(json.dumps(event()))
            env = {'GITHUB_EVENT_PATH': str(path), 'GITHUB_REPOSITORY': 'rudderlabs/rudder-monorepo-swift',
                   'GITHUB_RUN_ID': '1', 'SLACK_JOB_NAME': 'Slack PR summary'}
            for failure in (RuntimeError('HTTP 403'), '[]', '[{"jobs": []}]'):
                kwargs = {'side_effect': failure} if isinstance(failure, Exception) else {'return_value': failure}
                with self.subTest(failure=failure), patch.dict(os.environ, env), \
                        patch.object(slack_notify, 'run', **kwargs), patch.object(slack_notify, 'post') as sent, \
                        contextlib.redirect_stdout(io.StringIO()) as output:
                    self.assertEqual(main(['pr']), 0)
                    sent.assert_not_called()
                    self.assertIn('::warning::Slack notification not built', output.getvalue())

class WorkflowTests(unittest.TestCase):
    def read(self, name):
        return (ROOT / '.github/workflows' / name).read_text()

    def test_each_message_is_wired_with_its_own_webhook_and_never_fails_a_job(self):
        publish, complete, ci = self.read('publish.yml'), self.read('complete-publication.yml'), self.read('ci.yml')
        step = publish.split('- name: Announce the release in Slack\n', 1)[1].split('\n      - name:', 1)[0]
        self.assertIn("if: steps.verified.outputs.status == 'published' && steps.verified.outputs.takeover != 'true'", step)
        self.assertIn('continue-on-error: true', step)
        self.assertIn('SLACK_WEBHOOK_URL: ${{ secrets.SLACK_RELEASE_WEBHOOK_URL }}', step)
        self.assertLess(publish.index('Verify anonymous public customer upgrade'), publish.index('Announce the release'))
        attention = complete.split('\n  attention:\n', 1)[1]
        self.assertIn("if: always() && needs.pending.result != 'skipped'", attention)
        self.assertIn('SLACK_WEBHOOK_URL: ${{ secrets.SLACK_RELEASE_WEBHOOK_URL }}', attention)
        self.assertIn('continue-on-error: true', attention)
        notify = ci.split('\n  notify:\n', 1)[1]
        self.assertIn("if: always() && github.event_name == 'pull_request'", notify)
        self.assertIn('SLACK_WEBHOOK_URL: ${{ secrets.SLACK_PR_WEBHOOK_URL }}', notify)
        self.assertIn('continue-on-error: true', notify)
        self.assertIn('SLACK_JOB_NAME: Slack PR summary', notify)
        self.assertIn('name: Slack PR summary', notify)
        # The required gate does not wait for, or depend on, the advisory jobs.
        gate = ci.split('\n  ci-ok:\n', 1)[1].split('\n\n  ', 1)[0]
        self.assertIn('needs: [packages, policy, lint, test, export]', gate)

    def test_sanity_runs_only_for_the_sdk_and_reads_the_public_repo(self):
        publish = self.read('publish.yml')
        sanity = publish.split('\n  sanity:\n', 1)[1]
        self.assertIn("needs.publish.outputs.package == 'swift-sdk'", sanity)
        self.assertIn("needs.publish.outputs.takeover != 'true'", sanity)
        self.assertIn("format('publication/swift-sdk/{0}', needs.publish.outputs.version)", sanity)
        self.assertIn('uses: ./.github/workflows/release-sanity.yml', sanity)
        self.assertIn("needs.publish.outputs.status == 'awaiting_review'", sanity)
        self.assertIn('phase: pre-release', sanity)
        self.assertNotIn('post-release', sanity)
        release_sanity = self.read('release-sanity.yml')
        self.assertIn('environment: spm-release', release_sanity)
        self.assertIn('client-id: ${{ vars.RELEASE_APP_CLIENT_ID }}', release_sanity)
        self.assertIn('repositories: rudder-mobile-sdk-test', release_sanity)
        self.assertIn('continue-on-error: true\n    timeout-minutes: 75', release_sanity)

    def test_codeql_scans_swift_only_once_packages_exist(self):
        codeql = self.read('codeql.yml')
        self.assertIn('if [ -f Package.swift ]; then', codeql)
        self.assertIn("generic/platform=iOS Simulator", codeql)
        self.assertIn('permissions: {}', codeql)

    def test_codeql_builds_the_only_scheme_without_a_package_scheme(self):
        line = next(l for l in self.read('codeql.yml').splitlines() if 'xcodebuild -list -json' in l)
        snippet = line.split("python3 -c '", 1)[1].rsplit("'", 1)[0]
        for schemes, expected in ((['RudderMonorepoSwift'], 'RudderMonorepoSwift'),
                                  (['Braze', 'RudderMonorepoSwift-Package', 'RudderStackAnalytics'],
                                   'RudderMonorepoSwift-Package'),
                                  (['Braze', 'RudderStackAnalytics'], '')):
            out = subprocess.run([sys.executable, '-c', snippet], input=json.dumps({'workspace': {'schemes': schemes}}),
                                 capture_output=True, text=True, check=True).stdout.strip()
            self.assertEqual(out, expected)


if __name__ == '__main__':
    unittest.main()
