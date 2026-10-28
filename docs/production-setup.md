# Repository setup (admin)

What an admin configures once in `rudderlabs/rudder-monorepo-swift` before CI and releases can run.
Names must match exactly: the workflows read them as written here.

## Settings (done)

- Merges: squash only, message "Pull request title and description"; "Always suggest updating pull request branches" on; "Automatically delete head branches" on.
- Wiki and Projects off; Issues on.
- Repository variable `RELEASES_ENABLED` = `false` (publishing off until the first package moves).

## Rulesets (after the first CI run, so the checks exist)

- `main`: pull request + 1 approval + review from Code Owners; required checks `ci-ok` and `pr-title`; no bypass for the release bot.
- `release-lines` (pattern `release/*-*.*.x`): no deletion, no force push, pull request + 1 approval + Code Owners, squash only, required checks `ci-ok` and `pr-title`.
- `sonarcloud`, `Analyze (swift)`/`Analyze (actions)` and `Slack PR summary` stay advisory. Add Sonar and CodeQL to the required checks once they are green with real packages.

## Release bot

GitHub App `rudderstack-github-actions` installed on this repository with Contents and Pull requests (read and write). Whether it also needs Issues: write is checked separately.

| Where | Name | Value | Used by |
|---|---|---|---|
| Repository variable | `RELEASE_APP_CLIENT_ID` | the App's client ID | every workflow that mints the App token |
| Environment `spm-release` (no reviewers, no branch policy) | secret `RELEASE_PRIVATE_KEY` | the App's private key | Release Please, Publish Package, Tag & Release Packages, Abandon Unpublished Version, Create Maintenance Branch, Set Current Release Version, release sanity |
| Dependabot secrets | `RELEASE_PRIVATE_KEY` | the same private key | `dependabot-sync.yml` (Dependabot runs see only Dependabot secrets) |

Release sanity (the SDK's e2e suite) also needs the App installed on `rudderlabs/rudder-mobile-sdk-test` with **Actions: write**, as for `rudder-sdk-swift` today. Without it the sanity job only warns; it never fails a release.

## Slack

Two webhooks, so release and PR messages can go to different channels later. For now both hold the webhook `rudder-sdk-swift` uses today (`SLACK_WEBHOOK_URL` there).

| Where | Secret | Messages |
|---|---|---|
| Environment `spm-release` | `SLACK_RELEASE_WEBHOOK_URL` | a released package (after its customer install check passed); Tag & Release Packages left something incomplete |
| Environment `notifications` | `SLACK_PR_WEBHOOK_URL` | every PR validation run, passed or failed |

A missing webhook or a failed post is a warning only; it never fails a job.

## SonarCloud and CodeQL

- SonarCloud: create the project `rudderlabs_rudder-monorepo-swift` in organization `rudderlabs`; environment `sonarcloud` with secret `SONAR_TOKEN`.
- CodeQL: keep GitHub's **default** CodeQL setup disabled (Settings → Code security), or `codeql.yml` cannot upload results.
