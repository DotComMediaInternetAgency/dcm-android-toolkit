# Desktop UI standards

Use [`UI_COMPONENTS.md`](UI_COMPONENTS.md) as the catalog and ownership guide
for shared Qt helpers. This document defines the application-wide layout,
visual, accessibility, and behavior standards.

## Navigation and layout

- Use `SidebarNavigator` with one `QStackedWidget` page per destination. Add each
  page once and switch with `setCurrentWidget`; never reparent a page between
  containers.
- Build cards and scrollable pages with helpers from `qt_widgets.py`. Use
  consistent page headers, spacing, separators, field rows, and status notes.
- Group substantial content into cards by task and ownership. Keep fields that
  configure one saved project together (including its package ID and APK path),
  and group build actions separately from device-target/install actions. Keep
  dependent controls inside the card for their task instead of leaving them
  floating between cards. Do not add a card around every individual control;
  concise page-level mode selectors, global status, and dialog forms may remain
  outside cards when their hierarchy is clear.
- Use `FlowLayout` for action rows that need to wrap. Keep primary and closing
  actions visible. Use `QSplitter` for the resizable workspace and Activity
  console, and provide scrollbars for long content.
- Keep the app title, task guidance, and live Project / Device status in the top
  bar. Put version, credits, website, manual updates, and bug-report export in
  About.
- Keep Debug immediately before About and make its diagnostic controls and
  cleanup previews understandable without exposing device content.
- Put installed-app browsing in its own scrollable Tools page. Provide search,
  user/system filtering, package and version metadata, a visible connected-device
  label, and a clear empty/loading/error state. Keep package removal explicit
  with a selected row, confirmation, and a semantic danger action. Use a generic
  themed app icon when device icon resources are unavailable.
- Treat the package ID as the app's stable identity. Show the package ID even
  when a friendlier display name is available, keep version fields readable
  when Android returns only a version code, and label fallback names/icons so
  users can tell they are not Android's localized app presentation.
- Clear selection and disable removal when inventory is loading, stale, or the
  device disconnects. Show a distinct action label and confirmation for
  removing a system package only for the current Android user.

## Visual system and controls

- Centralize palette tokens in `qt_theme.py`; Light and Dark themes must retain
  readable contrast and apply consistently to existing widgets and dialogs.
- Render icons through `LucideIconLibrary` and `QSvgRenderer`; do not add
  external icon image files. Recolor icons when theme or enabled state changes.
- Keep labels visible, use semantic button variants, and make selected and
  disabled states apparent. Never communicate state through color alone.
- Give data-driven views distinct loading, empty, filtered-empty, failure, and
  stale-data states; each state should provide accurate context and a useful
  next action. Follow the shared widget and empty-state rules in
  [`UI_COMPONENTS.md`](UI_COMPONENTS.md).
- Checkbox indicators must show a high-contrast check glyph when selected; do
  not rely on a filled square alone to communicate the checked state.
- Preserve keyboard navigation, visible focus, adequate hit targets, and clear
  dialog close/cancel actions. Size dialogs to the available screen.
- Keep Activity readable with copy, clear, auto-scroll, and semantic
  error/warning/success/info colors. Show task status outside the resizable
  console; use an indeterminate progress indicator when completion is unknown.

## Threading and UI checks

- Marshal worker callbacks through `UiDispatcher` / `after()`. Never mutate a Qt
  widget from a worker thread or block the UI thread on device, file, package,
  build, or network work.
- Do not launch the app, take screenshots, or perform visual/runtime UI checks
  unless the user explicitly asks. A request to fix or edit the UI alone is not
  permission to inspect it visually.
- When visual checks are explicitly requested, use the updated app and report
  what was inspected and any remaining limitations.
