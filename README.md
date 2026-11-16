# RudderStack Swift SDK

This repository is where the RudderStack Swift SDK (`RudderStackAnalytics`) and its device-mode integrations are developed and released.

Each package still ships from its own public repository, so apps keep installing it from there with Swift Package Manager. Those repositories are read-only: their code is generated from this one at each release.

## Packages

| Package | Source | Install from | Platforms |
| --- | --- | --- | --- |
| RudderStack Analytics (SDK) | [`Packages/RudderStackAnalytics`](Packages/RudderStackAnalytics) | [rudder-sdk-swift](https://github.com/rudderlabs/rudder-sdk-swift) | iOS 15, macOS 12, tvOS 15, watchOS 8 |
| Adjust | [`Integrations/Adjust`](Integrations/Adjust) | [integration-swift-adjust](https://github.com/rudderlabs/integration-swift-adjust) | iOS 15, tvOS 15 |
| AppsFlyer | [`Integrations/AppsFlyer`](Integrations/AppsFlyer) | [integration-swift-appsflyer](https://github.com/rudderlabs/integration-swift-appsflyer) | iOS 15, macOS 12, tvOS 15 |
| Braze | [`Integrations/Braze`](Integrations/Braze) | [integration-swift-braze](https://github.com/rudderlabs/integration-swift-braze) | iOS 15, tvOS 15 |
| CleverTap | [`Integrations/CleverTap`](Integrations/CleverTap) | [integration-swift-clevertap](https://github.com/rudderlabs/integration-swift-clevertap) | iOS 15 |
| Facebook | [`Integrations/Facebook`](Integrations/Facebook) | [integration-swift-facebook](https://github.com/rudderlabs/integration-swift-facebook) | iOS 15 |
| Firebase | [`Integrations/Firebase`](Integrations/Firebase) | [integration-swift-firebase](https://github.com/rudderlabs/integration-swift-firebase) | iOS 15, macOS 12, tvOS 15 |
| Sprig | [`Integrations/Sprig`](Integrations/Sprig) | [integration-swift-sprig](https://github.com/rudderlabs/integration-swift-sprig) | iOS 15 |

Each package's README has its installation and usage guide. Sample apps are in [`Examples/`](Examples).

## Getting started

You need macOS with Xcode 16 or later, Python 3.9 or later, and SwiftLint.

1. Clone this repository.
2. Run `make prepare` once. It checks the tools (with install hints), turns on the repository's git hooks for this clone only, and resolves the dependencies. It prints `Ready` when done; running it again is safe.
3. Open `Package.swift` in Xcode. It holds every package, so you can build and test any of them.

## Making a change

1. Create a branch named `<type>/<name>`, for example `fix/sprig-empty-traits`.
2. Make the change and commit it. Commit messages and PR titles follow [Conventional Commits](https://www.conventionalcommits.org): `<type>(<optional scope>): <description>`, lowercase, no trailing period, at most 100 characters. Types: `feat` `fix` `refactor` `perf` `style` `test` `docs` `chore` `build` `ci` `revert`.
3. Check it locally:

   | Command | What it does |
   | --- | --- |
   | `make check` | The repository policy checks that CI runs |
   | `make test` | The Python tests, then every package's tests on the iOS Simulator |
   | `make test PKG=sprig` | One package's tests |
   | `make lint` | SwiftLint on the Swift files you changed |
   | `make affected` | The packages your branch changes |

4. Open a pull request into `main`. CI builds and tests only the packages your change affects, plus the packages that depend on them. sdk_team reviews every pull request.

A merged change is not released right away. See [Releases](#releases).

## Releases

Every package is versioned and released on its own:

1. [Release Please](https://github.com/googleapis/release-please) keeps one release PR open per changed package, with its next version and changelog.
2. Merging that PR exports the package and opens a publish PR in its public repository.
3. A maintainer reviews and merges the publish PR, then runs **Tag & Release Packages** (Actions → Run workflow). It creates the version tag and the GitHub Release, and checks that a clean app can install the new version.

Before merging the SDK's publish PR, check the result of its e2e release sanity run.

Details and how-tos (release one package alone, set the next version, patch an older version line, roll forward a bad version, discard an unpublished version): [Reviewed publication](docs/reviewed-publication/README.md).

## Adding an integration

- **New integration:** `make new-integration NAME=<Name>` creates the package, its tests and its release settings.
- **Existing repository:** `make import-integration REPO=<repo> TAG=<X.Y.Z> NAME=<Name>` imports it with its history.

Either way, its key must first be in `release/allowlist.json` (sdk_team approval). All options: [Development guide](docs/development.md#adding-a-package).

## Repository layout

| Path | Contents |
| --- | --- |
| `Packages/` | The core SDK |
| `Integrations/` | One folder per integration |
| `Examples/` | Sample apps |
| `release/` | The package list, allowlist, release texts and templates |
| `scripts/`, `Makefile` | Development, CI and release tooling |
| `Tests/` | Tests for the tooling |
| `docs/` | Guides for maintainers |

## Documentation

- [Development guide](docs/development.md): CI, git hooks, shared code, export rules and the local release rehearsal.
- [Reviewed publication](docs/reviewed-publication/README.md): how a release reaches the public repositories, and maintainer how-tos.
- [Release boundaries](docs/release-boundaries/README.md): the branch model and acceptance checks.
- [Dependency management](docs/dependency-management/README.md): Dependabot setup.

## Contributing

To report a bug, request a feature or propose a change, see [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE)
