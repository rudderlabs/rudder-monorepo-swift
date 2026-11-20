# Supporting File Templates

All templates use `{{name}}` for the lowercase integration name (e.g., `firebase`) and `{{Name}}` for the PascalCase name (e.g., `Firebase`).

## .gitignore

```
# Xcode
#
# gitignore contributors: Feel free to update this file as needed for the integrations.

## User settings
xcuserdata/

## Obj-C/Swift specific
*.hmap

## App packaging
*.ipa
*.dSYM.zip
*.dSYM

## Playgrounds
timeline.xctimeline
playground.xcworkspace

## Swift Package Manager
/.build/
.netrc
.swiftpm/

# Dependency management files (not needed for libraries)
Packages/
Package.pins

# Example app build artifacts
Example/.build

# Xcode user-specific files
xcuserdata/
*.xcuserstate
DerivedData/

# macOS and editor metadata
.DS_Store
*.swp
*.swo
*.tmp

# Logs
*.log
```

## CODEOWNERS

```
* @rudderlabs/sdk-ios
```

## LICENSE.md

```
MIT License

Copyright (c) 2026 RudderStack, Inc.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
```

## CONTRIBUTING.md

```
# Contributing to RudderStack

Thanks for taking the time and for your help in improving this project!

## Table of contents

- [**RudderStack Contributor Agreement**](#rudderstack-contributor-agreement)
- [**How you can contribute to RudderStack**](#how-you-can-contribute-to-rudderstack)
- [**Committing**](#committing)
- [**Getting help**](#getting-help)

## RudderStack Contributor Agreement

To contribute to this project, we need you to sign the [**Contributor License Agreement ("CLA")**][CLA] for the first commit you make. By agreeing to the [**CLA**][CLA], we can add you to list of approved contributors and review the changes proposed by you.

## How you can contribute to RudderStack

If you come across any issues or bugs, or have any suggestions for improvement, you can navigate to the specific file in the [**repo**](https://github.com/rudderlabs/integration-swift-{{name}}), make the change, and raise a PR.

You can also contribute to any open-source RudderStack project. View our [**GitHub page**](https://github.com/rudderlabs) to see all the different projects.

## Committing

We prefer squash or rebase commits so that all changes from a branch are committed to master as a single commit. All pull requests are squashed when merged, but rebasing prior to merge gives you better control over the commit message.

## Getting help

For any questions, concerns, or queries, you can start by asking a question in our [**Slack**](https://rudderstack.com/join-rudderstack-slack-community/) community.

### We look forward to your feedback on improving this project!


<!----variables---->

[CLA]: https://rudderlabs.wufoo.com/forms/rudderlabs-contributor-license-agreement
```

## .github/pull_request_template.md

```
## Description
<!-- Describe your changes in detail -->

## Type of change
<!-- What types of changes does your code introduce? Put an `x` in all the boxes that apply -->
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Implementation Details
<!-- Provide a brief explanation of the implementation approach -->

## Checklist
<!-- Put an `x` in all the boxes that apply -->
- [ ] My code follows the style guidelines of this project
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes

## Screenshots (if appropriate)
<!-- Add screenshots to help explain your changes -->

## Additional Notes
<!-- Add any other context about the pull request here -->
```

## README.md Template

```markdown
# RudderIntegration{{Name}}

RudderStack Swift SDK device mode integration for {{Name}}.

## Installation

### Swift Package Manager

Add the following dependency to your `Package.swift`:

```swift
.package(url: "https://github.com/rudderlabs/integration-swift-{{name}}.git", .upToNextMajor(from: "1.0.0"))
```

Or add it via Xcode:
1. Go to **File > Add Package Dependencies**
2. Enter the repository URL: `https://github.com/rudderlabs/integration-swift-{{name}}`
3. Select **Up to Next Major Version** from `1.0.0`

## Usage

### Swift

```swift
import RudderStackAnalytics
import RudderIntegration{{Name}}

let config = Configuration(writeKey: "<WRITE_KEY>", dataPlaneUrl: "<DATA_PLANE_URL>")
let analytics = Analytics(configuration: config)

let {{name}}Integration = {{Name}}Integration()
analytics.add(plugin: {{name}}Integration)
```

### Objective-C

```objc
@import RudderStackAnalytics;
@import RudderIntegration{{Name}};

RSSConfigurationBuilder *builder = [[RSSConfigurationBuilder alloc] initWithWriteKey:@"<WRITE_KEY>"
                                                      dataPlaneUrl:@"<DATA_PLANE_URL>"];
RSSAnalytics *analytics = [[RSSAnalytics alloc] initWithConfiguration:[builder build]];

RSS{{Name}}Integration *{{name}}Integration = [[RSS{{Name}}Integration alloc] init];
[analytics addPlugin:{{name}}Integration];
```

## License

MIT License - see [LICENSE.md](LICENSE.md) for details.
```
