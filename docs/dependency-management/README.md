# Staged dependency-management configuration

Owner: SDK team. Status: local dependency guards implemented and enforced by CI. Dependabot alerts and security updates are on through the organization's security configuration. Version updates are off: the template is not activated, pending a team decision.

This bundle holds the dependency-management requirements: exporter dependency guards, release markers, regression tests, and a read-only monitoring collector. Follow [acceptance commands and gates](ACCEPTANCE.md) before activation.

## Proposed configuration

`dependabot.yml.template` is valid YAML kept outside `.github/dependabot.yml`. GitHub does not load it. The current sample has one declarative root `Package.swift`, so the Swift updater uses `/`. `Packages/*` and `Integrations/*` are targets, not separate package roots. Actions also uses `/`.

The candidate uses `open-pull-requests-limit: 0` to avoid routine version PRs. It does not disable alerts or automatic security PRs. The monthly schedule is a required version-update setting, not alert or security-response cadence. Final production PR policy remains undecided; this template is one concrete security-first option.

No `target-branch` is needed when source default is `main`. Recheck the actual default branch during provisioning. No ignore, exclude, auto-dismissal, or severity filter is proposed. SHA-pinned Actions remain pinned; their native advisory-detection limitation needs separate evidence.

If only alert collection is selected, no updater YAML is required. Dependency graph inputs and alert settings are still required.

## Settings and graph inputs — separate from YAML

| Surface | Proposed requirement | Acceptance evidence |
| --- | --- | --- |
| Source monorepo | Enable dependency graph and alerts; retain all severities and no-fix/no-PR findings. Capture a clean public-URL `Package.resolved` on the source default branch. | Expected vendor identities and resolved versions appear in GitHub; record default branch, commit, graph export, run date, and any missing packages. |
| Publication repositories | Preserve all existing native alerts. Establish a reviewed graph-input route for generated releases. | Verify each actual default branch. Output now uses default `main`, but hosted graph ingestion still requires evidence. Consumer coverage does not silently replace missing publication visibility. |
| Rules | Inventory effective organization/repository rules. Do not suppress low/development alerts to reduce noise. | Record rule state and preserve original alert identities, including existing dismissed records for audit. |
| PR settings | Select automatic, selective, or requested security PR handling separately. | Record chosen mode and hosted behavior. No automatic-merge setting is proposed. |

Local mirror resolutions are not valid remote graph inputs. The source's public vendor-only lock may be suitable after inspection; customer-check locks are generated per release against the public URLs. Keep `.lab/` and local mirrors out of remote commits. Lockfiles used by consumers do not change the downstream version requirements of published libraries.

Do not introduce a custom Swift graph-submission workflow before checking normal lockfile ingestion. If ingestion fails, record the error and prove a supported alternative; a successful `swift package resolve` alone is not graph evidence.

## Local implementation and remaining prerequisites

1. `scripts/dependency_policy.py check` compares export vendor metadata against SwiftPM's parsed canonical manifest. Export invokes the same check before creating output. Git requirements may be `exact`, `upToNextMajor` (including `from:`), `upToNextMinor`, or a version range; markers and inventory store `{kind, lower, upper}` and the generated manifest uses the same kind. Branch and revision requirements are rejected. Products from one vendor package share a single `.package` line.
2. `scripts/dependency_policy.py sync` derives vendor metadata and writes package-local `dependency-requirements.json` markers. The check command rejects stale or missing markers. Include reviewed markers in the same `fix:` commit as a vendor update so Release Please can see the affected integration paths.
3. `release_plan.py affected --base-ref <commit> Package.swift` compares current parsed requirements with committed package markers at the pre-change baseline. Root lock-only changes are release-neutral. Local classification tests cover one vendor consumer and two integrations sharing a vendor. Real Release Please and the hosted shared-vendor release remain pending.
4. CI runs dependency guards and local regressions without publisher credentials. The extended local rehearsal tests a Swift Collections 1.1.4-to-1.1.5 update through Firebase export, release, and consumer resolution. These local Git results do not prove hosted updater/security behavior.
5. Clean public-URL graph input and publication-default coverage remain unresolved hosted gates. The exporter still excludes `Package.resolved`; decide how publication graph inputs are maintained without generated exports erasing them.

Use the existing exporter and release-marker design. Do not add another version authority or an automatic bot commit to a Release Please branch. Updates to `sdkMinimum` remain explicit release-policy changes. Review all changed markers and the resulting Release Please intent before merging.

## Activation

1. Import every package and confirm the default branch of this repository and each public package repository.
2. Resolve the source vendors from clean public URLs; review and commit the resolved file.
3. Enable and verify the dependency graph and alerts. Record package identities and all findings before enabling updates.
4. Copy the reviewed template to `.github/dependabot.yml` in this repository only. A Dependabot PR that changes `Package.swift` also needs its release markers: run `make sync` on its branch, push the result, and give the PR a releasable title, for example `fix(firebase): bump firebase-ios-sdk to 13.0.0`.
5. Verify the first Dependabot PR changes the canonical dependency requirement, its markers, and only the affected packages' release intent.

A benign vendor version update proves updater/export behavior, not security-fix behavior. Do not add a vulnerable dependency to force an alert.

## Required failure cases and evidence

- A manifest-only vendor update with stale export metadata fails before publication, or exporter-derived metadata automatically uses the manifest requirement.
- A vendor-only fix selects the correct consumer integration and produces reviewed release intent.
- A lock-only change is classified separately from a changed public dependency requirement.
- A missing/stale default-branch graph is reported as a coverage gap, not zero vulnerabilities.
- Generated publication drift is rejected; a later export cannot overwrite a fix silently.
- Missing registry or package access produces an explicit failed result; no publisher credentials are exposed to updater PR jobs.

Retain source/consumer/publication SHAs, resolved files, package identities, graph exports, settings/rules, updater logs and PR, release selection, generated manifests, consumer output, and remaining unsupported findings. Keep critical, high, medium, low, unknown, no-fix, and no-PR findings visible.

## References

- [Production migration plan](https://app.notion.com/p/3c1f2b415dd08197b28dd097c7c476cc)
- [GitHub configuration options](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference)
- [Swift support](https://docs.github.com/en/code-security/reference/supply-chain-security/supported-ecosystems-and-repositories#swift)
- [Dependency graph inputs](https://docs.github.com/en/code-security/reference/supply-chain-security/dependency-graph-supported-package-ecosystems)
