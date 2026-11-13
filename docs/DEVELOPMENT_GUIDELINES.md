# Developer guidelines

This document is the entry point for contributors to DCM Android Toolkit. Read it
with the topic guide for the area being changed. Repository instructions in
[`AGENTS.md`](../AGENTS.md) apply to every task; this document and its linked
guides define implementation conventions.

## Product and platform

- DCM Android Toolkit is a standalone, local-first Python application using
  PySide6 Essentials. It builds and manages APKs across multiple Android
  projects; do not hard-code one project's name, paths, or package ID.
- Keep dependencies minimal. Prefer the standard library, Qt, or installed
  platform tools such as ADB. Update `requirements.txt` and both launchers when
  adding a runtime dependency.
- Keep UI, device/process integration, and persistence responsibilities
  separate. Keep callbacks small; move blocking work to workers and dispatch UI
  changes through `UiDispatcher` / `after()` on the Qt thread.
- Invoke external commands with argument arrays, practical timeouts, captured
  output, and actionable error reporting. Do not interpolate user input into a
  shell command.
- Keep device app inventory in memory and scoped to the active device and
  Android user. Do not add app inventory to project profiles, settings, APK
  history, or diagnostics. Follow the device and UI topic guides for metadata
  fallbacks, device changes, and confirmed removal behavior.

## Topic guides

- [Architecture and runtime](ARCHITECTURE.md): modules, worker boundaries,
  launchers, build tools, and update behavior.
- [Desktop UI standards](UI_STANDARDS.md): navigation, layout, theme, controls,
  accessibility, and UI verification boundaries.
- [Shared UI components](UI_COMPONENTS.md): component ownership, the reusable
  widget catalog, and empty/loading/error state conventions.
- [Device operations and privacy](DEVICE_OPERATIONS.md): ADB targeting,
  connection modes, emulator behavior, explicit actions, SMS, and diagnostics.
- [Local data and project profiles](DATA_AND_PRIVACY.md): persistence,
  profiles, APK history, exports, cleanup, and Git exclusions.
- [Changes and verification](QUALITY.md): documentation, changelog, review,
  and verification expectations.
- [Release workflow](RELEASING.md): versioning, commit, push, GitHub release,
  source archive, and post-release checks.

## Documentation ownership

- Update the README when setup, user-facing behavior, or supported workflows
  change.
- Update the relevant topic guide when implementation conventions or safety
  rules change.
- Record user-facing fixes and features in `CHANGELOG.md` under `Unreleased`
  using Keep a Changelog headings.
- Keep `AGENTS.md` as a short repository-wide entry point. Do not duplicate the
  detailed topic guides there.
