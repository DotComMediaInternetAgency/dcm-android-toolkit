"""Modern PySide6 theme, QSS stylesheet builder, and offline Lucide SVG icon library."""
from __future__ import annotations

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

LIGHT_THEME = {
    "mode": "light",
    "bg_canvas": "#f3f5f8",
    "bg_surface": "#ffffff",
    "bg_input": "#ffffff",
    "bg_subtle": "#eef2f6",
    "bg_nav_active": "#e6f4f1",
    "bg_nav_hover": "#f1f5f9",
    "border": "#dce3ec",
    "border_strong": "#cbd5e1",
    "text_primary": "#0f172a",
    "text_secondary": "#475569",
    "text_muted": "#64748b",
    "nav_active_fg": "#0f766e",
    "accent": "#0f766e",
    "accent_soft": "#ccfbf1",
    "accent_hover": "#0d5f59",
    "accent_pressed": "#0a4c47",
    "build": "#1d4ed8",
    "build_hover": "#1e40af",
    "build_pressed": "#1e3a8a",
    "info_btn": "#0369a1",
    "info_btn_hover": "#075985",
    "info_btn_pressed": "#0c4a6e",
    "warning_bg": "#fef3c7",
    "warning_fg": "#92400e",
    "warning_hover": "#fde68a",
    "warning_pressed": "#fcd34d",
    "warning_border": "#fcd34d",
    "danger_bg": "#fef2f2",
    "danger_fg": "#b91c1c",
    "danger_hover": "#fee2e2",
    "danger_pressed": "#fecaca",
    "danger_border": "#fecaca",
    "high_fg": "#c83932",
    "pill_ok_bg": "#dcfce7",
    "pill_ok_fg": "#166534",
    "pill_ok_border": "#bbf7d0",
    "pill_idle_bg": "#e2e8f0",
    "pill_idle_fg": "#475569",
    "pill_idle_border": "#cbd5e1",
    "console_bg": "#0f172a",
    "console_header": "#162033",
    "console_fg": "#e2e8f0",
    "console_error": "#fca5a5",
    "console_warn": "#fcd34d",
    "console_success": "#86efac",
    "disabled_bg": "#e2e8f0",
    "disabled_fg": "#94a3b8",
    "code_bg": "#f8fafc",
    "scrollbar_thumb": "#cbd5e1",
    "scrollbar_hover": "#94a3b8",
}

DARK_THEME = {
    "mode": "dark",
    "bg_canvas": "#0b1120",
    "bg_surface": "#111827",
    "bg_input": "#1e293b",
    "bg_subtle": "#1e293b",
    "bg_nav_active": "#134e4a",
    "bg_nav_hover": "#1e293b",
    "border": "#1e293b",
    "border_strong": "#334155",
    "text_primary": "#f8fafc",
    "text_secondary": "#cbd5e1",
    "text_muted": "#94a3b8",
    "nav_active_fg": "#5eead4",
    "accent": "#0f766e",
    "accent_soft": "#134e4a",
    "accent_hover": "#115e59",
    "accent_pressed": "#134e4a",
    "build": "#2563eb",
    "build_hover": "#1d4ed8",
    "build_pressed": "#1e40af",
    "info_btn": "#0284c7",
    "info_btn_hover": "#0369a1",
    "info_btn_pressed": "#075985",
    "warning_bg": "#451a03",
    "warning_fg": "#fcd34d",
    "warning_hover": "#78350f",
    "warning_pressed": "#92400e",
    "warning_border": "#92400e",
    "danger_bg": "#450a0a",
    "danger_fg": "#fca5a5",
    "danger_hover": "#7f1d1d",
    "danger_pressed": "#991b1b",
    "danger_border": "#991b1b",
    "high_fg": "#f87171",
    "pill_ok_bg": "#052e16",
    "pill_ok_fg": "#86efac",
    "pill_ok_border": "#166534",
    "pill_idle_bg": "#1e293b",
    "pill_idle_fg": "#94a3b8",
    "pill_idle_border": "#334155",
    "console_bg": "#090e1a",
    "console_header": "#111827",
    "console_fg": "#e2e8f0",
    "console_error": "#fca5a5",
    "console_warn": "#fcd34d",
    "console_success": "#86efac",
    "disabled_bg": "#1e293b",
    "disabled_fg": "#64748b",
    "code_bg": "#0f172a",
    "scrollbar_thumb": "#334155",
    "scrollbar_hover": "#475569",
}

