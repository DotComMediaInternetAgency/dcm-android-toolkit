# DCM Android Toolkit

**Build, install, replace, and manage Android APKs from one simple desktop app.**

DCM Android Toolkit is a local Python/Tk utility for working with Android devices and APKs across multiple Gradle projects. Connect over USB or Wi-Fi, build debug or release APKs, install them, and keep a searchable local build history.

> **Designed for Android developers who work across more than one project.** Each project keeps its own Gradle folder, module, APK path, and package name.

## What it does

- **Build APKs** from a selected Gradle project and module, in debug or release mode.
- **Install and launch** an APK on the selected Android device.
- **Manage project profiles** without copying or moving your Android projects.
- **Keep APK history** with archived builds, version details, and notes.
- **Connect with ADB** over USB or Wi-Fi, discover devices, and scan a subnet for ADB candidates.
- **Manage Android emulators** by listing installed virtual devices, starting and stopping those launched by the toolkit, and explicitly connecting one for device actions.
- **Inspect and clean toolkit state** with a Debug tab for tool diagnostics, stale temporary files, selected SDK components, and local APK history or profile reset actions.
- **Use device tools** to remove an app, mirror a screen with optional `scrcpy`, or export SMS diagnostics where device access permits.

## Get started

### Requirements

- Internet access on first launch so the platform launcher can check and install missing requirements.
- On Windows, [Windows Package Manager (`winget`)](https://learn.microsoft.com/windows/package-manager/winget/) from Microsoft's **App Installer**. The launcher tries to register it if present and opens its Store page if it is missing.
- On macOS, an administrator account for [Homebrew setup](https://docs.brew.sh/Installation) if Homebrew is not already installed. Homebrew's Command Line Tools requirements also apply.
- Optional screen mirroring via [`scrcpy`](https://github.com/Genymobile/scrcpy); the launchers attempt to install it too.

The launchers check for Python 3.9+ with Tk support, Android SDK Platform-Tools (`adb`), and JDK 17 or newer. They install missing requirements with the platform package manager. They also attempt to install `scrcpy`; if that optional install fails, the toolkit still starts without screen mirroring.

The Emulator tab's **Download & create AVD** action prepares the SDK without Android Studio: it downloads Google's official Command-line Tools when needed, verifies their SHA-256 checksum, installs Platform-Tools, the Android Emulator, and an Android 16 Google APIs system image for the host architecture, then creates a default Pixel virtual device. Review and explicitly accept any SDK license prompt in the app. This one-time setup needs an internet connection and several gigabytes of free space. Starting the AVD still depends on compatible hardware virtualization support from the host OS and CPU; see Google's [emulator acceleration guide](https://developer.android.com/studio/run/emulator-acceleration) and [Command-line Tools downloads](https://developer.android.com/studio#command-line-tools-only).

### Launch

**macOS:** double-click `Launch DCM Android Toolkit.command`. It installs Homebrew first if needed, then installs any missing requirements.

**Windows:** double-click `Launch DCM Android Toolkit.bat`. It starts `setup_windows.ps1`, which uses `winget` to install any missing requirements and launches the app after verifying them. Setup and Android command-line helpers run without leaving console windows in front of the toolkit; the Android Emulator still opens its own window.

**Any platform:** run from this directory:

```sh
python3 dcm_android_toolkit.py
```

Direct Python launch assumes Python with Tk support, ADB, and JDK 17+ for builds are already installed. The launch scripts handle setup automatically.

The app checks GitHub Releases for a newer version at startup. If an update is available, choose **Yes** to download and install it automatically; the app verifies the release asset's SHA-256 digest, updates its application files, preserves local configuration and APK history, then restarts. The app folder must be writable. Choose **No** to keep the current version and check again later from the **About** tab. The About tab also includes app details, a **Website** button, and **Report a bug…**, which saves the Activity log to your Desktop and lets you copy the support email address.

## Build and install an APK

1. Open the **APK** tab and choose a saved project, or select **Add project…** to create one. Enter a project name and choose the Gradle root folder containing `gradlew` (macOS/Linux) or `gradlew.bat` (Windows). The name is required; choosing a folder suggests its folder name.
2. The project is saved and selected automatically. Set its Gradle module (for example, `app`), APK path, and Android package name as needed. Each named profile keeps its own settings so you can switch between projects from the selector.
3. Choose **debug** or **release**, then select **Build APK…**. The toolkit runs the matching Gradle `assembleDebug` or `assembleRelease` task and shows live progress in a fixed status row below the resizable workspace. Full build output streams into Activity. Closing the toolkit or reaching the build timeout stops the Gradle process tree it started.
4. Choose an authorized device or running emulator from **Install target**, then install the APK. After a successful install, the toolkit attempts to launch the package on that target. This target can differ from the active device used by other tools.
5. Find completed builds in **Version history…**. APKs are archived locally with the project name, version, build type, and build time.

You can also set the APK path and package name directly to install a prebuilt APK without a Gradle project.

## Run with an emulator

If the Emulator SDK package is missing, the toolkit opens on the **Emulator** tab. Choose **Download & create AVD** to install the required SDK tools, emulator, system image, and default virtual device. Refresh the installed AVD list if needed, select the created device, and choose **Start emulator**; the emulator opens in its own window while the toolkit waits for Android to finish booting. Choose **Connect emulator** to make it the active ADB device, or select it directly in the APK tab's **Install target** selector to install and launch an APK without changing the active device. **Stop emulator** is available for instances started by the toolkit. AVD data remains in the Android SDK's local user-data files across normal stops.

## Debug and cleanup

The **Debug** tab, immediately before **About**, reports detected tools and paths and can export a diagnostic report with recent handled errors and uncaught UI or worker exceptions. The report includes the selected project folder and a Gradle-root check to help diagnose project setup problems. The bounded error log stays local under `data/logs/`; exported reports include local paths but redact device addresses and omit SMS details. The tab can also remove stale toolkit temporary files older than 24 hours, uninstall the Emulator package from the selected SDK, remove toolkit-named bootstrap Command-line Tools folders, clear archived APK history, or reset saved toolkit settings and project profiles. Each destructive action previews its target and asks for confirmation. SDK packages can be shared with Android Studio and other projects; the confirmation shows the selected SDK path. Cleanup does not remove Android projects, AVD data, SMS exports, or APKs outside the toolkit archive. Resetting profiles closes the app so its normal shutdown save cannot recreate the settings file.

## Device tools

The toolkit supports USB and Wi-Fi ADB connections, device discovery, subnet scanning, package removal, optional `scrcpy` mirroring, and SMS diagnostics on devices that allow ADB shell access. Device actions are initiated from the app and target the selected device.

SMS exports can contain private messages. Choose a local export folder and keep those files private.

## Local data and privacy

Settings, project profiles, connection details, APK history, and archived APKs stay on your computer in `dcm-android-toolkit.json` and `data/`. These files are excluded from Git. Existing APK history is kept in `data/apk_versions/` when you update the toolkit.

The toolkit does not copy selected Android projects into this repository. Profiles can point to project folders anywhere on your computer.

## Credits

Made by **Emre Demir** · [DotComMedia.online](https://dotcommedia.online)

## Releases

Download the latest version from [GitHub Releases](https://github.com/DotComMediaInternetAgency/dcm-android-toolkit/releases).

See the [changelog](CHANGELOG.md) for unreleased work and version history.
