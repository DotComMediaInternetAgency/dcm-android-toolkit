# Changes and verification

## Before and during a change

- Read `README.md`, `AGENTS.md`, and this guide. Read the relevant topic guide
  before changing the associated subsystem.
- Inspect the worktree before editing. Preserve unrelated user changes and do
  not include unrelated untracked files in a requested change or release.
- Keep UI, device/process integration, and persistence concerns in their
  owning modules. Prefer focused changes that follow existing helpers and
  naming patterns.
- For UI changes, consult [`UI_STANDARDS.md`](UI_STANDARDS.md) and
  [`UI_COMPONENTS.md`](UI_COMPONENTS.md). Reuse the documented component owner,
  keep loading/empty/error states distinct, and update the component catalog
  when a shared convention changes.
- For device app inventory changes, review both user and system package paths,
  missing-metadata fallbacks, active-user scope, device-switch invalidation,
  selected-row state, explicit confirmation, and post-action device-state
  checks. Keep those records out of persistent configuration and diagnostics.
- Do not add or run tests unless the user asks for tests or verification.
  Follow the user's requested verification scope; report what was and was not
  checked. Visual/runtime UI checks require an explicit request (see
  [Desktop UI standards](UI_STANDARDS.md)).

## Documentation and changelog

- Update README for setup or user-facing behavior changes. Update the relevant
  developer guide when a convention changes.
- Maintain root `CHANGELOG.md` using [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
  Put unreleased user-facing additions, changes, fixes, removals, deprecations,
  and security changes under `## [Unreleased]` and standard matching headings.
- For each release, move every Unreleased entry into the new dated version
  section, leave Unreleased present and empty, and update comparison links.
  Compare numeric versions with at least four components to distinguish
  four-part releases such as `0.1.3.1` from three-part predecessors.
- See [Release workflow](RELEASING.md). A user request to release authorizes the
  complete documented workflow; do not stop after local edits or ask again
  whether to commit and push.

## Completion report

- Summarize the behavior changed, documentation updated, verification performed,
  and any relevant limitations.
- Do not claim a command, test, device operation, or visual inspection succeeded
  without evidence from its result.
- Keep the topic guides aligned: architecture defines ownership, device
  operations define ADB and safety rules, UI standards define presentation,
  UI components define shared Qt patterns, and data/privacy defines persistence
  boundaries. Update the README for user behavior and the changelog for
  user-facing changes.
