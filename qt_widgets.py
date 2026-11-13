"""Reusable PySide6 UI primitives, state bindings, and dialog helpers."""
from __future__ import annotations

from PySide6.QtCore import QObject, QPoint, QRect, QSize, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from qt_theme import (
    BUTTON_ICONS,
    LIGHT_THEME,
    TAB_ICONS,
    LucideIconLibrary,
    icon_color_for_variant,
    icon_name_for_label,
)


class UiDispatcher(QObject):
    """Marshals worker-thread callbacks onto the Qt main thread."""

    invoke = Signal(object)
    schedule = Signal(int, object)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self.invoke.connect(self._run_now, Qt.ConnectionType.QueuedConnection)
        self.schedule.connect(self._run_later, Qt.ConnectionType.QueuedConnection)

    @staticmethod
    def _run_now(func):
        if callable(func):
            func()

    @staticmethod
    def _run_later(ms: int, func):
        if callable(func):
            QTimer.singleShot(max(0, int(ms)), func)


class StateVar(QObject):
    """Observable value wrapper compatible with StringVar/BooleanVar/IntVar patterns."""

    changed = Signal(object)

    def __init__(self, value=None, coerce=str, parent: QObject | None = None):
        super().__init__(parent)
        self._coerce = coerce
        self._value = coerce(value) if value is not None else coerce()

    def get(self):
        return self._value

    def set(self, value):
        coerced = self._coerce(value)
        if coerced != self._value:
            self._value = coerced
            self.changed.emit(coerced)

    def trace_add(self, _mode: str, callback):
        self.changed.connect(lambda val: callback(val))


def bind_line_edit(edit: QLineEdit, var: StateVar):
    """Two-way bind a QLineEdit to a StateVar."""
    edit.setText(str(var.get()))
    guard = [False]

    def on_text(text: str):
        if guard[0]:
            return
        guard[0] = True
        var.set(text)
        guard[0] = False

    def on_var(val):
        if guard[0]:
            return
        text = str(val)
        if edit.text() != text:
            guard[0] = True
            edit.setText(text)
            guard[0] = False

    edit.textChanged.connect(on_text)
    var.changed.connect(on_var)


def bind_combo_box(combo: QComboBox, var: StateVar):
    """Two-way bind a QComboBox (editable or readonly) to a StateVar."""
    guard = [False]

    def sync_from_var(val):
        if guard[0]:
            return
        text = str(val)
        guard[0] = True
        if combo.isEditable():
            if combo.currentText() != text:
                combo.setCurrentText(text)
        else:
            idx = combo.findText(text)
            if idx >= 0:
                combo.setCurrentIndex(idx)
            elif text:
                combo.setCurrentIndex(-1)
        guard[0] = False

    def sync_from_combo(text: str):
        if guard[0]:
            return
        guard[0] = True
        var.set(text)
        guard[0] = False

    sync_from_var(var.get())
    combo.currentTextChanged.connect(sync_from_combo)
    var.changed.connect(sync_from_var)


def bind_checkbox(checkbox: QCheckBox, var: StateVar):
    """Two-way bind a QCheckBox to a boolean StateVar."""
    checkbox.setChecked(bool(var.get()))
    guard = [False]

    def on_toggled(checked: bool):
        if guard[0]:
            return
        guard[0] = True
        var.set(bool(checked))
        guard[0] = False

    def on_var(val):
        if guard[0]:
            return
        checked = bool(val)
        if checkbox.isChecked() != checked:
            guard[0] = True
            checkbox.setChecked(checked)
            guard[0] = False

    checkbox.toggled.connect(on_toggled)
    var.changed.connect(on_var)


def bind_radio(radio: QRadioButton, var: StateVar, value: str):
    """Two-way bind a QRadioButton to a string StateVar."""
    radio.setChecked(str(var.get()) == str(value))
    guard = [False]

    def on_toggled(checked: bool):
        if guard[0] or not checked:
            return
        guard[0] = True
        var.set(value)
        guard[0] = False

    def on_var(val):
        if guard[0]:
            return
        should_check = str(val) == str(value)
        if radio.isChecked() != should_check:
            guard[0] = True
            radio.setChecked(should_check)
            guard[0] = False

    radio.toggled.connect(on_toggled)
    var.changed.connect(on_var)


