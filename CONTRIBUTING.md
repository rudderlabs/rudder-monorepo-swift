# Contributing

## Outside contributors

Report bugs and request features in this repository's [Issues](https://github.com/rudderlabs/rudder-monorepo-swift/issues/new/choose). To propose a change, open a pull request here; sdk_team reviews it. The public package repositories accept no issues or pull requests: their code is generated from here.

## Maintainers

Edit canonical source here. Do not edit generated publication repositories.
Use short Conventional Commit subjects (`fix(sprig): handle empty config`); the `pr-title` check enforces them.
Run `make prepare` once per clone (git hooks: release markers, commit message and branch name checks), then `make check test` before review (see [Making a change](README.md#making-a-change)). PR CI runs only the packages your change affects ([PR checks](docs/development.md#pr-checks)); so does a push, compared with the branch's previous commit. From a terminal, the pre-push hook tests only the packages your branch changed (against your local `origin/main`, so `git fetch origin` first); CI also tests their dependents. `SKIP_PRE_PUSH_TESTS=1 git push` skips those tests (the branch name and global checks still run; CI runs the tests).
Add packages with `make new-integration` or `make import-integration`, never by hand. To import a branch that is ahead of the latest tag with non-code changes only (license, README, CODEOWNERS), add `REF=main`; the version stays the tag's and the import fails if any code differs.
Keep independent changes in separate commits.
`.github/CODEOWNERS` assigns every path to `@rudderlabs/sdk_team`, so sdk_team reviews every change, including `release/allowlist.json`.
