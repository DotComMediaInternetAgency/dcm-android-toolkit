# Local data and project profiles

## Persistence boundaries

- Keep machine-specific settings, device addresses, project paths, APK history,
  APK archives, SMS exports, emulator state, and build artifacts local and out
  of version control.
- Preserve user configuration, profiles, build notes, APK history, and exports
  when changing storage or profile behavior. Use atomic JSON writes where a
  partial write could corrupt existing state.
- Do not copy selected Android projects into this repository. Profiles may point
  to project folders anywhere on the computer.
- Treat desktop APK history and notes as local development data, separate from
  Android release artifacts.

## Device app inventory

- Installed package IDs, versions, labels, and user/system classifications are
  device-derived data. Keep the Apps page's inventory and filtering state
  transient in memory; do not write them to settings, project profiles, APK
  history, or exports.
- Do not include package inventory in diagnostic reports or Activity logs by
  default. If a future feature needs to save or export it, define the user
  action, destination, retention, and disclosure first, and keep it local.
- Keep package display names and icons as presentation metadata. The package ID
  remains the stable identity used for selection, removal, and verification.

## Project profiles

- Each profile stores its name, Gradle or Expo root, Android module, APK path,
  and Android package name. Do not hard-code project names or package IDs.
- Create profiles through a focused flow that requires a non-empty name and a
  supported project root. Gradle roots need the platform wrapper and root
  settings/build files; Expo roots need a `package.json` declaring `expo`.
- Suggest the selected folder name, explain unsupported folders, and include
  the selected path in local validation diagnostics. Select a newly saved
  profile while preserving all existing profiles and APK history.
- Validate module paths before deriving Gradle tasks or output paths.

## Archives and cleanup

- Restrict APK deletion to files inside the validated toolkit archive and keep
  the history index synchronized. Require explicit confirmation for bulk
  deletion.
- In file-history dialogs, disable row-specific actions until selection and
  disable file actions if the file is missing. Validate resolved paths remain
  inside the intended archive. Use a native reveal/open-folder action and a
  save dialog when copying files for sharing.
- Restrict temporary cleanup to known toolkit prefixes and staging paths, use
  an age threshold, skip symlinks and active operations, and preview exact
  targets before deletion.
- Never scan or delete arbitrary project folders, Gradle caches, user-selected
  SMS export directories, AVD data, or APKs outside the toolkit archive.
- SDK packages can be shared with Android Studio. Confirm package removal
  separately and show the exact SDK root. Limit bootstrap cleanup to
  toolkit-named `dcm-bootstrap-*` folders. Treat Python, Java, ADB, and scrcpy
  as shared dependencies; do not broadly uninstall them without ownership
  records and explicit per-package confirmation.
- Configuration reset must prevent normal shutdown from saving profiles again
  and must leave APK archives, SMS exports, Android SDK data, and project files
  intact.
