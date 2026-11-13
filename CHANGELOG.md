# Changelog

Notable changes to DCM Android Toolkit are documented here.

This changelog follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.4.8] - 2026-11-13

### Changed

- Overhauled the desktop UI with a `UI_COLORS` design-token system, soft-slate canvas (`#f3f5f8`) and 1px-bordered white card containers (`_card()`), a grouped left `SidebarNavigator` rail (**Workspace**, **Tools**, **System**), live Project and Device header status pills, semantic button styles (primary build, accent, info, warning, subtle, danger) with matched disabled icon states, consistent `Toplevel` dialog theming, standardized card section headers/status notes, and a dark Activity console with `Copy`, `Clear`, `Auto-scroll`, and color-coded log tags.
- Replaced Unicode glyph icons with a zero-dependency `VectorIconLibrary` (`ICON_PATHS`) that renders anti-aliased Lucide-style `tk.PhotoImage` icons for sidebar tabs, buttons, radio buttons, and checkbuttons with style-matched colors.
- Grouped the APK tab's package name and install target into an **Install & target** card, placed `Build type` on its own field row so all 4 action buttons align cleanly, and standardized **SMS Export**, **Watch Screen**, and **About** card headers, inline folder selection, and status labels.

### Fixed

- Fixed vertical `ttk.Scrollbar` sizing and contrast under the `clam` theme so scrollable tab pages and consoles display a usable scrollbar instead of collapsing to 4px.
- Fixed mismatched label background styles inside cards (`CardSub.TLabel`) and on the slate canvas (`TLabel`), and wrapped multi-button action rows (`_wrap_row`) so buttons such as `Version history…` and `Connect emulator` remain visible when horizontal space is narrow.
- Added Tk 9 `<TouchpadScroll>` support alongside `<MouseWheel>` for scrollable tab pages so laptop touchpads and mouse wheels scroll page content smoothly, and disabled/clamped scrolling when all page content already fits within the viewport.

## [0.1.4.7] - 2026-11-13

### Changed

- Moved APK install, remove, and version-history actions into the build action row to reduce vertical space.

### Fixed

- Fixed JDK discovery for Windows `java.exe` installations and common platform install locations.
- APK builds now repair missing Java 17+ and Expo Node.js/npm runtimes through winget or Homebrew, then re-detect them before continuing.

## [0.1.4.6] - 2026-11-13

### Added

- Added Expo project detection and local APK builds that install locked npm dependencies when needed, generate the Android Gradle project with user confirmation, then reuse Gradle archive, device/emulator install, and launch flows.
- Added Expo package ID detection from generated Android Gradle configuration so a built APK can be installed and launched without manually entering its package name.

### Changed

- Expanded the APK project picker and guidance to accept either Android Gradle roots or Expo project roots.

## [0.1.4.5] - 2026-11-13

### Added

- Added a bounded, local error log that records handled application errors and uncaught UI or worker exceptions; the Debug export now includes recent errors and selected Gradle project diagnostics.
- Added clearer checks when adding or building a project so missing Gradle wrappers or root build files identify the expected project folder contents.

## [0.1.4.4] - 2026-11-13

### Fixed

- Suppressed Windows console windows for background ADB, SDK Manager, AVD Manager, and emulator helper processes while preserving the Android Emulator window.
- Made the Windows launcher start the toolkit without leaving a PowerShell or Python console in front of the app.
- Disabled **Download & create AVD** after the Emulator package and at least one AVD are available.
- Created default AVDs without requiring a named hardware profile, avoiding device profile metadata lookup errors on some SDK installations.

## [0.1.4.3] - 2026-11-13

### Fixed

- Fixed Windows startup layout so the tab workspace stays visible above Activity, and open directly to Emulator setup when the Emulator SDK package is missing.

## [0.1.4.2] - 2026-11-13

### Added

- Added **Download & create AVD** setup to install Android SDK Command-line Tools when needed, Platform-Tools, the Emulator, and an architecture-matched Android 16 Google APIs image, then create a default Pixel virtual device without Android Studio.
- Added a Debug tab before About with tool diagnostics, diagnostic report export, stale temporary-file cleanup, selected SDK component removal, APK archive cleanup, and a separate settings/profile reset.

### Changed

- Made the Emulator tab explain that setup downloads a large system image and needs internet access; SDK license acceptance remains explicit.

## [0.1.4.1] - 2026-11-13

### Fixed

