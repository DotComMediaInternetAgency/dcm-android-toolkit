# DCM Android Toolkit development guidelines

This document owns implementation and UI conventions for the standalone Python/Tk desktop app. See the toolkit [README](../README.md) for setup and operation.

## Runtime and code structure

- Keep the helper local-first and standard-library based. Add a dependency only when a clear requirement cannot be met with Python's standard library or an installed platform tool such as ADB.
- Keep UI, ADB/process integration, and local persistence responsibilities clear. Keep UI callbacks small and move blocking work to a worker thread.
- Invoke ADB and other commands with argument arrays. Do not build shell command strings or interpolate user input into a shell.
- Set practical timeouts for external commands, capture output, and report actionable failures. Check command output and resulting device state when a zero exit code does not prove the requested operation succeeded.
- Send worker-thread UI updates through Tk's event queue (`after`); never mutate widgets directly from a worker thread.
- After making application code changes, stop any currently running instance and launch the updated app again when it can start successfully. If the updated app does not start, report the startup failure and leave the old instance stopped. Restarting to load changes does not authorize visual inspection, screenshots, or UI checks; those remain opt-in.
- Keep release checks on the official GitHub HTTPS API endpoint. Use normal TLS certificate verification and, if the platform CA store fails verification, retry with an available `certifi` bundle. Never disable certificate verification.
- Startup device restoration must run in a worker with a one-second total deadline, including Wi-Fi reconnect attempts. A timeout or unavailable device leaves the app responsive and its saved connection method/address ready for manual retry. Device refresh must also run off the UI thread.
- Keep machine-specific configuration, generated builds, APK archives, device data, and exports local and ignored. Write JSON state atomically when partial writes could corrupt existing user data.
- Keep bug-report exports user initiated and local. Save the Activity log to the Desktop, show the saved path, and offer a copy-email action; never send logs or emails automatically.
- Keep platform launchers idempotent: check for Python with Tk, ADB, and JDK 17+, install only missing requirements through Homebrew or winget, and explain when a platform package manager or administrator access is required. The macOS launcher may bootstrap Homebrew using its official installer. Attempt optional scrcpy installation without blocking app startup if it fails. Keep Windows setup logic in PowerShell and make the .bat entry point minimal.
- In Windows PowerShell setup, read JDK version from the JDK `release` file when available. Java writes `-version` output to stderr; do not treat that normal output as a setup failure under stop-on-error handling.

## Consistent and responsive interface

- Keep DCM Android Toolkit identity separate from the selected Android project's identity. Use shared `ttk.Style` definitions and explicit colors for native `tk` widgets so dialogs do not fall back to platform dark colors or unreadable defaults.
- Prefix notebook tab names and labeled action buttons with consistent, context-specific symbols. Centralize the symbol mapping, keep the text label visible, and use glyphs supported by the platform fonts without adding image or icon dependencies.
- Keep the main window's app title and task guidance in its header. Put app version, author credits, website, and manual update checking in a dedicated **About** notebook tab. Keep these actions in the tab so they remain available across platforms without relying on native menu integration.
- Use a consistent white background for notebook pages and their content. Labels inside the tab workspace should use a white background too, so text does not appear on mismatched patches. Keep the About description and put its **Website** button beside **Check for updates**.
- Give every notebook page the same outer padding and a shared title, description, and horizontal divider before its content. Use horizontal `ttk.Separator` widgets between related content sections so the pages scan consistently.
- Make every app-created window fit the available display. Derive initial geometry and minimum size from screen dimensions; never set a minimum size larger than the available screen.
- Keep primary and closing actions visible at every supported window size. Put actions in a dedicated, non-expanding footer row. Let content take the remaining space and scroll when needed. Do not place buttons after an expanding widget in a way that pushes them below the visible window.
- For a user-adjustable vertical panel such as Activity, use a vertical `ttk.Panedwindow` sash and give long output a connected scrollbar. Keep the main content and panel usable at the minimum window size.
- Prefer grid layouts with explicit row and column weights for dialogs containing resizable content. Keep footer rows at natural height and content rows expandable. If horizontal space is constrained, wrap or stack controls without hiding the primary action.
- Resize long text, tables, and previews with the window; add scrollbars where content can exceed the available area. Avoid fixed-height text areas that clip content or action buttons.
- Make notebook tab content vertically scrollable with a visible scrollbar and mouse-wheel support so resizing the Activity pane cannot permanently hide lower controls.
- Keep layout, spacing, button hierarchy, labels, selected states, and modal backgrounds consistent with the main helper. Give destructive actions a clear danger treatment and separate them from routine actions.
- Give the APK build action its own high-contrast `Build.TButton` variant with mapped active, pressed, and disabled states. Show live build state in a fixed main-window row outside the resizable Activity pane so it cannot be clipped, and use an indeterminate indicator rather than inventing a completion percentage.
- Keep keyboard dismissal and focus behavior predictable. Provide clear action labels, visible focus, adequate hit targets, and a keyboard path to close or cancel a dialog. Never use color alone to communicate a state.
- Visual inspection, screenshots, and runtime UI checks are opt-in and require an explicit user request.