def bind_slider(slider: QSlider, var: StateVar):
    """Two-way bind a QSlider to an integer StateVar."""
    slider.setValue(int(var.get()))
    guard = [False]

    def on_value(val: int):
        if guard[0]:
            return
        guard[0] = True
        var.set(int(val))
        guard[0] = False

    def on_var(val):
        if guard[0]:
            return
        num = int(val)
        if slider.value() != num:
            guard[0] = True
            slider.setValue(num)
            guard[0] = False

    slider.valueChanged.connect(on_value)
    var.changed.connect(on_var)


def bind_label(label: QLabel, var: StateVar):
    """One-way bind a QLabel's text to a StateVar."""
    label.setText(str(var.get()))
    var.changed.connect(lambda val: label.setText(str(val)))


class FlowLayout(QLayout):
    """Wrapping horizontal flow layout for responsive button rows."""

    def __init__(self, parent: QWidget | None = None, margin: int = 0, h_spacing: int = 8, v_spacing: int = 8):
        super().__init__(parent)
        self._items = []
        self._h_spacing = h_spacing
        self._v_spacing = v_spacing
        self.setContentsMargins(margin, margin, margin, margin)

    def addItem(self, item):
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index: int):
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect: QRect):
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def _do_layout(self, rect: QRect, *, test_only: bool) -> int:
        margins = self.contentsMargins()
        effective = rect.adjusted(margins.left(), margins.top(), -margins.right(), -margins.bottom())
        x = effective.x()
        y = effective.y()
        line_height = 0

        for item in self._items:
            widget = item.widget()
            if widget is not None and not widget.isVisible():
                continue
            item_size = item.sizeHint()
            next_x = x + item_size.width() + self._h_spacing
            if next_x - self._h_spacing > effective.right() and line_height > 0:
                x = effective.x()
                y += line_height + self._v_spacing
                next_x = x + item_size.width() + self._h_spacing
                line_height = 0
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item_size))
            x = next_x
            line_height = max(line_height, item_size.height())

        return y + line_height - rect.y() + margins.bottom()


class SidebarNavigator(QObject):
    """Left sidebar navigation rail paired with a QStackedWidget of scrollable pages."""

    tab_changed = Signal(object)

    def __init__(self, rail_layout: QVBoxLayout, stage: QStackedWidget, icons: LucideIconLibrary, parent: QObject | None = None):
        super().__init__(parent)
        self.rail_layout = rail_layout
        self.stage = stage
        self.icons = icons
        self.theme = LIGHT_THEME
        self._items: list[tuple[QWidget, QPushButton, str]] = []
        self._current_page: QWidget | None = None

    def add_section(self, title: str):
        label = QLabel(title)
        label.setObjectName("NavSection")
        self.rail_layout.addWidget(label)

    def add(self, page: QWidget, text: str = ""):
        btn = QPushButton(text)
        btn.setProperty("navItem", True)
        btn.setProperty("active", False)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setIconSize(QSize(16, 16))
        btn.clicked.connect(lambda _checked=False, p=page: self.select(p))
        self.rail_layout.addWidget(btn)
        self.stage.addWidget(page)
        self._items.append((page, btn, text))
        self._refresh_button_icon(btn, text, active=False)
        if self._current_page is None:
            self.select(page)
        return page

    def finalize_rail(self):
        self.rail_layout.addStretch(1)

    def select(self, target: QWidget | None = None):
        if target is None:
            return self._current_page
        for page, btn, text in self._items:
            is_active = page is target
            btn.setProperty("active", is_active)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            self._refresh_button_icon(btn, text, active=is_active)
        self.stage.setCurrentWidget(target)
        if self._current_page is not target:
            self._current_page = target
            self.tab_changed.emit(target)
        return target

    def apply_theme(self, theme: dict[str, str]):
        self.theme = theme
        for page, btn, text in self._items:
            is_active = page is self._current_page
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            self._refresh_button_icon(btn, text, active=is_active)

    def _refresh_button_icon(self, btn: QPushButton, title: str, *, active: bool):
        icon_name = TAB_ICONS.get(title.strip().casefold())
        if not icon_name:
            return
        color = self.theme["nav_active_fg"] if active else self.theme["text_secondary"]
        btn.setIcon(self.icons.get(icon_name, color=color, size=16, disabled_color=self.theme["disabled_fg"]))


def make_card(parent_layout: QVBoxLayout | None = None, padding: int = 18) -> tuple[QFrame, QVBoxLayout]:
    """Create a rounded white/dark surface card container."""
    card = QFrame()
    card.setProperty("card", True)
    layout = QVBoxLayout(card)
    layout.setContentsMargins(padding, padding, padding, padding)
    layout.setSpacing(10)
    if parent_layout is not None:
        parent_layout.addWidget(card)
    return card, layout


