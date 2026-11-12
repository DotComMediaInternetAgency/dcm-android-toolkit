# Changelog

Notable changes to DCM Android Toolkit are documented here.

This changelog follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-11-12

### Added

- Initial public release with multi-project Gradle builds, ADB device tools, APK installation, and local APK version history.
- macOS and Windows launch scripts that check for Python with Tk, ADB, and JDK 17+, then install missing requirements.
- Automatic Homebrew setup on macOS when it is not installed, plus GitHub release update checks.
- About tab for app version, credits, and manual update checks.
- About tab bug-report action exports Activity log to the Desktop and offers a button to copy the support email address.
- Launchers attempt optional scrcpy installation for screen mirroring.

### Changed

- Standardized notebook page backgrounds to white and expanded the About tab with an app description and a Website button beside update checking.
- Standardized tab content placement with shared page headers and horizontal separators between sections.
- Made the Activity panel height adjustable with a draggable divider and added a vertical scrollbar.
- Windows setup runs from a dedicated PowerShell helper; the BAT file is now a minimal launcher.
- macOS and Windows launchers install missing Python with Tk, Android Platform-Tools, and JDK 17 or newer.
- macOS launcher installs Homebrew through its official installer if missing; Windows setup uses winget and opens the Store if App Installer is unavailable.

### Fixed

- GitHub release checks now retry certificate verification with `certifi` when Python's default CA store is incomplete.
- Windows setup now detects Java after winget installs it and proceeds to launch the app.

[Unreleased]: https://github.com/DotComMediaInternetAgency/dcm-android-toolkit/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/DotComMediaInternetAgency/dcm-android-toolkit/releases/tag/v0.1.0
