# DCM Android Toolkit contributor instructions

- This is a standalone Python/PySide6 utility for building and managing Android APKs
  across multiple Gradle projects. Project profiles store a Gradle root, module,
  APK path, and Android package name.
- Preserve existing user configuration and APK history when changing storage or
  profile behavior. Keep device addresses, SMS exports, APK archives, and
  machine-specific data local and out of version control.
- Keep ADB operations bound to the selected device serial and keep installs,
  uninstalls, SMS exports, and device-setting changes user initiated.
- Do not launch the app for visual inspection, use screenshots, or perform
  visual UI checks unless the user explicitly asks.
- Read `README.md` and `docs/DEVELOPMENT_GUIDELINES.md` before changes; update
  the documentation when app behavior or setup changes.
- Keep the runtime requirements in `requirements.txt`, provision them inside the ignored `.venv` from both platform launchers, and make successful self-updates restart through the relevant launcher so new dependencies are installed before app startup.
- Maintain `CHANGELOG.md` using [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) sections. Put unreleased additions, changes, fixes, removals, deprecations, and security changes under `## [Unreleased]`, grouped under the matching standard headings. On every release, move **all** entries from `Unreleased` into the new dated version section, leaving `## [Unreleased]` empty, and update the comparison links. Do not leave release-bound entries under `Unreleased` after publishing.
- Treat a user request to release as authorization to finish the GitHub release workflow documented in [`docs/RELEASING.md`](docs/RELEASING.md): choose/bump the app version, transfer every `Unreleased` entry to that version, commit all intended source and documentation changes, push the release commit to GitHub, publish the release with its source archive, and verify the pushed commit, tag, and asset. Do not stop after making local changes or ask again whether to commit and push. Exclude ignored local configuration, APK history, exports, and other machine-specific data; do not sweep unrelated untracked files into the release.