LUCIDE_PATHS = {
    "link": '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>',
    "unlink": '<path d="m18.84 12.25 1.72-1.71h-.02a5.004 5.004 0 0 0-.12-7.07 5.006 5.006 0 0 0-6.95 0l-1.72 1.71"/><path d="m5.17 11.75-1.71 1.71a5.004 5.004 0 0 0 .12 7.07 5.006 5.006 0 0 0 6.95 0l1.71-1.71"/><line x1="8" x2="8" y1="2" y2="5"/><line x1="2" x2="5" y1="8" y2="8"/><line x1="16" x2="16" y1="19" y2="22"/><line x1="19" x2="22" y1="16" y2="16"/>',
    "package": '<path d="M11 21.73a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73z"/><path d="M12 22V12"/><path d="m3.3 7 7.703 4.734a2 2 0 0 0 1.994 0L20.7 7"/><path d="m7.5 4.27 9 5.15"/>',
    "mail": '<rect width="20" height="16" x="2" y="4" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/>',
    "search": '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
    "monitor": '<rect width="20" height="14" x="2" y="3" rx="2"/><line x1="8" x2="16" y1="21" y2="21"/><line x1="12" x2="12" y1="17" y2="21"/>',
    "smartphone": '<rect width="14" height="20" x="5" y="2" rx="2" ry="2"/><path d="M12 18h.01"/>',
    "sliders-horizontal": '<line x1="21" x2="14" y1="4" y2="4"/><line x1="10" x2="3" y1="4" y2="4"/><line x1="21" x2="12" y1="12" y2="12"/><line x1="8" x2="3" y1="12" y2="12"/><line x1="21" x2="16" y1="20" y2="20"/><line x1="12" x2="3" y1="20" y2="20"/><line x1="14" x2="14" y1="2" y2="6"/><line x1="8" x2="8" y1="10" y2="14"/><line x1="16" x2="16" y1="18" y2="22"/>',
    "info": '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>',
    "wifi": '<path d="M12 20h.01"/><path d="M2 8.82a15 15 0 0 1 20 0"/><path d="M5 12.859a10 10 0 0 1 14 0"/><path d="M8.5 16.429a5 5 0 0 1 7 0"/>',
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/>',
    "moon": '<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/>',
    "refresh-cw": '<path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M8 16H3v5"/>',
    "crosshair": '<circle cx="12" cy="12" r="10"/><line x1="22" x2="18" y1="12" y2="12"/><line x1="6" x2="2" y1="12" y2="12"/><line x1="12" x2="12" y1="6" y2="2"/><line x1="12" x2="12" y1="22" y2="18"/>',
    "save": '<path d="M15.2 3a2 2 0 0 1 1.4.6l3.8 3.8a2 2 0 0 1 .6 1.4V19a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z"/><path d="M17 21v-7a1 1 0 0 0-1-1H8a1 1 0 0 0-1 1v7"/><path d="M7 3v4a1 1 0 0 0 1 1h7"/>',
    "plus": '<path d="M5 12h14"/><path d="M12 5v14"/>',
    "play": '<polygon points="6 3 20 12 6 21 6 3"/>',
    "square": '<rect width="14" height="14" x="5" y="5" rx="2"/>',
    "download": '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/>',
    "trash-2": '<path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/><line x1="10" x2="10" y1="11" y2="17"/><line x1="14" x2="14" y1="11" y2="17"/>',
    "history": '<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M12 7v5l4 2"/>',
    "external-link": '<path d="M15 3h6v6"/><path d="M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>',
    "flag": '<path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><line x1="4" x2="4" y1="22" y2="15"/>',
    "folder": '<path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/>',
    "copy": '<rect width="14" height="14" x="8" y="8" rx="2" ry="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/>',
    "file-text": '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M10 9H8"/><path d="M16 13H8"/><path d="M16 17H8"/>',
    "rotate-ccw": '<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/>',
    "alert-triangle": '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
    "check": '<path d="M20 6 9 17l-5-5"/>',
    "x": '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
}