def make_divider() -> QFrame:
    line = QFrame()
    line.setObjectName("Divider")
    line.setFrameShape(QFrame.Shape.HLine)
    return line


def make_scrollable_page() -> tuple[QScrollArea, QWidget, QVBoxLayout]:
    """Create a QScrollArea page with a vertical content layout."""
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    content = QWidget()
    content.setObjectName("StageContent")
    layout = QVBoxLayout(content)
    layout.setContentsMargins(20, 20, 20, 20)
    layout.setSpacing(14)
    scroll.setWidget(content)
    return scroll, content, layout


def style_button(
    btn: QPushButton,
    text: str,
    *,
    variant: str = "secondary",
    icons: LucideIconLibrary | None = None,
    theme: dict[str, str] = LIGHT_THEME,
    icon_name: str | None = None,
) -> QPushButton:
    btn.setText(text)
    btn.setProperty("variant", variant)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setProperty("icon_name_override", icon_name or "")
    refresh_button_icon(btn, icons=icons, theme=theme)
    btn.style().unpolish(btn)
    btn.style().polish(btn)
    return btn


def refresh_button_icon(btn: QPushButton, *, icons: LucideIconLibrary | None, theme: dict[str, str]):
    if icons is None:
        return
    override = btn.property("icon_name_override") or ""
    name = override or icon_name_for_label(btn.text(), BUTTON_ICONS)
    if not name:
        btn.setIcon(btn.icon())
        return
    variant = btn.property("variant") or "secondary"
    color = icon_color_for_variant(variant, theme)
    btn.setIconSize(QSize(15, 15))
    btn.setIcon(icons.get(name, color=color, size=15, disabled_color=theme["disabled_fg"]))


class QtDialogs:
    """Drop-in replacements for tkinter.messagebox / simpledialog / filedialog."""

    @staticmethod
    def showinfo(title: str, message: str, parent: QWidget | None = None):
        QMessageBox.information(parent or QApplication.activeWindow(), title, message)

    @staticmethod
    def showwarning(title: str, message: str, parent: QWidget | None = None):
        QMessageBox.warning(parent or QApplication.activeWindow(), title, message)

    @staticmethod
    def showerror(title: str, message: str, parent: QWidget | None = None):
        QMessageBox.critical(parent or QApplication.activeWindow(), title, message)

    @staticmethod
    def askyesno(title: str, message: str, parent: QWidget | None = None) -> bool:
        reply = QMessageBox.question(
            parent or QApplication.activeWindow(),
            title,
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return reply == QMessageBox.StandardButton.Yes

    @staticmethod
    def askstring(title: str, prompt: str, *, parent: QWidget | None = None, show: str | None = None) -> str | None:
        echo = QLineEdit.EchoMode.Password if show else QLineEdit.EchoMode.Normal
        text, ok = QInputDialog.getText(parent or QApplication.activeWindow(), title, prompt, echo)
        return text if ok else None

    @staticmethod
    def askdirectory(title: str = "Select folder", initialdir: str = "", parent: QWidget | None = None) -> str:
        return QFileDialog.getExistingDirectory(parent or QApplication.activeWindow(), title, initialdir or "")

    @staticmethod
    def askopenfilename(title: str = "Select file", filetypes=None, parent: QWidget | None = None) -> str:
        filter_str = _to_qt_file_filter(filetypes)
        path, _ = QFileDialog.getOpenFileName(parent or QApplication.activeWindow(), title, "", filter_str)
        return path

    @staticmethod
    def asksaveasfilename(
        title: str = "Save file",
        initialdir: str = "",
        initialfile: str = "",
        defaultextension: str = "",
        filetypes=None,
        parent: QWidget | None = None,
    ) -> str:
        start = initialdir or ""
        if initialfile:
            import os

            start = os.path.join(start, initialfile) if start else initialfile
        filter_str = _to_qt_file_filter(filetypes)
        path, _ = QFileDialog.getSaveFileName(parent or QApplication.activeWindow(), title, start, filter_str)
        if path and defaultextension and "." not in path.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]:
            path += defaultextension
        return path


def _to_qt_file_filter(filetypes) -> str:
    if not filetypes:
        return "All files (*)"
    parts = []
    for label, pattern in filetypes:
        parts.append(f"{label} ({pattern})")
    return ";;".join(parts)