- Added an actionable Yes/No prompt when SDK Manager requests license acceptance, and connected the answer to its input so the install no longer hangs or silently skips the Emulator package.
- Fixed the Windows emulator installer path that could raise an unbound `command` local-variable error when SDK Manager was already available.
- Kept release comparison compatible with four-part version tags, including versions with trailing zero components.

## [0.1.4] - 2026-11-13

### Fixed

- Fixed Windows emulator downloads by installing bootstrapped SDK Command-line Tools directly into a permanent SDK directory, so `sdkmanager.bat` dependencies remain available when it runs.
- Prevented a standalone WinGet Platform-Tools package from being selected as the Android SDK root when resolving the emulator download destination.
- Updated release version comparison to recognize four-part version numbers such as 0.1.3.1 and 0.1.4.

## [0.1.3] - 2026-11-13

### Fixed

- Enabled **Download emulator** on Windows when Android CLI and SDK Command-line Tools are missing by downloading and checksum-verifying Google's official Windows Command-line Tools before installing the Emulator package.

## [0.1.2] - 2026-11-13

### Added

- Added an Emulator tab to discover installed Android Virtual Devices, start and stop toolkit-managed emulators, wait for boot, and explicitly connect one as the active ADB device.
- Added an APK install target selector so APKs can be installed and launched on a running emulator without changing the active device.
- Added a cross-platform Emulator tab action to download the Android Emulator SDK package through Android CLI or SDK Command-line Tools.
- Added automatic GitHub release downloads and application-file updates with SHA-256 verification, local-data preservation, and automatic restart.

## [0.1.1] - 2026-11-13

### Added

- Added action-specific symbols to notebook tabs, buttons, and connection controls.
- Added a project setup dialog that requires a project name and Gradle root, then saves and selects the new profile.
- Added live Gradle task status, streamed build output in Activity, and a dedicated colored build button.

### Changed

- Project setup now suggests a name from the chosen folder and defaults the new profile's module to `app`.
- Windows builds now invoke the selected project's `gradlew.bat` wrapper.
- Made every notebook tab's content vertically scrollable, with a scrollbar and mouse-wheel support, so controls remain reachable when Activity is resized.

### Fixed

- Windows setup no longer assigns to PowerShell's reserved `$HOME` variable while locating Java, preventing setup from failing before the app launches.
- Windows setup now reads JDK version metadata without treating Java's normal stderr version output as a setup failure.
- Kept live Gradle build progress visible outside the resizable Activity pane.
- Stopped toolkit-owned Gradle process trees when the app closes or a build times out, preventing orphaned builds from retaining project cache locks.
- Explained when a configuration-cache lock is held by a separate Gradle invocation.

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

[Unreleased]: https://github.com/DotComMediaInternetAgency/dcm-android-toolkit/compare/v0.1.4.8...HEAD
[0.1.4.8]: https://github.com/DotComMediaInternetAgency/dcm-android-toolkit/compare/v0.1.4.7...v0.1.4.8
[0.1.4.7]: https://github.com/DotComMediaInternetAgency/dcm-android-toolkit/compare/v0.1.4.6...v0.1.4.7
[0.1.4.6]: https://github.com/DotComMediaInternetAgency/dcm-android-toolkit/compare/v0.1.4.5...v0.1.4.6
[0.1.4.5]: https://github.com/DotComMediaInternetAgency/dcm-android-toolkit/compare/v0.1.4.4...v0.1.4.5
[0.1.4.4]: https://github.com/DotComMediaInternetAgency/dcm-android-toolkit/compare/v0.1.4.3...v0.1.4.4
[0.1.4.3]: https://github.com/DotComMediaInternetAgency/dcm-android-toolkit/compare/v0.1.4.2...v0.1.4.3
[0.1.4.2]: https://github.com/DotComMediaInternetAgency/dcm-android-toolkit/compare/v0.1.4.1...v0.1.4.2
[0.1.4.1]: https://github.com/DotComMediaInternetAgency/dcm-android-toolkit/compare/v0.1.4...v0.1.4.1
[0.1.4]: https://github.com/DotComMediaInternetAgency/dcm-android-toolkit/compare/v0.1.3...v0.1.4
[0.1.3]: https://github.com/DotComMediaInternetAgency/dcm-android-toolkit/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/DotComMediaInternetAgency/dcm-android-toolkit/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/DotComMediaInternetAgency/dcm-android-toolkit/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/DotComMediaInternetAgency/dcm-android-toolkit/releases/tag/v0.1.0