TAB_ICONS = {
    "connection": "link",
    "apk": "package",
    "sms export": "mail",
    "apps": "package",
    "subnet scan": "search",
    "watch screen": "monitor",
    "emulator": "smartphone",
    "debug": "sliders-horizontal",
    "about": "info",
}

BUTTON_ICONS = {
    "checking…": "refresh-cw",
    "building…": "refresh-cw",
    "check for updates": "refresh-cw",
    "website": "external-link",
    "report a bug…": "flag",
    "copy email address": "copy",
    "refresh": "refresh-cw",
    "refresh devices": "refresh-cw",
    "refresh emulators": "refresh-cw",
    "start emulator": "play",
    "stop emulator": "square",
    "connect emulator": "link",
    "download emulator": "download",
    "download & create avd": "download",
    "connect usb": "link",
    "connect wi-fi": "link",
    "usb": "link",
    "wi-fi": "wifi",
    "use fixed ip": "crosshair",
    "keep screen awake while charging": "sun",
    "pair…": "link",
    "scan subnet…": "search",
    "scan subnet": "search",
    "disconnect": "unlink",
    "save project": "save",
    "add project…": "plus",
    "browse…": "folder",
    "choose…": "folder",
    "choose output folder…": "folder",
    "build apk…": "play",
    "install / overwrite": "download",
    "remove app from device": "trash-2",
    "version history…": "history",
    "read sms count": "mail",
    "preview 2 sms": "file-text",
    "export sms to json": "download",
    "open screen window": "monitor",
    "scan debug state": "refresh-cw",
    "export diagnostic report and error log…": "file-text",
    "clean stale temporary files…": "trash-2",
    "uninstall emulator package…": "trash-2",
    "remove bootstrap tools…": "trash-2",
    "clear apk history…": "trash-2",
    "reset saved settings…": "rotate-ccw",
    "copy": "copy",
    "clear": "trash-2",
}


class LucideIconLibrary:
    """Renders offline Lucide SVG paths into crisp HiDPI QIcons."""

    def __init__(self):
        self._cache: dict[tuple[str, str, int, str], QIcon] = {}

    def _render_pixmap(self, name: str, color: str, size: int) -> QPixmap:
        paths = LUCIDE_PATHS.get(name, "")
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
            f'fill="none" stroke="{color}" stroke-width="2" '
            f'stroke-linecap="round" stroke-linejoin="round">{paths}</svg>'
        )
        renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
        scale = 2
        pixmap = QPixmap(size * scale, size * scale)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter, QRectF(0, 0, size * scale, size * scale))
        painter.end()
        pixmap.setDevicePixelRatio(scale)
        return pixmap

    def get(self, name: str, color: str = "#0f172a", size: int = 16, disabled_color: str = "#94a3b8") -> QIcon:
        key = (name, color, size, disabled_color)
        if key not in self._cache:
            icon = QIcon()
            icon.addPixmap(self._render_pixmap(name, color, size), QIcon.Mode.Normal, QIcon.State.Off)
            icon.addPixmap(self._render_pixmap(name, disabled_color, size), QIcon.Mode.Disabled, QIcon.State.Off)
            self._cache[key] = icon
        return self._cache[key]


