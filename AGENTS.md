# DCM Android Toolkit repository instructions

- Read [`README.md`](README.md) and [`docs/DEVELOPMENT_GUIDELINES.md`](docs/DEVELOPMENT_GUIDELINES.md) before making changes; read the linked topic guide for the subsystem involved.
- This is a standalone Python/PySide6 utility for building and managing Android APKs across multiple Gradle and Expo projects. Keep project profiles independent.
- Preserve existing configuration, profiles, APK history, notes, and exports when changing storage or profile behavior. Keep device addresses, SMS exports, APK archives, and machine-specific data local and out of version control.
- Bind ADB operations to the selected device serial. Keep connections, installs, uninstalls, SMS exports, pairing, and device-setting changes explicit and user initiated.
- Keep installed-app inventory scoped to the connected device and active Android user. Treat package inventory as transient device data; follow [`docs/DEVICE_OPERATIONS.md`](docs/DEVICE_OPERATIONS.md) for listing, metadata fallbacks, and removal verification.
- Keep desktop UI patterns unified through [`docs/UI_STANDARDS.md`](docs/UI_STANDARDS.md) and the shared component catalog in [`docs/UI_COMPONENTS.md`](docs/UI_COMPONENTS.md); extend shared Qt helpers instead of duplicating cross-page behavior.
- Do not launch the app, use screenshots, or perform visual/runtime UI checks unless the user explicitly asks.
- Keep runtime requirements in `requirements.txt`; provision them in ignored `.venv` from both platform launchers. Successful self-updates must restart through the relevant launcher so new dependencies are installed before app startup.
- Update the README for setup or user-facing behavior changes, the relevant developer guide for standards changes, and `CHANGELOG.md` for user-facing changes.
- Maintain `CHANGELOG.md` using [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Group Unreleased entries under standard headings. For releases, move every Unreleased entry into the dated version section, leave Unreleased present and empty, and update comparison links.
- A user request to release authorizes the complete workflow in [`docs/RELEASING.md`](docs/RELEASING.md): version, changelog, intended commit, push, GitHub release/source archive, and verification. Exclude ignored local configuration, APK history, exports, machine-specific data, and unrelated untracked files.
