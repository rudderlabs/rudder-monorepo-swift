# RudderStack Swift SDK monorepo

The Swift SDK (`RudderStackAnalytics`) and its integrations are developed and released here.
Customers keep installing each package from its own public repository with Swift Package Manager; every release reaches that repository through a reviewed bot PR, and Tag & Release Packages then creates its public tag and GitHub Release.

The repository starts with no packages: each one arrives with its import (`make import-integration`), and releases stay off until `RELEASES_ENABLED` is `true`.

## Getting started

1. Clone this repository.
2. Run `make prepare` once per clone: it checks Xcode 16+, Python 3.9+, SwiftLint and git-filter-repo (with install hints), turns on the repository git hooks (`core.hooksPath`, this clone only) and resolves the vendor packages. It prints `Ready`; re-running it is safe.
3. Open `Package.swift` in Xcode. There is no root `Package.swift` until the first package is imported; until then the repository holds only the release tooling.

## Branch model

Use `main` for source and Release Please; maintenance lines `release/<key>-X.Y.x` patch an older version line.
Source merges do not publish packages. Only approved releases update the public package repositories.
See [release boundaries and acceptance checks](docs/release-boundaries/README.md).
Every change lands through a reviewed PR. Publication updates use bot-created PRs on the public repositories; after merge, Tag & Release Packages verifies and tags the approved export.
See [reviewed publication](docs/reviewed-publication/README.md).
Plain version tags identify published SwiftPM packages.
Remote publication is gated by the `RELEASES_ENABLED` repository variable.

## Run the complete local rehearsal

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

## Structure

