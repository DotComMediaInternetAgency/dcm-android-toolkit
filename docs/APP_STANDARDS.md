# Application consistency standards

This guide defines the cross-page rules that keep DCM Android Toolkit clear
and consistent as features are added. It is an index and review contract, not
a replacement for the topic guides that own detailed implementation rules.

## Sources of truth

| Topic | Source of truth | Keep it authoritative for |
| --- | --- | --- |
| User setup and workflows | [`README.md`](../README.md) | What the app does and how users complete tasks |
| Product-wide consistency | This guide | Shared terminology, interaction expectations, and consistency review |
| Desktop layout and accessibility | [`UI_STANDARDS.md`](UI_STANDARDS.md) | Navigation, page layout, themes, controls, accessibility, and UI checks |
| Shared Qt patterns | [`UI_COMPONENTS.md`](UI_COMPONENTS.md) | Shared widget ownership, reuse, and empty/loading/error states |
| Modules and runtime | [`ARCHITECTURE.md`](ARCHITECTURE.md) | Ownership, workers, subprocesses, build/runtime behavior |
| Device actions and safety | [`DEVICE_OPERATIONS.md`](DEVICE_OPERATIONS.md) | ADB targeting, device state, confirmations, and privacy |
| Local persistence | [`DATA_AND_PRIVACY.md`](DATA_AND_PRIVACY.md) | Profiles, history, exports, local files, and cleanup boundaries |
| Change process | [`QUALITY.md`](QUALITY.md) | Documentation, review, and requested verification |
| Releases | [`RELEASING.md`](RELEASING.md) | Versioning, publication, and release verification |

When rules overlap, use the guide that owns the behavior. For example, use UI
standards for control presentation, device operations for which serial an ADB
command must target, and data/privacy for whether the resulting information may
be persisted.

## Product consistency

- Preserve the local-first product model. Work across independent Gradle and
  Expo project profiles; do not assume a fixed project, path, package ID, or
  device.
- Reuse the product's terms consistently. Use **project profile** for saved
  project configuration, **install target** for the APK destination selector,
  **connected device** for the active ADB connection, **Version history** for
  the archived-build view, and **Activity** for the live output view. Use APK
  history when referring specifically to its persisted index or archive data.
  Do not use two labels for the same concept unless the context requires a
  distinction.
- Give each action one clear scope and target. Keep target selection visible
  near device actions, retain the captured target through asynchronous work,
  and explain when an action uses the connected device instead of an install
  target.
- Make action states predictable across pages: available, running, succeeded,
  failed, or unavailable. Disable conflicting controls while an operation is
  active, show progress outside a resizable output area, and restore controls
  on every completion path.
- Report the outcome that actually occurred. If a workflow has stages, report
  each meaningful stage separately; success in one stage does not imply success
  in the next. A failed prerequisite or earlier stage must stop dependent work.
- Keep user-initiated and destructive operations explicit. Put the target and
  consequence in the confirmation or nearby guidance; do not infer consent
  from an earlier action.
- Use the same words for the same action in button labels, prompts, status
  messages, README instructions, and changelog entries. Keep labels short and
  put supporting detail in guidance or dialogs.

## Page and component consistency

- Follow [`UI_STANDARDS.md`](UI_STANDARDS.md) for page hierarchy, cards,
  navigation, accessibility, themes, and responsive layout.
- Follow [`UI_COMPONENTS.md`](UI_COMPONENTS.md) before building a new control
  or interaction pattern. Search the shared widget and theme modules first;
  extend their owner when a pattern is reused across pages.
- Keep a shared helper generic and presentation-focused. Page-specific labels,
  state, recovery actions, and product policy stay with the page that owns
  them.
- Prefer one well-labeled card per task. A single card may contain clearly
  separated sequential steps when its primary action performs the full flow.
  Unrelated actions, especially actions with different device targets or
  consequences, stay in separate groups or cards.
- Data-driven controls explain loading, empty, filtered-empty, stale, and error
  states, with a safe next action where one exists. Placeholder rows must never
  become persisted values or operation targets.

## Change review checklist

Before editing, find the closest existing page and shared component, read its
owning topic guide, and identify which files own presentation, behavior,
persistence, and user documentation. Before finishing, check that:

1. Existing page patterns and terminology are reused, or the relevant guide
   explains a deliberate new pattern.
2. Actions show their target, progress, outcome, and failure recovery without
   blocking the UI thread.
3. Shared behavior is implemented through its existing owner rather than a
   page-local duplicate.
4. Device, project, profile, and persistence boundaries are preserved according
   to the relevant topic guides.
5. README, topic guides, and changelog are updated according to
   [`QUALITY.md`](QUALITY.md).
6. Verification matches the user's request and repository policy. Never launch
   or visually inspect the app unless explicitly asked; do not add or run tests
   unless the user asks for tests or verification.
