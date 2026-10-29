# Reviewed publication

The existing `rudderstack-github-actions` GitHub App creates publication PRs.
No new GitHub App or branch-rule bypass is required.
The App needs Contents write and Pull requests write on the publication repositories in `release/allowlist.json`; each import adds its repository.
The normal Actions token remains Contents read.

## Release flow

1. Merge the package's Release Please PR in the source repository (one PR per package, see [Release one package alone](#release-one-package-alone)).
2. Record the component version and full source commit SHA.
3. Export and build the standalone package from that source snapshot.
4. Push the generated files to `publication/<package>/<version>`.
5. Open the publication PR through the existing App token.
6. Review and merge the publication PR under the existing branch rules.
7. Run Tag & Release Packages (`complete-publication.yml`, the central completion workflow) after merge.
8. Verify the exact merge commit against its stored provenance.
9. Create the plain version tag at that verified merge commit.
10. Create the public GitHub Release.
11. Test an anonymous customer install with a generated SwiftPM package built for iOS Simulator and macOS.

Step 7 is manual. **Merged a bot PR? Run Tag & Release Packages.** It has no inputs and scans all packages.
Bot commits are authored as `rudderstack-github-actions[bot]` with the App's noreply email; `publish.yml` looks up the bot user id at runtime and the publisher refuses any other identity.
All PR, commit and Release texts come from `release/texts.json` and follow the standalone repositories: commit and PR title `chore(release): <version>`, Release title `<version>`. The Release body is `# <title> <version>` (`title` in `release/packages.json`, default the target), the package's CHANGELOG.md section for the version as `## Features`/`## Bug Fixes`/... with full monorepo PR links, `## What's Changed` (PR title and author from the GitHub API; best effort, omitted on any API error), `**Full Changelog**` against the previous version tag, and a `Source: monorepo commit` footer. The publish PR body repeats the heading and sections, then lists the built platforms.
An existing Release only has to be the single non-draft Release for its tag: the tag and its `.publication.json` carry the provenance, so Releases created with earlier texts (or edited by hand) still complete.
The source workflow holds the credentials. Publication repositories need no relay workflow or secrets.
This central workflow replaces the proposed per-repository merge-event relay.

Source component releases are durable release intent. The completion workflow discovers incomplete publication from these releases.
It does not require transient Release Please action outputs, a PR comment, or a new source change.
Completed tag/release pairs are excluded from the completion queue.
SDK work precedes integration work in the queue. Each integration also checks its required SDK tag before building.
An integration that needs an unpublished SDK reports `awaiting_dependency` and resumes on a later check.
The completion workflow reports and skips a broken item (as `incomplete`) instead of failing the whole queue, and never rebuilds an item whose bot PR is still open (`awaiting_review`).

## Publication boundaries

An open publication PR creates no public version tag or GitHub Release. Publication `main` keeps the previous package.
After the reviewed merge, branch-based customers can see the generated update before its tag exists.
This short interval is inherent in the reviewed PR route. Version-based customers remain on their selected immutable tags.
Source `main` can advance without entering the export. Publication `main` can advance without changing the selected merge commit.
A tag always identifies the verified merge commit, not whichever commit is currently at `main`.

Before merge, the publisher compares the PR's file hashes and complete provenance record with a new deterministic export.
Updating an open PR's hashes together with an unauthorized file change does not bypass this comparison.
After merge (and for an existing tag), the version is verified against its own stored `.publication.json`: every file hash and the package, version and source commit (D25). It is not re-exported, so completion runs and re-runs survive exporter changes. The reviewed merge is the gate for the merged content.
It checks PR bot identity, allowlisted destination, source ancestry, and merged commit ancestry.
A closed, unmerged PR, a conflicting version branch, manual drift, or an existing tag conflict stops publication.
The publisher never force-pushes a publication branch or rewrites a version tag.

## States

| State | Meaning | What to do |
| --- | --- | --- |
| `awaiting_review` | Valid generated PR exists; no tag is created | Review and merge; completion runs later |
| `awaiting_dependency` | Required SDK tag is unavailable | Complete SDK publication; run Tag & Release Packages again |
| `awaiting_takeover` | Public repository has no `.publication.json` and is not README-only, or takeover found `.github/workflows` | Remove `.github/workflows` by PR, dispatch `mode=takeover`, merge the bot PR, run Tag & Release Packages |
| `published` | Served version tag and public Release are verified | No further publication write |
| `incomplete` | Build, verification, API, or publication failed | Inspect evidence; retry the original source SHA and version |

The batch status is `awaiting_publication` when packages are waiting. Waiting does not count as customer success.
An interruption after branch push reuses the matching branch. An interruption after PR creation reuses the matching PR.
An interruption after merge tags the verified merge commit. An interruption after tagging repairs only the missing Release.
A failed customer build fails the workflow, while publication evidence records any already served tag.
Rerun that failed publisher job or dispatch `publish.yml` with the original source SHA and version to repeat customer verification.
Do not move a public tag to repair a customer failure.

The anonymous customer check generates a disposable SwiftPM package that depends on the published version exactly and imports its target.
xcodebuild builds it on iOS Simulator and macOS where the package supports them; tvOS and watchOS are not checked.
It records the built platforms and the resolved `Package.resolved` pins.

## Takeover, bootstrap and anchors

`publish.yml` takes `mode`: `normal` (default), `takeover` or `bootstrap`.
- A repository with `.publication.json` publishes normally. A README-only repository (README, maybe LICENSE and `.gitignore`) gets a bootstrap bot PR that replaces it with the export; after merge, Tag & Release Packages tags it.
- Any other repository is `awaiting_takeover`. Other packages continue.
- `mode=takeover` opens one bot PR on `takeover/<key>/<version>` at the existing public tag `<version>`. It removes every non-generated file and adds the export. Before the PR it checks `Sources/` byte-identical to that tag (only a missing `Version.swift` may be added) and `Package.swift` semantically equal with `swift package dump-package` (products, targets, platforms, dependency requirements). The PR body lists the removed files and the allowed differences. No tag or Release is created; after merge the package publishes normally.
- If `.github/workflows` exists, takeover refuses with "Remove .github/workflows by PR first" and the package stays `awaiting_takeover` (D31). The bot never writes or deletes workflow files and needs no Workflows permission.

Every export adds a generated CONTRIBUTING.md, `.github/CODEOWNERS` (`* @rudderlabs/sdk_team`) and a README block (`release/templates/`). All are hashed in provenance; `copiedFiles` records a `transform` per file (`copy`, `vendored-strip-import`, `generated`).

While this monorepo is internal, outside users report issues in each public package repository (Issues stay on there) and the public repositories accept no pull requests (Pull request creation "Collaborators only"), so they change only through bot publish PRs. Once this monorepo is public, its open issues move here, the public repositories turn Issues off, and `release/templates/` points to this repository; that template change re-exports every package, so each package's next release carries the new text.

**Set Current Release Version** (`anchor-package.yml`; manual: package, version, full `main` SHA) validates the package against the allowlist and package list, the SemVer version against `version.txt` at that commit, and the SHA on `main`, then creates the plain tag `<component>-<version>`. It creates no GitHub Release, so the completion queue never sees it, and no workflow starts on a tag.

## Maintainer how-tos

### Release one package alone

Release Please opens one release PR per package (`"separate-pull-requests": true` in `release-please-config.json`), for example `chore(release): swift-sdk 2.0.1` on branch `release-please--branches--main--components--swift-sdk` and `chore(release): integration-sprig 2.0.1` on `release-please--branches--main--components--integration-sprig`. The title comes from `pull-request-title-pattern`, matching rudder-sdk-swift's `chore(release): …` style. Each PR holds only its package's version files, CHANGELOG and manifest line.
Merge only the PR of the package you want to release; the others stay open and are rebuilt on the next push to `main` (`"always-update": true`: every open release PR is rebuilt from the current `main`, so the shared manifest line never conflicts after another release PR merges). `release-please.yml` then plans only the merged package: merging only the Sprig PR runs one `publish (sprig)` leg and skips `publish (swift-sdk)`. Merging the SDK PR releases only the SDK; merge each integration's own PR when it should follow.
An integration whose `sdkMinimum` needs an unreleased SDK waits as `awaiting_dependency` until the SDK is published, so merge the SDK PR first in a coordinated release.

### Override the next version with Release-As

Release Please normally picks the next version from the commit types (`fix` a patch, `feat` a minor, `!` a major). To choose it yourself, end the squash commit message on `main` with the footer:

```text
fix(sprig): send the session id on identify

