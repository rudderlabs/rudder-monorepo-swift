# Development guide

The details behind the commands in the [README](../README.md): branches, git hooks, CI, adding packages, shared code, export, and the local release rehearsal.

## Branch model

Use `main` for source and Release Please; maintenance lines `release/<key>-X.Y.x` patch an older version line.
Source merges do not publish packages. Only approved releases update the public package repositories.
See [release boundaries and acceptance checks](release-boundaries/README.md).
Every change lands through a reviewed PR. Publication updates use bot-created PRs on the public repositories; after merge, Tag & Release Packages verifies and tags the approved export.
See [reviewed publication](reviewed-publication/README.md).
Plain version tags identify published SwiftPM packages.
Remote publication is gated by the `RELEASES_ENABLED` repository variable.

## Git hooks and commit rules

`make prepare` sets `core.hooksPath` to `scripts/git-hooks` for this clone only. Each hook runs the global hook of the same name first.

- `pre-commit`: when the commit stages `Package.swift`, `release/packages.json`, `release/allowlist.json` or `Shared/`, it runs the matching sync and adds the regenerated markers and generated files to the same commit; other commits run no sync. It also runs SwiftLint. Without the hooks, run `make sync` and include its changes yourself (CI rejects stale markers).
- `commit-msg`: the PR-title rules below.
- `pre-push`: checks the branch name. From a terminal, it also runs CI's plan since `origin/main`, without dependents: `make test PKG=<key>` per package the branch changed (CI also tests their dependents), `make test-python` for tooling changes, nothing for docs. It does not fetch, so `git fetch origin` first. `SKIP_PRE_PUSH_TESTS=1 git push` skips only the tests.

Commit messages and PR titles: `<type>(<optional scope>)<optional !>: <description>` with types `feat` `fix` `refactor` `perf` `style` `test` `docs` `chore` `build` `ci` `revert`, a description that starts lowercase and has no trailing period, at most 100 characters (`Merge …` and `Revert "…"` are allowed). The `commit-msg` hook and the `pr-title` check apply the same rules. The scope is cosmetic: folders decide what releases, and `scope-hint` only warns when the scope names a package the PR does not touch.

## PR checks

