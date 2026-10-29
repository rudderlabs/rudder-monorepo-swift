# Repository setup (admin)

What an admin configures once in `rudderlabs/rudder-monorepo-swift` before CI and releases can run.
Names must match exactly: the workflows read them as written here.

## Settings (done)

- Merges: squash only, message "Pull request title and description"; "Always suggest updating pull request branches" on; "Automatically delete head branches" on.
- Wiki and Projects off; Issues on.
- Repository variable `RELEASES_ENABLED` = `false` (publishing off until the first package moves).

## Rulesets (done)

Both rulesets: active, no bypass (not even the release bot); no deletion, no force push; pull request with 1 approval, review from Code Owners (`.github/CODEOWNERS`) and an extra approval for unattributed Copilot pull requests; squash only; required checks `ci-ok` and `pr-title`; branches need not be up to date before merging (`main` CI runs after every merge).

- `main`: the default branch.
- `release-lines`: pattern `release/*-*.*.x`.

Organization rulesets also apply to `main` (pull request, no deletion, no force push, Copilot review).

`sonarcloud`, `Analyze (swift)`/`Analyze (actions)` and `Slack PR summary` stay advisory. Add Sonar and CodeQL to the required checks once they are green with real packages.

## Release bot

GitHub App `rudderstack-github-actions` installed on this repository with Contents and Pull requests (read and write). Whether it also needs Issues: write is checked separately.

| Where | Name | Value | Used by | Status |
|---|---|---|---|---|
| Organization variable | `RELEASE_APP_CLIENT_ID` | the App's client ID | every workflow that mints the App token | done (organization) |
| Organization secret | `RELEASE_PRIVATE_KEY` | the App's private key | Release Please, Publish Package, Tag & Release Packages, Abandon Unpublished Version, Create Maintenance Branch, Set Current Release Version, release sanity | done (organization) |
| Dependabot secrets | `RELEASE_PRIVATE_KEY` | the same private key | `dependabot-sync.yml` (Dependabot runs see only Dependabot secrets) | before the first package import |

Environment `spm-release` (no reviewers, no branch policy) is the release workflows' environment; it holds the release Slack webhook.

Release sanity (the SDK's e2e suite) also needs the App installed on `rudderlabs/rudder-mobile-sdk-test` with **Actions: write**, as for `rudder-sdk-swift` today. Without it the sanity job only warns; it never fails a release.

## Slack (done)

Two webhooks, so release and PR messages can go to different channels later. For now both hold the webhook `rudder-sdk-swift` uses today (`SLACK_WEBHOOK_URL` there).

| Where | Secret | Messages |
|---|---|---|
| Environment `spm-release` | `SLACK_RELEASE_WEBHOOK_URL` | a released package (after its customer install check passed); Tag & Release Packages left something incomplete |
| Environment `notifications` | `SLACK_PR_WEBHOOK_URL` | every PR validation run, passed or failed |

Environment secrets, not repository secrets: Release Please and Tag & Release Packages call Publish Package, and a called workflow gets repository secrets only when the caller passes them; its job's environment secrets it always gets. A missing webhook or a failed post is a warning only; it never fails a job.

## SonarCloud and CodeQL

- SonarCloud: off until the repository variable `SONARCLOUD_ENABLED` is `true`; the `sonarcloud` job is skipped until then. Before turning it on, create the project `rudderlabs_rudder-monorepo-swift` in organization `rudderlabs` (Analyze new project) and turn Automatic Analysis off (CI runs the scan). `SONAR_TOKEN` is an organization secret. Until `Packages/` or `Integrations/` exists, the `sonarcloud` job skips the scan; after that, a missing project fails the job.
- CodeQL: keep GitHub's **default** CodeQL setup disabled (Settings → Code security), or `codeql.yml` cannot upload results.
