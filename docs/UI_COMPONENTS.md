# Shared UI components and consistency

This guide defines where reusable desktop UI behavior belongs and how new
components should follow the toolkit's existing visual and interaction
patterns. The detailed layout, accessibility, and threading rules are in
[`UI_STANDARDS.md`](UI_STANDARDS.md).

## Sources of truth

| Concern | Owner | Rule |
| --- | --- | --- |
| Palette, theme tokens, QSS, icon rendering | `qt_theme.py` | Define colors and theme-dependent styling once. Keep Light and Dark behavior aligned. |
| Reusable widgets, layouts, state bindings, dialogs, UI dispatch | `qt_widgets.py` | Put cross-page Qt behavior here rather than copying it into page code. |
| Page composition and application-specific actions | `dcm_android_toolkit.py` | Compose shared parts and connect them to app state and workflows. |
| Product behavior and setup instructions | `README.md` | Describe user-visible workflows without implementation detail. |
| Contributor conventions | `docs/` | Keep the relevant topic guide authoritative and link it from the developer entry point. |

Do not add a second palette, icon renderer, state-binding convention, or
parallel widget helper for behavior that already has a shared owner. App-specific
text and actions belong beside the page that owns their meaning; reusable
rendering and interaction behavior belongs in the shared modules.

## Shared component catalog

Use these helpers before creating a page-local substitute:

| Need | Shared component |
| --- | --- |
| Scrollable page body | `make_scrollable_page()` |
| Card with body layout | `make_card()` |
| Section divider | `make_divider()` |
| Wrapping action row | `FlowLayout` |
| Sidebar destinations | `SidebarNavigator` |
| Theme-aware button appearance and icon | `style_button()`, `refresh_button_icon()` |
| Two-way widget state | `StateVar` with the matching `bind_*()` helper |
| Worker result on the Qt thread | `UiDispatcher` / `after()` |
| Dynamic combo with no choices | `show_combo_empty_state()` |
| Native file/message/input dialogs | `QtDialogs` |

When a repeated pattern is not represented here, first check `qt_widgets.py` and
`qt_theme.py`. Add or extend a shared helper when multiple pages need the same
behavior. Keep a helper focused: avoid generic frameworks for a single page or
helpers that mix presentation with device, process, or persistence policy.

## Empty, loading, and error states

Every data-driven view should explain what the user sees while data is loading,
when no data exists, when filtering yields no matches, and when loading fails.
Keep these states distinct because their next steps differ:

- **Loading:** say what is being retrieved and keep the UI responsive.
- **Empty:** say what is absent and, when possible, provide the relevant next
  action nearby.
- **Filtered empty:** say that no results match the current search/filter and
  make it easy to change or clear the filter.
- **Error:** summarize the failure and offer a retry when retry is safe.
- **Stale:** identify when displayed data belongs to a previous device or
  context; disable actions that could target stale data.

For a dynamic, non-editable `QComboBox`, populate its real options first, then
call `show_combo_empty_state(combo, message)` if the list is empty. Use a
context-specific message. Its disabled row is display-only and must never be
used as a selection, persisted value, device serial, project name, or action
target. Preserve adjacent status guidance and recovery actions.

Do not use the combo helper for editable inputs, fixed-choice controls, tables,
or lists. An editable field remains usable without suggestions. A table or list
needs an inline contextual empty presentation that does not masquerade as a
selectable record. Keep empty state wording close to the view and use the
existing theme tokens for its appearance.

## Adding or changing a shared component

1. Search the codebase for existing controls and helpers before adding a new
   pattern.
2. Define visual values in the theme owner and behavior in the widget owner.
   Keep app-specific labels, state, and recovery actions with the owning page.
3. Preserve keyboard behavior, focus visibility, readable Light/Dark contrast,
   and enabled/disabled semantics.
4. Ensure placeholder or presentation-only rows cannot enter bound or persisted
   state.
5. Update this catalog and [`UI_STANDARDS.md`](UI_STANDARDS.md) when the shared
   convention changes; update [`ARCHITECTURE.md`](ARCHITECTURE.md) if module
   ownership changes.
6. Follow [`QUALITY.md`](QUALITY.md) for review and requested verification.

