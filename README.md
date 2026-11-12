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
- **Use device tools** to remove an app, mirror a screen with optional `scrcpy`, or export SMS diagnostics where device access permits.

## Get started

### Requirements

- Internet access on first launch so the platform launcher can check and install missing requirements.
- On Windows, [Windows Package Manager (`winget`)](https://learn.microsoft.com/windows/package-manager/winget/) from Microsoft's **App Installer**. The launcher tries to register it if present and opens its Store page if it is missing.
- On macOS, an administrator account for [Homebrew setup](https://docs.brew.sh/Installation) if Homebrew is not already installed. Homebrew's Command Line Tools requirements also apply.
- Optional screen mirroring via [`scrcpy`](https://github.com/Genymobile/scrcpy); the launchers attempt to install it too.

The launchers check for Python 3.9+ with Tk support, Android SDK Platform-Tools (`adb`), and JDK 17 or newer. They install missing requirements with the platform package manager. They also attempt to install `scrcpy`; if that optional install fails, the toolkit still starts without screen mirroring.

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

1. Open the **APK** tab and choose a saved project, or select **Save as…** to create a profile.
2. Set the Gradle project folder (the folder containing `gradlew`), module (for example, `app`), APK path, and Android package name.
3. Choose **debug** or **release**, then start the build. The toolkit runs the matching Gradle `assembleDebug` or `assembleRelease` task.
4. Connect and select the target device, then install the APK. After a successful install, the toolkit attempts to launch the package.
5. Find completed builds in **Version history…**. APKs are archived locally with the project name, version, build type, and build time.

You can also set the APK path and package name directly to install a prebuilt APK without a Gradle project.

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