## ADB operations and user control

- Require a connected, authorized device before device-specific actions. Bind each operation to the selected serial so multiple attached devices cannot receive an unintended command.
- Keep connect, pair, install/overwrite, uninstall, SMS export, display-setting changes, and screen control explicit. Confirm destructive or privacy-sensitive operations before executing them; never infer consent from a previous operation.
- Distinguish discovery from connection: a responding TCP port is only a scan candidate. Confirm the ADB transport and device state before showing a device as connected, and explain authorization, offline, and network failures accurately.
- Verify installation before launching an app, and report when installation succeeded but launch failed. Do not report an ADB action as successful based only on a button press or a non-error-looking label.
- Treat SMS bodies, sender identifiers, phone numbers, pairing codes, and exported JSON as sensitive. Never include message bodies, pairing codes, or secrets in logs, notifications, screenshots, fixtures, or version control. Keep SMS exports local in the user-selected folder and avoid partial overwrite on failure.
- Treat desktop APK history and per-build notes as local development data, separate from versioned Android release artifacts. Restrict deletion to the local archive, make bulk deletion explicit, and keep the history index synchronized with files.
- In file-history dialogs, disable row-dependent actions until a row is selected, and disable file actions when the selected file is missing. File actions must validate that the resolved path stays inside the intended archive; provide a native reveal/open-folder action and a save dialog when copying a file for sharing.
- Preserve the user's exact choice when errors occur. Do not automatically retry a different connection mode, grant permissions, install software, install/uninstall packages, or change device settings without a clearly initiated action.

## Verification and documentation

- Maintain the root [CHANGELOG](../CHANGELOG.md) using [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Add user-facing changes under `## [Unreleased]`, grouped by the standard headings (`Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Security`). Leave entries there until a release is requested; when releasing, move them into a dated version section and update the comparison links.

- Keep project profiles independent. Each profile stores its Gradle root, module
  path, APK path, and Android package name; project names and package IDs must
  not be hard-coded to one product.
- Create project profiles through a focused flow that requires a non-empty name and a valid Gradle root containing the current platform's wrapper (`gradlew` or `gradlew.bat`). Suggest the folder name as a starting value, select the new profile after saving, and preserve all existing profiles and APK history.
- Build from the selected Gradle root and module. Validate module paths before
  using them to construct a task or output path. Label archived APK records with
  their profile name so projects remain distinguishable.
- Stream Gradle output from a worker process and marshal UI updates through a thread-safe queue and Tk's `after` method. Use `--console=plain`, keep the existing build timeout, prevent a second build and profile edits while a build is running, and report success only after the process exits successfully and APK outputs are found and archived. On Windows, run `gradlew.bat` with the validated argument sequence and Python's batch-file handling; never concatenate the project path or module into a shell command.
- Launch Gradle in an isolated process group, use `--no-daemon`, and stop the entire toolkit-owned process tree when the app closes or a build times out. Never terminate Gradle processes started by other tools; explain cache-lock conflicts and identify that the other build must finish or be closed.
- Preserve local configuration, APK history, notes, and SMS exports when
  changing persistence. Keep all local device data and build artifacts ignored
  by Git.
- Follow the user's requested verification scope. Do not perform visual UI
  checks unless explicitly asked.
- Update this guide for desktop implementation standards and the toolkit
  [README](../README.md) for setup or user-facing behavior.
- Do not copy Android-specific Compose/Material 3 rules into the desktop helper. Shared product identity and safety apply across surfaces; component and layout conventions remain platform-specific.
