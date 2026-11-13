# Architecture and runtime

## Application structure

- `dcm_android_toolkit.py` owns the desktop application and coordinates UI
  actions, ADB/build workers, app configuration, and local history.
- `qt_theme.py` owns centralized Light and Dark palette tokens, QSS generation,
  and the offline Lucide icon renderer.
- `qt_widgets.py` owns reusable Qt layouts, state bindings, dialogs, and the
  queued UI dispatcher.
- `docs/UI_COMPONENTS.md` is the developer catalog for shared component
  ownership and adoption. Keep `qt_widgets.py` as the implementation source of
  truth and the guide as its usage contract.
- Keep changes in the module that owns the responsibility. Avoid duplicating
  theme values, state binding behavior, or command execution helpers.
- Compose page-specific content in the application coordinator from shared
  controls. Put repeated cross-page widget behavior in `qt_widgets.py` and
  visual tokens or QSS in `qt_theme.py`; do not let shared helpers own device or
  persistence policy.
- Keep profiles independent so users can work with multiple Gradle or Expo
  projects. Treat the selected project and app identity as separate concepts.

## Device app inventory

- The Apps page is a view over the currently connected Android device and its
  active user, not a project-profile feature. Its search/filter state and
  package records remain in memory only.
- Keep page construction and presentation in `dcm_android_toolkit.py`, reusable
  navigation/icon behavior in `qt_widgets.py` and `qt_theme.py`, and ADB
  inventory/removal work in workers in the application coordinator. Do not
  introduce a second package-command or theme implementation.
- The inventory flow separates package IDs/type from optional package details.
  Missing names, labels, or versions must degrade to an explicit fallback; a
  missing icon uses the themed generic package icon. Avoid a new runtime
  dependency or device-side installation just to enrich presentation.
- A removal action carries the captured serial, package ID, package type, and
  active user through confirmation, execution, and verification. The UI reports
  success only after the package list confirms it is absent for that user.

## Threads and external processes

- Keep UI callbacks short. Run ADB, filesystem scans over large trees, package
  manager operations, network requests, Gradle, and emulator setup in workers.
- Worker threads must not mutate Qt widgets. Send results and errors through
  `UiDispatcher` / `after()`.
- Call subprocesses using argument lists and explicit working directories. Set
  timeouts, capture output, and check both exit status and resulting state.
- Stream long-running task output into Activity. Make cancellation and app-close
  behavior explicit, and terminate only process trees started by this toolkit.
- Never terminate Gradle or other processes started by another tool. Explain
  cache-lock conflicts and how the user can resolve them.

## Runtime and launchers

- Keep runtime requirements in `requirements.txt`. Both platform launchers must
  provision them inside the ignored `.venv` before starting the app.
- Keep the Windows entry point minimal and its setup in PowerShell. Keep
  launchers idempotent and report prerequisite failures with useful output.
- Check ADB and JDK 17+ before builds. Expo builds also require Node.js/npm.
  Install missing prerequisites only from a clearly initiated action and report
  when installation fails or the tool remains undiscoverable.
- Optional `scrcpy` installation failure must not prevent startup.
- Self-updates must use official release metadata, normal TLS verification,
  digest and embedded-version checks, safe extraction, rollback, and preservation
  of local data. Successful updates restart through the platform launcher so
  changed dependencies are provisioned before app startup.
- Keep `force_update.py` independent of Qt imports so it can repair a broken app
  startup. Preserve `.venv`, local configuration, and `data/` during updates.
- Restore the previous device in a worker with a one-second total deadline,
  including Wi-Fi reconnect attempts. A timeout leaves the UI responsive and
  the saved method/address ready for manual retry. Device refresh also runs in a
  worker.
- Keep the Debug tab immediately before About. Discover the Emulator from the
  selected project's `local.properties`, SDK environment variables, and
  standard SDK locations. Do not install emulator packages on startup.

## Explicit emulator setup

- The user-initiated **Download & create AVD** action may install the official
  Android Emulator, Platform-Tools, configured Google APIs system image, and
  one default Pixel AVD. Support Windows x64, macOS ARM64/Intel, and Linux x64.
- If command-line tools are missing, obtain the matching official Android
  Command-line Tools archive, verify its published platform-specific SHA-256,
  and safely extract it directly into a permanent uniquely named SDK directory.
  Do not rename an extraction directory after unpacking; SDK launchers may keep
  references to that path.
- Resolve the SDK root before installation, prioritize `local.properties` over
  an ADB executable from a standalone WinGet package, and use a host-compatible
  system-image ABI. Warn that the download is large and never overwrite an
  existing AVD.
- Stream setup progress. If `sdkmanager` requests a license, keep stdin open,
  show a native Yes/No dialog on the Qt thread, and send only the user's
  explicit response. Never accept licenses automatically.
- Disable setup when the selected SDK already has the Emulator executable and
  at least one AVD; recompute after setup and refresh. Stop toolkit-owned setup
  processes when the app closes.

## Android builds

- Build Gradle projects from the selected root and validated module. Pass
  arguments separately; on Windows use Python's batch-file handling for
  `gradlew.bat` rather than constructing a shell command.
- Use `--no-daemon` and `--console=plain`, retain the configured build timeout,
  prevent overlapping builds and profile edits during a build, and report
  success only after APK output is found and archived.
- Expo builds must use the project's local Expo CLI. Offer `npm ci` only when a
  lockfile exists and the user confirms. Ask before Prebuild; do not use
  `--clean`, which can remove native project work. Explain its generated files
  and stream its output.
- APK is the supported direct ADB install artifact; Android App Bundles are not
  directly installable through this workflow.
