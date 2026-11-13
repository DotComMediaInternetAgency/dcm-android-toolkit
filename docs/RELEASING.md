# Release workflow

Use this workflow whenever the user asks to release or bump the release version. A release includes the full contents of `CHANGELOG.md` under `## [Unreleased]` at the time the version is prepared.

1. Inspect the worktree and latest GitHub release. Confirm that only intended source, documentation, and release files will be committed; leave ignored configuration, APK archives, exports, and other machine-specific files out.
2. Choose the next requested version, update `APP_VERSION` in `dcm_android_toolkit.py`, and add a dated version heading to `CHANGELOG.md`.
3. Move **all** entries, including every standard subsection and bullet, from `## [Unreleased]` into the new version section without dropping or rewriting their meaning. Leave `## [Unreleased]` present and empty. Set its comparison link to `v<new-version>...HEAD`, and add the new version link comparing the previous tag to the new tag.
4. Check that the changelog version matches `APP_VERSION` and that no unreleased bullets remain. Run `python3 -m py_compile dcm_android_toolkit.py` and `git diff --check`.
5. Commit all intended changes as the release commit and push `main` (or follow the user's requested branch integration instructions). Create and push the annotated `v<new-version>` tag.
6. Create a source archive from that tag named exactly `dcm-android-toolkit-<new-version>-source.zip`, with the matching top-level directory. Publish it on the GitHub release so the app updater can find the expected asset and GitHub SHA-256 digest.
7. Verify the GitHub release, tag, source ZIP name and digest, pushed commit, and clean worktree. Report the release link, commit, asset, and verification results.

Never publish a release with release-bound bullets still under `Unreleased`; empty that section as part of preparing every release, even when earlier releases left items behind.
