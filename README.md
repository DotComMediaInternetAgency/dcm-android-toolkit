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
- **Use device tools** to remove an app, mirror a screen with optional `scrcpy`, or export SMS diagnostics where device access permits.

## Get started

### Requirements

- Internet access on first launch so the platform launcher can check and install missing requirements.
- On Windows, [Windows Package Manager (`winget`)](https://learn.microsoft.com/windows/package-manager/winget/) from Microsoft's **App Installer**. The launcher tries to register it if present and opens its Store page if it is missing.
- On macOS, an administrator account for [Homebrew setup](https://docs.brew.sh/Installation) if Homebrew is not already installed. Homebrew's Command Line Tools requirements also apply.
- Optional screen mirroring via [`scrcpy`](https://github.com/Genymobile/scrcpy); the launchers attempt to install it too.

The launchers check for Python 3.9+ with Tk support, Android SDK Platform-Tools (`adb`), and JDK 17 or newer. They install missing requirements with the platform package manager. They also attempt to install `scrcpy`; if that optional install fails, the toolkit still starts without screen mirroring.

The Emulator tab can download the Android Emulator SDK package using Android CLI or SDK Command-line Tools. If neither tool is installed, install Android SDK Command-line Tools first. The **Download emulator** action works on macOS and Windows and installs only that SDK package; it does not accept SDK licenses, create AVDs, or download system images. Use Android Studio's Device Manager to accept any required licenses and create a virtual device with a system image. Choose an AOSP system image if you want an Android image without Google apps or services. Hardware acceleration support depends on the host OS and CPU; see Google's [emulator acceleration guide](https://developer.android.com/studio/run/emulator-acceleration).

### Launch

**macOS:** double-click `Launch DCM Android Toolkit.command`. It installs Homebrew first if needed, then installs any missing requirements.

**Windows:** double-click `Launch DCM Android Toolkit.bat`. It starts `setup_windows.ps1`, which uses `winget` to install any missing requirements and launches the app after verifying them.

**Any platform:** run from this directory:

```sh
python3 dcm_android_toolkit.py
```

Direct Python launch assumes Python with Tk support, ADB, and JDK 17+ for builds are already installed. The launch scripts handle setup automatically.

The app checks the GitHub releases page for a newer version at startup. Open the **About** tab and select **Check for updates** to check manually. The check runs in the background and opens the release page only if you choose to view an available update. The About tab includes app details, a **Website** button, and **Report a bug…**, which saves the Activity log to your Desktop and lets you copy the support email address.

## Build and install an APK

1. Open the **APK** tab and choose a saved project, or select **Add project…** to create one. Enter a project name and choose the Gradle root folder containing `gradlew` (macOS/Linux) or `gradlew.bat` (Windows). The name is required; choosing a folder suggests its folder name.
2. The project is saved and selected automatically. Set its Gradle module (for example, `app`), APK path, and Android package name as needed. Each named profile keeps its own settings so you can switch between projects from the selector.
3. Choose **debug** or **release**, then select **Build APK…**. The toolkit runs the matching Gradle `assembleDebug` or `assembleRelease` task and shows live progress in a fixed status row below the resizable workspace. Full build output streams into Activity. Closing the toolkit or reaching the build timeout stops the Gradle process tree it started.
4. Choose an authorized device or running emulator from **Install target**, then install the APK. After a successful install, the toolkit attempts to launch the package on that target. This target can differ from the active device used by other tools.
5. Find completed builds in **Version history…**. APKs are archived locally with the project name, version, build type, and build time.

You can also set the APK path and package name directly to install a prebuilt APK without a Gradle project.

## Run with an emulator

Open the **Emulator** tab and choose **Download emulator** if the Android Emulator SDK package is missing. Refresh the installed AVD list, select a stopped AVD, and choose **Start emulator**; the emulator opens in its own window while the toolkit waits for Android to finish booting. Choose **Connect emulator** to make it the active ADB device, or select it directly in the APK tab's **Install target** selector to install and launch an APK without changing the active device. **Stop emulator** is available for instances started by the toolkit. AVD data remains in the Android SDK's local user-data files across normal stops.

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