def icon_name_for_label(label: str, mapping: dict[str, str] | None = None) -> str | None:
    cleaned = " ".join(str(label or "").strip().split()).casefold()
    if not cleaned:
        return None
    source = mapping or BUTTON_ICONS
    if cleaned in source:
        return source[cleaned]
    for prefix, icon_name in source.items():
        if cleaned.startswith(prefix):
            return icon_name
    return None


def icon_color_for_variant(variant: str, theme: dict[str, str]) -> str:
    if variant in ("accent", "build", "info"):
        return "#ffffff"
    if variant == "danger":
        return theme["danger_fg"]
    if variant == "warning":
        return theme["warning_fg"]
    if variant == "console":
        return "#cbd5e1"
    return theme["text_primary"]


def build_qss(theme: dict[str, str]) -> str:
    c = theme
    return f"""
    QMainWindow, QDialog {{
        background-color: {c["bg_canvas"]};
        color: {c["text_primary"]};
    }}
    QWidget {{
        color: {c["text_primary"]};
        font-family: "SF Pro Text", "Segoe UI", "Helvetica Neue", Arial, sans-serif;
        font-size: 13px;
    }}
    QWidget#HeaderBar {{
        background-color: {c["bg_surface"]};
        border-bottom: 1px solid {c["border"]};
    }}
    QLabel#HeaderTitle {{
        font-size: 18px;
        font-weight: 700;
        color: {c["text_primary"]};
    }}
    QLabel#HeaderVersion {{
        background-color: {c["bg_subtle"]};
        color: {c["text_secondary"]};
        border: 1px solid {c["border"]};
        border-radius: 6px;
        padding: 2px 8px;
        font-size: 12px;
        font-weight: 700;
    }}
    QLabel#HeaderSubtitle {{
        color: {c["text_muted"]};
        font-size: 12px;
    }}
    QLabel#ProjectPill {{
        background-color: {c["bg_subtle"]};
        color: {c["text_primary"]};
        border: 1px solid {c["border"]};
        border-radius: 7px;
        padding: 5px 10px;
        font-size: 12px;
        font-weight: 600;
    }}
    QLabel#DevicePill[connected="true"] {{
        background-color: {c["pill_ok_bg"]};
        color: {c["pill_ok_fg"]};
        border: 1px solid {c["pill_ok_border"]};
        border-radius: 7px;
        padding: 5px 10px;
        font-size: 12px;
        font-weight: 600;
    }}
    QLabel#DevicePill[connected="false"] {{
        background-color: {c["pill_idle_bg"]};
        color: {c["pill_idle_fg"]};
        border: 1px solid {c["pill_idle_border"]};
        border-radius: 7px;
        padding: 5px 10px;
        font-size: 12px;
        font-weight: 600;
    }}
    QFrame#WorkspaceShell {{
        background-color: {c["bg_canvas"]};
        border: 1px solid {c["border"]};
        border-radius: 10px;
    }}
    QFrame#SidebarRail {{
        background-color: {c["bg_surface"]};
        border-right: 1px solid {c["border"]};
        border-top-left-radius: 10px;
        border-bottom-left-radius: 10px;
    }}
    QLabel#NavSection {{
        color: {c["text_muted"]};
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        padding: 8px 10px 3px 10px;
    }}
    QPushButton[navItem="true"] {{
        background-color: transparent;
        color: {c["text_secondary"]};
        border: none;
        border-left: 3px solid transparent;
        border-radius: 7px;
        padding: 8px 10px;
        text-align: left;
        font-size: 13px;
        font-weight: 500;
    }}
    QPushButton[navItem="true"]:hover {{
        background-color: {c["bg_nav_hover"]};
        color: {c["text_primary"]};
    }}
    QPushButton[navItem="true"][active="true"] {{
        background-color: {c["bg_nav_active"]};
        color: {c["nav_active_fg"]};
        border-left: 3px solid {c["accent"]};
        font-weight: 600;
    }}
    QScrollArea {{
        background-color: transparent;
        border: none;
    }}
    QWidget#StageContent {{
        background-color: {c["bg_canvas"]};
    }}
    QLabel#PageTitle {{
        font-size: 18px;
        font-weight: 700;
        color: {c["text_primary"]};
    }}
    QLabel#PageSubtitle {{
        font-size: 13px;
        color: {c["text_muted"]};
    }}
    QFrame#Divider {{
        background-color: {c["border"]};
        max-height: 1px;
        min-height: 1px;
        border: none;
    }}
    QFrame[card="true"] {{
        background-color: {c["bg_surface"]};
        border: 1px solid {c["border"]};
        border-radius: 10px;
    }}
    QLabel[sectionTitle="true"] {{
        font-size: 13px;
        font-weight: 700;
        color: {c["text_primary"]};
    }}
    QLabel[cardSub="true"] {{
        font-size: 12px;
        color: {c["text_muted"]};
    }}
    QLabel#WarningBanner {{
        background-color: {c["warning_bg"]};
        color: {c["warning_fg"]};
        border: 1px solid {c["warning_border"]};
        border-radius: 8px;
        padding: 8px 12px;
        font-size: 12px;
    }}
    QLineEdit, QComboBox {{
        background-color: {c["bg_input"]};
        color: {c["text_primary"]};
        border: 1px solid {c["border_strong"]};
        border-radius: 7px;
        padding: 6px 10px;
        min-height: 20px;
        font-size: 13px;
    }}
    QComboBox {{
        combobox-popup: 0;
        padding-right: 30px;
    }}
    QLineEdit:focus, QComboBox:focus {{
        border: 1.5px solid {c["accent"]};
    }}
    QLineEdit:disabled, QComboBox:disabled {{
        background-color: {c["disabled_bg"]};
        color: {c["disabled_fg"]};
    }}
    QComboBox::drop-down {{
        border: none;
        border-left: 1px solid {c["border"]};
        border-top-right-radius: 6px;
        border-bottom-right-radius: 6px;
        background-color: {c["bg_subtle"]};
        width: 28px;
    }}
    QComboBox::drop-down:hover {{
        background-color: {c["bg_nav_hover"]};
    }}
    QComboBox::down-arrow {{
        width: 0;
        height: 0;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 6px solid {c["text_secondary"]};
    }}
    QComboBox QAbstractItemView {{
        background-color: {c["bg_surface"]};
        color: {c["text_primary"]};
        border: 1px solid {c["border_strong"]};
        selection-background-color: {c["accent"]};
        selection-color: #ffffff;
        border-radius: 6px;
        padding: 4px;
        outline: 0;
    }}
    QComboBox QAbstractItemView::item {{
        min-height: 28px;
        padding: 4px 8px;
        border: none;
    }}
    QPlainTextEdit[monoCard="true"] {{
        background-color: {c["code_bg"]};
        color: {c["text_primary"]};
        border: 1px solid {c["border"]};
        border-radius: 8px;
        padding: 8px;
        font-family: "Menlo", "Consolas", "SF Mono", monospace;
        font-size: 12px;
    }}
    QPushButton {{
        background-color: {c["bg_surface"]};
        color: {c["text_primary"]};
        border: 1px solid {c["border_strong"]};
        border-radius: 7px;
        padding: 7px 13px;
        font-size: 12px;
        font-weight: 600;
    }}
    QPushButton:hover {{
        background-color: {c["bg_nav_hover"]};
    }}
    QPushButton:pressed {{
        background-color: {c["bg_subtle"]};
    }}
    QPushButton:disabled {{
        background-color: {c["disabled_bg"]};
        color: {c["disabled_fg"]};
        border-color: {c["border"]};
    }}
    QPushButton[variant="accent"] {{
        background-color: {c["accent"]};
        color: #ffffff;
        border: 1px solid {c["accent"]};
    }}
    QPushButton[variant="accent"]:hover {{
        background-color: {c["accent_hover"]};
        border-color: {c["accent_hover"]};
    }}
    QPushButton[variant="accent"]:pressed {{
        background-color: {c["accent_pressed"]};
    }}
    QPushButton[variant="accent"]:disabled {{
        background-color: {c["disabled_bg"]};
        color: {c["disabled_fg"]};
        border-color: {c["border"]};
    }}
    QPushButton[variant="build"] {{
        background-color: {c["build"]};
        color: #ffffff;
        border: 1px solid {c["build"]};
    }}
    QPushButton[variant="build"]:hover {{
        background-color: {c["build_hover"]};
        border-color: {c["build_hover"]};
    }}
    QPushButton[variant="build"]:pressed {{
        background-color: {c["build_pressed"]};
    }}
    QPushButton[variant="build"]:disabled {{
        background-color: {c["disabled_bg"]};
        color: {c["disabled_fg"]};
        border-color: {c["border"]};
    }}
    QPushButton[variant="info"] {{
        background-color: {c["info_btn"]};
        color: #ffffff;
        border: 1px solid {c["info_btn"]};
    }}
    QPushButton[variant="info"]:hover {{
        background-color: {c["info_btn_hover"]};
        border-color: {c["info_btn_hover"]};
    }}
    QPushButton[variant="info"]:pressed {{
        background-color: {c["info_btn_pressed"]};
    }}
    QPushButton[variant="info"]:disabled {{
        background-color: {c["disabled_bg"]};
        color: {c["disabled_fg"]};
        border-color: {c["border"]};
    }}
    QPushButton[variant="warning"] {{
        background-color: {c["warning_bg"]};
        color: {c["warning_fg"]};
        border: 1px solid {c["warning_border"]};
    }}
    QPushButton[variant="warning"]:hover {{
        background-color: {c["warning_hover"]};
    }}
    QPushButton[variant="warning"]:pressed {{
        background-color: {c["warning_pressed"]};
    }}
    QPushButton[variant="danger"] {{
        background-color: {c["danger_bg"]};
        color: {c["danger_fg"]};
        border: 1px solid {c["danger_border"]};
    }}
    QPushButton[variant="danger"]:hover {{
        background-color: {c["danger_hover"]};
    }}
    QPushButton[variant="danger"]:pressed {{
        background-color: {c["danger_pressed"]};
    }}
    QPushButton[variant="theme"] {{
        background-color: {c["bg_subtle"]};
        color: {c["text_primary"]};
        border: 1px solid {c["border_strong"]};
        border-radius: 7px;
        padding: 5px 10px;
        font-size: 12px;
        font-weight: 600;
    }}
    QPushButton[variant="theme"]:hover {{
        background-color: {c["bg_nav_hover"]};
    }}
    QCheckBox, QRadioButton {{
        spacing: 6px;
        font-size: 13px;
        color: {c["text_primary"]};
    }}
    QCheckBox#KeepAwakeCheck::indicator {{
        width: 18px;
        height: 18px;
        border: 2px solid {c["border_strong"]};
        border-radius: 4px;
        background-color: {c["bg_surface"]};
    }}
    QCheckBox#KeepAwakeCheck::indicator:hover {{
        border-color: {c["accent"]};
    }}
    QCheckBox#KeepAwakeCheck::indicator:checked {{
        border-color: {c["accent"]};
        background-color: {c["accent"]};
    }}
    QCheckBox#KeepAwakeCheck::indicator:disabled {{
        border-color: {c["border"]};
        background-color: {c["disabled_bg"]};
    }}
    QRadioButton[connectionMethod="true"] {{
        spacing: 8px;
        padding: 5px 9px;
        border: 1px solid transparent;
        border-radius: 7px;
    }}
    QRadioButton[connectionMethod="true"]:checked {{
        color: {c["nav_active_fg"]};
        background-color: {c["bg_nav_active"]};
        border-color: {c["accent"]};
        font-weight: 700;
    }}
    QRadioButton[connectionMethod="true"]::indicator {{
        width: 16px;
        height: 16px;
        border: 2px solid {c["text_muted"]};
        border-radius: 9px;
        background-color: {c["bg_surface"]};
    }}
    QRadioButton[connectionMethod="true"]::indicator:checked {{
        border-color: {c["accent"]};
        background-color: {c["accent"]};
    }}
    QRadioButton[connectionMethod="true"]::indicator:unchecked:hover {{
        border-color: {c["accent"]};
    }}
    QSlider::groove:horizontal {{
        height: 6px;
        background: {c["bg_subtle"]};
        border-radius: 3px;
    }}
    QSlider::sub-page:horizontal {{
        background: {c["accent"]};
        border-radius: 3px;
    }}
    QSlider::handle:horizontal {{
        background: {c["accent"]};
        width: 16px;
        height: 16px;
        margin: -5px 0;
        border-radius: 8px;
    }}
    QSplitter::handle:vertical {{
        height: 10px;
        background: transparent;
    }}
    QFrame#ActivityShell {{
        background-color: {c["console_bg"]};
        border: 1px solid {c["border_strong"]};
        border-radius: 10px;
    }}
    QWidget#ActivityHeader {{
        background-color: {c["console_header"]};
        border-top-left-radius: 9px;
        border-top-right-radius: 9px;
    }}
    QLabel#ActivityTitle {{
        color: #94a3b8;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.6px;
    }}
    QLabel#ActivityHint {{
        color: #64748b;
        font-size: 11px;
    }}
    QPushButton[variant="console"] {{
        background-color: #1e293b;
        color: #cbd5e1;
        border: 1px solid #334155;
        border-radius: 5px;
        padding: 3px 9px;
        font-size: 11px;
        font-weight: 600;
    }}
    QPushButton[variant="console"]:hover {{
        background-color: #334155;
        color: #ffffff;
    }}
    QCheckBox#ConsoleAutoScroll {{
        color: #cbd5e1;
        font-size: 11px;
    }}
    QPlainTextEdit#ActivityLog {{
        background-color: {c["console_bg"]};
        color: {c["console_fg"]};
        border: none;
        border-bottom-left-radius: 9px;
        border-bottom-right-radius: 9px;
        padding: 10px 12px;
        font-family: "Menlo", "Consolas", "SF Mono", monospace;
        font-size: 12px;
    }}
    QFrame#BuildStatusRow {{
        background-color: {c["bg_surface"]};
        border: 1px solid {c["border"]};
        border-radius: 8px;
    }}
    QProgressBar {{
        background-color: {c["bg_subtle"]};
        border: none;
        border-radius: 4px;
        height: 8px;
        text-align: center;
    }}
    QProgressBar::chunk {{
        background-color: {c["build"]};
        border-radius: 4px;
    }}
    QWidget#FooterBar {{
        background-color: {c["bg_surface"]};
        border-top: 1px solid {c["border"]};
    }}
    QLabel#FooterStatus {{
        color: {c["text_secondary"]};
        font-size: 12px;
    }}
    QTableWidget {{
        background-color: {c["bg_surface"]};
        color: {c["text_primary"]};
        gridline-color: {c["border"]};
        border: 1px solid {c["border"]};
        border-radius: 8px;
        selection-background-color: {c["accent"]};
        selection-color: #ffffff;
    }}
    QHeaderView::section {{
        background-color: {c["bg_subtle"]};
        color: {c["text_primary"]};
        border: none;
        border-bottom: 1px solid {c["border"]};
        padding: 6px 10px;
        font-weight: 600;
        font-size: 12px;
    }}
    QScrollBar:vertical {{
        background: transparent;
        width: 8px;
        margin: 2px;
    }}
    QScrollBar::handle:vertical {{
        background: {c["scrollbar_thumb"]};
        border-radius: 4px;
        min-height: 24px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {c["scrollbar_hover"]};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    """
