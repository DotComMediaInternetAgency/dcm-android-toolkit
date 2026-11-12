# DCM Android Toolkit contributor instructions

- This is a standalone Python/Tk utility for building and managing Android APKs
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
- Maintain `CHANGELOG.md` using [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) sections. Put unreleased additions, changes, fixes, removals, deprecations, and security changes under `## [Unreleased]`, grouped under the matching standard headings. Keep it there until the user releases a newer version; then move those entries into a dated version section and update the comparison links. Do not create a release entry or bump a version unless asked.