`ci.yml`: `policy` (the `make check` policy checks and the Python tests with `RUN_SWIFT_BUILD_TESTS=1`), `lint` (SwiftLint `--strict` with the root `.swiftlint.yml`; `Tests/`, `Examples/` and manifests are excluded, so the fixtures are not linted), one `test (<key>)` job per package (`xcodebuild test` on the iOS Simulator; a scheme written into the git-ignored `.swiftpm/` for the run holds only that package's test targets, so the job builds only what it tests) and one `export (<key>)` job per package (export, manifest check, generic iOS build). Both package jobs, and the release builds and customer check in `publish.yml`, run on `macos-15`, or on the package's `runner` from `release/packages.json` (`macos-26`; `ci_plan.py` and `package_ci.py runner` read it). They use the oldest supported Xcode (`DEFAULT_XCODE` in `scripts/package_ci.py`), or the package's `xcode` from `release/packages.json` (`package_ci.py xcode` sets `DEVELOPER_DIR`; the job fails if that Xcode is not installed). `ci-ok` needs all of them and fails if any failed or was cancelled; a skipped job passes.

A pull request runs only what it affects (`ci_plan.py --base <sha>`; try it locally with `--base origin/main`). A push runs only what changed since the branch's previous commit (`ci_plan.py --before <sha>`, the same rules), and every job for every package when that commit is unknown (a new branch, or a force push the checkout lacks).

- A package folder (or the shared code it vendors) tests and exports that package, and also tests every package that depends on it, so an SDK change tests every integration.
- A `release/packages.json` change is compared entry by entry with the PR base: an added, removed or changed package entry selects that package the same way (tested with its dependents, exported alone), a change outside `packages` (for example `schemaVersion`) or a file missing at the base selects every package, and a reformat or reorder selects none.
- Shared build inputs (root `Package.swift`/`Package.resolved`, `.swiftlint.yml`, `release/allowlist.json`, `ci.yml`, `scripts/ci/` and the package-job runner `package_ci.py` with the scripts it imports) select every package.
- A change to the plan itself (`ci_plan.py`, `release_plan.py`, the git hooks or `Makefile`) runs only `policy`.
- `LICENSE` and `release/templates/` re-export every package without tests; docs (`*.md`, `docs/`) select none.
- `policy` runs only when `scripts/`, `release/`, `Tests/`, `.github/`, `Shared/`, `Makefile`, the root manifest or lock file, a `dependency-requirements.json`/`shared-source.json` marker or the Release Please files change. `lint` always runs.

Advisory job outside `ci-ok`: `sonarcloud` (SonarCloud on the package folders; skipped until the repository variable `SONARCLOUD_ENABLED` is `true`).
`pr-slack-summary.yml`: one Slack message per PR run, passed or failed, with the failed job names. It runs after PR Validation completes, with `main`'s workflow and scripts, never the PR's, and reads the PR and the job results from the GitHub API. It never changes a check result.
`codeql.yml`: CodeQL for the workflows and for Swift (every package built for the iOS Simulator); advisory.
`pr-title.yml`: `pr-title` (`rudderlabs/github-action-check-pr-title` v2; a subject must not start with a capital letter) and the warning-only `scope-hint`.
Both workflows also run on PRs into maintenance branches `release/<key>-X.Y.x`, and `ci.yml` on pushes to them.
Required status checks on `main` and in the `release-lines` ruleset (`release/*-*.*.x`): `ci-ok` and `pr-title` only, because the matrix job names change as packages are added.

## Adding a package

Add packages with these commands, never by hand. The root `Package.swift` is the development manifest for every package. Its `// @integrations-products`, `// @integrations-dependencies` and `// @integrations-targets` anchors mark where the commands add lines (the core SDK sits above them).

- **New integration:** `make new-integration NAME=Braze [PLATFORMS="iOS 15,tvOS 15"] [SDK_MIN=2.0.0] [VENDOR_URL=… VENDOR_PRODUCTS=… VENDOR_FROM=…]`. The key (`braze`) must already be in `release/allowlist.json` (sdk_team approval). It writes `Integrations/Braze/` (source and test templates, `version.txt`, `CHANGELOG.md`, `README.md`), the inventory entry (platforms default `iOS 15`, `sdkMinimum` default the SDK's current version), the Release Please config entry and the root manifest lines, then runs `make sync`. The version placeholder is `0.0.0` with no manifest entry, so the first release PR is `1.0.0` (no `Release-As`).
- **Import:** `make import-integration REPO=integration-swift-sprig TAG=2.0.0 NAME=Sprig MODE=history|snapshot` (`KIND=core` for the SDK, into `Packages/<Name>`).
  - History mode (needs `git-filter-repo`) clones with `--no-local`, rewrites the clone under the package folder with `git filter-repo` (old tags become `legacy/<key>/<tag>` and stay out of the monorepo) and starts a merge of the tag with `--allow-unrelated-histories`. Snapshot mode copies the files at the tag.
  - Both remove nested `Package.swift`, `Package.resolved`, `.swiftpm/`, `.github/`, root Xcode projects and per-repository license, CODEOWNERS and hook files, move `Example(s)/` to `Examples/<Name>/` (local package references point at the monorepo root), and add the version files, the inventory entry (version from the tag, `sdkMinimum` from the imported `rudder-sdk-swift` requirement) and the root manifest lines. There is no Release Please entry.
  - The result is staged, never committed or pushed; the command prints the commit and the three next steps (import PR with a merge commit for history, anchor tag `<component>-<tag>`, `build(<key>): enable releases`).
  - `REF=<branch-or-sha>` (e.g. `REF=main`) imports that commit instead of the tag, at the tag's version: the tag must be an ancestor of `REF`, nothing under `Sources/` or outside the non-code allowlist (`*.md`, `LICENSE*`, `CODEOWNERS`, `.github/`, `docs/`, `.gitignore`) may differ, and a changed `Package.swift` must dump the same products, targets, dependencies, platforms and tools version; otherwise the import fails before the monorepo changes. The differing non-code files are printed and belong in the import PR body.

Adding a package needs only its `release/packages.json` entry, its allowlist entry, and the regenerated GitHub files; both commands write them.

A Dependabot PR that changes `Package.swift` needs the release markers too: run `make sync` on its branch, push the result, and retitle the PR so the affected packages release, for example `fix(firebase): bump firebase-ios-sdk to 13.0.0`.

## Shared code, markers and export

Shared markers contain source hashes under each affected package path.
Release Please sees these path changes in the reviewed feature or fix commit.
CI rejects stale markers. No extra post-processing commit is added to a Release Please branch.
SDK-only work does not modify integration markers.
Each marker lists only the files of the shared targets that package vendors, so a change to one shared target selects only its vendoring integrations.
Shared code uses Swift's `package` access level, never `public` or `open`. `sync-shared` (and CI's `--check`) rejects a `public`/`open` declaration under `Shared/`, and export rejects it in vendored code.
Export removes imports of vendored modules (including `@_exported`/`@testable` and `import struct Module.Type` forms); each integration then owns a private copy, so two integrations in one app never collide.
`RUN_SWIFT_BUILD_TESTS=1` additionally builds two exported integrations and a consumer of both (offline, about 15 seconds; CI sets it).

The SDK minimum requirement is explicit in each integration's inventory entry.
Update that requirement in a coordinated release when an integration needs a new SDK API.
Export fails if a package has an `external` policy but no `sdkMinimum`.
Each inventory entry also sets its own `platforms` (for example `["iOS 15"]`) and `toolsVersion` (for example `"5.9"`).
The generated manifest uses exactly those, never the root manifest's values.
Resources keep their `process` or `copy` rule from `swift package dump-package`. Folder resources are copied whole and listed by relative path in the inventory.
Every export adds a generated CONTRIBUTING.md, `.github/CODEOWNERS` (`* @rudderlabs/sdk_team`) and a README block (`release/templates/`); a template change re-exports every package, so it ships with each next release. `.publication.json` records a `transform` per file. No workflow file is ever exported.

Before any publication write, the publisher builds the exported package with `xcodebuild` for every declared platform (generic device destinations, unsigned, anonymous, temporary caches), plus a host `swift build` when the package declares macOS. PR CI builds only the iOS Simulator. A takeover builds nothing: it republishes the code already public at the existing tag, so it checks identity (byte-identical `Sources/`, same `Package.swift` meaning); the next release runs every build.

## Release workflows

Release Please targets `main` and owns version intent. It opens one release PR per package, so a package can be released alone, and creates component tags such as `swift-sdk-2.0.1` in this repository. The publisher emits plain tags such as `2.0.1` in the corresponding public package repository.
`release-please.yml` turns the path-based Release Please outputs into a plan (`release_plan.py from-outputs`): a `publish (swift-sdk)` job, then one matrix job with a `publish (<key>)` leg per released integration. No workflow lists package names. An integration-only release skips the SDK job.
Dependent integrations wait until their required SDK tag is available. Tag & Release Packages resumes pending publication.
Publication jobs take destinations only from `release/allowlist.json` (every package must be allowlisted with its own repository), use an environment-scoped App token, and run in one concurrency group per package.
A retry must use the original source SHA and version. A newer SHA cannot reuse the same version.
The manual `publish.yml` run also resumes a release if Release Please outputs are absent on rerun.
Bot commits use the App identity `rudderstack-github-actions[bot]`; a merged version is verified against its own stored `.publication.json`, so Tag & Release Packages survives exporter changes.
Package states, takeover, bootstrap and anchors: [reviewed publication](reviewed-publication/README.md).

Slack (`scripts/slack_notify.py`, texts in `release/texts.json`, no run links): one message per released package after its customer install check passes, and one from Tag & Release Packages only when something is left incomplete. Release messages use `SLACK_RELEASE_WEBHOOK_URL`, PR messages `SLACK_PR_WEBHOOK_URL`, so they can move to different channels without a code change. A missing webhook or failed post never fails a job.

Release sanity (`release-sanity.yml`, the SDK's e2e suite in `rudderlabs/rudder-mobile-sdk-test`) runs for `swift-sdk` only, once per release, before the release: when the bot opens the SDK publish PR it tests branch `publication/swift-sdk/<version>` of the public repository, which is exactly what customers get. It is advisory: **check its result before merging the SDK publish PR.** There is no post-release run (same code; the customer check covers the tag).

## Customer check

After a publication, `scripts/verify_public_customer.py <package> <version> <evidence-dir>` generates a throwaway SwiftPM package that depends on the public URL at that exact version and imports the package's target.
It builds it anonymously with xcodebuild on iOS Simulator and macOS, each only where the package declares the platform (Sprig: iOS only); tvOS and watchOS are not checked.
Versions are checked through the `Package.resolved` pin, since the SDKs keep version constants internal; `customer-result.json` and `Package.resolved` are the evidence.

## Local release rehearsal

Requirements: macOS, Xcode, Swift 5.9 or later, Python 3.9 or later, and Git. No network or GitHub access is needed.
`--ios` also builds the customer check package (`verify_public_customer.py`) with xcodebuild for iOS Simulator and macOS; it needs the iOS Simulator platform installed in Xcode. No signing account is needed.

```sh
python3 -m unittest discover -s Tests -p 'test_*.py'
python3 scripts/rehearse.py          # about 4 minutes; --quick skips the xcodebuild platform builds
python3 scripts/rehearse.py --ios    # also the xcodebuild customer check
```

Each run copies `Tests/Fixtures/demo` into a throwaway monorepo under a new `.lab/<timestamp>/` folder (`.lab/latest.json` points to it; earlier runs are never reset), creates one local bare "public" repository per allowlisted package (SDK and Firebase README-only, Sprig with foreign files, `.github/workflows` and tag `0.1.1`), and runs the real `publication_queue.py` and `publish.py` code paths step by step. Each step stops the run with its name on the first failed check; `evidence.json` records every Tag & Release Packages result, job result and check.

| Step | Proves |
| --- | --- |
| 1 | A README-only repository gets a bootstrap bot PR; Tag & Release Packages never rebuilds the open PR; after merge it tags the merge commit and creates the Release |
| 2 | A foreign repository waits as `awaiting_takeover`; takeover refuses while `.github/workflows` exists, then (after a person removes it) opens one PR with `Sources/` byte-identical to the old tag; no tag moves |
| 3 | An integration release: export, build, bot PR, merge, Tag & Release Packages tags it with matching provenance and Release body |
| 4 | An integration-only release leaves the SDK repository untouched, and an SDK-only release leaves the integrations untouched |
| 5 | An integration that needs an unpublished SDK version waits as `awaiting_dependency`, then continues once the SDK tag exists |
| 6 | A broken source release (off `main`) is reported and skipped while another package completes in the same Tag & Release Packages run |
| 7 | A hand edit in a public repository blocks publication before any branch, PR or tag; after a reviewed revert it publishes |
| 8 | Running Tag & Release Packages again changes no ref, PR or Release |
| 9 | Old tags (SDK, the pre-monorepo Sprig tag, Firebase) resolve and run in clean consumers, one package at a time |

Real: Git commits, merges, branches and tags; pre-receive hooks that reject `main` pushes and tag moves; export; `swift build` and the `xcodebuild` platform builds; the `dump-package` takeover check; fresh SwiftPM consumers with no credentials.
Modeled: `gh` (repository identity, bot PRs, Releases) as local JSON through a `gh` shim on `PATH`; Release Please as version commits, component tags and source Release records; reviewed merges as a reviewer clone plus a server-side `main` update; the App bot user id; Swift Collections as a local stand-in tag. Every `github.com` URL is rewritten to the local bare repositories or to a path that does not exist.
Not covered: GitHub Actions, App permissions, rulesets, environments, Release Please itself, anonymous public access, and reverse sync (ingest is not implemented; step 7 reverts the hand edit instead).
`RUN_SWIFT_BUILD_TESTS=1` runs steps 0 to 3 (`--quick`) in the unit suite.

## Tooling reference

| Path | Role |
| --- | --- |
| `Tests/Fixtures/demo` | Demo SDK, Sprig, Firebase and shared code, used as test data only |
| `release/packages.json` | The only package list: paths, components, targets, platforms and dependency policies; an optional `xcode` (for example `"26.2"`) for a package whose vendor needs a newer Xcode than the default, and an optional `runner` (`macos-26`) when that Xcode is only on the newer runner image |
| `release/allowlist.json` | Reviewed write targets (package key to repository); a key without a package is reserved |
| `release/texts.json` | The only source of Release, bot PR and commit texts (rendered by `scripts/release_notes.py` from each package's CHANGELOG.md) |
| `release/templates` | Generated CONTRIBUTING.md, `.github/CODEOWNERS` and README block added to every export |
| `Makefile` | Developer commands (`make prepare`, `make sync`, `make check`, `make test`, `make affected`, `make lint`, `make new-integration`, `make import-integration`); thin wrappers over `scripts/` |
| `scripts/git-hooks` | `pre-commit`, `commit-msg` and `pre-push` (see [Git hooks and commit rules](#git-hooks-and-commit-rules)) |
| `scripts/ci_plan.py` | CI plan and `make affected`: which packages to test and export, and whether the policy job runs |
| `scripts/package_ci.py` | PR CI jobs and `make test`/`make lint`: iOS Simulator tests, export check, lint, scope hint, `ci-ok` |
| `scripts/ci/pick-simulator.sh` | First available iPhone on the newest iOS runtime (no hardcoded device) |
| `scripts/scaffold.py` | `make new-integration`: a new package with its inventory, Release Please and root `Package.swift` entries |
| `scripts/import_package.py` | `make import-integration`: imports a repository at a tag, or at a later non-code-only `REF` (history or snapshot), without a Release Please entry |
| `scripts/check_inventory.py` | CI check: package list, allowlist, Release Please entries, generated files and action SHA pins agree |
| `scripts/generate_github.py` | Regenerates issue forms and the `package` dropdowns of manual workflows from the package list (`--check` in CI) |
| `scripts/project.py` | Graph inspection and deterministic standalone export |
| `scripts/publish.py` | Build validation, immutable tag publication, drift check, resuming pending publication; `--mode` normal, takeover or bootstrap |
| `scripts/reviewed_publication.py` | Bot PRs, takeover and bootstrap checks, merged-version verification from stored provenance |
| `scripts/release_notes.py` | Release and publish-PR notes from the package CHANGELOG.md section, in the standalone repositories' format |
| `scripts/discard_version.py` | Abandon Unpublished Version: discards a version without a public tag (public PRs, monorepo rollback PR, Release and tag) so its number is released again |
| `scripts/publication_queue.py` | Tag & Release Packages queue: reports and skips a broken item, never rebuilds an open bot PR |
| `scripts/anchor.py` | Validates an anchor tag request for `anchor-package.yml` |
| `scripts/release_plan.py` | Affected package selection and reviewed shared-source markers |
| `scripts/rehearse.py` | Offline lifecycle rehearsal on temporary fixture repositories (`.lab/<timestamp>/`) |
| `.github/workflows` | PR CI (`ci.yml`, `pr-title.yml`), gated release, reviewed publication, Tag & Release Packages and the other manual workflows |
