# Device operations and privacy

## ADB targeting and connections

- Require an authorized connected device for device-specific work. Bind every
  command to the selected serial when multiple devices may be attached.
- Keep USB and Wi-Fi as explicit user-selected connection methods. Preserve the
  user's choice on errors; do not silently switch modes or retry using another
  target.
- Distinguish discovery from connection: an open TCP port is only a scan
  candidate. Confirm the ADB transport and state before displaying a device as
  connected. Explain authorization, offline, and network failures accurately.
- Connect, pair, install/overwrite, uninstall, SMS export, display-setting
  changes, and screen control must be user initiated. Do not infer consent from
  an earlier operation.
- Check command output and resulting device state. A button press or a
  non-error-looking label is not proof of success.

## Installed apps and removal

- Build the inventory in a worker for the active Android user: obtain its ID
  with `am get-current-user`, then use `pm list packages --user <id> -3` for
  user apps and `pm list packages --user <id> -s` for system apps. Use package
  IDs as stable identities and preserve the user ID and classification with
  each in-memory record.
- Obtain version name/code from `dumpsys package` when available. Do not infer
  that package IDs are human-readable app names. ADB shell package listings do
  not reliably expose translated labels or icon bitmaps; use a generic icon and
  clearly identify the package-derived display-name fallback. Do not add an
  app-label/icon extraction dependency solely for this page.
- Bind list, removal, and verification commands to the serial captured when the
  operation starts. Never let a stale row from one device target another.
- Invalidate the displayed inventory when the active serial changes or the
  device disconnects. If a request completes for an old serial, discard its
  results and refresh only for the currently selected device.
- Require the user to select a package and confirm removal with its display
  name, package ID, target serial, and data/system-app consequences.
- Uninstall ordinary user apps with ADB's uninstall command. Remove system apps
  only for the active Android user through `pm uninstall --user`; explain that
  this does not erase the system image and that protected packages can reject
  the operation.
- Check command output and query the package list again for that user before
  reporting success. Treat package-manager output containing a failure as a
  failure even when the command exit code is zero. Refresh the visible list
  after a successful removal.
- Keep inventory records transient in memory. Never persist installed package
  lists in settings or project profiles, or include them in logs, exports, or
  diagnostics by default.

## Emulators and install targets

- Keep emulator controls in the Emulator tab. Inspect AVDs and ADB state in
  workers; wait for `sys.boot_completed=1` before reporting readiness.
- Map serials to AVD names with `adb -s <serial> emu avd name`. Starting an
  emulator must not silently select it; require an explicit Connect action.
- Stop only an AVD/serial pair this toolkit recorded as started. Use
  `adb -s <serial> emu kill` before process-tree fallback, and preserve managed
  emulator state locally across restarts.
- Keep APK install-target selection independent from the active connection.
  Populate it from authorized devices, label known emulator serials by AVD, and
  bind install and launch commands to the exact selected serial. Preserve the
  selection when its target remains available.
- Verify installation before launch. If launch fails after installation,
  report both outcomes clearly.

## Sensitive data and diagnostics

- Treat SMS bodies, sender identifiers, phone numbers, pairing codes, and
  exported JSON as sensitive. Never put message bodies, pairing codes, or
  secrets in logs, notifications, screenshots, fixtures, or version control.
- Keep SMS exports in the user-selected local folder. Avoid partial overwrite
  when an export fails.
- Debug may show tool availability, paths, version results, project diagnostics,
  and recent application errors, but must not read device content. Keep bounded
  error logs under ignored `data/logs/` and local unless explicitly exported.
- Diagnostic exports must omit device addresses and SMS contents, disclose
  that local project/tool/application paths are included, and require an
  explicit user action.
- Bug-report exports remain local and user initiated. Never send logs or email
  automatically.