| Path | Role |
| --- | --- |
| `Tests/Fixtures/demo` | Demo SDK, Sprig, Firebase and shared code, used as test data only |
| `release/packages.json` | The only package list: paths, components, targets, platforms and dependency policies |
| `release/allowlist.json` | Reviewed write targets (package key to repository); a key without a package is reserved |
| `release/texts.json` | The only source of Release, bot PR and commit texts (rendered by `scripts/release_notes.py` from each package's CHANGELOG.md) |
| `release/templates` | Generated CONTRIBUTING.md, `.github/CODEOWNERS` and README block added to every export |
| `Makefile` | Developer commands (`make prepare`, `make sync`, `make check`, `make test`, `make affected`, `make lint`, `make new-integration`, `make import-integration`); thin wrappers over `scripts/` |
| `scripts/git-hooks` | `pre-commit` (marker sync for `Package.swift`, `release/` and `Shared/` commits; SwiftLint), `commit-msg` (PR-title rules), `pre-push` (branch name; from a terminal, CI's plan since `origin/main` without dependents: `make test PKG=<key>` per package the branch changed (CI also tests their dependents), `make test-python` for tooling changes, nothing for docs; no fetch, so `git fetch origin` first; `SKIP_PRE_PUSH_TESTS=1 git push` skips only the tests). Each runs the global hook of the same name first |
| `scripts/ci_plan.py` | CI plan and `make affected`: which packages to test and export, and whether the policy job runs |
| `scripts/package_ci.py` | PR CI jobs and `make test`/`make lint`: iOS Simulator tests, export check, lint, scope hint, `ci-ok` |
| `scripts/ci/pick-simulator.sh` | First available iPhone on the newest iOS runtime (no hardcoded device) |
| `scripts/scaffold.py` | `make new-integration`: a new package with its inventory, Release Please and root `Package.swift` entries |
| `scripts/import_package.py` | `make import-integration`: imports a repository at a tag, or at a later non-code-only `REF` (history or snapshot), without a Release Please entry |
| `scripts/dependabot_sync.py` | Releasable title for a Dependabot PR whose markers changed (`dependabot-sync.yml`) |
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

## Developer path

1. Change canonical source in this repository on a `<type>/<name>` branch (for example `fix/sprig-empty-traits`).
2. Commit. With `make prepare` done, the pre-commit hook runs the matching sync when the commit stages `Package.swift`, `release/packages.json`, `release/allowlist.json` or `Shared/` and adds the regenerated markers and generated files to the same commit; other commits run no sync. Without the hooks, run `make sync` and include its changes yourself (CI rejects stale markers).
3. Run `make check test` (the CI policy checks, the Python tests and the iOS Simulator package tests; `make test PKG=sprig` runs one package). `make affected` previews which packages the branch changes; `make lint` runs SwiftLint on the changed files.
4. Review the affected integration paths in the commit.
5. Let Release Please prepare versions, Swift version constants, and changelogs.

Commit messages and PR titles: `<type>(<optional scope>)<optional !>: <description>` with types `feat` `fix` `refactor` `perf` `style` `test` `docs` `chore` `build` `ci` `revert`, a description that starts lowercase and has no trailing period, at most 100 characters (`Merge …` and `Revert "…"` are allowed). The `commit-msg` hook and the `pr-title` check apply the same rules. The scope is cosmetic: folders decide what releases, and `scope-hint` only warns when the scope names a package the PR does not touch.

### PR checks

`ci.yml`: `policy` (the `make check` policy checks and the Python tests with `RUN_SWIFT_BUILD_TESTS=1`), `lint` (SwiftLint `--strict` with the root `.swiftlint.yml`; `Tests/`, `Examples/` and manifests are excluded, so the fixtures are not linted), one `test (<key>)` job per package (`xcodebuild test` on the iOS Simulator; a scheme written into the git-ignored `.swiftpm/` for the run holds only that package's test targets, so the job builds only what it tests) and one `export (<key>)` job per package (export, manifest check, generic iOS build). The package jobs are skipped while `release/packages.json` is empty. `ci-ok` needs all of them and fails if any failed or was cancelled; a skipped job passes.
A pull request runs only what it affects (`ci_plan.py --base <sha>`, D34; try it locally with `--base origin/main`). A push runs only what changed since the branch's previous commit (`ci_plan.py --before <sha>`, the same rules), and every job for every package when that commit is unknown (a new branch, or a force push the checkout lacks). A package folder (or the shared code it vendors) tests and exports that package, and also tests every package that depends on it, so an SDK change tests every integration. A `release/packages.json` change is compared entry by entry with the PR base: an added, removed or changed package entry selects that package the same way (tested with its dependents, exported alone), a change outside `packages` (for example `schemaVersion`) or a file missing at the base selects every package, and a reformat or reorder selects none. Shared build inputs (root `Package.swift`/`Package.resolved`, `.swiftlint.yml`, `release/allowlist.json`, `ci.yml`, `scripts/ci/` and the package-job runner `package_ci.py` with the scripts it imports) select every package, while a change to the plan itself (`ci_plan.py`, `release_plan.py`, the git hooks or `Makefile`) runs only `policy`; `LICENSE` and `release/templates/` re-export every package without tests; docs (`*.md`, `docs/`) select none. `policy` runs only when `scripts/`, `release/`, `Tests/`, `.github/`, `Shared/`, `Makefile`, the root manifest or lock file, a `dependency-requirements.json`/`shared-source.json` marker or the Release Please files change. `lint` always runs.
Advisory jobs outside `ci-ok`: `sonarcloud` (SonarCloud on the existing package folders; nothing to scan before the first import; skipped until the repository variable `SONARCLOUD_ENABLED` is `true`) and `Slack PR summary` (one Slack message per PR run, passed or failed, with the failed job names; it never changes a check result).
`codeql.yml`: CodeQL for the workflows, and for Swift once the root `Package.swift` exists (every package built for the iOS Simulator); advisory until it is green with real packages.
`pr-title.yml`: `pr-title` (`rudderlabs/github-action-check-pr-title` v2, as in `rudder-sdk-swift`; a subject must not start with a capital letter) and the warning-only `scope-hint`.
Both workflows also run on PRs into maintenance branches `release/<key>-X.Y.x`, and `ci.yml` on pushes to them.
Required status checks on `main` and in the `release-lines` ruleset (`release/*-*.*.x`; an admin sets them): `ci-ok` and `pr-title` only, because the matrix job names change as packages are added.

The root `Package.swift` is the development manifest for every package. Its `// @integrations-products`, `// @integrations-dependencies` and `// @integrations-targets` anchors mark where the commands below add lines (the core SDK sits above them); the first command creates the manifest if it is missing.

- **New integration (Path B):** `make new-integration NAME=Braze [PLATFORMS="iOS 15,tvOS 15"] [SDK_MIN=2.0.0] [VENDOR_URL=… VENDOR_PRODUCTS=… VENDOR_FROM=…]`. The key (`braze`) must already be in `release/allowlist.json` (sdk_team approval). It writes `Integrations/Braze/` (source and test templates, `version.txt`, `CHANGELOG.md`, `README.md`), the inventory entry (platforms default `iOS 15`, `sdkMinimum` default the SDK's current version), the Release Please config entry and the root manifest lines, then runs `make sync`. The version placeholder is `0.0.0` with no manifest entry, so the first release PR is `1.0.0` (no `Release-As`).
- **Import (Path A):** `make import-integration REPO=integration-swift-sprig TAG=2.0.0 NAME=Sprig MODE=history|snapshot` (`KIND=core` for the SDK, into `Packages/<Name>`). History mode clones with `--no-local`, rewrites the clone under the package folder with `git filter-repo` (old tags become `legacy/<key>/<tag>` and stay out of the monorepo) and starts a merge of the tag with `--allow-unrelated-histories`; snapshot mode copies the files at the tag. Both remove nested `Package.swift`, `Package.resolved`, `.swiftpm/`, `.github/`, root Xcode projects and per-repository license, CODEOWNERS and hook files, move `Example(s)/` to `Examples/<Name>/` (local package references point at the monorepo root), and add the version files, the inventory entry (version from the tag, `sdkMinimum` from the imported `rudder-sdk-swift` requirement) and the root manifest lines. There is no Release Please entry. The result is staged, never committed or pushed; the command prints the commit and the three Path A steps (import PR with a merge commit for history, anchor tag `<component>-<tag>`, `build(<key>): enable releases`). History mode needs `git-filter-repo`. `REF=<branch-or-sha>` (e.g. `REF=main`) imports that commit instead of the tag, at the tag's version: the tag must be an ancestor of `REF`, nothing under `Sources/` or outside the non-code allowlist (`*.md`, `LICENSE*`, `CODEOWNERS`, `.github/`, `docs/`, `.gitignore`) may differ, and a changed `Package.swift` must dump the same products, targets, dependencies, platforms and tools version; otherwise the import fails before the monorepo changes. The differing non-code files are printed and belong in the import PR body.
- `dependabot-sync.yml` runs `make sync` on a Dependabot PR that changes `Package.swift`, pushes the markers with the release bot token (`RELEASE_PRIVATE_KEY` stored as a Dependabot secret) and retitles the PR, for example `fix(firebase): bump firebase-ios-sdk to 13.0.0`.

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
Before any publication write, the publisher builds the exported package with `xcodebuild` for every declared platform (generic device destinations, unsigned, anonymous, temporary caches), plus a host `swift build` when the package declares macOS. PR CI builds only the iOS Simulator. A takeover builds nothing: it republishes the code already public at the existing tag, so it checks identity (byte-identical `Sources/`, same `Package.swift` meaning); the next release runs every build.
Resources keep their `process` or `copy` rule from `swift package dump-package`. Folder resources are copied whole and listed by relative path in the inventory.

## Maintainer path

Release Please targets `main` and owns version intent. It opens one release PR per package, so a package can be released alone, and creates component tags such as `swift-sdk-2.0.1` in the source repository.
Release how-tos (release one package alone, `Release-As`, roll forward a bad version, discard an unpublished version): [Maintainer how-tos](docs/reviewed-publication/README.md#maintainer-how-tos).
The publisher emits plain tags such as `2.0.1` in the corresponding public package repository.
Dependent integrations wait until their required SDK tag is available. Tag & Release Packages resumes pending publication.
An integration-only release skips the SDK job.
`release-please.yml` turns the path-based Release Please outputs into a plan (`release_plan.py from-outputs`): a `publish (swift-sdk)` job, then one matrix job with a `publish (<key>)` leg per released integration. No workflow lists package names.
Publication jobs take destinations only from `release/allowlist.json` (every package must be allowlisted with its own repository), use an environment-scoped App token, and run in one concurrency group per package.
Adding a package needs only its `release/packages.json` entry, its allowlist entry, and the regenerated GitHub files; `make new-integration` and `make import-integration` write them.
A retry must use the original source SHA and version. A newer SHA cannot reuse the same version.
The manual `publish.yml` run also resumes a release if Release Please outputs are absent on rerun.

**Merged a bot PR? Run Tag & Release Packages** (`complete-publication.yml`, Actions → Run workflow, no inputs): every run scans all packages, tags merged versions and creates their Releases. A broken item is reported and skipped; the others still complete. An open bot PR stays `awaiting_review` and is never rebuilt.
Package states: `awaiting_review`, `awaiting_dependency`, `awaiting_takeover`, `published`, `incomplete`.
A public repository without `.publication.json` waits as `awaiting_takeover` (other packages continue) until a person removes `.github/workflows` by PR and dispatches `publish.yml` with `mode=takeover`: one bot PR, no tag, `Sources/` byte-identical to the existing tag and `Package.swift` semantically equal. A README-only repository gets a bootstrap bot PR automatically (`mode=bootstrap` forces it).
**Set Current Release Version** (`anchor-package.yml`; manual: package, version, main SHA) creates a plain `<component>-<version>` tag and no Release, so nothing is queued or published.
Every export adds a generated CONTRIBUTING.md, `.github/CODEOWNERS` (`* @rudderlabs/sdk_team`) and a README block (`release/templates/`). While this repository is internal, they send outside users to the public repository's own Issues and accept no pull requests; once it is public, they point to this repository instead (a template change re-exports every package, so it ships with each next release). `.publication.json` records a `transform` per file. No workflow file is ever exported.
Slack (`scripts/slack_notify.py`, texts in `release/texts.json`, no run links): one message per released package after its customer install check passes, and one from Tag & Release Packages only when something is left incomplete. Release messages use `SLACK_RELEASE_WEBHOOK_URL`, PR messages `SLACK_PR_WEBHOOK_URL`, so they can move to different channels without a code change. A missing webhook or failed post never fails a job.
Release sanity (`release-sanity.yml`, the SDK's e2e suite in `rudderlabs/rudder-mobile-sdk-test`) runs for `swift-sdk` only, once per release, before the release: when the bot opens the SDK publish PR it tests branch `publication/swift-sdk/<version>` of the public repository, which is exactly what customers get. It is advisory: **check its result before merging the SDK publish PR.** There is no post-release run (same code; the customer check covers the tag).
Admin setup (variables, environments, secrets, rulesets): [docs/production-setup.md](docs/production-setup.md).
Bot commits use the App identity `rudderstack-github-actions[bot]`; a merged version is verified against its own stored `.publication.json`, so Tag & Release Packages survives exporter changes.

## Customer path

After a publication, `scripts/verify_public_customer.py <package> <version> <evidence-dir>` generates a throwaway SwiftPM package that depends on the public URL at that exact version and imports the package's target.
It builds it anonymously with xcodebuild on iOS Simulator and macOS, each only where the package declares the platform (Sprig: iOS only); tvOS and watchOS are not checked.
Versions are checked through the `Package.resolved` pin, since the SDKs keep version constants internal; `customer-result.json` and `Package.resolved` are the evidence.