Release-As: 2.1.0
```

Put the footer in the commit message box of the squash-merge dialog (the extended description), as its last paragraph, and check it is there before you confirm. Release Please reads it from the commit body on `main`, not from the PR description.
The footer applies to every package whose folder the commit changes, and each of those packages' release PRs proposes that version. A commit that changes no file at all (an empty commit) applies to every package; a commit that changes only files outside the package folders (for example `docs/` or `scripts/`) applies to none.
To target one package, make the commit change only files under that package's folder (for example `Integrations/Sprig/`). The commit needs a type with a visible CHANGELOG section (`feat`, `fix`, `perf`, `refactor`, `chore`): Release Please skips a package whose notes would be empty, so a `docs:` or `test:` commit opens no release PR.
The alternative is a temporary `"release-as": "2.1.0"` inside that package's entry under `packages` in `release-please-config.json`. It works in manifest mode and targets exactly one package, but it still needs a releasable commit in that folder, and it keeps forcing that version until it is removed: remove it in a follow-up PR right after the release PR merges. Prefer the footer.

### Roll forward a bad published version

Never delete or move a public tag: the tag ruleset makes version tags immutable, and SwiftPM customers may already have resolved it. Publish a fixed version instead.

1. In this monorepo, undo the bad change with a `fix:` commit that changes only the affected package's folder, for example `fix(sprig): revert the session id change from 2.0.1`. Do not merge GitHub's `Revert "…"` title as-is: `revert` is a hidden type here and opens no release PR.
2. Merge the package's release PR (a patch, for example `2.0.2`), review and merge the publication PR, then run Tag & Release Packages.
3. Mark the bad version in the public repository's GitHub Release. Keep it a published (non-draft) Release, because completion expects one non-draft Release per tag. Prepend the warning to the existing notes:

```sh
REPO=rudderlabs/integration-swift-sprig BAD=2.0.1 GOOD=2.0.2
gh release view "$BAD" --repo "$REPO" --json body --jq .body > notes.md
{ printf '> ⚠️ Withdrawn — use %s\n\n' "$GOOD"; cat notes.md; } > withdrawn.md
gh release edit "$BAD" --repo "$REPO" --notes-file withdrawn.md
```

Customers on `from: "2.0.1"` get `2.0.2` with their next package update; customers pinned to `exact: "2.0.1"` must change the pin.

### Patch an older version line

Example: customers are on SDK 2.0.x and `main` has released 2.1.0. Ship a fix as 2.0.2 without the 2.1 changes. Integrations work the same way (for example `release/sprig-2.0.x`).

1. Run Actions → **Create Maintenance Branch** on `main`: pick the `package` from the list (e.g. `swift-sdk`) and enter `version` = the latest release of the line (e.g. `2.0.1`). It creates `release/swift-sdk-2.0.x` at the monorepo tag `swift-sdk-2.0.1` plus one bot commit `chore(swift-sdk): start 2.0.x maintenance line`: a `release-please-config.json` with only that package and `"versioning": "always-bump-patch"`, so even a `feat:` releases 2.0.2, never 2.1.0. It refuses an existing branch, a missing tag, a version that is not the latest patch of its line, and a line `main` has not left yet (release from `main` then). Try it locally with `python3 scripts/maintenance_branch.py create swift-sdk 2.0.1 --dry-run`.
2. Open the fix PR with base `release/swift-sdk-2.0.x` (branch name e.g. `fix/swift-sdk-2.0-crash`); review and squash-merge it as usual. PR Validation (`ci-ok`) and `pr-title` run on it as on `main`.
   A PR runs the workflow files of the branch it targets (plus its own changes). A branch cut from a tag older than this change has the old `ci.yml` and `pr-title.yml` (main only) and gets no PR checks: cherry-pick the trigger change onto it in its first PR.
3. Release Please opens the release PR on that branch (`chore(release): swift-sdk 2.0.2`, head `release-please--branches--release/swift-sdk-2.0.x--components--swift-sdk`). Merging it tags `swift-sdk-2.0.2` on the maintenance branch and starts publishing like on `main`.
   To run it again by hand, run Actions → **Release Please** with "Use workflow from" = `release/swift-sdk-2.0.x` (only `main` and `release/<key>-X.Y.x` are accepted). A branch cut from a tag older than this feature has an old `release-please.yml` that cannot do this: cherry-pick the current workflow onto it in its first PR.
4. The publisher sees that the source commit is on `release/swift-sdk-2.0.x`, not `main`, and publishes to the public branch `release/2.0.x`: the bot creates it once at public tag `2.0.1` (the latest 2.0.* tag), then opens the publish PR `chore(release): 2.0.2` against it. Review and merge it.
5. Run **Tag & Release Packages**. It tags `2.0.2` on the merge commit on `release/2.0.x` and creates the Release with "Latest" off while a higher version (2.1.0) exists. Public `main` does not change.
6. Forward-port the fix to `main` with a normal PR (cherry-pick); never merge the maintenance branch into `main`.

Notes:
- The `CHANGELOG.md` on `main` does not list 2.0.2; it lives on the maintenance branch and in the public 2.0.2 Release.
- Abandon Unpublished Version works the same: a public revert PR targets `release/2.0.x`, and the rollback PR targets `release/swift-sdk-2.0.x`.
- An integration maintenance version still waits as `awaiting_dependency` until its `sdkMinimum` SDK tag is public.
- Admin, once: the monorepo `release-lines` ruleset (pattern `release/*-*.*.x`) gives maintenance lines the same rules as `main` (PR review, no force push, no deletion) and requires the `ci-ok` and `pr-title` checks. Public repositories get no `release/*` ruleset: a public `release/X.Y.x` is needed only while a publish PR is open, tags hold the releases, the bot recreates the branch from the latest `X.Y.*` tag, and the drift check stops publication after any direct edit.

### Retire a maintenance line (admin)

Developers cannot delete release lines. Retire one only when nothing is pending on it: no open backport or release PR, and its last version is tagged publicly.

1. Settings → Rules → Rulesets → `release-lines` → Enforcement status **Disabled** → Save.
2. Delete the branch: Branches page, or `git push origin --delete release/<key>-X.Y.x`.
3. Set `release-lines` Enforcement status back to **Active** → Save.

To reopen the line later, run **Create Maintenance Branch** with its latest release (it starts from that monorepo tag).

### Discard an unpublished version

Run Actions → **Abandon Unpublished Version** on `main` with `package` (from the list) and `version` (e.g. `2.0.1`). It is the one way, whatever state the version is in, and the next release of the package gets the same number again (Firebase 2.0.1 discarded → the next Firebase release is 2.0.1, and its notes include the discarded changes).

1. It checks first and changes nothing if any check fails: the version has no public tag (a tagged version is refused: customers may have it, roll forward instead, see above); the monorepo tag `<component>-X.Y.Z` exists; it is the latest release of the package on its line (`.release-please-manifest.json` says `X.Y.Z`); and its release commit changes only the release files (manifest, `CHANGELOG.md`, `version.txt`, `Version.swift`).
2. Public side, by the state of the publish PR `publication/<package>/X.Y.Z`:
   - none (publication failed or waits for a dependency or takeover): nothing to do;
   - open: the bot comments "Discarded by Abandon Unpublished Version (run link)" and closes it;
   - closed without merging: the bot adds the same comment;
   - merged: the bot opens a revert PR on the public base. Merge it, then run the workflow again (two runs); the second run comments on both PRs and continues.
   The public branch `publication/<package>/X.Y.Z` is deleted, so the reused number starts fresh.
3. Monorepo side, on the version's line (`main`, or `release/<package>-X.Y.x`): the bot opens the rollback PR `revert(<package>): discard unpublished <component> X.Y.Z` (branch `discard/<package>/X.Y.Z`) that puts the release files back, adds a commit override to the old release PR so the next changelog skips it, and deletes the monorepo Release and tag `<component>-X.Y.Z` last.
4. **Merge the rollback PR next.** Release Please then proposes `X.Y.Z` again with the discarded changes. Until it is merged, Release Please may briefly show a wrong release PR; ignore it.

Notes:
- Re-running is safe: every step checks first; once done it reports "already discarded; nothing to do".
- Closing a publish PR by hand still stops Tag & Release Packages (review required) until this workflow runs for it.

## Validation limits

Local tests use real Git branches, protected-main rejection hooks, PR merge commits, and immutable tags.
Only GitHub PR API responses are modeled in the reviewed-route tests.
The rehearsal (`python3 scripts/rehearse.py`) runs bootstrap, takeover, releases, Tag & Release Packages, drift and clean consumers on fixture repositories with the same modeled PR API; `--ios` adds the iOS consumer build.
Hosted App access, bot PR creation, required review and public customer upgrades are exercised on GitHub by each release; local passing tests do not replace them or the dependency-monitoring acceptance gates.
