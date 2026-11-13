#!/usr/bin/env python3
"""Desktop toolkit for managing APK builds and Android devices across projects."""
from __future__ import annotations

import json
import math
import os
import platform
import shutil
import socket
import struct
import subprocess
import threading
import ipaddress
import queue
import re
import signal
import time
import sys
import webbrowser
import urllib.error
import urllib.request
import ssl
import hashlib
import stat
import tempfile
import zipfile
import zlib
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from pathlib import PurePosixPath
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCloseEvent, QColor, QKeySequence, QShortcut, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSlider,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from qt_theme import (
    BUTTON_ICONS,
    DARK_THEME,
    LIGHT_THEME,
    LucideIconLibrary,
    build_qss,
)
from qt_widgets import (
    FlowLayout,
    QtDialogs,
    SidebarNavigator,
    StateVar,
    UiDispatcher,
    bind_checkbox,
    bind_combo_box,
    bind_label,
    bind_line_edit,
    bind_radio,
    bind_slider,
    make_card,
    make_divider,
    make_scrollable_page,
    refresh_button_icon,
    style_button,
)

messagebox = QtDialogs
filedialog = QtDialogs
simpledialog = QtDialogs
UI_COLORS = LIGHT_THEME

APP_ROOT = Path(__file__).resolve().parent
HERE = APP_ROOT
CONFIG = APP_ROOT / "dcm-android-toolkit.json"
ERROR_LOG = APP_ROOT / "data" / "logs" / "application-errors.log"
MAX_ERROR_LOG_BYTES = 512 * 1024
APK_ARCHIVE = APP_ROOT / "data" / "apk_versions"
APK_HISTORY = APP_ROOT / "data" / "apk_versions.json"
APP_VERSION = "0.1.4.10"
GITHUB_REPOSITORY = "DotComMediaInternetAgency/dcm-android-toolkit"
BUG_REPORT_EMAIL = "dotcommediainternetagency@gmail.com"

MAX_UPDATE_ARCHIVE_BYTES = 100 * 1024 * 1024
CMDLINE_TOOLS_BUILD = "15859902"
CMDLINE_TOOLS_DOWNLOADS = {
    ("Windows", "amd64"): (
        "https://dl.google.com/android/repository/commandlinetools-win-15859902_latest.zip",
        "90ae805d20434428bffcb699c290860f19bb5f66a67e6b330067e3de801fb04a",
    ),
    ("Darwin", "arm64"): (
        "https://dl.google.com/android/repository/commandlinetools-mac_arm64-15859902_latest.zip",
        "835b62a26162b229b441d1f6d4680383815a270809eb33522c0d480fa5002c4e",
    ),
    ("Darwin", "x86_64"): (
        "https://dl.google.com/android/repository/commandlinetools-mac_x86_64-15859902_latest.zip",
        "c5a6378ab5cf7e0d5701921405115befff13e9ff7417fb588389338f8bd050f3",
    ),
    ("Linux", "x86_64"): (
        "https://dl.google.com/android/repository/commandlinetools-linux-15859902_latest.zip",
        "4e4c464f145a7512b57d088ac6c278c03c9eea610886b35a5e0804e74eedf583",
    ),
}
DEFAULT_AVD_API = 36
DEFAULT_AVD_NAME = "DCM_Toolkit_API36"
MAX_CMDLINE_TOOLS_ARCHIVE_BYTES = 250 * 1024 * 1024


def _windows_console_options(*, new_process_group=False):
    """Hide Windows console windows for background command-line helpers."""
    if os.name != "nt":
        return {}
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    if new_process_group:
        flags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    return {"creationflags": flags}

def load_config():
    try:
        return json.loads(CONFIG.read_text())
    except (OSError, json.JSONDecodeError):
        return {
            "project_dir": "",
            "module": "app",
            "apk": "",
            "package": "",
            "project_name": "New project",
        }


class Deployer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DCM Android Toolkit")
        screen = QApplication.primaryScreen()
        avail = screen.availableGeometry() if screen else None
        screen_width = avail.width() if avail else 1280
        screen_height = avail.height() if avail else 860
        width, height = min(1080, max(320, screen_width - 64)), min(900, max(360, screen_height - 96))
        self.resize(width, height)
        if avail:
            self.move(
                avail.x() + max(0, (screen_width - width) // 2),
                avail.y() + max(0, (screen_height - height) // 2),
            )
        self.setMinimumSize(min(720, width), min(620, height))
        self._ui_dispatcher = UiDispatcher(self)
        self._icons = LucideIconLibrary()
        self._themed_buttons: list[QPushButton] = []
        self.config_data = load_config()
        self.theme_mode = str(self.config_data.get("theme_mode", "light")).lower()
        if self.theme_mode not in ("light", "dark"):
            self.theme_mode = "light"
        self.current_theme = DARK_THEME if self.theme_mode == "dark" else LIGHT_THEME
        self.error_log_lock = threading.Lock()
        self.recent_errors = []
        self.previous_threading_excepthook = threading.excepthook
        threading.excepthook = self._report_thread_exception
        self.project_profiles = {
            item.get("name", ""): item
            for item in self.config_data.get("projects", [])
            if isinstance(item, dict) and item.get("name")
        }
        if not self.project_profiles:
            legacy_name = str(self.config_data.get("project_name") or "New project")
            self.project_profiles[legacy_name] = {
                "name": legacy_name,
                "project_dir": self.config_data.get("project_dir", ""),
                "module": self.config_data.get("module", "app"),
                "apk": self.config_data.get("apk", ""),
                "package": self.config_data.get("package", ""),
            }
        self.active_project_name = str(self.config_data.get("selected_project") or next(iter(self.project_profiles)))
        if self.active_project_name not in self.project_profiles:
            self.active_project_name = next(iter(self.project_profiles))
        active_project = self.project_profiles[self.active_project_name]
        self.project_name = StateVar(self.active_project_name, str, self)
        self.project_dir = StateVar(str(active_project.get("project_dir", "")), str, self)
        self.module = StateVar(str(active_project.get("module", "app")), str, self)
        self.apk = StateVar(str(active_project.get("apk", "")), str, self)
        self.package = StateVar(str(active_project.get("package", "")), str, self)
        self.adb = self._find_adb(self.project_dir.get())
        self.emulator_executable = self._find_emulator(self.adb, self.project_dir.get())
        self.android_cli = shutil.which("android") if os.name != "nt" else None
        self.android_sdk_roots = self._find_android_sdk_roots(self.adb, self.project_dir.get(), self.emulator_executable)
        configured_sdk = os.environ.get("ANDROID_SDK_ROOT", "").strip() or os.environ.get("ANDROID_HOME", "").strip()
        self.android_sdk_root = Path(configured_sdk).expanduser() if configured_sdk else next(
            (root for root in self.android_sdk_roots if root.is_dir()), None
        )
        if self.android_sdk_root is None:
            if os.name == "nt":
                local_app_data = os.environ.get("LOCALAPPDATA", "").strip()
                self.android_sdk_root = (
                    Path(local_app_data) / "Android" / "Sdk"
                    if local_app_data
                    else Path.home() / "AppData" / "Local" / "Android" / "Sdk"
                )
            elif sys.platform == "darwin":
                self.android_sdk_root = Path.home() / "Library" / "Android" / "sdk"
            else:
                self.android_sdk_root = Path.home() / "Android" / "Sdk"
            if self.android_sdk_root not in self.android_sdk_roots:
                self.android_sdk_roots.append(self.android_sdk_root)
        self.sdkmanager_executable = self._find_sdkmanager(self.android_sdk_roots)
        self.avdmanager_executable = self._find_avdmanager(self.android_sdk_roots)
        if self.android_sdk_root is None and self.sdkmanager_executable:
            manager_path = Path(self.sdkmanager_executable)
            if len(manager_path.parents) > 3 and manager_path.parent.parent.parent.name == "cmdline-tools":
                self.android_sdk_root = manager_path.parents[3]
                self.android_sdk_roots.insert(0, self.android_sdk_root)
        self.sdk_package_cli = shutil.which("android")
        self.target = StateVar("", str, self)
        self.install_target = StateVar(self.config_data.get("install_target", ""), str, self)
        self.available_device_serials = []
        self.install_target_serials = {}
        self.wifi = StateVar("", str, self)
        self.fixed_wifi = StateVar(self.config_data.get("fixed_wifi", ""), str, self)
        self.use_fixed_wifi = StateVar(bool(self.config_data.get("use_fixed_wifi", False)), bool, self)
        self.last_device = str(self.config_data.get("last_device") or self.config_data.get("fixed_wifi", "")).strip()
        self.last_device_method = self.config_data.get("last_device_method", "Wi-Fi" if ":" in self.last_device else "USB")
        self.connection_method = StateVar(self.config_data.get("connection_method", "Wi-Fi" if ":" in self.last_device else "USB"), str, self)
        if self.connection_method.get() not in ("USB", "Wi-Fi"):
            self.connection_method.set("USB")
        if ":" in self.last_device:
            self.wifi.set(self.last_device)
        self.connected_serial = None
        self.connected_model = ""
        self.keep_awake = StateVar(False, bool, self)
        self.keep_awake_original = None
        saved_display_settings = self.config_data.get("pending_display_settings", {})
        self.pending_display_settings = saved_display_settings if isinstance(saved_display_settings, dict) else {}
        has_saved_brightness = "brightness_level" in self.config_data
        saved_brightness = int(self.config_data.get("brightness_level", 78))
        if has_saved_brightness and self.config_data.get("brightness_level_unit") != "percent":
            saved_brightness = round(saved_brightness * 100 / 255)
        self.brightness_level = StateVar(max(0, min(100, saved_brightness)), int, self)
        self.brightness_text = StateVar(f"Brightness while awake: {self.brightness_level.get()}%", str, self)
        self.brightness_timer = None
        self.connection_widgets = []
        self.mirror_process = None
        self.subnet = StateVar("192.168.1.0/24", str, self)
        self.scan_port = StateVar("5555", str, self)
        self.export_dir = StateVar(str(APP_ROOT / "data"), str, self)
        self.sms_count_text = StateVar("SMS count not checked yet", str, self)
        self.build_type = StateVar("debug", str, self)
        self.build_status = StateVar("Ready to build", str, self)
        self.build_running = False
        self.closing = False
        self.update_running = False
        self.update_install_started = False
        self.update_download_cancel = threading.Event()
        self.debug_reset_config_on_close = False
        self.debug_sdk_remove_running = False
        self.debug_cleanup_running = False
        self.debug_version_scan_running = False
        self.debug_tool_versions = {}
        self.build_process = None
        self.build_process_lock = threading.Lock()
        self.emulator_avd = StateVar("", str, self)
        self.emulator_status = StateVar("Checking for Android Emulator…", str, self)
        self.emulator_avds = []
        self.emulator_states = {}
        self.emulator_busy = False
        self.emulator_refresh_running = False
        self.emulator_download_running = False
        self.emulator_download_process = None
        self.debug_sdk_process = None
        self.emulator_start_process = None
        self.emulator_start_serial = None
        self.emulator_processes = {}
        self.emulator_process_lock = threading.Lock()
        managed_emulator_items = self.config_data.get("managed_emulators", [])
        if not isinstance(managed_emulator_items, list):
            managed_emulator_items = []
        self.managed_emulators = {
            (str(item.get("avd", "")), str(item.get("serial", "")))
            for item in managed_emulator_items
            if isinstance(item, dict) and item.get("avd") and item.get("serial")
        }
        self.project_edit_widgets = []
        self.status = StateVar("ADB found" if self.adb else "ADB not found — install Android SDK Platform-Tools", str, self)
        self._build()
        self.apply_theme(self.theme_mode, save=False)
        self.after(250, self.refresh_emulators)
        self.after(1200, lambda: self.check_for_updates(manual=False))
        if self.adb:
            self.after(150, self.restore_previous_device)

    def after(self, ms, func=None):
        """Schedule a callable on the Qt main thread safely from any thread."""
        if func is None:
            return None
        if ms <= 0:
            self._ui_dispatcher.invoke.emit(func)
        else:
            self._ui_dispatcher.schedule.emit(ms, func)
        return None

    def closeEvent(self, event: QCloseEvent):
        if self.closing:
            event.accept()
            return
        self.close_app()
        if self.closing:
            event.accept()
        else:
            event.ignore()

    @staticmethod
    def _version_tuple(value):
        match = re.search(r"(?:^|[^0-9])v?(\d+(?:\.\d+)+)", str(value))
        if not match:
            return None
        parts = [int(part) for part in match.group(1).split(".")]
        return tuple(parts + [0] * max(0, 4 - len(parts)))

    @staticmethod
    def _style_to_variant(style_name: str | None) -> str:
        mapping = {
            "Accent.TButton": "accent",
            "Build.TButton": "build",
            "Info.TButton": "info",
            "Danger.TButton": "danger",
            "Warning.TButton": "warning",
            "TButton": "secondary",
        }
        return mapping.get(str(style_name or "TButton"), str(style_name or "secondary").lower())

    def _button(self, parent=None, *, text="", style="TButton", command=None, icon_name=None):
        btn = QPushButton(parent if isinstance(parent, QWidget) else None)
        variant = self._style_to_variant(style)
        style_button(btn, str(text), variant=variant, icons=self._icons, theme=self.current_theme, icon_name=icon_name)
        if command is not None:
            btn.clicked.connect(lambda _checked=False, cb=command: cb())
        self._themed_buttons.append(btn)
        return btn

    def _set_button_label(self, button: QPushButton, text: str, style: str | None = None):
        if style is not None:
            button.setProperty("variant", self._style_to_variant(style))
            button.style().unpolish(button)
            button.style().polish(button)
        button.setText(str(text))
        refresh_button_icon(button, icons=self._icons, theme=self.current_theme)

    def toggle_theme(self):
        next_mode = "dark" if self.theme_mode == "light" else "light"
        self.apply_theme(next_mode, save=True)

    def apply_theme(self, mode: str, *, save: bool = True):
        self.theme_mode = "dark" if mode == "dark" else "light"
        self.current_theme = DARK_THEME if self.theme_mode == "dark" else LIGHT_THEME
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(build_qss(self.current_theme))
        if hasattr(self, "tabs"):
            self.tabs.apply_theme(self.current_theme)
        alive_buttons = []
        for btn in self._themed_buttons:
            try:
                refresh_button_icon(btn, icons=self._icons, theme=self.current_theme)
                alive_buttons.append(btn)
            except RuntimeError:
                pass
        self._themed_buttons = alive_buttons
        if hasattr(self, "theme_toggle_button"):
            is_dark = self.theme_mode == "dark"
            self.theme_toggle_button.setText("Light" if is_dark else "Dark")
            self.theme_toggle_button.setProperty("icon_name_override", "sun" if is_dark else "moon")
            refresh_button_icon(self.theme_toggle_button, icons=self._icons, theme=self.current_theme)
        if hasattr(self, "header_project_pill"):
            self._update_header_pills()
        if save:
            self._save_config()

    def check_for_updates(self, manual=False):
        if getattr(self, "about_update_button", None) is not None:
            self._set_button_label(self.about_update_button, "Checking…")
            self.about_update_button.setEnabled(False)

        def worker():
            result = None
            error = None
            url = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/releases/latest"
            request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "DCM-Android-Toolkit"})
            try:
                with self._open_github_request(request) as response:
                    release = json.loads(response.read().decode("utf-8"))
                tag = str(release.get("tag_name", ""))
                latest = self._version_tuple(tag)
                current = self._version_tuple(APP_VERSION)
                if latest and current and latest > current:
                    result = release
                else:
                    result = None
            except (OSError, urllib.error.URLError, json.JSONDecodeError, ValueError) as exc:
                error = str(exc)
            self.after(0, lambda: self._update_check_finished(result, error, manual))

        threading.Thread(target=worker, daemon=True).start()

    @staticmethod
    def _open_github_request(request, timeout=8):
        """Use system TLS roots, falling back to certifi for incomplete Python CA stores."""
        try:
            return urllib.request.urlopen(request, timeout=timeout, context=ssl.create_default_context())
        except urllib.error.URLError as exc:
            if not isinstance(exc.reason, ssl.SSLCertVerificationError):
                raise
            try:
                import certifi
            except ImportError:
                raise exc
            context = ssl.create_default_context(cafile=certifi.where())
            return urllib.request.urlopen(request, timeout=timeout, context=context)

    def _update_check_finished(self, result, error, manual):
        if getattr(self, "about_update_button", None) is not None:
            self._set_button_label(self.about_update_button, "Check for updates")
            self.about_update_button.setEnabled(True)
        if result and result.get("tag_name"):
            tag = str(result["tag_name"])
            if messagebox.askyesno(
                "Update available",
                f"DCM Android Toolkit {tag} is available. Download and install it now? The app will restart.",
                parent=self,
            ):
                self._download_and_install_update(result)
        elif manual:
            if error:
                messagebox.showwarning("Update check failed", f"Could not check GitHub for updates.\n\n{error}")
            else:
                messagebox.showinfo("No updates available", f"You are using the latest version ({APP_VERSION}).")

    def _download_and_install_update(self, release):
        if self.update_running:
            return
        if self.build_running or self.emulator_download_running or self.emulator_busy:
            messagebox.showwarning(
                "Finish the current operation",
                "Wait for the current build or emulator operation to finish before updating.",
                parent=self,
            )
            return
        tag = str(release.get("tag_name", ""))
        version = tag[1:] if tag.lower().startswith("v") else tag
        expected_asset_name = f"dcm-android-toolkit-{version}-source.zip"
        asset = next(
            (item for item in release.get("assets", []) if item.get("name") == expected_asset_name),
            None,
        )
        digest = str(asset.get("digest", "")) if asset else ""
        download_url = str(asset.get("browser_download_url", "")) if asset else ""
        if not asset or not re.fullmatch(r"sha256:[0-9a-fA-F]{64}", digest) or not download_url.startswith("https://"):
            self.show_error(
                "Update unavailable",
                f"GitHub release {tag} does not contain a verifiable {expected_asset_name} asset.",
                parent=self,
            )
            return

        self.update_running = True
        self.update_install_started = False
        self.update_download_cancel.clear()
        self.status.set(f"Downloading DCM Android Toolkit {tag}…")
        if getattr(self, "about_update_button", None) is not None:
            self.about_update_button.setText("Downloading update…")
            self.about_update_button.setEnabled(False)
        self.log(f"Downloading update {tag} from GitHub Releases…")

        def worker():
            archive_path = None
            try:
                request = urllib.request.Request(
                    download_url,
                    headers={
                        "Accept": "application/octet-stream",
                        "User-Agent": "DCM-Android-Toolkit",
                    },
                )
                with self._open_github_request(request, timeout=30) as response:
                    if not response.geturl().startswith("https://"):
                        raise ValueError("GitHub redirected the update download to an insecure URL.")
                    content_length = response.headers.get("Content-Length")
                    if content_length and int(content_length) > MAX_UPDATE_ARCHIVE_BYTES:
                        raise ValueError("The update archive is larger than the 100 MB safety limit.")
                    handle, archive_path = tempfile.mkstemp(prefix="dcm-toolkit-update-", suffix=".zip")
                    digest_hash = hashlib.sha256()
                    total = 0
                    with os.fdopen(handle, "wb") as archive_file:
                        while True:
                            if self.update_download_cancel.is_set():
                                raise InterruptedError("Update download was canceled because the toolkit is closing.")
                            chunk = response.read(1024 * 1024)
                            if not chunk:
                                break
                            total += len(chunk)
                            if total > MAX_UPDATE_ARCHIVE_BYTES:
                                raise ValueError("The update archive exceeded the 100 MB safety limit.")
                            digest_hash.update(chunk)
                            archive_file.write(chunk)
                            if content_length:
                                self.after(
                                    0,
                                    self.status.set,
                                    f"Downloading update: {total / (1024 * 1024):.1f} MB",
                                )
                expected_digest = digest.split(":", 1)[1].lower()
                if digest_hash.hexdigest() != expected_digest:
                    raise ValueError("The downloaded update failed GitHub's SHA-256 digest check.")
                _validate_update_archive(archive_path, version)
                if self.closing or self.update_download_cancel.is_set():
                    os.unlink(archive_path)
                    return
                self.after(0, self._update_download_finished, archive_path, version, None, release)
            except Exception as error:
                if archive_path:
                    try:
                        os.unlink(archive_path)
                    except OSError:
                        pass
                if not self.closing:
                    self.after(0, self._update_download_finished, None, version, str(error), release)

        threading.Thread(target=worker, daemon=True).start()

    def _update_download_finished(self, archive_path, version, error, release):
        if self.closing:
            if archive_path:
                try:
                    os.unlink(archive_path)
                except OSError:
                    pass
            return
        if error:
            self.update_running = False
            self.status.set("Update download failed")
            self.log(f"Update download failed: {error}")
            if getattr(self, "about_update_button", None) is not None:
                self._set_button_label(self.about_update_button, "Check for updates")
                self.about_update_button.setEnabled(True)
            if messagebox.askyesno(
                "Could not install update",
                f"The update could not be installed automatically.\n\n{error}\n\nOpen the GitHub release page instead?",
                parent=self,
            ):
                webbrowser.open(str(release.get("html_url") or f"https://github.com/{GITHUB_REPOSITORY}/releases/latest"))
            return

        try:
            if self.keep_awake_original is not None and self.connected_serial:
                self._restore_keep_awake(self.connected_serial)
            self._save_config()
            helper_command = [
                sys.executable,
                str(Path(__file__).resolve()),
                "--apply-update",
                str(archive_path),
                str(APP_ROOT),
                str(os.getpid()),
                version,
            ]
            creationflags = 0
            if os.name == "nt":
                creationflags = getattr(subprocess, "DETACHED_PROCESS", 0)
            subprocess.Popen(
                helper_command,
                cwd=str(APP_ROOT),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=(os.name != "nt"),
                creationflags=creationflags,
            )
            self.update_install_started = True
            self.log(f"Verified update {version}; restarting to replace application files…")
            self.close_app()
        except Exception as start_error:
            self.update_running = False
            self.update_install_started = False
            try:
                os.unlink(archive_path)
            except OSError:
                pass
            if getattr(self, "about_update_button", None) is not None:
                self._set_button_label(self.about_update_button, "Check for updates")
                self.about_update_button.setEnabled(True)
            self.show_error("Could not start updater", str(start_error), parent=self)

    @staticmethod
    def _fit_dialog(dialog: QDialog, preferred=(900, 700), minimum=(640, 480)):
        """Size custom windows to the available display while keeping their footer in bounds."""
        screen = QApplication.primaryScreen()
        avail = screen.availableGeometry() if screen else None
        available_width = max(320, (avail.width() if avail else 1280) - 64)
        available_height = max(300, (avail.height() if avail else 860) - 96)
        width = min(preferred[0], available_width)
        height = min(preferred[1], available_height)
        dialog.resize(width, height)
        dialog.setMinimumSize(min(minimum[0], width), min(minimum[1], height))
        if avail:
            dialog.move(
                avail.x() + max(0, (avail.width() - width) // 2),
                avail.y() + max(0, (avail.height() - height) // 2),
            )
        return width, height

    @staticmethod
    def _find_adb(project_dir=""):
        """Prefer the selected Gradle project's SDK, then common SDK locations."""
        candidates = []
        roots = [Path(project_dir).expanduser()] if project_dir else []
        if roots:
            roots.append(roots[0] / "android")
            roots.append(roots[0].parent)
        for root in roots:
            local_properties = root / "local.properties"
            try:
                for line in local_properties.read_text(encoding="utf-8").splitlines():
                    if line.strip().startswith("sdk.dir="):
                        sdk_dir = line.split("=", 1)[1].strip().replace(r"\:", ":")
                        candidates.append(Path(sdk_dir).expanduser() / "platform-tools/adb")
                        break
            except OSError:
                pass
        import os
        for variable in ("ANDROID_SDK_ROOT", "ANDROID_HOME"):
            sdk_dir = os.environ.get(variable, "").strip()
            if sdk_dir:
                candidates.append(Path(sdk_dir).expanduser() / "platform-tools/adb")
        candidates.extend((
            Path.home() / "Library/Android/sdk/platform-tools/adb",
            Path("/opt/android-sdk/platform-tools/adb"),
        ))
        for candidate in candidates:
            if candidate.is_file() and candidate.stat().st_mode & 0o111:
                return str(candidate)
        return shutil.which("adb")

    @staticmethod
    def _find_android_sdk_roots(adb_path="", project_dir="", emulator_path=""):
        """Find configured and conventional Android SDK roots in preference order."""
        roots = []
        for variable in ("ANDROID_SDK_ROOT", "ANDROID_HOME"):
            value = os.environ.get(variable, "").strip()
            if value:
                roots.append(Path(value).expanduser())
        if project_dir:
            project_root = Path(project_dir).expanduser()
            for root in (project_root, project_root / "android", project_root.parent):
                try:
                    for line in (root / "local.properties").read_text(encoding="utf-8").splitlines():
                        if line.strip().startswith("sdk.dir="):
                            sdk_dir = line.split("=", 1)[1].strip().replace(r"\:", ":").replace(r"\\", "\\")
                            roots.append(Path(sdk_dir).expanduser())
                            break
                except OSError:
                    pass
        if emulator_path:
            roots.append(Path(emulator_path).expanduser().parent.parent)
        if adb_path:
            adb = Path(adb_path).expanduser()
            if adb.parent.name.lower() == "platform-tools":
                adb_root = adb.parent.parent
                normalized_parts = {part.casefold() for part in adb_root.parts}
                if not {"winget", "packages"}.issubset(normalized_parts):
                    roots.append(adb_root)
        local_app_data = os.environ.get("LOCALAPPDATA", "").strip()
        roots.extend((
            Path(local_app_data) / "Android/Sdk" if local_app_data else Path.home() / "AppData/Local/Android/Sdk",
            Path.home() / "Library/Android/sdk",
            Path.home() / "Android/Sdk",
            Path("/opt/android-sdk"),
        ))
        unique = []
        seen = set()
        for root in roots:
            try:
                root = root.resolve()
            except OSError:
                root = root.expanduser()
            key = os.path.normcase(str(root))
            if key not in seen:
                seen.add(key)
                unique.append(root)
        return unique

    @staticmethod
    def _find_sdkmanager(sdk_roots):
        executable_name = "sdkmanager.bat" if os.name == "nt" else "sdkmanager"
        for root in sdk_roots:
            command_bins = root / "cmdline-tools"
            try:
                versions = list(command_bins.iterdir())
            except OSError:
                continue
            versions.sort(key=lambda path: (path.name.lower() != "latest", path.name))
            for version in versions:
                candidate = version / "bin" / executable_name
                if candidate.is_file() and (os.name == "nt" or os.access(candidate, os.X_OK)):
                    return str(candidate)
        return shutil.which(executable_name)

    @staticmethod
    def _find_avdmanager(sdk_roots):
        executable_name = "avdmanager.bat" if os.name == "nt" else "avdmanager"
        for root in sdk_roots:
            command_bins = root / "cmdline-tools"
            try:
                versions = list(command_bins.iterdir())
            except OSError:
                continue
            versions.sort(key=lambda path: (path.name.lower() != "latest", path.name))
            for version in versions:
                candidate = version / "bin" / executable_name
                if candidate.is_file() and (os.name == "nt" or os.access(candidate, os.X_OK)):
                    return str(candidate)
        return shutil.which(executable_name)

    @staticmethod
    def _cmdline_tools_download_info():
        system = platform.system()
        machine = platform.machine().casefold()
        if machine in ("aarch64", "arm64"):
            architecture = "arm64" if system == "Darwin" else "aarch64"
        elif machine in ("amd64", "x86_64", "x64"):
            architecture = "amd64" if system == "Windows" else "x86_64"
        else:
            return None
        return CMDLINE_TOOLS_DOWNLOADS.get((system, architecture))

    @staticmethod
    def _find_emulator(adb_path="", project_dir=""):
        """Find the Android SDK emulator beside ADB or in a common SDK location."""
        roots = Deployer._find_android_sdk_roots(adb_path, project_dir)

        executable_name = "emulator.exe" if os.name == "nt" else "emulator"
        for root in roots:
            candidate = root / "emulator" / executable_name
            if candidate.is_file() and (os.name == "nt" or os.access(candidate, os.X_OK)):
                return str(candidate)
        return shutil.which(executable_name)

    def _build(self):
        self.about_update_button = None
        central = QWidget()
        self.setCentralWidget(central)
        outer_layout = QVBoxLayout(central)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # Top app bar with live project/device pills and Dark Mode toggle
        header_bar = QWidget()
        header_bar.setObjectName("HeaderBar")
        header_layout = QHBoxLayout(header_bar)
        header_layout.setContentsMargins(20, 12, 20, 12)
        header_layout.setSpacing(12)

        title_col = QVBoxLayout()
        title_col.setContentsMargins(0, 0, 0, 0)
        title_col.setSpacing(2)
        title_line = QHBoxLayout()
        title_line.setContentsMargins(0, 0, 0, 0)
        title_line.setSpacing(10)
        title_lbl = QLabel("DCM Android Toolkit")
        title_lbl.setObjectName("HeaderTitle")
        title_line.addWidget(title_lbl)
        ver_lbl = QLabel(f"v{APP_VERSION}")
        ver_lbl.setObjectName("HeaderVersion")
        title_line.addWidget(ver_lbl)
        title_line.addStretch(1)
        title_col.addLayout(title_line)

        sub_lbl = QLabel("Build, install, and manage Android APKs across Gradle & Expo projects")
        sub_lbl.setObjectName("HeaderSubtitle")
        title_col.addWidget(sub_lbl)
        header_layout.addLayout(title_col, 1)

        pills_col = QHBoxLayout()
        pills_col.setContentsMargins(0, 0, 0, 0)
        pills_col.setSpacing(8)
        self.header_project_pill = QLabel()
        self.header_project_pill.setObjectName("ProjectPill")
        pills_col.addWidget(self.header_project_pill)

        self.header_device_pill = QLabel()
        self.header_device_pill.setObjectName("DevicePill")
        self.header_device_pill.setProperty("connected", False)
        pills_col.addWidget(self.header_device_pill)

        self.theme_toggle_button = self._button(
            text="Light" if self.theme_mode == "dark" else "Dark",
            style="theme",
            command=self.toggle_theme,
            icon_name="sun" if self.theme_mode == "dark" else "moon",
        )
        self.theme_toggle_button.setToolTip("Switch between Light and Dark mode")
        pills_col.addWidget(self.theme_toggle_button)
        header_layout.addLayout(pills_col)
        outer_layout.addWidget(header_bar)

        root_widget = QWidget()
        root_layout = QVBoxLayout(root_widget)
        root_layout.setContentsMargins(16, 14, 16, 10)
        root_layout.setSpacing(8)
        outer_layout.addWidget(root_widget, 1)

        def add_page_header(page_layout, title, description):
            t = QLabel(title)
            t.setObjectName("PageTitle")
            page_layout.addWidget(t)
            d = QLabel(description)
            d.setObjectName("PageSubtitle")
            d.setWordWrap(True)
            page_layout.addWidget(d)
            page_layout.addWidget(make_divider())

        workspace = QSplitter(Qt.Orientation.Vertical)
        self.workspace = workspace
        root_layout.addWidget(workspace, 1)

        shell_border = QFrame()
        shell_border.setObjectName("WorkspaceShell")
        shell_layout = QHBoxLayout(shell_border)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)

        rail_frame = QFrame()
        rail_frame.setObjectName("SidebarRail")
        rail_frame.setFixedWidth(196)
        rail_layout = QVBoxLayout(rail_frame)
        rail_layout.setContentsMargins(10, 10, 10, 10)
        rail_layout.setSpacing(3)
        shell_layout.addWidget(rail_frame)

        stage_stack = QStackedWidget()
        shell_layout.addWidget(stage_stack, 1)
        workspace.addWidget(shell_border)

        tabs = SidebarNavigator(rail_layout, stage_stack, self._icons, self)
        self.tabs = tabs

        def create_scrollable_tab():
            scroll, _content, layout = make_scrollable_page()
            return scroll, layout

        connection_page, connection_tab = create_scrollable_tab()
        apk_page, apk_tab = create_scrollable_tab()
        sms_page, sms_tab = create_scrollable_tab()
        scan_page, scan_tab = create_scrollable_tab()
        watch_page, watch_tab = create_scrollable_tab()
        emulator_page, emulator_tab = create_scrollable_tab()
        debug_page, debug_tab = create_scrollable_tab()
        about_page, about_tab = create_scrollable_tab()
        self.emulator_tab_id = emulator_page
        self.debug_tab_id = debug_page

        tabs.add_section("Workspace")
        tabs.add(connection_page, "Connection")
        tabs.add(apk_page, "APK")
        tabs.add_section("Tools")
        tabs.add(sms_page, "SMS Export")
        tabs.add(scan_page, "Subnet Scan")
        tabs.add(watch_page, "Watch Screen")
        tabs.add(emulator_page, "Emulator")
        tabs.add_section("System")
        tabs.add(debug_page, "Debug")
        tabs.add(about_page, "About")
        tabs.finalize_rail()
        tabs.tab_changed.connect(self._debug_tab_selected)
        self.project_name.trace_add("write", lambda *_args: self._update_header_pills())

        self._build_debug_tab(debug_tab)

        # ABOUT TAB
        add_page_header(about_tab, "About DCM Android Toolkit", "Application overview, credits, and release update information.")
        _about_card, about_body = make_card(about_tab)
        about_desc = QLabel(
            "DCM Android Toolkit helps Android developers work across Gradle and Expo projects. "
            "Build debug or release APKs, connect to devices over USB or Wi-Fi, install apps, "
            "and keep local build history. It also includes device and SMS diagnostic tools."
        )
        about_desc.setWordWrap(True)
        about_body.addWidget(about_desc)
        about_body.addWidget(make_divider())
        ver_meta = QLabel(f"Version {APP_VERSION}")
        ver_meta.setProperty("cardSub", True)
        about_body.addWidget(ver_meta)
        about_body.addWidget(QLabel("Made by Emre Demir · DotComMedia.online"))
        about_body.addWidget(make_divider())
        about_actions_wrap = QWidget()
        about_actions = FlowLayout(about_actions_wrap)
        self.about_update_button = self._button(text="Check for updates", style="Info.TButton", command=lambda: self.check_for_updates(manual=True))
        about_actions.addWidget(self.about_update_button)
        about_actions.addWidget(self._button(text="Website", command=lambda: webbrowser.open("https://dotcommedia.online")))
        about_actions.addWidget(self._button(text="Report a bug…", command=self.export_activity_log_for_bug_report))
        about_body.addWidget(about_actions_wrap)
        about_tab.addStretch(1)

        # CONNECTION TAB
        add_page_header(connection_tab, "Connect a device", "Connect over USB or Wi-Fi. Disconnect to change connection settings.")
        method_row = QHBoxLayout()
        method_row.setSpacing(14)
        method_lbl = QLabel("Connection method")
        method_lbl.setProperty("sectionTitle", True)
        method_row.addWidget(method_lbl)
        for method in ("USB", "Wi-Fi"):
            radio = QRadioButton(method)
            bind_radio(radio, self.connection_method, method)
            radio.toggled.connect(lambda checked: checked and self._connection_method_changed())
            method_row.addWidget(radio)
            self.connection_widgets.append(radio)
        method_row.addStretch(1)
        connection_tab.addLayout(method_row)
        connection_tab.addWidget(make_divider())

        self.device_card, device_body = make_card(connection_tab)
        usb_sec = QLabel("USB connection")
        usb_sec.setProperty("sectionTitle", True)
        device_body.addWidget(usb_sec)
        usb_row = QHBoxLayout()
        usb_row.setSpacing(8)
        self.devices = QComboBox()
        bind_combo_box(self.devices, self.target)
        usb_row.addWidget(self.devices, 1)
        refresh_button = self._button(text="Refresh", command=self.refresh_devices)
        usb_row.addWidget(refresh_button)
        self.connect_usb_button = self._button(text="Connect USB", style="Accent.TButton", command=self.connect_usb)
        usb_row.addWidget(self.connect_usb_button)
        device_body.addLayout(usb_row)
        self.connection_widgets.extend([self.devices, refresh_button, self.connect_usb_button])
        usb_hint = QLabel("Connect the phone by cable, enable USB debugging, and accept its authorization prompt.")
        usb_hint.setProperty("cardSub", True)
        usb_hint.setWordWrap(True)
        device_body.addWidget(usb_hint)

        self.wifi_card, wifi_body = make_card(connection_tab)
        wifi_sec = QLabel("Wi-Fi connection")
        wifi_sec.setProperty("sectionTitle", True)
        wifi_body.addWidget(wifi_sec)
        fixed_check = QCheckBox("Use fixed IP")
        bind_checkbox(fixed_check, self.use_fixed_wifi)
        fixed_check.toggled.connect(lambda _c: self._update_ip_mode())
        wifi_body.addWidget(fixed_check)
        self.connection_widgets.append(fixed_check)
        wifi_body.addWidget(QLabel("Saved fixed IP and port"))
        self.fixed_entry = QLineEdit()
        bind_line_edit(self.fixed_entry, self.fixed_wifi)
        wifi_body.addWidget(self.fixed_entry)
        wifi_body.addWidget(QLabel("Manual IP and port (example: 192.168.1.42:5555)"))
        self.manual_entry = QComboBox()
        self.manual_entry.setEditable(True)
        bind_combo_box(self.manual_entry, self.wifi)
        wifi_body.addWidget(self.manual_entry)
        self.connection_widgets.extend([self.fixed_entry, self.manual_entry])
        wbuttons_wrap = QWidget()
        wbuttons = FlowLayout(wbuttons_wrap)
        self.pair_button = self._button(text="Pair…", command=self.pair_wifi)
        self.connect_wifi_button = self._button(text="Connect Wi-Fi", style="Accent.TButton", command=self.connect_wifi)
        self.scan_open_button = self._button(text="Scan subnet…", command=self.open_scan_tab)
        wbuttons.addWidget(self.pair_button)
        wbuttons.addWidget(self.connect_wifi_button)
        wbuttons.addWidget(self.scan_open_button)
        wifi_body.addWidget(wbuttons_wrap)
        self.connection_widgets.extend([self.pair_button, self.connect_wifi_button, self.scan_open_button])

        self.connected_card, connected_body = make_card(connection_tab)
        connected_top = QHBoxLayout()
        connected_top.setSpacing(12)
        title_block = QVBoxLayout()
        title_block.setSpacing(4)
        self.active_label = QLabel("Connected device")
        self.active_label.setProperty("sectionTitle", True)
        self.active_label.setWordWrap(True)
        title_block.addWidget(self.active_label)
        self.connection_detail_label = QLabel("")
        self.connection_detail_label.setProperty("cardSub", True)
        self.connection_detail_label.setWordWrap(True)
        title_block.addWidget(self.connection_detail_label)
        connected_top.addLayout(title_block, 1)
        self.disconnect_button = self._button(text="Disconnect", style="Danger.TButton", command=self.disconnect_device)
        connected_top.addWidget(self.disconnect_button, 0, Qt.AlignmentFlag.AlignTop)
        connected_body.addLayout(connected_top)

        self.keep_awake_button = QCheckBox("Keep screen awake while charging")
        bind_checkbox(self.keep_awake_button, self.keep_awake)
        self.keep_awake_button.toggled.connect(lambda _c: self.toggle_keep_awake())
        self.keep_awake_button.setEnabled(False)
        connected_body.addWidget(self.keep_awake_button)
        awake_hint = QLabel("Temporarily disables battery saver and screen dim timeout while enabled. Original settings are restored when you turn it off.")
        awake_hint.setProperty("cardSub", True)
        awake_hint.setWordWrap(True)
        connected_body.addWidget(awake_hint)

        self.brightness_value_label = QLabel()
        self.brightness_value_label.setProperty("sectionTitle", True)
        bind_label(self.brightness_value_label, self.brightness_text)
        connected_body.addWidget(self.brightness_value_label)
        self.brightness_scale = QSlider(Qt.Orientation.Horizontal)
        self.brightness_scale.setRange(0, 100)
        bind_slider(self.brightness_scale, self.brightness_level)
        self.brightness_scale.valueChanged.connect(self._brightness_changed)
        connected_body.addWidget(self.brightness_scale)
        self._update_brightness_visuals(self.brightness_level.get())

        presets_row = QHBoxLayout()
        presets_row.setSpacing(6)
        presets_row.addWidget(QLabel("Presets"))
        for percent in (25, 50, 75):
            presets_row.addWidget(self._button(text=f"{percent}%", command=lambda v=percent: self.set_brightness_preset(v), icon_name="sun"))
        presets_row.addStretch(1)
        connected_body.addLayout(presets_row)

        amoled_warn = QLabel("AMOLED care: avoid prolonged high brightness with static content; it can increase burn-in risk. No 100% preset is provided.")
        amoled_warn.setObjectName("WarningBanner")
        amoled_warn.setWordWrap(True)
        connected_body.addWidget(amoled_warn)
        conn_note = QLabel("ADB connection is active. Disconnect to change device or connection settings.")
        conn_note.setProperty("cardSub", True)
        connected_body.addWidget(conn_note)
        connection_tab.addStretch(1)

        # APK TAB
        add_page_header(apk_tab, "APK build, install, and removal", "Build APKs from Gradle or Expo projects, then install them on a device or emulator.")
        _apk_card, card2 = make_card(apk_tab)
        prof_title = QLabel("Project profile")
        prof_title.setProperty("sectionTitle", True)
        card2.addWidget(prof_title)
        card2.addWidget(make_divider())

        profile_row = QHBoxLayout()
        profile_row.setSpacing(8)
        self.project_selector = QComboBox()
        self.project_selector.addItems(sorted(self.project_profiles))
        bind_combo_box(self.project_selector, self.project_name)
        self.project_selector.currentIndexChanged.connect(lambda _idx: self._project_profile_selected())
        profile_row.addWidget(self.project_selector, 1)
        self.project_edit_widgets.append(self.project_selector)
        save_proj_btn = self._button(text="Save project", command=self.save_project_profile)
        profile_row.addWidget(save_proj_btn)
        self.project_edit_widgets.append(save_proj_btn)
        self.add_project_button = self._button(text="Add project…", command=self.add_project)
        profile_row.addWidget(self.add_project_button)
        self.project_edit_widgets.append(self.add_project_button)
        card2.addLayout(profile_row)

        card2.addWidget(QLabel("Project folder (Gradle or Expo)"))
        proj_dir_row = QHBoxLayout()
        proj_dir_row.setSpacing(8)
        proj_dir_entry = QLineEdit()
        bind_line_edit(proj_dir_entry, self.project_dir)
        proj_dir_row.addWidget(proj_dir_entry, 1)
        self.project_edit_widgets.append(proj_dir_entry)
        choose_proj_btn = self._button(text="Choose…", command=self.choose_project_dir)
        proj_dir_row.addWidget(choose_proj_btn)
        self.project_edit_widgets.append(choose_proj_btn)
        card2.addLayout(proj_dir_row)

        mod_row = QHBoxLayout()
        mod_row.setSpacing(8)
        mod_row.addWidget(QLabel("Android module"))
        module_entry = QLineEdit()
        module_entry.setFixedWidth(180)
        bind_line_edit(module_entry, self.module)
        mod_row.addWidget(module_entry)
        self.project_edit_widgets.append(module_entry)
        mod_hint = QLabel("(for example: app or :client:app)")
        mod_hint.setProperty("cardSub", True)
        mod_row.addWidget(mod_hint)
        mod_row.addStretch(1)
        card2.addLayout(mod_row)

        card2.addWidget(QLabel("APK file"))
        apk_row = QHBoxLayout()
        apk_row.setSpacing(8)
        apk_entry = QLineEdit()
        bind_line_edit(apk_entry, self.apk)
        apk_row.addWidget(apk_entry, 1)
        self.project_edit_widgets.append(apk_entry)
        choose_apk_btn = self._button(text="Choose…", command=self.choose_apk)
        apk_row.addWidget(choose_apk_btn)
        self.project_edit_widgets.append(choose_apk_btn)
        card2.addLayout(apk_row)

        build_wrap = QWidget()
        build_flow = FlowLayout(build_wrap)
        build_type_group = QWidget()
        bt_layout = QHBoxLayout(build_type_group)
        bt_layout.setContentsMargins(0, 0, 4, 0)
        bt_layout.setSpacing(6)
        bt_layout.addWidget(QLabel("Build type"))
        bt_combo = QComboBox()
        bt_combo.addItems(["debug", "release"])
        bind_combo_box(bt_combo, self.build_type)
        bt_layout.addWidget(bt_combo)
        self.project_edit_widgets.append(bt_combo)
        build_flow.addWidget(build_type_group)
        self.build_button = self._button(text="Build APK…", style="Build.TButton", command=self.build_apk)
        build_flow.addWidget(self.build_button)
        build_flow.addWidget(self._button(text="Install / overwrite", style="Accent.TButton", command=self.install))
        build_flow.addWidget(self._button(text="Remove app from device", style="Danger.TButton", command=self.uninstall))
        build_flow.addWidget(self._button(text="Version history…", command=self.open_version_history))
        card2.addWidget(build_wrap)

        apk_tab.addWidget(make_divider())
        apk_tab.addWidget(QLabel("Android package name (for example: com.example.app)"))
        pkg_entry = QLineEdit()
        bind_line_edit(pkg_entry, self.package)
        apk_tab.addWidget(pkg_entry)
        self.project_edit_widgets.append(pkg_entry)

        target_row = QHBoxLayout()
        target_row.setSpacing(8)
        target_row.addWidget(QLabel("Install target"))
        self.install_target_selector = QComboBox()
        bind_combo_box(self.install_target_selector, self.install_target)
        target_row.addWidget(self.install_target_selector, 1)
        target_row.addWidget(self._button(text="Refresh devices", command=self.refresh_devices))
        apk_tab.addLayout(target_row)
        apk_tab.addStretch(1)

        # SMS EXPORT TAB
        add_page_header(sms_tab, "SMS debug export", "Read a small sample or export SMS diagnostics from the connected device.")
        _sms_card, card3 = make_card(sms_tab)
        sms_desc = QLabel("Reads the device SMS database through ADB. Android may restrict this unless the app is the default SMS handler or the device grants shell access.")
        sms_desc.setProperty("cardSub", True)
        sms_desc.setWordWrap(True)
        card3.addWidget(sms_desc)
        export_dir_row = QHBoxLayout()
        export_dir_row.setSpacing(8)
        export_entry = QLineEdit()
        bind_line_edit(export_entry, self.export_dir)
        export_dir_row.addWidget(export_entry, 1)
        export_dir_row.addWidget(self._button(text="Choose output folder…", command=self.choose_export_dir))
        card3.addLayout(export_dir_row)
        card3.addWidget(make_divider())
        sms_count_lbl = QLabel()
        sms_count_lbl.setProperty("sectionTitle", True)
        bind_label(sms_count_lbl, self.sms_count_text)
        card3.addWidget(sms_count_lbl)
        card3.addWidget(make_divider())
        sms_wrap = QWidget()
        sms_actions = FlowLayout(sms_wrap)
        self.count_button = self._button(text="Read SMS count", command=self.count_sms)
        self.preview_button = self._button(text="Preview 2 SMS", command=self.preview_sms)
        self.export_button = self._button(text="Export SMS to JSON", style="Accent.TButton", command=self.export_sms)
        sms_actions.addWidget(self.count_button)
        sms_actions.addWidget(self.preview_button)
        sms_actions.addWidget(self.export_button)
        card3.addWidget(sms_wrap)
        sms_tab.addStretch(1)

        # SUBNET SCAN TAB
        add_page_header(scan_tab, "Find a device on your network", "Scan a local subnet for hosts that may be accepting ADB connections.")
        _scan_card, scan_body = make_card(scan_tab)
        scan_sec = QLabel("Scan subnet")
        scan_sec.setProperty("sectionTitle", True)
        scan_body.addWidget(scan_sec)
        scan_desc = QLabel("Enter a CIDR subnet and ADB port. The result is copied into the manual IP field on the Connection tab.")
        scan_desc.setProperty("cardSub", True)
        scan_desc.setWordWrap(True)
        scan_body.addWidget(scan_desc)
        scan_body.addWidget(make_divider())
        scan_row = QHBoxLayout()
        scan_row.setSpacing(8)
        subnet_entry = QLineEdit()
        subnet_entry.setFixedWidth(200)
        bind_line_edit(subnet_entry, self.subnet)
        scan_row.addWidget(subnet_entry)
        port_entry = QLineEdit()
        port_entry.setFixedWidth(90)
        bind_line_edit(port_entry, self.scan_port)
        scan_row.addWidget(port_entry)
        self.scan_button = self._button(text="Scan subnet", style="Accent.TButton", command=self.scan_subnet)
        scan_row.addWidget(self.scan_button)
        scan_row.addStretch(1)
        scan_body.addLayout(scan_row)
        self.connection_widgets.append(self.scan_button)
        scan_tab.addStretch(1)

        # WATCH SCREEN TAB
        add_page_header(watch_tab, "Watch your device", "View and control the connected Android screen in a separate window.")
        _watch_card, watch_body = make_card(watch_tab)
        watch_sec = QLabel("Live screen with touch control")
        watch_sec.setProperty("sectionTitle", True)
        watch_body.addWidget(watch_sec)
        watch_body.addWidget(make_divider())
        watch_desc = QLabel("Opens the connected Android screen in a separate window. Clicks, taps, swipes, and keyboard input in that window are sent to the phone over ADB.")
        watch_desc.setProperty("cardSub", True)
        watch_desc.setWordWrap(True)
        watch_body.addWidget(watch_desc)
        self.watch_device_label = QLabel("Connect a device first.")
        self.watch_device_label.setProperty("sectionTitle", True)
        watch_body.addWidget(self.watch_device_label)
        self.watch_button = self._button(text="Open screen window", style="Accent.TButton", command=self.open_screen_mirror)
        self.watch_button.setEnabled(False)
        watch_body.addWidget(self.watch_button, 0, Qt.AlignmentFlag.AlignLeft)
        watch_hint = QLabel("Screen mirroring uses scrcpy. Install with `brew install scrcpy` if it is not already available.")
        watch_hint.setProperty("cardSub", True)
        watch_hint.setWordWrap(True)
        watch_body.addWidget(watch_hint)
        watch_tab.addStretch(1)

        # EMULATOR TAB
        add_page_header(emulator_tab, "Android emulator", "Start and stop Android Virtual Devices installed in your Android SDK, then connect one to the toolkit.")
        _emu_card, emu_body = make_card(emulator_tab)
        emu_sec = QLabel("Virtual devices on this computer")
        emu_sec.setProperty("sectionTitle", True)
        emu_body.addWidget(emu_sec)
        emu_body.addWidget(make_divider())
        emu_desc = QLabel(
            "The Android Emulator opens in its own window. Download & create AVD installs the Emulator, "
            "Platform-Tools, and an Android 16 Google APIs system image, then creates a default Pixel AVD. "
            "Android Studio is not required. The system image is a large download and requires an internet connection."
        )
        emu_desc.setProperty("cardSub", True)
        emu_desc.setWordWrap(True)
        emu_body.addWidget(emu_desc)
        emu_sel_row = QHBoxLayout()
        emu_sel_row.setSpacing(10)
        emu_sel_row.addWidget(QLabel("Android Virtual Device"))
        self.emulator_selector = QComboBox()
        bind_combo_box(self.emulator_selector, self.emulator_avd)
        self.emulator_selector.currentIndexChanged.connect(lambda _idx: self._update_emulator_controls())
        emu_sel_row.addWidget(self.emulator_selector, 1)
        emu_body.addLayout(emu_sel_row)

        emu_wrap = QWidget()
        emu_actions = FlowLayout(emu_wrap)
        self.emulator_download_button = self._button(text="Download & create AVD", style="Build.TButton", command=self.download_emulator_package)
        self.emulator_refresh_button = self._button(text="Refresh emulators", command=self.refresh_emulators)
        self.emulator_start_button = self._button(text="Start emulator", style="Accent.TButton", command=self.start_selected_emulator)
        self.emulator_stop_button = self._button(text="Stop emulator", style="Danger.TButton", command=self.stop_selected_emulator)
        self.emulator_connect_button = self._button(text="Connect emulator", style="Info.TButton", command=self.connect_selected_emulator)
        for btn in (
            self.emulator_download_button,
            self.emulator_refresh_button,
            self.emulator_start_button,
            self.emulator_stop_button,
            self.emulator_connect_button,
        ):
            emu_actions.addWidget(btn)
        emu_body.addWidget(emu_wrap)
        emu_body.addWidget(make_divider())
        self.emulator_status_label = QLabel()
        self.emulator_status_label.setProperty("cardSub", True)
        self.emulator_status_label.setWordWrap(True)
        bind_label(self.emulator_status_label, self.emulator_status)
        emu_body.addWidget(self.emulator_status_label)
        emulator_tab.addStretch(1)

        # ACTIVITY CONSOLE
        log_shell = QFrame()
        log_shell.setObjectName("ActivityShell")
        log_shell_layout = QVBoxLayout(log_shell)
        log_shell_layout.setContentsMargins(0, 0, 0, 0)
        log_shell_layout.setSpacing(0)

        log_header = QWidget()
        log_header.setObjectName("ActivityHeader")
        lh_layout = QHBoxLayout(log_header)
        lh_layout.setContentsMargins(12, 6, 12, 6)
        lh_layout.setSpacing(8)
        act_title = QLabel("ACTIVITY")
        act_title.setObjectName("ActivityTitle")
        lh_layout.addWidget(act_title)
        act_hint = QLabel("· drag divider above to resize")
        act_hint.setObjectName("ActivityHint")
        lh_layout.addWidget(act_hint)
        lh_layout.addStretch(1)
        lh_layout.addWidget(self._button(text="Copy", style="console", command=self._copy_activity_log))
        lh_layout.addWidget(self._button(text="Clear", style="console", command=self._clear_activity_log))
        self.activity_autoscroll = StateVar(True, bool, self)
        autoscroll_chk = QCheckBox("Auto-scroll")
        autoscroll_chk.setObjectName("ConsoleAutoScroll")
        bind_checkbox(autoscroll_chk, self.activity_autoscroll)
        lh_layout.addWidget(autoscroll_chk)
        log_shell_layout.addWidget(log_header)

        self.output = QPlainTextEdit()
        self.output.setObjectName("ActivityLog")
        self.output.setReadOnly(True)
        self.output.setMinimumHeight(110)
        log_shell_layout.addWidget(self.output, 1)
        workspace.addWidget(log_shell)
        workspace.setStretchFactor(0, 5)
        workspace.setStretchFactor(1, 2)
        workspace.setSizes([520, 180])

        # FIXED BUILD STATUS ROW (outside QSplitter)
        self.build_status_row = QFrame()
        self.build_status_row.setObjectName("BuildStatusRow")
        bs_layout = QHBoxLayout(self.build_status_row)
        bs_layout.setContentsMargins(12, 7, 12, 7)
        bs_layout.setSpacing(12)
        self.build_status_label = QLabel()
        self.build_status_label.setProperty("cardSub", True)
        self.build_status_label.setWordWrap(True)
        bind_label(self.build_status_label, self.build_status)
        bs_layout.addWidget(self.build_status_label, 1)
        self.build_progress = QProgressBar()
        self.build_progress.setRange(0, 0)
        self.build_progress.setFixedWidth(136)
        self.build_progress.setTextVisible(False)
        bs_layout.addWidget(self.build_progress)
        self.build_status_row.setVisible(False)
        root_layout.addWidget(self.build_status_row)

        # BOTTOM STATUS BAR
        footer_bar = QWidget()
        footer_bar.setObjectName("FooterBar")
        footer_layout = QHBoxLayout(footer_bar)
        footer_layout.setContentsMargins(16, 7, 16, 7)
        self.status_label = QLabel()
        self.status_label.setObjectName("FooterStatus")
        bind_label(self.status_label, self.status)
        footer_layout.addWidget(self.status_label, 1)
        outer_layout.addWidget(footer_bar)

        if not self.emulator_executable:
            tabs.select(self.emulator_tab_id)
        self._update_ip_mode()
        self._update_header_pills()

    def _build_debug_tab(self, page_layout):
        t = QLabel("Debug and cleanup")
        t.setObjectName("PageTitle")
        page_layout.addWidget(t)
        d = QLabel("Inspect toolkit and Android SDK files, clean stale temporary data, or remove selected toolkit data.")
        d.setObjectName("PageSubtitle")
        d.setWordWrap(True)
        page_layout.addWidget(d)
        page_layout.addWidget(make_divider())

        _inv_card, inv_body = make_card(page_layout)
        inv_sec = QLabel("System and toolkit inventory")
        inv_sec.setProperty("sectionTitle", True)
        inv_body.addWidget(inv_sec)
        inv_desc = QLabel("The export includes detected tools, the selected project folder, and recent application errors. Local paths are included; device addresses and SMS details are redacted.")
        inv_desc.setProperty("cardSub", True)
        inv_desc.setWordWrap(True)
        inv_body.addWidget(inv_desc)
        self.debug_inventory_text = QPlainTextEdit()
        self.debug_inventory_text.setProperty("monoCard", True)
        self.debug_inventory_text.setReadOnly(True)
        self.debug_inventory_text.setMinimumHeight(210)
        inv_body.addWidget(self.debug_inventory_text)
        inv_wrap = QWidget()
        inv_actions = FlowLayout(inv_wrap)
        inv_actions.addWidget(self._button(text="Scan debug state", command=lambda: self._refresh_debug_inventory(scan_versions=True)))
        inv_actions.addWidget(self._button(text="Export diagnostic report and error log…", style="Info.TButton", command=self._export_debug_report))
        inv_body.addWidget(inv_wrap)

        _tmp_card, tmp_body = make_card(page_layout)
        tmp_sec = QLabel("Temporary files")
        tmp_sec.setProperty("sectionTitle", True)
        tmp_body.addWidget(tmp_sec)
        tmp_desc = QLabel("Finds toolkit-owned temporary downloads and abandoned staging folders older than 24 hours. It skips active operations and user-selected export folders.")
        tmp_desc.setProperty("cardSub", True)
        tmp_desc.setWordWrap(True)
        tmp_body.addWidget(tmp_desc)
        self.debug_cleanup_button = self._button(text="Clean stale temporary files…", style="Warning.TButton", command=self._debug_clean_temporary_files)
        tmp_body.addWidget(self.debug_cleanup_button, 0, Qt.AlignmentFlag.AlignLeft)

        _sdk_card, sdk_body = make_card(page_layout)
        sdk_sec = QLabel("Android SDK components")
        sdk_sec.setProperty("sectionTitle", True)
        sdk_body.addWidget(sdk_sec)
        sdk_desc = QLabel("SDK packages may be shared with Android Studio and other projects. Removal shows the selected SDK path and requires confirmation.")
        sdk_desc.setProperty("cardSub", True)
        sdk_desc.setWordWrap(True)
        sdk_body.addWidget(sdk_desc)
        sdk_wrap = QWidget()
        sdk_actions = FlowLayout(sdk_wrap)
        self.debug_remove_emulator_button = self._button(text="Remove emulator package…", style="Danger.TButton", command=self._debug_remove_emulator_package)
        self.debug_remove_bootstrap_button = self._button(text="Remove bootstrap tools…", style="Danger.TButton", command=self._debug_remove_bootstrap_tools)
        sdk_actions.addWidget(self.debug_remove_emulator_button)
        sdk_actions.addWidget(self.debug_remove_bootstrap_button)
        sdk_body.addWidget(sdk_wrap)

        _data_card, data_body = make_card(page_layout)
        data_sec = QLabel("Toolkit local data")
        data_sec.setProperty("sectionTitle", True)
        data_body.addWidget(data_sec)
        data_desc = QLabel("Clear archived APK builds or reset saved toolkit settings and project profiles. SMS exports and files outside the toolkit archive are preserved.")
        data_desc.setProperty("cardSub", True)
        data_desc.setWordWrap(True)
        data_body.addWidget(data_desc)
        data_wrap = QWidget()
        data_actions = FlowLayout(data_wrap)
        self.debug_clear_history_button = self._button(text="Clear APK history…", style="Danger.TButton", command=self._debug_clear_apk_history)
        data_actions.addWidget(self.debug_clear_history_button)
        data_actions.addWidget(self._button(text="Reset settings and profiles…", style="Danger.TButton", command=self._debug_reset_settings))
        data_body.addWidget(data_wrap)
        page_layout.addStretch(1)
        self._refresh_debug_inventory()

    @staticmethod
    def _debug_size_text(size):
        value = float(size)
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if value < 1024 or unit == "TB":
                return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
            value /= 1024

    def _debug_stale_temp_candidates(self):
        cutoff = time.time() - 24 * 60 * 60
        candidates = []

        def consider(path, kind):
            try:
                if path.is_symlink() or path.stat().st_mtime >= cutoff:
                    return
                if kind == "directory" and not path.is_dir():
                    return
                if kind == "file" and not path.is_file():
                    return
                size = path.stat().st_size if kind == "file" else None
                candidates.append({"path": path, "kind": kind, "size": size})
            except OSError:
                return

        try:
            temp_root = Path(tempfile.gettempdir())
            for item in temp_root.iterdir():
                if item.name.startswith(("dcm-toolkit-update-", "dcm-commandline-tools-")) and item.suffix.lower() == ".zip":
                    consider(item, "file")
        except OSError:
            pass
        try:
            for item in APP_ROOT.parent.glob(".dcm-update-*"):
                consider(item, "directory")
        except OSError:
            pass
        if self.android_sdk_root:
            try:
                command_tools_root = self.android_sdk_root / "cmdline-tools"
                for item in command_tools_root.glob(".dcm-cli-stage-*") if not command_tools_root.is_symlink() else ():
                    consider(item, "directory")
            except OSError:
                pass
        local_data = APP_ROOT / "data"
        if not local_data.is_symlink() and local_data.resolve() == APP_ROOT.resolve() / "data":
            consider(APK_HISTORY.with_suffix(APK_HISTORY.suffix + ".tmp"), "file")
        candidates.sort(key=lambda item: str(item["path"]).casefold())
        return candidates

    def _debug_bootstrap_directories(self):
        if not self.android_sdk_root:
            return []
        root = self.android_sdk_root / "cmdline-tools"
        if root.is_symlink():
            return []
        try:
            return sorted(
                (path for path in root.glob("dcm-bootstrap-*") if path.is_dir() and not path.is_symlink()),
                key=lambda path: path.name.casefold(),
            )
        except OSError:
            return []

    def _debug_archive_stats(self):
        archive = APK_ARCHIVE
        if archive.is_symlink() or not archive.is_dir():
            return 0, 0
        files = [path for path in archive.iterdir() if path.is_file() and not path.is_symlink() and path.suffix.lower() == ".apk"]
        return len(files), sum(path.stat().st_size for path in files)

    @staticmethod
    def _sanitize_diagnostic_error(title, message):
        title = str(title).strip() or "Application error"
        message = str(message).strip()
        if "sms" in title.casefold() or "content://sms" in message.casefold():
            return title, "Detailed error text omitted because it may contain private SMS data."

        def redact_ipv4(match):
            address = match.group(0)
            # Preserve common dotted version values such as 0.1.4.4.
            return "[device address]" if not address.startswith("0.") else address

        message = re.sub(r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])", redact_ipv4, message)
        message = re.sub(r"\bemulator-\d+\b", "emulator-[redacted]", message, flags=re.IGNORECASE)
        message = re.sub(r"\b([\w.-]+):\d{4,5}\b", "[device address]", message)
        message = re.sub(r"\b[A-Za-z0-9]{12,}\b", "[identifier redacted]", message)
        return title, message[:8000]

    def _record_diagnostic_error(self, title, message):
        title, message = self._sanitize_diagnostic_error(title, message)
        timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
        entry = f"[{timestamp}] {title}: {message}"
        self.recent_errors.append(entry)
        del self.recent_errors[:-200]
        try:
            if (APP_ROOT / "data").is_symlink() or ERROR_LOG.parent.is_symlink() or ERROR_LOG.is_symlink():
                return
            ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)
            with self.error_log_lock:
                if ERROR_LOG.exists() and ERROR_LOG.stat().st_size > MAX_ERROR_LOG_BYTES:
                    old_log = ERROR_LOG.read_text(encoding="utf-8", errors="replace")
                    ERROR_LOG.write_text(old_log[-MAX_ERROR_LOG_BYTES // 2 :], encoding="utf-8")
                with ERROR_LOG.open("a", encoding="utf-8", newline="\n") as error_file:
                    error_file.write(entry + "\n")
        except OSError:
            pass

    def _report_callback_exception(self, exception_type, exception, _traceback):
        detail = f"{exception_type.__name__}: {exception}"
        self._record_diagnostic_error("Unhandled UI callback exception", detail)
        if hasattr(self, "output"):
            self.log(f"Unhandled UI callback exception: {detail}", capture_errors=False)

    def _report_thread_exception(self, args):
        thread_name = args.thread.name if args.thread else "unnamed worker"
        self._record_diagnostic_error(
            f"Unhandled worker exception ({thread_name})",
            f"{args.exc_type.__name__}: {args.exc_value}",
        )

    def show_error(self, title, message, **options):
        """Record handled errors for the Debug export, then show the normal dialog."""
        self._record_diagnostic_error(title, message)
        if hasattr(self, "output"):
            self.log(f"ERROR · {title}: {message}", capture_errors=False)
        options.setdefault("parent", self)
        return messagebox.showerror(title, message, **options)

    def _diagnostic_error_log(self):
        try:
            if ERROR_LOG.is_file() and not ERROR_LOG.is_symlink():
                content = ERROR_LOG.read_text(encoding="utf-8", errors="replace")
                return content[-MAX_ERROR_LOG_BYTES:]
        except OSError:
            pass
        return "\n".join(self.recent_errors[-200:])

    def _debug_report_text(self):
        stale = self._debug_stale_temp_candidates()
        bootstrap = self._debug_bootstrap_directories()
        archive_count, archive_bytes = self._debug_archive_stats()
        sdk_root = str(self.android_sdk_root) if self.android_sdk_root else "Not found"
        project_root = self.project_dir.get().strip()
        project_check = self._project_folder_problem(Path(project_root).expanduser()) if project_root else "Not set"
        emulator_binary = "emulator.exe" if os.name == "nt" else "emulator"
        sdk_emulator = self.android_sdk_root / "emulator" / emulator_binary if self.android_sdk_root else None
        tools = (
            ("Python", sys.executable),
            ("Node.js", shutil.which("node") or "Not found"),
            ("npm", shutil.which("npm") or "Not found"),
            ("ADB", self.adb or shutil.which("adb") or "Not found"),
            ("Java", shutil.which("java") or "Not found"),
            ("Android CLI", self.sdk_package_cli or self.android_cli or "Not found"),
            ("SDK Manager", self.sdkmanager_executable or "Not found"),
            ("Android Emulator", str(sdk_emulator) if sdk_emulator and sdk_emulator.is_file() else "Not installed in selected SDK"),
            ("scrcpy", shutil.which("scrcpy") or "Not found"),
        )
        lines = [
            "DCM Android Toolkit diagnostic report",
            f"Application version: {APP_VERSION}",
            f"Operating system: {platform.platform()}",
            f"Python version: {platform.python_version()}",
            f"Application folder: {APP_ROOT}",
            f"Active project profile: {self.active_project_name or 'None'}",
            f"Selected project root: {project_root or 'Not set'}",
            f"Project type: {'Expo' if project_root and self._is_expo_project(Path(project_root).expanduser()) else 'Gradle'}",
            f"Android project check: {project_check or 'Valid'}",
            f"Selected Android SDK: {sdk_root}",
            "",
            "Detected tools:",
        ]
        lines.extend(
            f"  {name}: {value} · {self.debug_tool_versions[name]}" if name in self.debug_tool_versions else f"  {name}: {value} · version not scanned"
            for name, value in tools
        )
        lines.extend((
            "",
            f"Toolkit bootstrap SDK directories: {len(bootstrap)}",
            *(f"  {path}" for path in bootstrap),
            f"Archived APKs: {archive_count} ({self._debug_size_text(archive_bytes)})",
            f"Stale toolkit temporary items (>24h): {len(stale)}",
            *(f"  {item['path']} ({self._debug_size_text(item['size']) if item['size'] is not None else 'directory size not calculated'})" for item in stale),
            "",
            "Recent application errors (private SMS details and device addresses are redacted):",
            self._diagnostic_error_log().strip() or "No errors have been recorded.",
            "",
            "The report includes local application, project, and tool paths. Device addresses and SMS contents are excluded.",
        ))
        return "\n".join(lines)

    def _refresh_debug_inventory(self, scan_versions=False):
        if not hasattr(self, "debug_inventory_text"):
            return
        if scan_versions and not self.debug_version_scan_running:
            self.debug_version_scan_running = True
            threading.Thread(target=self._scan_debug_tool_versions, daemon=True).start()
        text = self._debug_report_text()
        self.debug_inventory_text.setPlainText(text)
        busy = (
            self.build_running
            or self.update_running
            or self.emulator_download_running
            or self.emulator_busy
            or self.debug_sdk_remove_running
            or self.debug_cleanup_running
        )
        if hasattr(self, "debug_cleanup_button"):
            self.debug_cleanup_button.setEnabled(not busy)
        if hasattr(self, "debug_clear_history_button"):
            self.debug_clear_history_button.setEnabled(not busy)
        if hasattr(self, "debug_remove_emulator_button"):
            sdk_manager_ready = bool(self.android_sdk_root and self.sdkmanager_executable)
            emulator_installed = bool(
                self.android_sdk_root
                and (self.android_sdk_root / "emulator" / ("emulator.exe" if os.name == "nt" else "emulator")).is_file()
            )
            running_emulator = bool(self.emulator_states)
            self.debug_remove_emulator_button.setEnabled(
                sdk_manager_ready and emulator_installed and not busy and not running_emulator
            )
        if hasattr(self, "debug_remove_bootstrap_button"):
            self.debug_remove_bootstrap_button.setEnabled(bool(self._debug_bootstrap_directories()) and not busy)

    def _debug_tab_selected(self, page=None):
        if page is not None and page is getattr(self, "debug_tab_id", None):
            self._refresh_debug_inventory(scan_versions=True)
        elif page is None and getattr(self, "debug_tab_id", None) is self.tabs.select():
            self._refresh_debug_inventory(scan_versions=True)
            self._refresh_debug_inventory()

    def _scan_debug_tool_versions(self):
        tools = {
            "ADB": ([self.adb or shutil.which("adb"), "version"], False),
            "Java": ([shutil.which("java"), "-version"], False),
            "Node.js": ([shutil.which("node"), "--version"], False),
            "npm": ([shutil.which("npm"), "--version"], os.name == "nt"),
            "Android CLI": ([self.sdk_package_cli or self.android_cli, "--version"], False),
            "SDK Manager": ([self.sdkmanager_executable, "--version"], os.name == "nt"),
            "scrcpy": ([shutil.which("scrcpy"), "--version"], False),
        }

        def probe(command, use_shell):
            if not command[0]:
                return "not found"
            try:
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=6,
                    shell=use_shell,
                    **_windows_console_options(),
                )
                output = (result.stdout + "\n" + result.stderr).strip()
                first_line = next((line.strip() for line in output.splitlines() if line.strip()), "")
                return (first_line[:200] if first_line else f"available (exit {result.returncode})")
            except (OSError, subprocess.TimeoutExpired) as error:
                return f"could not query version ({error})"

        versions = {}
        with ThreadPoolExecutor(max_workers=len(tools)) as pool:
            pending = {
                pool.submit(probe, command, use_shell): name
                for name, (command, use_shell) in tools.items()
            }
            for future in as_completed(pending):
                versions[pending[future]] = future.result()
        versions["Python"] = platform.python_version()
        if not self.closing:
            self.after(0, self._debug_tool_versions_finished, versions)

    def _debug_tool_versions_finished(self, versions):
        self.debug_tool_versions = versions
        self.debug_version_scan_running = False
        self._refresh_debug_inventory()

    def _export_debug_report(self):
        report = self._debug_report_text()
        destination = filedialog.asksaveasfilename(
            parent=self,
            title="Export diagnostic report",
            initialdir=str(Path.home() / "Desktop"),
            initialfile=f"DCM-Android-Toolkit-Diagnostics-{datetime.now().strftime('%Y%m%d-%H%M%S')}.txt",
            defaultextension=".txt",
            filetypes=(("Text files", "*.txt"), ("All files", "*")),
        )
        if not destination:
            return
        try:
            Path(destination).write_text(report + "\n", encoding="utf-8")
        except OSError as error:
            self.show_error("Could not export diagnostics", str(error), parent=self)
            return
        self.log(f"Diagnostic report saved to {destination}")
        messagebox.showinfo("Diagnostic report exported", f"Saved diagnostic report to:\n\n{destination}", parent=self)

    def _debug_clean_temporary_files(self):
        if self.build_running or self.update_running or self.emulator_download_running or self.emulator_busy or self.debug_cleanup_running or self.debug_sdk_remove_running:
            messagebox.showinfo("Finish the current operation", "Wait for the active build, update, or emulator operation to finish first.", parent=self)
            return
        candidates = self._debug_stale_temp_candidates()
        if not candidates:
            messagebox.showinfo("No stale temporary files", "No toolkit-owned temporary files older than 24 hours were found.", parent=self)
            self._refresh_debug_inventory()
            return
        total_bytes = sum(item["size"] or 0 for item in candidates)
        preview = "\n".join(str(item["path"]) for item in candidates[:12])
        if len(candidates) > 12:
            preview += f"\n…and {len(candidates) - 12} more item(s)"
        if not messagebox.askyesno(
            "Remove stale temporary files?",
            f"Remove {len(candidates)} toolkit-owned temporary item(s)? Known file sizes total {self._debug_size_text(total_bytes)}; folder contents are not pre-scanned.\n\n{preview}\n\nOnly known toolkit temporary names older than 24 hours are included.",
            parent=self,
        ):
            return
        self.debug_cleanup_running = True
        self._refresh_debug_inventory()
        self.log(f"Cleaning {len(candidates)} stale toolkit temporary item(s)…")

        def worker():
            removed = 0
            removed_bytes = 0
            failures = []
            for item in candidates:
                path = item["path"]
                try:
                    if path.is_symlink():
                        continue
                    if item["kind"] == "directory" and path.is_dir():
                        shutil.rmtree(path)
                    elif item["kind"] == "file" and path.is_file():
                        path.unlink()
                    else:
                        continue
                    removed += 1
                    removed_bytes += item["size"] or 0
                except OSError as error:
                    failures.append(f"{path}: {error}")
            if not self.closing:
                self.after(0, self._debug_cleanup_finished, removed, removed_bytes, failures)

        threading.Thread(target=worker, daemon=True).start()

    def _debug_cleanup_finished(self, removed, removed_bytes, failures):
        self.debug_cleanup_running = False
        self.log(f"Debug cleanup removed {removed} stale temporary item(s); known file sizes totaled {self._debug_size_text(removed_bytes)}.")
        self._refresh_debug_inventory()
        if failures:
            messagebox.showwarning("Some temporary files were not removed", "\n".join(failures[:12]), parent=self)
        else:
            messagebox.showinfo("Temporary cleanup complete", f"Removed {removed} item(s). Known file sizes totaled {self._debug_size_text(removed_bytes)}; folder sizes were not pre-scanned.", parent=self)

    def _debug_remove_emulator_package(self):
        self._refresh_debug_inventory()
        if self.build_running or self.update_running or self.emulator_download_running or self.emulator_busy or self.emulator_states or self.debug_cleanup_running or self.debug_sdk_remove_running:
            messagebox.showinfo("Finish active operations", "Stop running emulators and finish active operations before removing the Emulator package.", parent=self)
            return
        if not self.android_sdk_root or not self.sdkmanager_executable:
            self.show_error("SDK Manager unavailable", "Could not find SDK Manager for the selected Android SDK.", parent=self)
            return
        emulator_path = self.android_sdk_root / "emulator" / ("emulator.exe" if os.name == "nt" else "emulator")
        if not emulator_path.is_file():
            messagebox.showinfo("Emulator not installed", "The Android Emulator package is not installed in the selected SDK.", parent=self)
            return
        if not messagebox.askyesno(
            "Remove Android Emulator package?",
            f"Uninstall the Android Emulator SDK package from this SDK?\n\n{self.android_sdk_root}\n\nAndroid Studio and other projects using this SDK will also lose the Emulator package.",
            parent=self,
        ):
            return
        self.debug_sdk_remove_running = True
        self._refresh_debug_inventory()
        sdk_root = self.android_sdk_root
        manager = self.sdkmanager_executable
        self.log(f"Removing Android Emulator SDK package from {sdk_root}…")

        def worker():
            process = None
            output = ""
            error = ""
            try:
                environment = os.environ.copy()
                environment["ANDROID_SDK_ROOT"] = str(sdk_root)
                environment["ANDROID_HOME"] = str(sdk_root)
                process = subprocess.Popen(
                    [manager, f"--sdk_root={sdk_root}", "--uninstall", "emulator"],
                    cwd=str(sdk_root),
                    env=environment,
                    shell=os.name == "nt",
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    start_new_session=(os.name != "nt"),
                    **_windows_console_options(new_process_group=True),
                )
                with self.emulator_process_lock:
                    self.debug_sdk_process = process
                output, _ = process.communicate(timeout=1800)
                if process.returncode:
                    raise RuntimeError(output.strip() or f"SDK Manager exited with code {process.returncode}.")
                if emulator_path.exists():
                    raise RuntimeError("SDK Manager completed, but the Emulator executable is still present.")
            except Exception as error_value:
                error = str(error_value)
                if process and process.poll() is None:
                    self._stop_process_tree(process)
            finally:
                with self.emulator_process_lock:
                    if self.debug_sdk_process is process:
                        self.debug_sdk_process = None
                if not self.closing:
                    self.after(0, self._debug_emulator_remove_finished, error, output)

        threading.Thread(target=worker, daemon=True).start()

    def _debug_emulator_remove_finished(self, error, output=""):
        self.debug_sdk_remove_running = False
        if output.strip():
            for line in output.splitlines():
                self.log(line)
        if error:
            self.log(f"Emulator package removal failed: {error}")
            self.show_error("Could not remove Emulator package", error, parent=self)
        else:
            self.emulator_executable = None
            self.emulator_status.set("Android Emulator SDK package removed from the selected SDK.")
            self.log("Android Emulator SDK package removed.")
            self.refresh_emulators()
        self._refresh_debug_inventory()

    def _debug_remove_bootstrap_tools(self):
        if self.build_running or self.update_running or self.emulator_download_running or self.emulator_busy or self.debug_sdk_remove_running or self.debug_cleanup_running:
            messagebox.showinfo("Finish active operations", "Wait for active build, update, or emulator operations to finish first.", parent=self)
            return
        folders = self._debug_bootstrap_directories()
        if not folders:
            messagebox.showinfo("No toolkit bootstrap tools", "No toolkit bootstrap Command-line Tools folders were found in the selected SDK.", parent=self)
            return
        preview = "\n".join(str(folder) for folder in folders)
        if not messagebox.askyesno(
            "Remove bootstrap Command-line Tools?",
            f"Remove these toolkit-named SDK tool folders?\n\n{preview}\n\nThis only removes folders named dcm-bootstrap-*; other SDK tools are preserved.",
            parent=self,
        ):
            return
        self.debug_cleanup_running = True
        self._refresh_debug_inventory()
        self.log(f"Removing {len(folders)} toolkit bootstrap SDK folder(s)…")
        sdk_root = self.android_sdk_root

        def worker():
            removed = []
            failures = []
            for folder in folders:
                try:
                    if folder.is_symlink() or folder.parent != sdk_root / "cmdline-tools":
                        continue
                    shutil.rmtree(folder)
                    removed.append(str(folder))
                except OSError as error:
                    failures.append(f"{folder}: {error}")
            manager = self._find_sdkmanager(self.android_sdk_roots)
            if not self.closing:
                self.after(0, self._debug_bootstrap_remove_finished, removed, failures, manager)

        threading.Thread(target=worker, daemon=True).start()

    def _debug_bootstrap_remove_finished(self, removed, failures, manager):
        self.debug_cleanup_running = False
        self.sdkmanager_executable = manager
        self.log(f"Removed {len(removed)} toolkit bootstrap SDK folder(s).")
        self._refresh_debug_inventory()
        if failures:
            messagebox.showwarning("Some bootstrap tools remain", "\n".join(failures[:12]), parent=self)
        else:
            messagebox.showinfo("Bootstrap tools removed", f"Removed {len(removed)} folder(s).", parent=self)

    def _debug_clear_apk_history(self):
        if self.build_running or self.update_running or self.emulator_download_running or self.emulator_busy or self.debug_cleanup_running or self.debug_sdk_remove_running:
            messagebox.showinfo("Finish the current operation", "Wait for the active build, update, or emulator operation to finish first.", parent=self)
            return
        expected_archive = APP_ROOT.resolve() / "data" / "apk_versions"
        if (
            APK_ARCHIVE.is_symlink()
            or APK_ARCHIVE.parent.is_symlink()
            or APK_ARCHIVE.resolve() != expected_archive
        ):
            self.show_error("Unsafe archive path", "The local APK archive folder is a symbolic link; no files were removed.", parent=self)
            return
        files = []
        if APK_ARCHIVE.is_dir():
            files = [path for path in APK_ARCHIVE.iterdir() if path.is_file() and not path.is_symlink() and path.suffix.lower() == ".apk"]
        total_bytes = sum(path.stat().st_size for path in files)
        if not messagebox.askyesno(
            "Clear APK history?",
            f"Permanently remove {len(files)} archived APK file(s) ({self._debug_size_text(total_bytes)}) and clear their history notes?\n\nOnly APKs inside {APK_ARCHIVE} are deleted. APKs elsewhere on your computer are untouched.",
            parent=self,
        ):
            return
        self.debug_cleanup_running = True
        self._refresh_debug_inventory()
        self.log(f"Clearing {len(files)} APK history item(s)…")

        def worker():
            failures = []
            removed_count = 0
            for path in files:
                try:
                    if (
                        APK_ARCHIVE.is_symlink()
                        or APK_ARCHIVE.parent.is_symlink()
                        or path.is_symlink()
                        or path.parent.resolve() != expected_archive
                    ):
                        continue
                    path.unlink()
                    removed_count += 1
                except OSError as error:
                    failures.append(f"{path.name}: {error}")
            try:
                if APK_HISTORY.is_symlink() or APK_HISTORY.parent.is_symlink():
                    raise OSError("The APK history index is a symbolic link; it was not changed.")
                APK_HISTORY.parent.mkdir(parents=True, exist_ok=True)
                APK_HISTORY.write_text("[]\n", encoding="utf-8")
            except OSError as error:
                failures.append(str(error))
            if not self.closing:
                self.after(0, self._debug_apk_history_clear_finished, len(files), removed_count, failures)

        threading.Thread(target=worker, daemon=True).start()

    def _debug_apk_history_clear_finished(self, total, removed, failures):
        self.debug_cleanup_running = False
        self.log(f"Cleared local APK history; removed {removed} archived APK file(s).")
        self._refresh_debug_inventory()
        if failures:
            messagebox.showwarning("APK history partially cleared", "\n".join(failures[:12]), parent=self)
        else:
            messagebox.showinfo("APK history cleared", f"Removed {total} archived APK file(s).", parent=self)

    def _debug_reset_settings(self):
        if self.build_running or self.update_running or self.emulator_download_running or self.emulator_busy or self.debug_sdk_remove_running or self.debug_cleanup_running:
            messagebox.showinfo("Finish active operations", "Wait for active operations to finish before resetting settings.", parent=self)
            return
        if not messagebox.askyesno(
            "Reset toolkit settings and profiles?",
            f"Delete saved connection preferences and all project profiles in:\n\n{CONFIG}\n\nThe toolkit will close so the settings file is not recreated. APK history, SMS exports, Android projects, and SDK tools will be preserved.",
            parent=self,
        ):
            return
        self.debug_reset_config_on_close = True
        self.close_app()

    def _update_header_pills(self):
        if hasattr(self, "header_project_pill"):
            project = (self.project_name.get() or "").strip() or "No project"
            self.header_project_pill.setText(f"▣  {project}")
        if hasattr(self, "header_device_pill"):
            serial = self.connected_serial
            if serial:
                label = self.connected_model or serial
                self.header_device_pill.setText(f"●  {label}")
                self.header_device_pill.setProperty("connected", True)
            else:
                self.header_device_pill.setText("○  No device")
                self.header_device_pill.setProperty("connected", False)
            self.header_device_pill.style().unpolish(self.header_device_pill)
            self.header_device_pill.style().polish(self.header_device_pill)

    def _copy_activity_log(self):
        QApplication.clipboard().setText(self.output.toPlainText())
        self.status.set("Activity log copied to clipboard.")

    def _clear_activity_log(self):
        self.output.clear()
        self.status.set("Activity log cleared.")

    def log(self, text, *, capture_errors=True):
        line = text.rstrip()
        is_error = bool(re.search(
            r"\b(error|failed|failure|exception|timed out|timeout|could not|cannot|unable|missing|not found)\b|"
            r"no authorized devices|not installed",
            line,
            re.IGNORECASE,
        ))
        if capture_errors and is_error:
            self._record_diagnostic_error("Activity error", line)
        if is_error:
            color = self.current_theme["console_error"]
        elif re.search(r"\b(warning|warn|caution|stopped|disconnected)\b", line, re.IGNORECASE):
            color = self.current_theme["console_warn"]
        elif re.search(r"\b(succeeded|installed|connected|saved|complete|completed|ready)\b", line, re.IGNORECASE):
            color = self.current_theme["console_success"]
        else:
            color = self.current_theme["console_fg"]
        cursor = self.output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        cursor.insertText(line + "\n", fmt)
        if getattr(self, "activity_autoscroll", None) is None or self.activity_autoscroll.get():
            sb = self.output.verticalScrollBar()
            sb.setValue(sb.maximum())

    def export_activity_log_for_bug_report(self):
        """Save the visible Activity log to Desktop and show support details."""
        desktop = Path.home() / "Desktop"
        if not desktop.is_dir():
            self.show_error(
                "Could not export Activity log",
                f"The Desktop folder was not found:\n\n{desktop}",
                parent=self,
            )
            return

        exported_at = datetime.now().astimezone()
        stamp = exported_at.strftime("%Y%m%d-%H%M%S")
        base_name = f"DCM-Android-Toolkit-Activity-{stamp}"
        log_text = self.output.get("1.0", "end-1c")
        contents = (
            f"DCM Android Toolkit Activity Log\n"
            f"Exported: {exported_at.isoformat(timespec='seconds')}\n\n"
            f"{log_text}\n"
        )
        try:
            for suffix in range(1000):
                name = f"{base_name}{f'-{suffix}' if suffix else ''}.txt"
                export_path = desktop / name
                try:
                    with export_path.open("x", encoding="utf-8", newline="\n") as exported_file:
                        exported_file.write(contents)
                    break
                except FileExistsError:
                    continue
            else:
                raise FileExistsError("Could not find an unused Activity log filename on the Desktop.")
        except OSError as exc:
            self.show_error(
                "Could not export Activity log",
                f"Could not save the Activity log to the Desktop.\n\n{exc}",
                parent=self,
            )
            return

        self._show_bug_report_exported(export_path)

    def _show_bug_report_exported(self, export_path):
        dialog = QDialog(self)
        dialog.setWindowTitle("Activity log exported")
        self._fit_dialog(dialog, preferred=(620, 300), minimum=(480, 250))

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(10)
        title = QLabel("Activity log exported")
        title.setObjectName("PageTitle")
        layout.addWidget(title)
        desc = QLabel("The log is saved on your Desktop. Attach it to an email to support:")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        loc = QLabel(str(export_path))
        loc.setProperty("cardSub", True)
        loc.setWordWrap(True)
        layout.addWidget(loc)
        layout.addWidget(QLabel(BUG_REPORT_EMAIL))
        copied_lbl = QLabel("")
        copied_lbl.setProperty("cardSub", True)
        layout.addWidget(copied_lbl)
        layout.addStretch(1)

        footer = QHBoxLayout()
        def copy_email_address():
            QApplication.clipboard().setText(BUG_REPORT_EMAIL)
            copied_lbl.setText("Email address copied to clipboard.")

        footer.addWidget(self._button(text="Copy email address", command=copy_email_address))
        footer.addStretch(1)
        footer.addWidget(self._button(text="Close", command=dialog.accept))
        layout.addLayout(footer)
        dialog.exec()

    def run_adb(self, *args, timeout=90):
        if not self.adb:
            raise RuntimeError("ADB was not found. Install Android SDK Platform-Tools and ensure adb is on PATH.")
        return subprocess.run(
            [self.adb, *args], capture_output=True, text=True, timeout=timeout,
            **_windows_console_options(),
        )

    @staticmethod
    def _emulator_avd_name(output, avds):
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        for avd in avds:
            if any(line == avd or line.endswith(f" {avd}") for line in lines):
                return avd
        return ""

    def refresh_emulators(self):
        if self.emulator_busy or self.emulator_refresh_running:
            return
        if not self.emulator_executable:
            self.emulator_status.set(
                "Android Emulator is not installed. Choose Download & create AVD to prepare it automatically."
            )
            self._update_emulator_controls()
            return
        self.emulator_refresh_running = True
        self.emulator_status.set("Looking for installed Android Virtual Devices…")
        self._update_emulator_controls()

        def worker():
            try:
                listed = subprocess.run(
                    [self.emulator_executable, "-list-avds"],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=15,
                    **_windows_console_options(),
                )
                if listed.returncode:
                    raise RuntimeError((listed.stderr or listed.stdout).strip() or "The emulator could not list AVDs.")
                avds = list(dict.fromkeys(line.strip() for line in listed.stdout.splitlines() if line.strip()))
                states = {}
                active_serials = set()
                if self.adb:
                    devices = self.run_adb("devices", timeout=10)
                    for line in devices.stdout.splitlines()[1:]:
                        parts = line.split()
                        if len(parts) < 2 or not parts[0].startswith("emulator-"):
                            continue
                        serial, device_state = parts[0], parts[1]
                        active_serials.add(serial)
                        if device_state not in ("device", "offline"):
                            continue
                        try:
                            named = self.run_adb("-s", serial, "emu", "avd", "name", timeout=2)
                        except (OSError, subprocess.TimeoutExpired):
                            continue
                        avd = self._emulator_avd_name(named.stdout + "\n" + named.stderr, avds)
                        if avd:
                            states[avd] = {"serial": serial, "device_state": device_state}
                if not self.closing:
                    self.after(0, self._show_emulators, avds, states, active_serials)
            except Exception as error:
                if not self.closing:
                    self.after(0, self._show_emulator_refresh_error, str(error))

        threading.Thread(target=worker, daemon=True).start()

    def _show_emulators(self, avds, states, active_serials):
        self.emulator_refresh_running = False
        self.emulator_avds = avds
        self.emulator_states = states
        previous_managed = set(self.managed_emulators)
        self.managed_emulators = {
            (avd, serial)
            for avd, serial in self.managed_emulators
            if serial in active_serials
        }
        if self.managed_emulators != previous_managed:
            self._save_config()
        self.emulator_selector.blockSignals(True)
        self.emulator_selector.clear()
        self.emulator_selector.addItems(avds)
        self.emulator_selector.blockSignals(False)
        if self.emulator_avd.get() not in avds:
            self.emulator_avd.set(avds[0] if avds else "")
        else:
            self.emulator_selector.setCurrentText(self.emulator_avd.get())
        self._refresh_emulator_status()
        self._update_emulator_controls()
        self._refresh_install_targets()

    def _show_emulator_refresh_error(self, error):
        self.emulator_refresh_running = False
        self.emulator_status.set(f"Could not refresh emulators: {error}")
        self.log(f"Emulator refresh failed: {error}")
        self._update_emulator_controls()

    def _selected_emulator_state(self):
        avd = self.emulator_avd.get().strip()
        state = self.emulator_states.get(avd)
        if state:
            serial = state["serial"]
            state["managed"] = (avd, serial) in self.managed_emulators
        return avd, state

    def _refresh_emulator_status(self):
        avd, state = self._selected_emulator_state()
        if self.emulator_busy:
            return
        if not self.emulator_executable:
            message = (
                "Android Emulator is not installed. Choose Download & create AVD to prepare the SDK and a default virtual device."
            )
        elif not self.adb:
            message = "ADB was not found. Install Android SDK Platform-Tools to start and connect to virtual devices."
        elif not self.emulator_avds:
            message = "No virtual devices found. Choose Download & create AVD to set one up automatically."
        elif not state:
            message = f"{avd} is stopped. Starting it opens the Android Emulator in a separate window."
        elif state["device_state"] == "offline":
            message = f"{avd} is starting · ADB serial {state['serial']}"
        elif state["managed"]:
            message = f"Running · ADB serial {state['serial']} · started by DCM Android Toolkit"
        else:
            message = f"Running outside this session · ADB serial {state['serial']}"
        self.emulator_status.set(message)

    def _update_emulator_controls(self):
        if not hasattr(self, "emulator_selector"):
            return
        avd, state = self._selected_emulator_state()
        operation_active = self.emulator_busy or self.emulator_refresh_running or self.emulator_download_running
        setup_complete = bool(
            self.emulator_executable
            and Path(self.emulator_executable).is_file()
            and self.emulator_avds
        )
        self.emulator_selector.setEnabled(not (operation_active or not self.emulator_avds))
        self.emulator_download_button.setEnabled(
            not (operation_active or setup_complete or not (self.android_sdk_root and self._cmdline_tools_download_info()))
        )
        self._set_button_label(
            self.emulator_download_button,
            "Setting up…" if self.emulator_download_running else "Download & create AVD",
            style="Build.TButton",
        )
        self.emulator_refresh_button.setEnabled(not operation_active)
        self.emulator_start_button.setEnabled(
            bool(not operation_active and avd and not state and self.emulator_executable and self.adb)
        )
        self.emulator_stop_button.setEnabled(
            bool(not operation_active and state and state.get("managed"))
        )
        self.emulator_connect_button.setEnabled(
            bool(not operation_active and state and state["device_state"] == "device")
        )

    def _bootstrap_sdkmanager(self):
        if not self.android_sdk_root:
            raise RuntimeError("Could not determine the Android SDK folder for emulator setup.")
        download = self._cmdline_tools_download_info()
        if not download:
            raise RuntimeError(
                f"Automatic Android SDK setup is not available for {platform.system()} {platform.machine()}."
            )
        download_url, expected_sha256 = download

        tools_root = self.android_sdk_root / "cmdline-tools"
        tools_root.mkdir(parents=True, exist_ok=True)
        handle, archive_path = tempfile.mkstemp(prefix="dcm-commandline-tools-", suffix=".zip")
        stage_root = None
        try:
            request = urllib.request.Request(
                download_url,
                headers={"User-Agent": "DCM-Android-Toolkit", "Accept": "application/zip"},
            )
            self.after(0, self.status.set, "Downloading official Android SDK Command-line Tools…")
            with os.fdopen(handle, "wb") as archive_file, self._open_github_request(request, timeout=45) as response:
                if not response.geturl().startswith("https://"):
                    raise RuntimeError("Google redirected the SDK download to an insecure URL.")
                content_length = response.headers.get("Content-Length")
                if content_length and int(content_length) > MAX_CMDLINE_TOOLS_ARCHIVE_BYTES:
                    raise RuntimeError("The Android SDK Command-line Tools archive exceeds the 250 MB limit.")
                digest = hashlib.sha256()
                received = 0
                while True:
                    if self.closing:
                        raise InterruptedError("SDK tools download canceled because the toolkit is closing.")
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    received += len(chunk)
                    if received > MAX_CMDLINE_TOOLS_ARCHIVE_BYTES:
                        raise RuntimeError("The Android SDK Command-line Tools archive exceeded the 250 MB limit.")
                    archive_file.write(chunk)
                    digest.update(chunk)
                    if content_length:
                        self.after(
                            0,
                            self.status.set,
                            f"Downloading SDK tools: {received / (1024 * 1024):.0f} MB / {int(content_length) / (1024 * 1024):.0f} MB",
                        )
            if digest.hexdigest() != expected_sha256:
                raise RuntimeError("The downloaded SDK Command-line Tools failed the official SHA-256 check.")

            install_dir = tools_root / f"dcm-bootstrap-{CMDLINE_TOOLS_BUILD}"
            suffix = 1
            while install_dir.exists():
                install_dir = tools_root / f"dcm-bootstrap-{CMDLINE_TOOLS_BUILD}-{suffix}"
                suffix += 1
            install_dir.mkdir()
            stage_root = install_dir
            unpacked_size = 0
            with zipfile.ZipFile(archive_path) as package:
                for info in package.infolist():
                    if "\\" in info.filename:
                        raise RuntimeError("The SDK Command-line Tools archive contains an unsafe path.")
                    member = PurePosixPath(info.filename)
                    if member.is_absolute() or ".." in member.parts or not member.parts or member.parts[0] != "cmdline-tools":
                        raise RuntimeError("The SDK Command-line Tools archive contains an unsafe path.")
                    relative_parts = member.parts[1:]
                    if not relative_parts or info.is_dir():
                        continue
                    mode = info.external_attr >> 16
                    if stat.S_ISLNK(mode) or ":" in relative_parts[0]:
                        raise RuntimeError("The SDK Command-line Tools archive contains an unsafe file.")
                    unpacked_size += info.file_size
                    if unpacked_size > 600 * 1024 * 1024:
                        raise RuntimeError("The expanded SDK Command-line Tools exceed the 600 MB limit.")
                    staged_file = install_dir.joinpath(*relative_parts)
                    staged_file.parent.mkdir(parents=True, exist_ok=True)
                    with package.open(info) as source, staged_file.open("xb") as destination:
                        shutil.copyfileobj(source, destination, length=1024 * 1024)
                    if os.name != "nt" and stat.S_IMODE(mode) & 0o111:
                        staged_file.chmod(stat.S_IMODE(mode))
            manager_name = "sdkmanager.bat" if os.name == "nt" else "sdkmanager"
            avdmanager_name = "avdmanager.bat" if os.name == "nt" else "avdmanager"
            if not (install_dir / "bin" / manager_name).is_file():
                raise RuntimeError(f"The SDK Command-line Tools archive did not contain {manager_name}.")
            if os.name != "nt":
                for name in (manager_name, avdmanager_name):
                    manager_file = install_dir / "bin" / name
                    if manager_file.is_file():
                        manager_file.chmod(manager_file.stat().st_mode | 0o111)

            stage_root = None
            sdkmanager = install_dir / "bin" / manager_name
            self.sdkmanager_executable = str(sdkmanager)
            self.avdmanager_executable = str(install_dir / "bin" / avdmanager_name)
            return str(sdkmanager)
        finally:
            try:
                os.unlink(archive_path)
            except OSError:
                pass
            if stage_root:
                shutil.rmtree(stage_root, ignore_errors=True)

    def download_emulator_package(self):
        if self.emulator_download_running or self.emulator_busy or self.emulator_refresh_running:
            return
        if not self.android_sdk_root:
            self.emulator_status.set("Could not determine the Android SDK folder for emulator setup.")
            return
        if not self._cmdline_tools_download_info():
            self.emulator_status.set(
                f"Automatic Android SDK setup is not available for {platform.system()} {platform.machine()}."
            )
            return
        sdk_root = self.android_sdk_root
        machine = platform.machine().casefold()
        if machine in ("arm64", "aarch64"):
            image_arch = "arm64-v8a"
        elif machine in ("amd64", "x86_64", "x64"):
            image_arch = "x86_64"
        else:
            self.emulator_status.set(f"No default Android system image is available for {platform.machine()}.")
            return
        system_image = f"system-images;android-{DEFAULT_AVD_API};google_apis;{image_arch}"
        selected_avd = self.emulator_avd.get().strip()

        self.emulator_download_running = True
        self.emulator_status.set("Preparing SDK tools, emulator, system image, and virtual device…")
        self.log(f"Setting up emulator, Platform-Tools, {system_image}, and a default AVD…")
        self._update_emulator_controls()

        def worker():
            process = None
            reader = None
            output_queue = queue.Queue()
            output_lines = []
            licenses_declined = False
            try:
                env = os.environ.copy()
                env["ANDROID_SDK_ROOT"] = str(sdk_root)
                env["ANDROID_HOME"] = str(sdk_root)
                sdkmanager = self.sdkmanager_executable
                avdmanager = self.avdmanager_executable
                if not sdkmanager or not avdmanager:
                    sdkmanager = self._bootstrap_sdkmanager()
                    avdmanager = self.avdmanager_executable
                if not sdkmanager or not avdmanager or not Path(avdmanager).is_file():
                    raise RuntimeError("Android SDK Command-line Tools must include sdkmanager and avdmanager.")
                command = [
                    sdkmanager,
                    f"--sdk_root={sdk_root}",
                    "--install",
                    "platform-tools",
                    "emulator",
                    system_image,
                ]
                with self.emulator_process_lock:
                    if self.closing:
                        return
                    process = subprocess.Popen(
                        command,
                        cwd=str(sdk_root) if sdk_root.is_dir() else None,
                        env=env,
                        shell=os.name == "nt",
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        bufsize=1,
                        start_new_session=(os.name != "nt"),
                        **_windows_console_options(new_process_group=True),
                    )
                    self.emulator_download_process = process

                def read_output():
                    try:
                        pending = ""
                        while True:
                            character = process.stdout.read(1)
                            if not character:
                                break
                            pending += character
                            if character in "\r\n" or re.search(r"Accept\?\s*\(y/N\)", pending, re.IGNORECASE):
                                output_queue.put(pending.strip())
                                pending = ""
                        if pending:
                            output_queue.put(pending.strip())
                    finally:
                        output_queue.put(None)

                reader = threading.Thread(target=read_output, daemon=True)
                reader.start()
                output_finished = False
                deadline = time.monotonic() + 1800
                while process.poll() is None or not output_finished:
                    if self.closing:
                        self._stop_process_tree(process)
                        return
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        self._stop_process_tree(process)
                        raise TimeoutError("Emulator package download exceeded the 30-minute time limit.")
                    try:
                        line = output_queue.get(timeout=min(0.2, remaining))
                    except queue.Empty:
                        continue
                    if line is None:
                        output_finished = True
                        continue
                    output_lines.append(line)
                    if line:
                        self.after(0, self.log, line)
                    if re.search(r"Accept\?\s*\(y/N\)", line, re.IGNORECASE):
                        response_event = threading.Event()
                        response = {"accepted": False}

                        def ask_for_license():
                            try:
                                if not self.closing:
                                    response["accepted"] = messagebox.askyesno(
                                        "Android SDK License",
                                        "Review the license text in Activity. Do you accept this Android SDK license to continue?",
                                        parent=self,
                                    )
                            finally:
                                answer = "y\n" if response["accepted"] else "n\n"
                                try:
                                    process.stdin.write(answer)
                                    process.stdin.flush()
                                except (AttributeError, OSError, ValueError):
                                    pass
                                response_event.set()

                        self.after(0, ask_for_license)
                        response_deadline = time.monotonic() + 300
                        while not response_event.wait(timeout=0.2):
                            if self.closing:
                                raise InterruptedError("SDK license prompt canceled because the toolkit is closing.")
                            if time.monotonic() >= response_deadline:
                                raise TimeoutError("Timed out waiting for a response to the Android SDK license prompt.")
                        if not response["accepted"]:
                            licenses_declined = True
                return_code = process.wait()
                reader.join(timeout=2)
                with self.emulator_process_lock:
                    if self.emulator_download_process is process:
                        self.emulator_download_process = None
                if return_code:
                    details = "\n".join(output_lines[-40:])
                    raise RuntimeError(
                        details or f"Android SDK package installation exited with code {return_code}."
                    )
                if licenses_declined:
                    raise RuntimeError(
                        "Setup stopped because an Android SDK license was declined. Restart setup and accept the required license to continue."
                    )
                emulator_name = "emulator.exe" if os.name == "nt" else "emulator"
                installed_emulator = sdk_root / "emulator" / emulator_name
                if not installed_emulator.is_file():
                    raise RuntimeError(
                        "The package command completed, but the Emulator executable was not found in the selected SDK."
                    )
                listed = subprocess.run(
                    [str(installed_emulator), "-list-avds"],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=30,
                    env=env,
                    **_windows_console_options(),
                )
                if listed.returncode:
                    raise RuntimeError((listed.stderr or listed.stdout).strip() or "Could not list AVDs after installing the Emulator.")
                existing_avds = {line.strip() for line in listed.stdout.splitlines() if line.strip()}
                if existing_avds:
                    avd_name = selected_avd if selected_avd in existing_avds else sorted(existing_avds)[0]
                    self.after(0, self.log, f"Keeping existing Android Virtual Device {avd_name}; no duplicate was created.")
                else:
                    avd_name = DEFAULT_AVD_NAME
                    suffix = 2
                    while avd_name in existing_avds:
                        avd_name = f"{DEFAULT_AVD_NAME}_{suffix}"
                        suffix += 1
                    avd_command = [
                        avdmanager,
                        "create",
                        "avd",
                        "-n",
                        avd_name,
                        "-k",
                        system_image,
                    ]
                    with self.emulator_process_lock:
                        if self.closing:
                            return
                        process = subprocess.Popen(
                            avd_command,
                            cwd=str(sdk_root),
                            env=env,
                            shell=os.name == "nt",
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            text=True,
                            encoding="utf-8",
                            errors="replace",
                            start_new_session=(os.name != "nt"),
                            **_windows_console_options(new_process_group=True),
                        )
                        self.emulator_download_process = process
                    try:
                        avd_output, _ = process.communicate(input="no\n", timeout=300)
                    except subprocess.TimeoutExpired:
                        self._stop_process_tree(process)
                        raise TimeoutError("Creating the default Android Virtual Device timed out.")
                    finally:
                        with self.emulator_process_lock:
                            if self.emulator_download_process is process:
                                self.emulator_download_process = None
                    if avd_output.strip():
                        for line in avd_output.splitlines():
                            self.after(0, self.log, line)
                    if process.returncode:
                        raise RuntimeError(avd_output.strip() or f"AVD creation exited with code {process.returncode}.")
                adb_executable = "adb.exe" if os.name == "nt" else "adb"
                installed_adb = sdk_root / "platform-tools" / adb_executable
                if not self.closing:
                    self.after(0, self._emulator_download_finished, True, "", str(sdk_root), avd_name, str(installed_adb))
            except Exception as error:
                if process and process.poll() is None:
                    self._stop_process_tree(process)
                if reader and reader.is_alive():
                    reader.join(timeout=2)
                with self.emulator_process_lock:
                    if self.emulator_download_process is process:
                        self.emulator_download_process = None
                if not self.closing:
                    details = "\n".join(output_lines[-40:])
                    message = f"{error}\n\n{details}".strip()
                    if "license" in message.lower():
                        message += "\n\nReview the license text in Activity and accept it in the prompt to continue setup."
                    self.after(0, self._emulator_download_finished, False, message)

        threading.Thread(target=worker, daemon=True).start()

    def _emulator_download_finished(self, succeeded, error, sdk_root="", avd_name="", adb_path=""):
        self.emulator_download_running = False
        if succeeded:
            if sdk_root:
                self.android_sdk_root = Path(sdk_root).expanduser()
                if self.android_sdk_root not in self.android_sdk_roots:
                    self.android_sdk_roots.insert(0, self.android_sdk_root)
                self.sdkmanager_executable = self._find_sdkmanager(self.android_sdk_roots)
                self.avdmanager_executable = self._find_avdmanager(self.android_sdk_roots)
                if adb_path and Path(adb_path).is_file() and not self.adb:
                    self.adb = adb_path
            emulator_name = "emulator.exe" if os.name == "nt" else "emulator"
            candidate = self.android_sdk_root / "emulator" / emulator_name if self.android_sdk_root else None
            self.emulator_executable = (
                str(candidate) if candidate and candidate.is_file() else self._find_emulator(self.adb, self.project_dir.get())
            )
            if avd_name:
                self.emulator_avd.set(avd_name)
            self.emulator_status.set(f"Android Emulator setup is complete. {avd_name} is ready to start.")
            self.log(f"Android Emulator setup is complete. AVD {avd_name} is ready; Android Studio is not required.")
            self.refresh_emulators()
        else:
            self.emulator_status.set("Could not download the Android Emulator package. Review Activity for details.")
            self.log(f"Android Emulator package installation failed:\n{error}")
            self.show_error("Could not download emulator", error, parent=self)
        self._update_emulator_controls()

    def start_selected_emulator(self):
        avd, state = self._selected_emulator_state()
        if not avd or state or not self.emulator_executable:
            return
        if not self.adb:
            self.emulator_status.set("ADB is required to wait for the emulator to finish booting.")
            return
        self.emulator_busy = True
        self.emulator_status.set(f"Starting {avd}… The first boot can take several minutes.")
        self._update_emulator_controls()
        self.log(f"Starting Android Virtual Device {avd}…")

        def worker():
            process = None
            reader = None
            serial = ""
            output_queue = queue.Queue()
            output_lines = []
            try:
                self.run_adb("start-server", timeout=15)
                emulator_dir = Path(self.emulator_executable).parent
                sdk_root = emulator_dir.parent
                process_env = os.environ.copy()
                process_env["ANDROID_SDK_ROOT"] = str(sdk_root)
                process_env["ANDROID_HOME"] = str(sdk_root)
                process_env["PATH"] = os.pathsep.join(
                    (str(emulator_dir), str(Path(self.adb).parent), process_env.get("PATH", ""))
                )
                with self.emulator_process_lock:
                    if self.closing:
                        return
                    # Prefer the SDK executable on Windows: the Android CLI wrapper can
                    # create additional visible command windows while starting an AVD.
                    start_with_android_cli = bool(self.android_cli) and os.name != "nt"
                    start_args = (
                        [self.android_cli, "--no-metrics", f"--sdk={sdk_root}", "emulator", "start", avd]
                        if start_with_android_cli
                        else [self.emulator_executable, "-avd", avd]
                    )
                    process = subprocess.Popen(
                        start_args,
                        cwd=str(emulator_dir),
                        env=process_env,
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        bufsize=1,
                        start_new_session=(os.name != "nt"),
                        **_windows_console_options(new_process_group=True),
                    )
                    self.emulator_start_process = process
                    self.emulator_start_serial = None

                def read_output():
                    try:
                        for line in process.stdout:
                            output_queue.put(line.rstrip())
                    finally:
                        output_queue.put(None)

                reader = threading.Thread(target=read_output, daemon=True)
                reader.start()
                deadline = time.monotonic() + 600
                next_status = 0.0
                while time.monotonic() < deadline:
                    if self.closing:
                        self._stop_process_tree(process)
                        return
                    while True:
                        try:
                            line = output_queue.get_nowait()
                        except queue.Empty:
                            break
                        if line:
                            output_lines.append(line)
                            output_lines = output_lines[-40:]
                    if process.poll() is not None and process.returncode != 0:
                        detail = "\n".join(output_lines[-20:])
                        raise RuntimeError(detail or f"The emulator exited with code {process.returncode} before booting.")

                    devices = self.run_adb("devices", timeout=10)
                    candidates = [
                        parts[0]
                        for line in devices.stdout.splitlines()[1:]
                        if len(parts := line.split()) >= 2 and parts[0].startswith("emulator-")
                    ]
                    for candidate in candidates:
                        try:
                            named = self.run_adb("-s", candidate, "emu", "avd", "name", timeout=2)
                            if self._emulator_avd_name(named.stdout + "\n" + named.stderr, [avd]) == avd:
                                serial = candidate
                                with self.emulator_process_lock:
                                    self.emulator_start_serial = serial
                                break
                        except (OSError, subprocess.TimeoutExpired):
                            continue
                    if serial:
                        device = self.run_adb("-s", serial, "get-state", timeout=5)
                        if device.returncode == 0 and device.stdout.strip() == "device":
                            boot = self.run_adb("-s", serial, "shell", "getprop", "sys.boot_completed", timeout=8)
                            if boot.returncode == 0 and boot.stdout.strip() == "1":
                                with self.emulator_process_lock:
                                    self.emulator_start_process = None
                                    self.emulator_start_serial = None
                                    self.emulator_processes[avd] = process
                                if not self.closing:
                                    self.after(0, self._emulator_started, avd, serial)
                                return
                    if time.monotonic() >= next_status:
                        self.after(0, self.emulator_status.set, f"Booting {avd}… waiting for Android to be ready")
                        next_status = time.monotonic() + 5
                    time.sleep(1)
                raise TimeoutError(f"{avd} did not finish booting within 10 minutes.")
            except Exception as error:
                if serial:
                    try:
                        self.run_adb("-s", serial, "emu", "kill", timeout=5)
                    except (OSError, subprocess.TimeoutExpired):
                        pass
                if process:
                    self._stop_process_tree(process)
                if reader and reader.is_alive():
                    reader.join(timeout=2)
                with self.emulator_process_lock:
                    if self.emulator_start_process is process:
                        self.emulator_start_process = None
                        self.emulator_start_serial = None
                details = str(error)
                if output_lines and "\n".join(output_lines[-20:]) not in details:
                    details = f"{details}\n\n" + "\n".join(output_lines[-20:])
                if not self.closing:
                    self.after(0, self._emulator_start_failed, avd, details)

        threading.Thread(target=worker, daemon=True).start()

    def _emulator_started(self, avd, serial):
        self.emulator_busy = False
        self.managed_emulators.add((avd, serial))
        self.emulator_states[avd] = {"serial": serial, "device_state": "device", "managed": True}
        self._save_config()
        self.emulator_status.set(f"Running · ADB serial {serial} · started by DCM Android Toolkit")
        self.log(f"Android Emulator is ready: {avd} ({serial}). Select Connect emulator to use it in the toolkit.")
        self._update_emulator_controls()
        self.refresh_devices()

    def _emulator_start_failed(self, avd, error):
        self.emulator_busy = False
        self.emulator_status.set(f"Could not start {avd}. Review the error details.")
        self.log(f"Could not start Android Virtual Device {avd}:\n{error}")
        self.show_error("Could not start emulator", error, parent=self)
        self._update_emulator_controls()
        self.refresh_emulators()

    def stop_selected_emulator(self):
        avd, state = self._selected_emulator_state()
        if not state or not state.get("managed"):
            return
        serial = state["serial"]
        self.emulator_busy = True
        self.emulator_status.set(f"Stopping {avd} ({serial})…")
        self._update_emulator_controls()

        def worker():
            try:
                stopped = self.run_adb("-s", serial, "emu", "kill", timeout=10)
                if stopped.returncode:
                    raise RuntimeError((stopped.stderr or stopped.stdout).strip() or "The emulator did not accept the stop command.")
                process = self.emulator_processes.get(avd)
                deadline = time.monotonic() + 20
                while time.monotonic() < deadline:
                    if process and process.poll() is not None:
                        break
                    devices = self.run_adb("devices", timeout=5)
                    active = any(
                        (parts := line.split()) and parts[0] == serial
                        for line in devices.stdout.splitlines()[1:]
                    )
                    if not active:
                        break
                    time.sleep(1)
                if process and process.poll() is None:
                    self._stop_process_tree(process)
                if not self.closing:
                    self.after(0, self._emulator_stopped, avd, serial)
            except Exception as error:
                if not self.closing:
                    self.after(0, self._emulator_stop_failed, avd, str(error))

        threading.Thread(target=worker, daemon=True).start()

    def _emulator_stopped(self, avd, serial):
        self.emulator_busy = False
        self.managed_emulators.discard((avd, serial))
        self.emulator_states.pop(avd, None)
        with self.emulator_process_lock:
            self.emulator_processes.pop(avd, None)
        self._save_config()
        self.emulator_status.set(f"{avd} is stopped.")
        self.log(f"Stopped Android Virtual Device {avd} ({serial}).")
        if self.connected_serial == serial:
            self.pending_display_settings.pop(serial, None)
            self.keep_awake_original = None
            self._clear_connection()
        self._update_emulator_controls()
        self.refresh_devices()
        self.refresh_emulators()

    def _emulator_stop_failed(self, avd, error):
        self.emulator_busy = False
        self.emulator_status.set(f"Could not stop {avd}: {error}")
        self.log(f"Could not stop Android Virtual Device {avd}: {error}")
        self._update_emulator_controls()

    def connect_selected_emulator(self):
        avd, state = self._selected_emulator_state()
        if not state or state["device_state"] != "device":
            return
        serial = state["serial"]
        self.emulator_busy = True
        self.emulator_status.set(f"Connecting to {avd} ({serial})…")
        self._update_emulator_controls()

        def worker():
            try:
                model = self.run_adb("-s", serial, "shell", "getprop", "ro.product.model", timeout=10)
                if model.returncode:
                    raise RuntimeError((model.stderr or model.stdout).strip() or "ADB could not read the emulator model.")
                if not self.closing:
                    self.after(0, self._emulator_connected, avd, serial, model.stdout.strip() or "Android Emulator")
            except Exception as error:
                if not self.closing:
                    self.after(0, self._emulator_connect_failed, avd, str(error))

        threading.Thread(target=worker, daemon=True).start()

    def _emulator_connected(self, avd, serial, model):
        self.emulator_busy = False
        self._set_active_device(serial, model)
        self._save_config()
        self.emulator_status.set(f"Connected to {avd} · {serial}")
        self.log(f"Selected Android Emulator {avd} as the active device ({serial}).")
        self._update_emulator_controls()

    def _emulator_connect_failed(self, avd, error):
        self.emulator_busy = False
        self.emulator_status.set(f"Could not connect to {avd}: {error}")
        self.log(f"Could not connect to Android Emulator {avd}: {error}")
        self._update_emulator_controls()

    def _connection_method_changed(self):
        self._render_connection_state()
        self._save_config()

    def refresh_devices(self):
        self.status.set("Checking for connected devices…")

        def worker():
            try:
                result = self.run_adb("devices", timeout=10)
                devices = [
                    parts[0]
                    for line in result.stdout.splitlines()[1:]
                    if len(parts := line.split()) >= 2 and parts[1] == "device"
                ]
                self.after(0, lambda: self._show_refreshed_devices(result.stdout, devices))
            except Exception as e:
                self.after(0, lambda error=str(e): self._show_refresh_error(error))

        threading.Thread(target=worker, daemon=True).start()

    def _show_refreshed_devices(self, output, devices):
        self.available_device_serials = list(devices)
        usb_devices = [device for device in devices if ":" not in device]
        self.devices.blockSignals(True)
        self.devices.clear()
        self.devices.addItems(usb_devices)
        self.devices.blockSignals(False)
        if self.last_device in usb_devices:
            self.target.set(self.last_device)
        elif self.target.get() not in usb_devices:
            self.target.set(usb_devices[0] if usb_devices else "")
        if self.target.get():
            self.devices.setCurrentText(self.target.get())
        if not self.connected_serial:
            self.status.set(f"{len(devices)} authorized device(s) available" if devices else "No authorized devices. Check the USB prompt or Wi-Fi connection.")
        self.log(output or "No device listed. For Wi-Fi, enable Wireless debugging on the phone.")
        self._refresh_install_targets()

    def _refresh_install_targets(self):
        if not hasattr(self, "install_target_selector"):
            return
        avd_names = {
            state.get("serial"): avd
            for avd, state in self.emulator_states.items()
            if state.get("device_state") == "device"
        }
        target_serials = {}
        for serial in self.available_device_serials:
            if serial.startswith("emulator-"):
                avd = avd_names.get(serial)
                label = f"{avd} · {serial}" if avd else f"Android emulator · {serial}"
            elif ":" in serial:
                label = f"Wi-Fi device · {serial}"
            else:
                label = f"USB device · {serial}"
            target_serials[label] = serial
        self.install_target_serials = target_serials
        labels = list(target_serials)
        self.install_target_selector.blockSignals(True)
        self.install_target_selector.clear()
        self.install_target_selector.addItems(labels)
        self.install_target_selector.blockSignals(False)
        current_serial = target_serials.get(self.install_target.get())
        if current_serial not in self.available_device_serials:
            preferred = self.connected_serial if self.connected_serial in self.available_device_serials else ""
            if not preferred:
                preferred = next(iter(target_serials.values()), "")
            selected_label = next((label for label, serial in target_serials.items() if serial == preferred), "")
            self.install_target.set(selected_label)
        if self.install_target.get():
            self.install_target_selector.setCurrentText(self.install_target.get())

    def _show_refresh_error(self, error):
        if not self.connected_serial:
            self.status.set(error)
        self.log(error)

    def restore_previous_device(self):
        if not self.last_device:
            self.refresh_devices()
            return
        serial = self.last_device
        method = self.last_device_method
        self.status.set(f"Checking previous {method} device for up to 1 second…")

        def worker():
            deadline = time.monotonic() + 1.0
            messages = [f"Checking previous {method} device {serial} (1 second maximum)…"]
            model = "Android device"
            try:
                result = self.run_adb("devices", timeout=max(0.001, deadline - time.monotonic()))
                messages.append(result.stdout.strip() or "ADB listed no devices.")
                states = {}
                for line in result.stdout.splitlines()[1:]:
                    parts = line.split()
                    if len(parts) >= 2:
                        states[parts[0]] = parts[1]
                online = states.get(serial) == "device"
                if not online and method == "Wi-Fi" and ":" in serial and time.monotonic() < deadline:
                    remaining = deadline - time.monotonic()
                    try:
                        connected = self.run_adb("connect", serial, timeout=max(0.001, remaining))
                        messages.append((connected.stdout + connected.stderr).strip() or "ADB connect timed out.")
                    except subprocess.TimeoutExpired:
                        messages.append("Reconnect attempt reached the 1-second startup limit.")
                    if time.monotonic() < deadline:
                        try:
                            check = self.run_adb("devices", timeout=max(0.001, deadline - time.monotonic()))
                            states = {
                                parts[0]: parts[1]
                                for line in check.stdout.splitlines()[1:]
                                if len(parts := line.split()) >= 2
                            }
                            online = states.get(serial) == "device"
                        except subprocess.TimeoutExpired:
                            pass
                if online and time.monotonic() < deadline:
                    try:
                        model_result = self.run_adb("-s", serial, "shell", "getprop", "ro.product.model", timeout=max(0.001, deadline - time.monotonic()))
                        model = model_result.stdout.strip() or model
                    except subprocess.TimeoutExpired:
                        pass
                self.after(0, lambda: self._finish_restore(serial, method, online, model, messages))
            except subprocess.TimeoutExpired:
                messages.append("Previous device check reached the 1-second startup limit.")
                self.after(0, lambda: self._finish_restore(serial, method, False, model, messages))
            except Exception as e:
                messages.append(f"Device restore error: {e}")
                self.after(0, lambda: self._finish_restore(serial, method, False, model, messages))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_restore(self, serial, method, online, model, messages):
        for message in messages:
            self.log(message)
        if online:
            self._set_active_device(serial, model)
            self.log(f"Restored previous {method} device: {model}")
            return
        if method == "Wi-Fi":
            self.wifi.set(serial)
        self.status.set(f"Previous device not available after 1 second. {method} remains selected; connect when ready.")

    def _update_ip_mode(self):
        if not hasattr(self, "manual_entry"):
            return
        active = self.connected_serial is not None
        if active:
            for widget in self.connection_widgets:
                widget.setEnabled(False)
            self._set_button_label(self.disconnect_button, "Disconnect", style="Danger.TButton")
            self.disconnect_button.setEnabled(True)
            self.keep_awake_button.setEnabled(True)
            self.brightness_scale.setEnabled(True)
            self._render_connection_state()
            return
        self._set_button_label(self.disconnect_button, "Disconnect", style="Danger.TButton")
        self.disconnect_button.setEnabled(False)
        self.keep_awake_button.setEnabled(False)
        self.brightness_scale.setEnabled(False)
        self._render_connection_state()
        self.fixed_entry.setEnabled(bool(self.use_fixed_wifi.get()))
        self.manual_entry.setEnabled(not bool(self.use_fixed_wifi.get()))
        for widget in self.connection_widgets:
            if widget in (self.fixed_entry, self.manual_entry):
                continue
            widget.setEnabled(True)

    def _render_connection_state(self):
        self._update_watch_screen_state()
        if not hasattr(self, "connected_card"):
            return
        if self.connected_serial:
            self.device_card.setVisible(False)
            self.wifi_card.setVisible(False)
            self.connected_card.setVisible(True)
        else:
            self.connected_card.setVisible(False)
            if self.connection_method.get() == "USB":
                self.wifi_card.setVisible(False)
                self.device_card.setVisible(True)
            else:
                self.device_card.setVisible(False)
                self.wifi_card.setVisible(True)

    def _update_watch_screen_state(self):
        if not hasattr(self, "watch_button"):
            return
        if self.connected_serial:
            connection_type = "Android Emulator" if self.connected_serial.startswith("emulator-") else self.connection_method.get()
            self.watch_device_label.setText(f"Ready: {self.connected_model or 'Android device'} · {connection_type}")
            self.watch_button.setEnabled(True)
        else:
            self.watch_device_label.setText("Connect a device first.")
            self.watch_button.setEnabled(False)

    def open_screen_mirror(self):
        if not self.connected_serial:
            messagebox.showinfo("Connect a device", "Connect an authorized Android device on the Connection tab first.")
            return
        if self.mirror_process and self.mirror_process.poll() is None:
            self.status.set("Screen window is already open")
            self.log("The screen mirror is already running. Close its window before opening another.")
            return

        scrcpy = shutil.which("scrcpy")
        if not scrcpy:
            for candidate in (Path("/opt/homebrew/bin/scrcpy"), Path("/usr/local/bin/scrcpy")):
                if candidate.is_file():
                    scrcpy = str(candidate)
                    break
        if not scrcpy:
            self.show_error("scrcpy is required", "Install scrcpy to mirror and control the phone screen.\n\nOn macOS, run:\n\nbrew install scrcpy")
            self.log("Screen mirror unavailable: scrcpy was not found. Install it with `brew install scrcpy`.")
            return

        serial = self.connected_serial
        title = f"{self.connected_model or 'Android device'} · DCM Android Toolkit"
        import os
        process_env = os.environ.copy()
        process_env["PATH"] = os.pathsep.join((str(Path(scrcpy).parent), str(Path(self.adb).parent) if self.adb else "", process_env.get("PATH", "")))
        try:
            self.mirror_process = subprocess.Popen(
                [scrcpy, f"--serial={serial}", f"--window-title={title}", "--no-audio"],
                env=process_env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            self.status.set("Opening interactive screen window…")
            self.log(f"Opening live screen for {self.connected_model or serial}. Touch input is enabled in the mirror window.")
            self.after(900, self._check_screen_mirror_start)
        except OSError as error:
            self.mirror_process = None
            self.show_error("Could not open screen window", str(error))
            self.log(f"Screen mirror error: {error}")

    def _check_screen_mirror_start(self):
        if self.mirror_process is None:
            return
        if self.mirror_process.poll() is None:
            self.status.set("Live screen window is open · touch control enabled")
            return
        exit_code = self.mirror_process.returncode
        self.mirror_process = None
        self.status.set("Screen mirror closed")
        self.log(f"Screen mirror exited ({exit_code}). Confirm the device is connected and authorized in ADB, then try again.")

    def _stop_screen_mirror(self):
        process = self.mirror_process
        self.mirror_process = None
        if process and process.poll() is None:
            process.terminate()

    def _activate_device(self, serial):
        result = self.run_adb("devices")
        devices = [line.split()[0] for line in result.stdout.splitlines()[1:] if len(line.split()) >= 2 and line.split()[1] == "device"]
        self.devices["values"] = [device for device in devices if ":" not in device]
        if serial not in devices:
            self.status.set("ADB did not report the device as authorized. Check the phone prompt and refresh.")
            self.log(result.stdout)
            return
        model_result = self.run_adb("-s", serial, "shell", "getprop", "ro.product.model")
        model = model_result.stdout.strip() if model_result.returncode == 0 else ""
        if not model:
            model = "Android device"
        self._set_active_device(serial, model)

    def _set_active_device(self, serial, model):
        self.target.set(serial)
        self.connected_serial = serial
        self.last_device = serial
        self.connected_model = model
        saved_settings = self.pending_display_settings.get(serial)
        if isinstance(saved_settings, dict):
            self.keep_awake_original = {
                tuple(key.split("|", 1)): value
                for key, value in saved_settings.items()
                if "|" in key
            }
            self.keep_awake.set(bool(self.keep_awake_original))
        else:
            self.keep_awake_original = None
            self.keep_awake.set(False)
        if serial.startswith("emulator-"):
            self.last_device_method = "Emulator"
            detail = f"Connection: Android Emulator · {serial}"
        elif ":" in serial:
            self.connection_method.set("Wi-Fi")
            self.last_device_method = "Wi-Fi"
            detail = f"Connection: Wi-Fi · {serial}"
        else:
            self.connection_method.set("USB")
            self.last_device_method = "USB"
            detail = "Connection: USB cable"
        self.active_label.setText(f"Connected device: {model}")
        self.connection_detail_label.setText(detail)
        self.status.set(f"Connected to {model}")
        self._save_config()
        self._update_ip_mode()
        self._update_header_pills()

    def connect_usb(self):
        serial = self.target.get().strip()
        if not serial:
            messagebox.showinfo("Choose a device", "Refresh the list and choose an authorized USB device first.")
            return
        if ":" in serial:
            messagebox.showinfo("Choose a USB device", "This is a Wi-Fi ADB connection. Switch to Wi-Fi or select a USB device.")
            return
        try:
            self._activate_device(serial)
        except Exception as e:
            self.status.set("Could not identify connected device")
            self.log(f"Device identification error: {e}")

    def disconnect_device(self):
        serial = self.connected_serial
        if not serial:
            return
        self.disconnect_button.setEnabled(False)
        self.keep_awake_button.setEnabled(False)
        self.status.set("Restoring device settings and disconnecting…")

        def worker():
            try:
                if self.keep_awake_original is not None:
                    self.after(0, lambda: self.log("Leaving keep-awake and brightness active on the device after ADB disconnect. Reconnect and turn the toggle off to restore the previous settings."))
                if ":" in serial:
                    result = self.run_adb("disconnect", serial)
                    if result.returncode:
                        raise RuntimeError((result.stderr or result.stdout).strip() or "ADB could not disconnect the Wi-Fi device")
                    self.after(0, lambda: self.log((result.stdout + result.stderr).strip() or f"Disconnected {serial}"))
                self.after(0, self._clear_connection)
            except Exception as e:
                message = str(e)
                self.after(0, lambda: self._disconnect_failed(message))

        threading.Thread(target=worker, daemon=True).start()

    def _disconnect_failed(self, message):
        self.keep_awake.set(self.keep_awake_original is not None)
        self.disconnect_button.setEnabled(True)
        self.keep_awake_button.setEnabled(True)
        self.status.set("Could not complete disconnect")
        self.log(f"Disconnect error: {message}")
        self.show_error("Disconnect failed", message)

    def _clear_connection(self):
        old = self.connected_serial
        self._stop_screen_mirror()
        keep_active = old in self.pending_display_settings
        self.connected_serial = None
        self.active_label.setText("No device connected")
        if keep_active:
            self.keep_awake.set(True)
            self.status.set(f"Disconnected {old} · keep-awake and brightness remain active; reconnect to restore")
        else:
            self.keep_awake.set(False)
            self.keep_awake_original = None
            self.status.set(f"Disconnected {old}")
        self._update_ip_mode()
        self._update_header_pills()

    def toggle_keep_awake(self):
        serial = self.connected_serial
        if not serial:
            self.keep_awake.set(False)
            return
        enable = self.keep_awake.get()
        brightness = self.brightness_level.get()
        self.keep_awake_button.setEnabled(False)
        self.brightness_scale.setEnabled(False)
        self.status.set("Enabling stay-awake and brightness…" if enable else "Restoring previous display settings…")
        self.log(("Applying" if enable else "Restoring") + f" Android display settings on {self.connected_model}…")

        def worker():
            try:
                if enable:
                    originals = {}
                    setting_keys = (
                        ("global", "stay_on_while_plugged_in"),
                        ("global", "low_power"),
                        ("system", "screen_brightness_mode"),
                        ("system", "screen_brightness"),
                        ("system", "screen_off_timeout"),
                    )
                    for namespace, key in setting_keys:
                        read = self.run_adb("-s", serial, "shell", "settings", "get", namespace, key)
                        if read.returncode:
                            raise RuntimeError((read.stderr or read.stdout).strip() or f"Could not read Android setting {key}")
                        originals[(namespace, key)] = read.stdout.strip()
                    current = 0 if originals[("global", "stay_on_while_plugged_in")] in ("", "null") else int(originals[("global", "stay_on_while_plugged_in")])
                    desired = current | 7  # AC, USB, and wireless charging.
                    self.keep_awake_original = originals
                    self.pending_display_settings[serial] = {f"{namespace}|{key}": value for (namespace, key), value in originals.items()}
                    low_power = originals[("global", "low_power")]
                    if low_power not in ("", "null", "0"):
                        power_mode = self.run_adb("-s", serial, "shell", "cmd", "power", "set-mode", "0")
                        if power_mode.returncode:
                            raise RuntimeError((power_mode.stderr or power_mode.stdout).strip() or "Android rejected the temporary battery-saver change")
                        power_verify = self.run_adb("-s", serial, "shell", "settings", "get", "global", "low_power")
                        if power_verify.returncode or power_verify.stdout.strip() != "0":
                            raise RuntimeError("Android did not confirm that battery saver was turned off temporarily.")
                    android_brightness = round(brightness * 255 / 100)
                    changes = (
                        ("global", "stay_on_while_plugged_in", str(desired)),
                        ("system", "screen_brightness_mode", "0"),
                        ("system", "screen_brightness", str(android_brightness)),
                        ("system", "screen_off_timeout", "2147483647"),
                    )
                    for namespace, key, value in changes:
                        write = self.run_adb("-s", serial, "shell", "settings", "put", namespace, key, value)
                        if write.returncode:
                            raise RuntimeError((write.stderr or write.stdout).strip() or f"Android rejected setting {key}")
                        verify = self.run_adb("-s", serial, "shell", "settings", "get", namespace, key)
                        if verify.returncode or verify.stdout.strip() != value:
                            raise RuntimeError(f"Android did not confirm setting {key}={value}.")
                    self.after(0, self._save_config)
                    self.after(0, lambda: self._keep_awake_finished(True, f"Screen stays awake without auto-dim at {self.brightness_level.get()}% brightness."))
                else:
                    self._restore_keep_awake(serial)
                    self.after(0, lambda: self._keep_awake_finished(False, "Previous Android stay-awake and brightness settings restored."))
            except Exception as e:
                message = str(e)
                if enable and self.keep_awake_original is not None:
                    try:
                        self._restore_keep_awake(serial)
                    except Exception as restore_error:
                        message += f"\n\nCould not restore all original display settings: {restore_error}"
                self.after(0, lambda: self.keep_awake.set(self.keep_awake_original is not None))
                self.after(0, lambda: self.keep_awake_button.setEnabled(True))
                self.after(0, lambda: self.brightness_scale.setEnabled(bool(self.connected_serial)))
                self.after(0, lambda: self.status.set("Could not change stay-awake setting"))
                self.after(0, lambda: self.log(f"Stay-awake error: {message}"))
                self.after(0, self._save_config)
                self.after(0, lambda: self.show_error("Keep screen awake", message))

        threading.Thread(target=worker, daemon=True).start()

    def _restore_keep_awake(self, serial):
        original = self.keep_awake_original
        if original is None:
            saved = self.pending_display_settings.get(serial)
            if isinstance(saved, dict):
                original = {tuple(key.split("|", 1)): value for key, value in saved.items() if "|" in key}
        if not original:
            return
        restore_order = (
            ("system", "screen_brightness"),
            ("system", "screen_brightness_mode"),
            ("system", "screen_off_timeout"),
            ("global", "stay_on_while_plugged_in"),
            ("global", "low_power"),
        )
        for namespace, key in restore_order:
            if (namespace, key) not in original:
                continue
            value = original[(namespace, key)]
            if namespace == "global" and key == "low_power" and value not in ("", "null"):
                result = self.run_adb("-s", serial, "shell", "cmd", "power", "set-mode", "1" if value not in ("0",) else "0")
            elif value in ("", "null"):
                result = self.run_adb("-s", serial, "shell", "settings", "delete", namespace, key)
            else:
                result = self.run_adb("-s", serial, "shell", "settings", "put", namespace, key, value)
            if result.returncode:
                raise RuntimeError((result.stderr or result.stdout).strip() or f"Could not restore the previous {key} setting")
        self.pending_display_settings.pop(serial, None)
        if serial == self.connected_serial:
            self.keep_awake_original = None

    def _brightness_changed(self, value):
        level = max(0, min(100, round(float(value))))
        self.brightness_level.set(level)
        self.brightness_text.set(f"Brightness while awake: {level}%")
        self._update_brightness_visuals(level)
        if self.brightness_timer is not None:
            self.brightness_timer.stop()
            self.brightness_timer.deleteLater()
        self.brightness_timer = QTimer(self)
        self.brightness_timer.setSingleShot(True)
        self.brightness_timer.timeout.connect(self._commit_brightness_change)
        self.brightness_timer.start(400)

    def _update_brightness_visuals(self, level):
        high = level > 75
        color = self.current_theme["high_fg"] if high else self.current_theme["text_primary"]
        self.brightness_value_label.setStyleSheet(f"color: {color};")

    def set_brightness_preset(self, level):
        self.brightness_level.set(level)
        self._brightness_changed(level)

    def _commit_brightness_change(self):
        self.brightness_after_id = None
        self._save_config()
        if self.keep_awake_original is None or not self.connected_serial:
            return
        serial = self.connected_serial
        level = self.brightness_level.get()
        android_level = round(level * 255 / 100)
        self.status.set(f"Setting screen brightness to {level}%…")

        def worker():
            try:
                result = self.run_adb("-s", serial, "shell", "settings", "put", "system", "screen_brightness", str(android_level))
                verify = self.run_adb("-s", serial, "shell", "settings", "get", "system", "screen_brightness")
                if result.returncode or verify.returncode or verify.stdout.strip() != str(android_level):
                    raise RuntimeError((result.stderr or verify.stderr or "Android did not confirm the brightness level.").strip())
                self.after(0, lambda: self.status.set(f"Screen brightness set to {level}%"))
                self.after(0, lambda: self.log(f"Updated active screen brightness to {level}% ({android_level}/255 on Android)."))
            except Exception as e:
                message = str(e)
                self.after(0, lambda: self.status.set("Could not set screen brightness"))
                self.after(0, lambda: self.log(f"Brightness error: {message}"))

        threading.Thread(target=worker, daemon=True).start()

    def _keep_awake_finished(self, enabled, message):
        self.keep_awake.set(enabled)
        self.keep_awake_button.setEnabled(bool(self.connected_serial))
        self.brightness_scale.setEnabled(bool(self.connected_serial))
        self.status.set(message)
        self.log(message)
        self._save_config()

    def close_app(self):
        if self.update_running and not self.update_install_started:
            self.update_download_cancel.set()
        self._stop_screen_mirror()
        if self.keep_awake_original is not None and self.connected_serial:
            try:
                self._restore_keep_awake(self.connected_serial)
                self.log("Restored the device stay-awake setting before exit.")
                self._save_config()
            except Exception as e:
                if not messagebox.askyesno("Could not restore setting", f"The previous stay-awake setting could not be restored:\n\n{e}\n\nClose anyway?"):
                    self.debug_reset_config_on_close = False
                    return
        self._save_config()
        self.closing = True
        if threading.excepthook == self._report_thread_exception:
            threading.excepthook = self.previous_threading_excepthook
        with self.build_process_lock:
            build_process = self.build_process
        if build_process and build_process.poll() is None:
            self._stop_process_tree(build_process)
        with self.emulator_process_lock:
            starting_emulator_process = self.emulator_start_process
            starting_emulator_serial = self.emulator_start_serial
            emulator_download_process = self.emulator_download_process
            debug_sdk_process = self.debug_sdk_process
        if starting_emulator_serial and self.adb:
            try:
                self.run_adb("-s", starting_emulator_serial, "emu", "kill", timeout=5)
            except (OSError, subprocess.TimeoutExpired):
                pass
        if starting_emulator_process and starting_emulator_process.poll() is None:
            self._stop_process_tree(starting_emulator_process)
        if emulator_download_process and emulator_download_process.poll() is None:
            self._stop_process_tree(emulator_download_process)
        if debug_sdk_process and debug_sdk_process.poll() is None:
            self._stop_process_tree(debug_sdk_process)
        if self.debug_reset_config_on_close:
            try:
                CONFIG.unlink(missing_ok=True)
            except OSError as error:
                self.show_error(
                    "Could not reset settings",
                    f"Could not remove the saved settings file:\n\n{CONFIG}\n\n{error}",
                    parent=self,
                )
        self.close()

    @staticmethod
    def _stop_process_tree(process):
        """Stop a process tree launched in its own group by this toolkit."""
        if os.name == "nt":
            if process.poll() is None:
                try:
                    subprocess.run(
                        ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                        capture_output=True,
                        text=True,
                        timeout=8,
                        **_windows_console_options(),
                    )
                except (OSError, subprocess.TimeoutExpired):
                    process.kill()
        else:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            if process.poll() is None:
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    pass
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        if process.poll() is None:
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

    def connect_wifi(self):
        address = (self.fixed_wifi.get() if self.use_fixed_wifi.get() else self.wifi.get()).strip()
        try:
            host, port_text = address.rsplit(":", 1)
            ipaddress.ip_address(host.strip("[]"))
            port = int(port_text)
            if not 1 <= port <= 65535:
                raise ValueError
        except (ValueError, AttributeError):
            messagebox.showinfo("Wi-Fi ADB", "Enter the device IP and port, for example 192.168.1.42:5555. Android 11+ may require Wireless debugging → Pair device first.")
            return
        if self.use_fixed_wifi.get():
            self.wifi.set(address)
        else:
            self.fixed_wifi.set(address)
        self._save_config()
        self.status.set(f"Connecting to {address} over Wi-Fi…")
        self.log(f"Connecting to {address} over Wi-Fi…")

        def worker():
            try:
                current = self.run_adb("devices")
                states = {
                    parts[0]: parts[1]
                    for line in current.stdout.splitlines()[1:]
                    if len(parts := line.split()) >= 2
                }
                if states.get(address) == "device":
                    self.after(0, lambda: self._activate_device(address))
                    return
                if states.get(address) == "unauthorized":
                    raise RuntimeError("The phone has not authorized this computer. Accept the USB debugging prompt on the phone, then try again.")

                # Remove an offline transport first; ADB can otherwise keep retrying
                # an old Wi-Fi route after the phone or network has changed.
                if address in states:
                    stale = self.run_adb("disconnect", address)
                    stale_text = (stale.stdout + stale.stderr).strip()
                    if stale_text:
                        self.after(0, lambda message=stale_text: self.log(message))

                result = self.run_adb("connect", address)
                output = (result.stdout + result.stderr).strip()
                lowered = output.lower()
                if result.returncode or "failed to connect" in lowered or "cannot connect" in lowered:
                    raise RuntimeError(output or f"ADB could not connect to {address}.")

                check = self.run_adb("devices")
                connected_state = next(
                    (parts[1] for line in check.stdout.splitlines()[1:] if len(parts := line.split()) >= 2 and parts[0] == address),
                    None,
                )
                if connected_state != "device":
                    if connected_state == "unauthorized":
                        raise RuntimeError(f"ADB reached {address}, but the phone has not authorized this computer. Accept the USB debugging prompt and try again.")
                    if connected_state == "offline":
                        raise RuntimeError(f"ADB reached {address}, but the device is offline. Unlock the phone, confirm Wireless debugging is enabled, then retry.")
                    raise RuntimeError(output or f"ADB did not list {address} as an authorized device.")

                self.after(0, lambda message=output: self.log(message or f"Connected to {address}."))
                self.after(0, lambda: self._activate_device(address))
            except Exception as error:
                message = str(error)
                if "no route to host" in message.lower() or "network is unreachable" in message.lower():
                    message += "\n\nThe selected address is not reachable from this computer. Confirm the phone is on the same Wi-Fi network, Wireless debugging is on, and the IP/port still match the phone. If its address or port changed, scan again or enter the current Wireless debugging address."
                self.after(0, lambda: self.status.set("Wi-Fi ADB connection failed"))
                self.after(0, lambda text=message: self.log(f"Wi-Fi connection failed: {text}"))
                self.after(0, lambda text=message: self.show_error("Wi-Fi connection failed", text))

        threading.Thread(target=worker, daemon=True).start()

    def open_scan_tab(self):
        self.tabs.select(3)

    def scan_subnet(self):
        try:
            network = ipaddress.ip_network(self.subnet.get().strip(), strict=False)
            port = int(self.scan_port.get().strip())
            if not 1 <= port <= 65535:
                raise ValueError("Port must be between 1 and 65535.")
            if network.num_addresses > 512:
                raise ValueError("Subnet is too large. Enter a subnet with at most 512 addresses (for example, 192.168.1.0/24).")
        except ValueError as e:
            self.show_error("Invalid scan range", str(e))
            return
        self.status.set(f"Scanning {network} on port {port}…")
        self.log(f"Scanning {network} on TCP port {port}…")

        def probe(ip):
            try:
                with socket.create_connection((str(ip), port), timeout=0.45):
                    return str(ip)
            except OSError:
                return None

        def worker():
            found = []
            try:
                with ThreadPoolExecutor(max_workers=80) as pool:
                    futures = [pool.submit(probe, ip) for ip in network.hosts()]
                    for future in as_completed(futures):
                        result = future.result()
                        if result:
                            found.append(f"{result}:{port}")
                found.sort(key=lambda value: ipaddress.ip_address(value.rsplit(":", 1)[0]))
                self.after(0, lambda: self._scan_finished(found))
            except Exception as e:
                self.after(0, lambda: self.status.set(f"Scan failed: {e}"))
        threading.Thread(target=worker, daemon=True).start()

    def _scan_finished(self, found):
        if found:
            self.log("TCP port responded at: " + ", ".join(found) + " (connect will verify ADB)")
            self.manual_entry.blockSignals(True)
            self.manual_entry.clear()
            self.manual_entry.addItems(found)
            self.manual_entry.blockSignals(False)
            self.wifi.set(found[0])
            self.use_fixed_wifi.set(False)
            self.connection_method.set("Wi-Fi")
            self._update_ip_mode()
            self.tabs.select(0)
            self.status.set(f"Found {len(found)} host(s). Selected {found[0]} — click Connect Wi-Fi.")
        else:
            self.status.set("No open ports found. Check Wireless debugging port or scan the correct subnet.")
            self.log("No hosts responded. Android 11+ usually needs its current Wireless debugging port, not 5555.")

    def pair_wifi(self):
        address = simpledialog.askstring("Pair Android device", "Pairing IP and port shown under Wireless debugging → Pair device with pairing code:", parent=self)
        if not address:
            return
        code = simpledialog.askstring("Pairing code", "Six-digit pairing code shown on the phone:", parent=self, show="•")
        if not code:
            return
        self._async_action("Pairing device…", lambda: self.run_adb("pair", address.strip(), code.strip()))

    def choose_apk(self):
        value = filedialog.askopenfilename(title="Choose APK", filetypes=[("Android APK", "*.apk"), ("All files", "*")])
        if value:
            self.apk.set(value)
            self._save_config()

    def _save_profile_values(self, name=None):
        name = name or self.active_project_name
        self.project_profiles[name] = {
            "name": name,
            "project_dir": str(Path(self.project_dir.get()).expanduser().resolve()),
            "module": self.module.get().strip() or "app",
            "apk": str(Path(self.apk.get()).expanduser().resolve()),
            "package": self.package.get().strip(),
        }

    def _project_profile_selected(self, _event=None):
        selected = self.project_name.get()
        if not selected or selected == self.active_project_name:
            return
        self._save_profile_values(self.active_project_name)
        profile = self.project_profiles.get(selected)
        if not profile:
            return
        self.active_project_name = selected
        self.project_dir.set(str(profile.get("project_dir", "")))
        self.module.set(str(profile.get("module", "app")))
        self.apk.set(str(profile.get("apk", "")))
        self.package.set(str(profile.get("package", "")))
        self.adb = self._find_adb(self.project_dir.get())
        self.status.set("ADB found" if self.adb else "ADB not found — install Android SDK Platform-Tools")
        self._save_config()

    def save_project_profile(self):
        if not self.active_project_name.strip():
            self.show_error("Project name required", "Add a project and give it a name before saving it.", parent=self)
            return
        self._save_profile_values()
        self._save_config()
        self.adb = self._find_adb(self.project_dir.get())
        self.status.set(f"Saved project profile: {self.active_project_name}")

    @staticmethod
    def _gradle_wrapper_name():
        return "gradlew.bat" if os.name == "nt" else "gradlew"

    @staticmethod
    def _is_expo_project(folder):
        folder = Path(folder).expanduser()
        manifest = folder / "package.json"
        if not manifest.is_file():
            return False
        try:
            package = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False
        dependencies = {}
        for section in ("dependencies", "devDependencies"):
            values = package.get(section, {})
            if isinstance(values, dict):
                dependencies.update(values)
        return "expo" in dependencies or isinstance(package.get("expo"), dict)

    def _project_folder_problem(self, folder):
        folder = Path(folder).expanduser()
        try:
            if not folder.exists():
                return "The selected folder does not exist or is not currently accessible."
            if not folder.is_dir():
                return "The selected item is a file. Choose the Android project's folder instead."
            if self._is_expo_project(folder):
                return ""
            wrapper = folder / self._gradle_wrapper_name()
            gradle_markers = (
                "settings.gradle",
                "settings.gradle.kts",
                "build.gradle",
                "build.gradle.kts",
            )
            has_gradle_files = any((folder / name).is_file() for name in gradle_markers)
            if not wrapper.is_file():
                if has_gradle_files:
                    return (
                        f"Gradle build files were found, but the required {self._gradle_wrapper_name()} is missing. "
                        "Choose a project copy that includes its Gradle wrapper, or restore the wrapper files."
                    )
                return (
                    f"This folder does not look like a Gradle project: it has no {self._gradle_wrapper_name()} "
                    "and no root settings.gradle(.kts) or build.gradle(.kts). Choose the Android project's "
                    "Gradle root folder, not the Android SDK, an APK, or a parent folder."
                )
            if not has_gradle_files:
                return (
                    "The Gradle wrapper is present, but no root settings.gradle(.kts) or build.gradle(.kts) "
                    "was found. Choose the folder containing the project's Gradle build files."
                )
        except OSError as error:
            return f"The selected folder could not be inspected: {error}"
        return ""

    def add_project(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Android project")
        self._fit_dialog(dialog, preferred=(720, 380), minimum=(520, 300))

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(10)

        title = QLabel("Add Android project")
        title.setObjectName("PageTitle")
        layout.addWidget(title)
        sub = QLabel("Choose a Gradle Android project root or an Expo project root, then give it a name so you can find it in the project list.")
        sub.setObjectName("PageSubtitle")
        sub.setWordWrap(True)
        layout.addWidget(sub)

        suggested_name = [""]
        layout.addWidget(QLabel("Project name (required)"))
        name_entry = QLineEdit()
        layout.addWidget(name_entry)

        layout.addWidget(QLabel("Project folder (Gradle or Expo, required)"))
        folder_row = QHBoxLayout()
        folder_row.setSpacing(8)
        folder_entry = QLineEdit()
        folder_row.addWidget(folder_entry, 1)

        def browse_folder():
            initial_dir = folder_entry.text().strip() or self.project_dir.get().strip() or str(Path.home())
            selected = filedialog.askdirectory(title="Choose Gradle or Expo project folder", initialdir=initial_dir, parent=dialog)
            if selected:
                folder_entry.setText(selected)
                current_name = name_entry.text().strip()
                if not current_name or current_name == suggested_name[0]:
                    suggested_name[0] = Path(selected).name
                    name_entry.setText(suggested_name[0])

        folder_row.addWidget(self._button(text="Browse…", command=browse_folder))
        layout.addLayout(folder_row)

        hint = QLabel(
            f"Select the Gradle root containing {self._gradle_wrapper_name()}, or the Expo root containing package.json and the expo dependency. "
            "Expo projects generate android/ during the first build."
        )
        hint.setProperty("cardSub", True)
        hint.setWordWrap(True)
        layout.addWidget(hint)
        layout.addStretch(1)

        footer = QHBoxLayout()
        footer.addStretch(1)

        def create_profile():
            name = name_entry.text().strip()
            if not name:
                self.show_error("Project name required", "Enter a name for this project.", parent=dialog)
                name_entry.setFocus()
                return
            folder_text = folder_entry.text().strip()
            if not folder_text:
                self.show_error("Project folder required", "Choose a Gradle or Expo project folder.", parent=dialog)
                return
            folder = Path(folder_text).expanduser()
            problem = self._project_folder_problem(folder)
            if problem:
                self.show_error(
                    "Not a supported Android project folder",
                    f"{problem}\n\nSelected folder:\n{folder}",
                    parent=dialog,
                )
                return
            folder = folder.resolve()
            if name in self.project_profiles and not messagebox.askyesno(
                "Replace project profile?",
                f"A project named {name} already exists. Replace its saved settings?",
                parent=dialog,
            ):
                return

            self._save_profile_values(self.active_project_name)
            self.active_project_name = name
            self.project_name.set(name)
            self.project_dir.set(str(folder))
            self.module.set("app")
            self.package.set("")
            build_root = folder / "android" if self._is_expo_project(folder) else folder
            self.apk.set(str(build_root / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"))
            self.project_profiles[name] = {
                "name": name,
                "project_dir": str(folder),
                "module": "app",
                "apk": self.apk.get(),
                "package": "",
            }
            self.adb = self._find_adb(str(folder))
            self.project_selector.blockSignals(True)
            self.project_selector.clear()
            self.project_selector.addItems(sorted(self.project_profiles))
            self.project_selector.setCurrentText(name)
            self.project_selector.blockSignals(False)
            self._save_config()
            self.status.set(f"Added project profile: {name}")
            dialog.accept()

        footer.addWidget(self._button(text="Cancel", command=dialog.reject))
        create_btn = self._button(text="Create project", style="Accent.TButton", command=create_profile)
        create_btn.setDefault(True)
        footer.addWidget(create_btn)
        layout.addLayout(footer)
        name_entry.setFocus()
        dialog.exec()

    def choose_project_dir(self):
        value = filedialog.askdirectory(title="Choose Gradle or Expo project folder", initialdir=self.project_dir.get() or str(Path.home()))
        if value:
            self.project_dir.set(value)
            self.adb = self._find_adb(value)
            self._save_config()

    def _module_parts(self):
        module = self.module.get().strip().strip(":")
        if not module:
            return []
        parts = module.split(":")
        if any(not re.fullmatch(r"[A-Za-z0-9_.-]+", part) for part in parts):
            raise ValueError("Enter a valid Gradle module path, such as app or :client:app.")
        return parts

    def _default_apk_path(self):
        try:
            parts = self._module_parts()
        except ValueError:
            parts = ["app"]
        project_root = Path(self.project_dir.get()).expanduser()
        if self._is_expo_project(project_root):
            project_root = project_root / "android"
        module_dir = project_root.joinpath(*parts)
        return module_dir / "build/outputs/apk/debug/app-debug.apk"

    def _set_build_running(self, running):
        self.build_running = running
        self._set_button_label(self.build_button, "Building…" if running else "Build APK…", style="Build.TButton")
        self.build_button.setEnabled(not running)
        for widget in self.project_edit_widgets:
            widget.setEnabled(not running)
        self.build_status_row.setVisible(bool(running))

    def _build_output_received(self, line):
        self.log(line)
        if line.startswith("> Task "):
            self.build_status.set(line[len("> Task "):].strip())
        elif line.startswith("BUILD SUCCESSFUL"):
            self.build_status.set("Gradle finished successfully; checking for APKs…")
        elif line.startswith("BUILD FAILED"):
            self.build_status.set("Gradle reported a failure…")
        else:
            self.build_status.set(line if len(line) <= 110 else line[:107] + "…")

    def _build_succeeded(self, archived, detected_package=""):
        self._set_build_running(False)
        if detected_package and not self.package.get().strip():
            self.package.set(detected_package)
            self._save_profile_values()
            self._save_config()
            self.log(f"Detected Android application ID: {detected_package}")
        self.build_status.set(f"Build complete · {len(archived)} APK(s) archived")
        self.status.set(f"Build complete for {self.active_project_name} · {len(archived)} APK(s) archived")
        self._choose_built_apk(archived)

    def _build_failed(self, error):
        self._set_build_running(False)
        if "Timeout waiting to lock Configuration Cache" in error:
            self.build_status.set("Another Gradle process holds this project's cache lock")
            error = (
                "Another Gradle process is using this project's Configuration Cache. Wait for or close that build "
                "in Android Studio or a terminal, then retry. The toolkit stops the Gradle process tree it started "
                "when you close the app or when a build times out.\n\n" + error
            )
        else:
            self.build_status.set("Build failed · review the build output")
        self.status.set("APK build failed")
        self.log("Build failed. See the error details for the complete build output.")
        self._record_diagnostic_error("APK build failed", error)
        self._show_build_error(error)

    @staticmethod
    def _android_package_id(android_project_dir):
        for filename in ("build.gradle", "build.gradle.kts"):
            app_build_file = Path(android_project_dir) / "app" / filename
            try:
                source = app_build_file.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for key in ("applicationId", "namespace"):
                match = re.search(rf"\b{key}\s*(?:=\s*)?[\"']([^\"']+)[\"']", source)
                if match:
                    return match.group(1)
        return ""

    @staticmethod
    def _find_java_home():
        """Find and validate a JDK 17+ on Windows, macOS, or PATH."""
        candidates = []
        configured_home = os.environ.get("JAVA_HOME", "").strip()
        if configured_home:
            candidates.append(Path(configured_home).expanduser())
        if sys.platform == "darwin":
            candidates.extend(Path("/Library/Java/JavaVirtualMachines").glob("*/Contents/Home"))
            for prefix in (Path("/opt/homebrew/opt"), Path("/usr/local/opt")):
                for jdk in sorted(prefix.glob("openjdk*")):
                    candidates.extend((jdk / "libexec/openjdk.jdk/Contents/Home", jdk))
            java_home_tool = Path("/usr/libexec/java_home")
            if java_home_tool.is_file():
                try:
                    result = subprocess.run(
                        [str(java_home_tool), "-v", "17+"], capture_output=True, text=True, timeout=5
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        candidates.append(Path(result.stdout.strip()))
                except (OSError, subprocess.SubprocessError):
                    pass
        elif os.name == "nt":
            for program_root in (Path(os.environ.get("ProgramFiles", r"C:\Program Files")),
                                 Path(os.environ.get("LOCALAPPDATA", Path.home()) ) / "Programs"):
                for vendor in ("Eclipse Adoptium", "Microsoft", "Java"):
                    candidates.extend(sorted((program_root / vendor).glob("jdk*")))
                candidates.extend(sorted(program_root.glob("jdk-*")))
        java_on_path = shutil.which("java")
        if java_on_path and not (sys.platform == "darwin" and java_on_path == "/usr/bin/java"):
            java_path = Path(java_on_path).resolve()
            if java_path.name.lower() in ("java", "java.exe"):
                candidates.append(java_path.parent.parent)

        seen = set()
        for home in candidates:
            try:
                home = home.resolve()
            except OSError:
                continue
            if home in seen:
                continue
            seen.add(home)
            java = home / "bin" / ("java.exe" if os.name == "nt" else "java")
            if not java.is_file():
                continue
            try:
                release = home / "release"
                if release.is_file():
                    version_line = next(line for line in release.read_text(encoding="utf-8").splitlines() if line.startswith("JAVA_VERSION="))
                    version = version_line.split("=", 1)[1].strip('"')
                    major = int(version.split(".", 1)[0])
                else:
                    result = subprocess.run([str(java), "-version"], capture_output=True, text=True, timeout=5)
                    version_match = re.search(r'version "(?:1\.)?(\d+)', result.stderr + result.stdout)
                    major = int(version_match.group(1)) if version_match else 0
            except (OSError, StopIteration, ValueError, subprocess.SubprocessError):
                continue
            if major >= 17:
                return home
        return None

    @staticmethod
    def _runtime_install_command(runtime):
        """Return the supported package-manager command for a missing build runtime."""
        if os.name == "nt":
            winget = shutil.which("winget") or str(Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/WindowsApps/winget.exe")
            if not Path(winget).is_file():
                return None
            package_id = "EclipseAdoptium.Temurin.17.JDK" if runtime == "Java 17+" else "OpenJS.NodeJS.LTS"
            return [winget, "install", "--exact", "--id", package_id, "--silent", "--accept-source-agreements", "--accept-package-agreements"]
        if sys.platform == "darwin":
            brew = shutil.which("brew")
            if not brew:
                brew = next((path for path in ("/opt/homebrew/bin/brew", "/usr/local/bin/brew") if Path(path).is_file()), None)
            if brew:
                return [brew, "install", "openjdk@17" if runtime == "Java 17+" else "node"]
        return None

    @staticmethod
    def _find_node_tools():
        node = shutil.which("node")
        npm = shutil.which("npm")
        candidates = []
        if os.name == "nt":
            for root in (Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "nodejs",
                         Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Programs/nodejs",
                         Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Microsoft/WinGet/Links"):
                candidates.extend((root / "node.exe", root / "npm.cmd"))
            packages = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Microsoft/WinGet/Packages"
            if packages.is_dir():
                for package in packages.glob("OpenJS.NodeJS.LTS_*"):
                    candidates.extend(package.rglob("node.exe"))
                    candidates.extend(package.rglob("npm.cmd"))
        else:
            candidates.extend(Path(path) / tool for path in ("/opt/homebrew/bin", "/usr/local/bin") for tool in ("node", "npm"))
        for candidate in candidates:
            if not candidate.is_file():
                continue
            if candidate.name.lower().startswith("node") and not node:
                node = str(candidate)
            elif candidate.name.lower().startswith("npm") and not npm:
                npm = str(candidate)
        return node, npm

    def build_apk(self):
        if not self.active_project_name.strip():
            self.show_error("Project name required", "Add a named project profile before building.", parent=self)
            return
        project_dir = Path(self.project_dir.get()).expanduser().resolve()
        expo_project = self._is_expo_project(project_dir)
        project_problem = self._project_folder_problem(project_dir)
        if project_problem:
            self.show_error(
                "Android project folder required",
                f"{project_problem}\n\nSelected folder:\n{project_dir}",
                parent=self,
            )
            return
        android_project_dir = project_dir / "android" if expo_project else project_dir
        gradlew = android_project_dir / self._gradle_wrapper_name()
        build_type = self.build_type.get().strip().lower()
        if build_type not in ("debug", "release"):
            self.show_error("Build type", "Choose debug or release.")
            return
        try:
            module_parts = self._module_parts()
        except ValueError as error:
            self.show_error("Android module", str(error))
            return
        node_executable, npm_executable = self._find_node_tools() if expo_project else (None, None)
        expo_cli = project_dir / "node_modules" / "expo" / "bin" / "cli"
        needs_expo_prebuild = expo_project and not gradlew.is_file()
        needs_npm_install = expo_project and not expo_cli.is_file()
        if needs_npm_install and not (project_dir / "package-lock.json").is_file():
            self.show_error(
                "Expo dependencies not installed",
                "The local Expo CLI is missing and this project has no package-lock.json for a reproducible npm ci. Run the project's package-manager install command, then build again.",
                parent=self,
            )
            return
        java_home = self._find_java_home()
        runtime_installs = []
        for runtime, missing in (("Java 17+", java_home is None),
                                 ("Node.js and npm", expo_project and (not node_executable or not npm_executable))):
            if not missing:
                continue
            command = self._runtime_install_command(runtime)
            if not command:
                self.show_error(
                    f"{runtime} is unavailable",
                    f"The toolkit could not find {runtime} or a supported package manager. Launch it with the platform setup script to install missing runtimes, then retry.",
                    parent=self,
                )
                self.log(f"Build stopped: {runtime} is missing and no supported installer was found.")
                return
            runtime_installs.append((runtime, command))
        setup_note = " Missing build runtimes will be installed automatically." if runtime_installs else ""
        build_confirmation = f"Build the {build_type} APK for {self.active_project_name}? Gradle may download dependencies the first time.{setup_note}"
        if expo_project:
            expo_steps = []
            if needs_npm_install:
                expo_steps.append("install the dependencies pinned by package-lock.json with npm ci")
            if needs_expo_prebuild:
                expo_steps.append("run Expo Prebuild to generate the android/ project (and update Expo-generated package metadata if needed)")
            expo_steps.append("build the APK with the generated Android Gradle project")
            build_confirmation = (
                f"Build the {build_type} APK for {self.active_project_name}?\n\n"
                + "This Expo build will "
                + "; then it will ".join(expo_steps)
                + ". Generated Android files are written into the selected project."
                + setup_note
            )
        if not messagebox.askyesno(
            "Build APK",
            build_confirmation,
            parent=self,
        ):
            return
        self._save_config()
        self._set_build_running(True)
        self.build_status.set(f"Starting {build_type} build for {self.active_project_name}…")
        self.status.set(f"Building {self.active_project_name} ({build_type})…")
        module_label = ":" + ":".join(module_parts) if module_parts else "root project"
        task = f"{module_label}:assemble{build_type.title()}" if module_parts else f"assemble{build_type.title()}"
        output_dir = android_project_dir.joinpath(*module_parts, "build", "outputs", "apk", build_type)
        self.log(f"Preparing {self.active_project_name} ({'Expo' if expo_project else 'Gradle'}) for {build_type} APK build…")

        def worker():
            process = None
            reader_thread = None
            output_lines = []
            try:
                build_env = os.environ.copy()
                commands = []
                for runtime, command in runtime_installs:
                    commands.append((f"Install {runtime}", command, Path.cwd(), False, 1800, runtime))
                if needs_npm_install:
                    commands.append(("Install Expo dependencies", None, project_dir, os.name == "nt", 1800, "npm-ci"))
                if needs_expo_prebuild:
                    commands.append((
                        "Generate Android project with Expo Prebuild",
                        None,
                        project_dir,
                        False,
                        900,
                        "prebuild",
                    ))
                commands.append((
                    f"Gradle {task}",
                    None,
                    gradlew.parent,
                    os.name == "nt",
                    900,
                    "gradle",
                ))

                for label, command, cwd, use_shell, timeout_seconds, command_kind in commands:
                    if len(commands) > 1:
                        self.after(0, self.build_status.set, f"{label}…")
                    if command_kind == "npm-ci":
                        node_executable, npm_executable = self._find_node_tools()
                        if not node_executable or not npm_executable:
                            raise RuntimeError("Node.js and npm are still unavailable after the runtime setup step.")
                        build_env["PATH"] = str(Path(node_executable).parent) + os.pathsep + build_env.get("PATH", "")
                        command = [npm_executable, "ci", "--no-audit", "--no-fund"]
                    elif command_kind == "prebuild":
                        node_executable, _npm = self._find_node_tools()
                        if not node_executable:
                            raise RuntimeError("Node.js is still unavailable after the runtime setup step.")
                        build_env["PATH"] = str(Path(node_executable).parent) + os.pathsep + build_env.get("PATH", "")
                        command = [node_executable, str(expo_cli), "prebuild", "--platform", "android", "--no-install", "--non-interactive"]
                    elif command_kind == "gradle":
                        java_home = self._find_java_home()
                        if java_home is None:
                            raise RuntimeError("Java 17 or newer is still unavailable after the runtime setup step.")
                        build_env["JAVA_HOME"] = str(java_home)
                        build_env["PATH"] = str(java_home / "bin") + os.pathsep + build_env.get("PATH", "")
                        command = [str(gradlew), task, "--console=plain", "--no-daemon"]
                    phase_lines = []
                    output_events = queue.Queue()
                    with self.build_process_lock:
                        if self.closing:
                            return
                        process = subprocess.Popen(
                            command,
                            cwd=str(cwd),
                            env=build_env,
                            shell=use_shell,
                            stdin=subprocess.DEVNULL,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            text=True,
                            encoding="utf-8",
                            errors="replace",
                            bufsize=1,
                            start_new_session=(os.name != "nt"),
                            **_windows_console_options(new_process_group=True),
                        )
                        self.build_process = process

                    def read_output(active_process=process, events=output_events):
                        try:
                            for output_line in active_process.stdout:
                                events.put(output_line)
                        finally:
                            events.put(None)

                    reader_thread = threading.Thread(target=read_output, daemon=True)
                    reader_thread.start()
                    output_finished = False
                    deadline = time.monotonic() + timeout_seconds
                    while process.poll() is None or not output_finished:
                        remaining = deadline - time.monotonic()
                        if remaining <= 0:
                            self._stop_process_tree(process)
                            reader_thread.join(timeout=2)
                            raise TimeoutError(f"{label} exceeded its {timeout_seconds // 60}-minute time limit.")
                        try:
                            line = output_events.get(timeout=min(0.2, remaining))
                        except queue.Empty:
                            continue
                        if line is None:
                            output_finished = True
                            continue
                        phase_lines.append(line)
                        output_lines.append(line)
                        clean_line = line.rstrip()
                        if clean_line and not self.closing:
                            self.after(0, self._build_output_received, clean_line)
                    return_code = process.wait()
                    self._stop_process_tree(process)
                    reader_thread.join(timeout=2)
                    with self.build_process_lock:
                        if self.build_process is process:
                            self.build_process = None
                    reader_thread = None
                    if return_code:
                        phase_output = "".join(phase_lines).strip()
                        raise RuntimeError(f"{label} failed with exit code {return_code}.\n\n{phase_output}".strip())
                    if command_kind == "Java 17+" and self._find_java_home() is None:
                        raise RuntimeError("The package manager completed, but no Java 17+ JDK could be detected. Restart the toolkit through its launcher and retry.")
                    if command_kind == "Node.js and npm" and not all(self._find_node_tools()):
                        raise RuntimeError("The package manager completed, but Node.js and npm could not be detected. Restart the toolkit through its launcher and retry.")

                if not gradlew.is_file():
                    raise RuntimeError(
                        f"Expo Prebuild finished, but the Android Gradle wrapper was not created:\n{gradlew}"
                    )
                apks = sorted(output_dir.rglob("*.apk")) if output_dir.is_dir() else []
                if not apks:
                    raise RuntimeError(f"Gradle finished but no APK was found under {output_dir}.")
                archived = self._archive_built_apks(apks, build_type)
                if not self.closing:
                    self.after(0, self._build_succeeded, archived, self._android_package_id(android_project_dir))
            except Exception as e:
                if process and process.poll() is None:
                    self._stop_process_tree(process)
                with self.build_process_lock:
                    if self.build_process is process:
                        self.build_process = None
                if reader_thread and reader_thread.is_alive():
                    reader_thread.join(timeout=2)
                error = str(e)
                captured_output = "".join(output_lines).strip()
                if captured_output and captured_output not in error:
                    error = f"{error}\n\n{captured_output}"
                if not self.closing:
                    self.after(0, self._build_failed, error)

        threading.Thread(target=worker, daemon=True).start()

    def _show_build_error(self, error):
        dialog = QDialog(self)
        dialog.setWindowTitle("APK build failed")
        self._fit_dialog(dialog, preferred=(1100, 850), minimum=(640, 480))

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)
        title = QLabel("APK build failed")
        title.setObjectName("PageTitle")
        layout.addWidget(title)
        sub = QLabel("Review the build output below. You can scroll through it or close this window to return to DCM Android Toolkit.")
        sub.setObjectName("PageSubtitle")
        sub.setWordWrap(True)
        layout.addWidget(sub)

        output = QPlainTextEdit()
        output.setObjectName("ActivityLog")
        output.setReadOnly(True)
        output.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        output.setPlainText(error)
        layout.addWidget(output, 1)

        footer = QHBoxLayout()
        footer.addStretch(1)

        def copy_output():
            QApplication.clipboard().setText(error)
            self.status.set("Full build output copied to clipboard")
            self.log("Copied the full Gradle failure output to the clipboard.")

        footer.addWidget(self._button(text="Copy all output", command=copy_output))
        footer.addWidget(self._button(text="Close", command=dialog.accept))
        layout.addLayout(footer)
        dialog.exec()

    def _choose_built_apk(self, apks):
        self.status.set(f"Build archived · {len(apks)} APK version(s) available")
        dialog = QDialog(self)
        dialog.setWindowTitle("Choose APK to install")
        self._fit_dialog(dialog, preferred=(900, 560), minimum=(600, 420))

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)
        lbl = QLabel("Build archived. Choose this build to push now; it will remain in Version history:")
        lbl.setWordWrap(True)
        layout.addWidget(lbl)

        listing = QListWidget()
        for entry in apks:
            listing.addItem(self._version_label(entry))
        if listing.count() > 0:
            listing.setCurrentRow(0)
        layout.addWidget(listing, 1)

        def use_and_install():
            row = listing.currentRow()
            if row < 0:
                messagebox.showinfo("Choose an APK", "Select an APK from the list.", parent=dialog)
                return
            self.apk.set(str(APP_ROOT / apks[row]["apk"]))
            self._save_config()
            dialog.accept()
            if not self.connected_serial:
                messagebox.showinfo("APK ready", "APK selected. Connect and select a device, then click Install / overwrite.")
                return
            if messagebox.askyesno("Install selected APK?", f"Install this APK on {self.connected_serial}?\n\n{self.apk.get()}"):
                self.install()

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(self._button(text="Cancel", command=dialog.reject))
        buttons.addWidget(self._button(text="Use this APK and install…", style="Accent.TButton", command=use_and_install))
        layout.addLayout(buttons)
        dialog.exec()

    @staticmethod
    def _format_local_timestamp(value):
        if not value:
            return ""
        try:
            timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            return timestamp.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
        except (TypeError, ValueError):
            return str(value)

    @staticmethod
    def _version_label(entry):
        project = entry.get("project_name") or "Legacy APK"
        version = entry.get("version_name") or "version unknown"
        code = entry.get("version_code")
        if code not in (None, ""):
            version += f" (code {code})"
        built = Deployer._format_local_timestamp(entry.get("built_at_utc", ""))
        return f"{project} · {version} · {entry.get('build_type', '?')} · {built} · {Path(entry['apk']).name}"

    @staticmethod
    def _load_apk_history():
        try:
            entries = json.loads(APK_HISTORY.read_text(encoding="utf-8"))
            if isinstance(entries, list):
                return [entry for entry in entries if isinstance(entry, dict) and (APP_ROOT / entry.get("apk", "")).is_file()]
        except (OSError, json.JSONDecodeError):
            pass
        return []

    def _archive_built_apks(self, apks, build_type):
        APK_ARCHIVE.mkdir(parents=True, exist_ok=True)
        metadata_path = apks[0].parent / "output-metadata.json"
        output_metadata = {}
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            output_metadata = {item.get("outputFile"): item for item in metadata.get("elements", [])}
        except (OSError, json.JSONDecodeError, AttributeError):
            pass

        entries = self._load_apk_history()
        archived = []
        for source in apks:
            details = output_metadata.get(source.name, {})
            version_name = str(details.get("versionName") or "unknown")
            version_code = details.get("versionCode")
            safe_version = re.sub(r"[^A-Za-z0-9._-]+", "_", version_name)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
            archive_name = f"{source.stem}-v{safe_version}-{version_code or 'x'}-{stamp}.apk"
            destination = APK_ARCHIVE / archive_name
            shutil.copy2(source, destination)
            entry = {
                "project_name": self.active_project_name,
                "version_name": version_name,
                "version_code": version_code,
                "build_type": build_type,
                "built_at_utc": datetime.now(timezone.utc).isoformat(),
                "source_name": source.name,
                "apk": str(destination.relative_to(APP_ROOT)),
            }
            entries.append(entry)
            archived.append(entry)
        APK_HISTORY.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return archived

    def open_version_history(self):
        entries = sorted(self._load_apk_history(), key=lambda item: item.get("built_at_utc", ""), reverse=True)
        dialog = QDialog(self)
        dialog.setWindowTitle("APK version history")
        self._fit_dialog(dialog, preferred=(1220, 740), minimum=(760, 480))

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        heading = QHBoxLayout()
        title_lbl = QLabel("APK version history")
        title_lbl.setObjectName("PageTitle")
        heading.addWidget(title_lbl)
        heading.addStretch(1)
        count_label = QLabel("")
        count_label.setObjectName("PageSubtitle")
        heading.addWidget(count_label)
        layout.addLayout(heading)

        table = QTableWidget(0, 7)
        table.setHorizontalHeaderLabels(["Project", "Version", "Code", "Build", "Built (local time)", "Archived APK", "Internal note"])
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setStretchLastSection(True)
        for col, col_width in ((0, 130), (1, 120), (2, 65), (3, 70), (4, 185), (5, 290)):
            table.setColumnWidth(col, col_width)
        layout.addWidget(table, 1)

        action_buttons = {}

        def archive_path(entry):
            if entry is None:
                return None
            path = (APP_ROOT / entry.get("apk", "")).resolve()
            if path.parent != APK_ARCHIVE.resolve() or path.suffix.lower() != ".apk":
                return None
            return path

        def selected_entry():
            row = table.currentRow()
            if 0 <= row < len(entries):
                return entries[row]
            return None

        def update_action_states():
            if not action_buttons:
                return
            entry = selected_entry()
            selected = entry is not None
            file_path = archive_path(entry)
            existing_file = bool(file_path and file_path.is_file())
            for name in ("remove", "note"):
                action_buttons[name].setEnabled(selected)
            for name in ("show", "copy", "install"):
                action_buttons[name].setEnabled(existing_file)

        def save_history():
            APK_HISTORY.parent.mkdir(parents=True, exist_ok=True)
            temp = APK_HISTORY.with_suffix(APK_HISTORY.suffix + ".tmp")
            temp.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            temp.replace(APK_HISTORY)

        def refresh_table(select_path=None):
            nonlocal entries
            entries = sorted(self._load_apk_history(), key=lambda item: item.get("built_at_utc", ""), reverse=True)
            table.setRowCount(0)
            target_row = 0 if entries else -1
            for row_idx, entry in enumerate(entries):
                table.insertRow(row_idx)
                values = (
                    entry.get("project_name", "Legacy APK"),
                    entry.get("version_name", "unknown"),
                    str(entry.get("version_code", "")),
                    entry.get("build_type", ""),
                    self._format_local_timestamp(entry.get("built_at_utc", "")),
                    Path(entry["apk"]).name,
                    entry.get("note", ""),
                )
                for col_idx, val in enumerate(values):
                    table.setItem(row_idx, col_idx, QTableWidgetItem(str(val)))
                if entry.get("apk") == select_path:
                    target_row = row_idx
            if target_row >= 0:
                table.selectRow(target_row)
            count_label.setText(f"Archived APK builds · {len(entries)} version(s)")
            update_action_states()

        def edit_note():
            entry = selected_entry()
            if entry is None:
                messagebox.showinfo("Select a build", "Select a build to add or edit its note.", parent=dialog)
                return
            note_dialog = QDialog(dialog)
            note_dialog.setWindowTitle("Build note")
            self._fit_dialog(note_dialog, preferred=(720, 520), minimum=(480, 360))
            n_layout = QVBoxLayout(note_dialog)
            n_layout.setContentsMargins(18, 18, 18, 18)
            n_layout.setSpacing(10)
            n_title = QLabel(f"Internal note · {entry.get('version_name', 'build')}")
            n_title.setObjectName("PageTitle")
            n_layout.addWidget(n_title)
            note = QPlainTextEdit()
            note.setProperty("monoCard", True)
            note.setPlainText(entry.get("note", ""))
            n_layout.addWidget(note, 1)
            n_actions = QHBoxLayout()
            n_actions.addStretch(1)

            def save_note():
                entry["note"] = note.toPlainText().strip()
                try:
                    save_history()
                except OSError as error:
                    self.show_error("Could not save note", str(error), parent=note_dialog)
                    return
                path = entry["apk"]
                refresh_table(path)
                note_dialog.accept()

            n_actions.addWidget(self._button(text="Cancel", command=note_dialog.reject))
            n_actions.addWidget(self._button(text="Save note", style="Accent.TButton", command=save_note))
            n_layout.addLayout(n_actions)
            note_dialog.exec()

        def remove_selected():
            nonlocal entries
            entry = selected_entry()
            if entry is None:
                messagebox.showinfo("Select a build", "Select a build to remove.", parent=dialog)
                return
            path = archive_path(entry)
            if path is None:
                self.show_error("Invalid archive entry", "This entry does not point to an APK in the local build archive.", parent=dialog)
                return
            if not messagebox.askyesno("Remove archived build?", f"Permanently delete this APK and its note?\n\n{Path(entry['apk']).name}", parent=dialog):
                return
            try:
                path.unlink(missing_ok=True)
                entries = [item for item in entries if item.get("apk") != entry.get("apk")]
                save_history()
                if Path(self.apk.get()).expanduser().resolve() == path:
                    self.apk.set(str(self._default_apk_path()))
                    self._save_config()
                refresh_table()
            except OSError as error:
                self.show_error("Could not remove build", str(error), parent=dialog)

        def remove_all():
            nonlocal entries
            archive = APK_ARCHIVE.resolve()
            try:
                builds = [path for path in archive.glob("*.apk") if path.is_file()]
            except OSError as error:
                self.show_error("Could not list builds", str(error), parent=dialog)
                return
            if not builds and not entries:
                messagebox.showinfo("No builds", "There are no archived APK builds to remove.", parent=dialog)
                return
            if not messagebox.askyesno("Remove all archived builds?", f"Permanently delete all {len(builds)} APK file(s) in the local archive and clear their notes? This cannot be undone.", parent=dialog):
                return
            try:
                for path in builds:
                    path.unlink()
                entries = []
                save_history()
                if "apk_versions" in Path(self.apk.get()).expanduser().resolve().parts:
                    self.apk.set(str(self._default_apk_path()))
                    self._save_config()
                refresh_table()
            except OSError as error:
                self.show_error("Could not remove all builds", str(error), parent=dialog)

        def use_selected():
            entry = selected_entry()
            path = archive_path(entry)
            if path is None or not path.is_file():
                messagebox.showinfo("Choose an APK", "Select an archived APK file that still exists.", parent=dialog)
                return
            self.apk.set(str(path))
            self._save_config()
            dialog.accept()
            if not self.connected_serial:
                messagebox.showinfo("APK selected", "Version selected. Connect a device, then click Install / overwrite.")
            elif messagebox.askyesno("Install selected version?", f"Install {self._version_label(entry)} on {self.connected_serial}?"):
                self.install()

        def show_selected_file():
            entry = selected_entry()
            path = archive_path(entry)
            if path is None or not path.is_file():
                update_action_states()
                return
            try:
                if sys.platform == "darwin":
                    subprocess.Popen(["open", "-R", str(path)])
                elif os.name == "nt":
                    os.startfile(path.parent)
                else:
                    subprocess.Popen(["xdg-open", str(path.parent)])
            except OSError as error:
                self.show_error("Could not open folder", str(error), parent=dialog)

        def copy_selected_file():
            entry = selected_entry()
            path = archive_path(entry)
            if path is None or not path.is_file():
                update_action_states()
                return
            destination = filedialog.asksaveasfilename(
                title="Copy APK to share",
                initialfile=path.name,
                defaultextension=".apk",
                filetypes=[("Android APK", "*.apk"), ("All files", "*.*")],
                parent=dialog,
            )
            if not destination:
                return
            try:
                shutil.copy2(path, destination)
                messagebox.showinfo("APK copied", f"Copied APK to:\n{destination}", parent=dialog)
            except OSError as error:
                self.show_error("Could not copy APK", str(error), parent=dialog)

        table.itemSelectionChanged.connect(update_action_states)

        row_actions = QHBoxLayout()
        row_actions.setSpacing(8)
        row_actions.addWidget(self._button(text="Remove all builds", style="Danger.TButton", command=remove_all))
        action_buttons["remove"] = self._button(text="Remove build", style="Danger.TButton", command=remove_selected)
        row_actions.addWidget(action_buttons["remove"])
        action_buttons["note"] = self._button(text="Add / edit note…", command=edit_note)
        row_actions.addWidget(action_buttons["note"])
        row_actions.addStretch(1)
        layout.addLayout(row_actions)

        bottom_actions = QHBoxLayout()
        bottom_actions.setSpacing(8)
        action_buttons["copy"] = self._button(text="Copy APK…", command=copy_selected_file)
        bottom_actions.addWidget(action_buttons["copy"])
        action_buttons["show"] = self._button(text="Show in folder", command=show_selected_file)
        bottom_actions.addWidget(action_buttons["show"])
        bottom_actions.addStretch(1)
        bottom_actions.addWidget(self._button(text="Close", command=dialog.accept))
        action_buttons["install"] = self._button(text="Select and install…", style="Accent.TButton", command=use_selected)
        bottom_actions.addWidget(action_buttons["install"])
        layout.addLayout(bottom_actions)

        refresh_table()
        dialog.exec()

    def choose_export_dir(self):
        value = filedialog.askdirectory(title="Choose SMS JSON output folder", initialdir=self.export_dir.get())
        if value:
            self.export_dir.set(value)

    @staticmethod
    def _parse_sms_ids(output):
        ids = [int(value) for value in re.findall(r"(?m)^Row:\s*\d+\s+_id=(\d+)", output)]
        if not ids and output.strip() and "no result found" not in output.lower():
            raise RuntimeError(f"ADB returned an unrecognized SMS query response instead of rows:\n{output[:1200]}")
        return ids

    @staticmethod
    def _parse_sms_rows(output):
        messages = []
        field_re = re.compile(r"(?:^|, )([A-Za-z_][A-Za-z0-9_]*)=")
        for line in output.splitlines():
            if not line.startswith("Row: "):
                continue
            payload = re.sub(r"^Row: \d+ ", "", line)
            matches = list(field_re.finditer(payload))
            row = {}
            for i, match in enumerate(matches):
                end = matches[i + 1].start() if i + 1 < len(matches) else len(payload)
                row[match.group(1)] = payload[match.end():end].strip()
            date_value = row.get("date", "")
            try:
                millis = int(date_value)
                iso = datetime.fromtimestamp(millis / 1000, tz=timezone.utc).isoformat()
            except (ValueError, OverflowError, OSError):
                millis, iso = None, None
            messages.append({
                "id": row.get("_id"),
                "address": row.get("address") or None,
                "date_unix_ms": millis,
                "date_utc": iso,
                "type": row.get("type"),
                "body": row.get("body", ""),
                "read": row.get("read"),
                "thread_id": row.get("thread_id"),
            })
        return messages

    def count_sms(self):
        serial = (self.connected_serial or "").strip()
        if not serial:
            messagebox.showinfo("Choose a device", "Connect an authorized device on the Connection tab first.")
            return
        self.count_button.setEnabled(False)
        self.preview_button.setEnabled(False)
        self.export_button.setEnabled(False)
        self.sms_count_text.set("Checking SMS access and counting messages…")
        self.status.set("Counting SMS records…")
        self.log(f"SMS count check started for {serial}. Watch the phone for an 'Allow USB debugging' prompt and accept it if shown.")

        def worker():
            try:
                if not self.adb:
                    raise RuntimeError("ADB was not found. Install Android SDK Platform-Tools and ensure adb is on PATH.")
                self._require_device_online(serial)
                result = subprocess.run(
                    [self.adb, "-s", serial, "shell", "content", "query", "--uri", "content://sms", "--projection", "_id"],
                    capture_output=True, text=True, timeout=60,
                    **_windows_console_options(),
                )
                output = (result.stderr + "\n" + result.stdout).strip()
                lower = output.lower()
                if result.returncode or "permission denial" in lower or "securityexception" in lower or "exception occurred" in lower or "unsupported argument" in lower or "usage:" in lower or "can't create" in lower:
                    raise RuntimeError(output or "ADB could not read the SMS message index")
                count = len(self._parse_sms_ids(result.stdout))
                self.after(0, lambda: self.sms_count_text.set(f"SMS messages readable through ADB: {count:,}"))
                self.after(0, lambda: self.status.set(f"SMS count check complete · {count:,} messages"))
                self.after(0, lambda: self.log(f"SMS count check complete: {count:,} records readable from content://sms on {serial}."))
            except subprocess.TimeoutExpired:
                message = "ADB did not respond in 60 seconds. Check that the phone is awake, connected, and authorized, then retry."
                self.after(0, lambda: self.sms_count_text.set("SMS count timed out"))
                self.after(0, lambda: self.status.set("SMS count check timed out"))
                self.after(0, lambda: self.log(message))
                self.after(0, lambda: messagebox.showwarning("SMS count timed out", message))
            except Exception as e:
                error = str(e)
                if "permission" in error.lower() or "securityexception" in error.lower():
                    error += "\n\nAccept any 'Allow USB debugging' prompt on the phone. SMS access may require the inspected app to be the default SMS app with SMS permission granted. If Android still denies the ADB shell query, that device build blocks shell access to the SMS provider."
                self.after(0, lambda: self.sms_count_text.set("Could not read SMS count — see Activity"))
                self.after(0, lambda: self.status.set("SMS count check failed"))
                self.after(0, lambda: self.log(f"SMS count check failed: {error}"))
                self.after(0, lambda: self.show_error("SMS count check failed", error))
            finally:
                self.after(0, lambda: self.count_button.setEnabled(True))
                self.after(0, lambda: self.preview_button.setEnabled(True))
                self.after(0, lambda: self.export_button.setEnabled(True))

        threading.Thread(target=worker, daemon=True).start()

    def preview_sms(self):
        serial = (self.connected_serial or "").strip()
        if not serial:
            messagebox.showinfo("Choose a device", "Connect an authorized device on the Connection tab first.")
            return
        self.count_button.setEnabled(False)
        self.preview_button.setEnabled(False)
        self.export_button.setEnabled(False)
        self.status.set("Reading a two-message SMS sample…")
        self.log(f"SMS content preview started for {serial}. Reading up to two messages; preview stays in this app and is not written to disk.")

        def worker():
            try:
                if not self.adb:
                    raise RuntimeError("ADB was not found. Install Android SDK Platform-Tools and ensure adb is on PATH.")
                self._require_device_online(serial)
                id_result = subprocess.run(
                    [self.adb, "-s", serial, "shell", "content", "query", "--uri", "content://sms", "--projection", "_id"],
                    capture_output=True, text=True, timeout=60,
                    **_windows_console_options(),
                )
                output = (id_result.stderr + "\n" + id_result.stdout).strip()
                lower = output.lower()
                if id_result.returncode or "permission denial" in lower or "securityexception" in lower or "exception occurred" in lower or "unsupported argument" in lower or "usage:" in lower or "can't create" in lower:
                    raise RuntimeError(output or "ADB could not read the SMS message index")
                ids = self._parse_sms_ids(id_result.stdout)
                if not ids:
                    self.after(0, lambda: self.status.set("No SMS records found"))
                    self.after(0, lambda: self.log("Content preview finished: the SMS provider returned no message IDs."))
                    return
                messages = []
                chosen_ids = ids[:2]
                for index, message_id in enumerate(chosen_ids, start=1):
                    self.after(0, lambda i=index, n=len(chosen_ids): self.status.set(f"Reading sample {i}/{n}…"))
                    result = subprocess.run(
                        [self.adb, "-s", serial, "shell", "content", "query", "--uri", "content://sms",
                         "--projection", "_id:address:date:type:body:read:thread_id",
                         "--where", f"'_id = {message_id}'"],
                        capture_output=True, text=True, timeout=60,
                        **_windows_console_options(),
                    )
                    output = (result.stderr + "\n" + result.stdout).strip()
                    lower = output.lower()
                    if result.returncode or "permission denial" in lower or "securityexception" in lower or "exception occurred" in lower or "unsupported argument" in lower or "usage:" in lower or "can't create" in lower:
                        raise RuntimeError(output or f"ADB could not read sample message {index}")
                    rows = self._parse_sms_rows(result.stdout)
                    if len(rows) != 1:
                        raise RuntimeError(f"Expected one SMS row for ID {message_id}, but ADB returned {len(rows)} rows. Response: {output[:1000]}")
                    messages.extend(rows)
                    self.after(0, lambda i=index, n=len(chosen_ids), mid=message_id: self.log(f"Content preview: read message {i}/{n} (ID {mid})."))
                preview_json = json.dumps({"message_count": len(messages), "messages": messages}, ensure_ascii=False, indent=2)
                self.after(0, lambda: self._show_sms_preview(preview_json, len(messages)))
                self.after(0, lambda: self.status.set(f"Read {len(messages)} sample SMS message(s)"))
                self.after(0, lambda: self.log(f"Content preview confirmed: read and parsed {len(messages)} actual SMS message(s). No file was written."))
            except subprocess.TimeoutExpired:
                message = "ADB did not respond in 60 seconds. Check that the phone is awake, connected, and authorized, then retry."
                self.after(0, lambda: self.status.set("SMS content preview timed out"))
                self.after(0, lambda: self.log(message))
                self.after(0, lambda: messagebox.showwarning("SMS preview timed out", message))
            except Exception as e:
                error = str(e)
                if "permission" in error.lower() or "securityexception" in error.lower():
                    error += "\n\nAccept any 'Allow USB debugging' prompt on the phone. If Android denies SMS provider access, check that the device is online and ADB is authorized."
                self.after(0, lambda: self.status.set("SMS content preview failed"))
                self.after(0, lambda: self.log(f"SMS content preview failed: {error}"))
                self.after(0, lambda: self.show_error("SMS content preview failed", error))
            finally:
                self.after(0, lambda: self.count_button.setEnabled(True))
                self.after(0, lambda: self.preview_button.setEnabled(True))
                self.after(0, lambda: self.export_button.setEnabled(True))

        threading.Thread(target=worker, daemon=True).start()

    def _show_sms_preview(self, preview_json, count):
        dialog = QDialog(self)
        dialog.setWindowTitle("SMS content preview")
        self._fit_dialog(dialog, preferred=(1000, 820), minimum=(600, 500))
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        title = QLabel(f"Read and parsed {count} SMS message(s)")
        title.setObjectName("PageTitle")
        layout.addWidget(title)
        sub = QLabel("This local preview is not saved. Message bodies may contain private information.")
        sub.setObjectName("PageSubtitle")
        sub.setWordWrap(True)
        layout.addWidget(sub)
        content = QPlainTextEdit()
        content.setProperty("monoCard", True)
        content.setReadOnly(True)
        content.setPlainText(preview_json)
        layout.addWidget(content, 1)
        actions = QHBoxLayout()
        actions.addStretch(1)
        actions.addWidget(self._button(text="Close", command=dialog.accept))
        layout.addLayout(actions)
        dialog.exec()

    def _require_device_online(self, serial):
        result = subprocess.run(
            [self.adb, "devices"], capture_output=True, text=True, timeout=15,
            **_windows_console_options(),
        )
        states = {}
        for line in result.stdout.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 2:
                states[parts[0]] = parts[1]
        state = states.get(serial)
        if state != "device":
            if state == "offline":
                raise RuntimeError(f"ADB reports {serial} as offline. On the phone, keep Wireless debugging enabled. Then disconnect and reconnect Wi-Fi ADB; if it remains offline, toggle Wireless debugging off and on and accept the debugging prompt again.")
            raise RuntimeError(f"ADB device {serial} is not connected (state: {state or 'not listed'}). Reconnect it on the Connection tab and authorize the phone prompt if shown.")

    def export_sms(self):
        serial = (self.connected_serial or "").strip()
        if not serial:
            messagebox.showinfo("Choose a device", "Connect an authorized device on the Connection tab first.")
            return
        out_dir = Path(self.export_dir.get()).expanduser()
        self.export_button.setEnabled(False)
        self.count_button.setEnabled(False)
        self.preview_button.setEnabled(False)
        self.status.set("Starting SMS export…")
        self.log(f"SMS export started for {serial}. Watch the phone for an 'Allow USB debugging' prompt and accept it if shown. Reading the message index…")

        def report(message, status=None):
            self.after(0, lambda: self.log(message))
            if status:
                self.after(0, lambda: self.status.set(status))

        def run_export_adb(*args):
            return subprocess.run(
                [self.adb, *args], capture_output=True, text=True, timeout=60,
                **_windows_console_options(),
            )

        def require_query_success(result, step):
            output = (result.stderr + "\n" + result.stdout).strip()
            lower = output.lower()
            if result.returncode or "permission denial" in lower or "securityexception" in lower or "exception occurred" in lower or "unsupported argument" in lower or "usage:" in lower or "can't create" in lower:
                raise RuntimeError(output or f"ADB could not read SMS data during {step}")

        def worker():
            try:
                if not self.adb:
                    raise RuntimeError("ADB was not found. Install Android SDK Platform-Tools and ensure adb is on PATH.")
                self._require_device_online(serial)
                id_result = run_export_adb("-s", serial, "shell", "content", "query", "--uri", "content://sms", "--projection", "_id")
                require_query_success(id_result, "the message index")
                ids = self._parse_sms_ids(id_result.stdout)
                self.after(0, lambda: self.sms_count_text.set(f"SMS messages readable through ADB: {len(ids):,}"))
                if not ids:
                    messages = []
                    report("No SMS records found. Writing an empty JSON export…", "Writing empty SMS export…")
                else:
                    first_id, last_id = min(ids), max(ids)
                    batch_width = 250
                    batch_count = ((last_id - first_id) // batch_width) + 1
                    report(f"Found {len(ids):,} message IDs. Exporting in {batch_count} batches of up to {batch_width:,} IDs…", f"Exporting SMS: 0/{batch_count} batches")
                    messages = []
                    for batch_index, lower in enumerate(range(first_id, last_id + 1, batch_width), start=1):
                        upper = lower + batch_width
                        result = run_export_adb(
                            "-s", serial, "shell", "content", "query", "--uri", "content://sms",
                            "--projection", "_id:address:date:type:body:read:thread_id",
                            "--where", f"'_id >= {lower} AND _id < {upper}'",
                        )
                        require_query_success(result, f"batch {batch_index}/{batch_count}")
                        batch_messages = self._parse_sms_rows(result.stdout)
                        messages.extend(batch_messages)
                        report(f"Batch {batch_index}/{batch_count}: exported {len(batch_messages):,} messages ({len(messages):,}/{len(ids):,} total).", f"Exporting SMS: {batch_index}/{batch_count} batches · {len(messages):,}/{len(ids):,} messages")
                out_dir.mkdir(parents=True, exist_ok=True)
                filename = out_dir / "sms_export.json"
                document = {
                    "exported_at_utc": datetime.now(timezone.utc).isoformat(),
                    "device_serial": serial,
                    "source": "content://sms",
                    "message_count": len(messages),
                    "messages": messages,
                }
                temporary_file = filename.with_suffix(filename.suffix + ".tmp")
                temporary_file.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                temporary_file.replace(filename)
                self.after(0, lambda: self.status.set(f"Exported {len(messages)} SMS messages"))
                self.after(0, lambda: self.log(f"Saved {len(messages)} messages to {filename}"))
            except subprocess.TimeoutExpired:
                report("ADB timed out during SMS export. Check that the phone is awake, connected, and authorized, then retry.", "SMS export timed out")
                self.after(0, lambda: messagebox.showwarning("SMS export timed out", "ADB did not respond in 60 seconds. Check the phone connection and USB debugging authorization, then try again."))
            except Exception as e:
                error = str(e)
                if "Permission Denial" in error or "permission" in error.lower():
                    error += "\n\nCheck the phone for an 'Allow USB debugging' prompt and accept it. SMS access may also require the inspected app to be the default SMS app with SMS permission granted. If Android still denies the ADB shell query, that device build does not allow shell access to the SMS provider."
                report(f"SMS export failed: {error}", "SMS export failed — see Activity for next steps")
                self.after(0, lambda: self.show_error("SMS export needs attention", error))
            finally:
                self.after(0, lambda: self.export_button.setEnabled(True))
                self.after(0, lambda: self.count_button.setEnabled(True))
                self.after(0, lambda: self.preview_button.setEnabled(True))

        threading.Thread(target=worker, daemon=True).start()

    def _async_action(self, label, action, on_success=None):
        self.status.set(label)
        def worker():
            try:
                result = action()
                output = result.stdout + result.stderr
                self.after(0, lambda: self.log(output or "Done."))
                if result.returncode:
                    raise RuntimeError(output.strip() or f"ADB exited with {result.returncode}")
                self.after(0, lambda: self.status.set("Completed"))
                if on_success:
                    self.after(0, on_success)
            except Exception as e:
                self.after(0, lambda: self.status.set("Action failed"))
                self.after(0, lambda: self.log(f"Error: {e}"))
        threading.Thread(target=worker, daemon=True).start()

    def install(self):
        apk = Path(self.apk.get()).expanduser()
        if not apk.is_file():
            self.show_error("APK missing", f"Could not find APK:\n{apk}")
            return
        package = self.package.get().strip()
        if not package or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+", package):
            self.show_error("Invalid package name", "Enter the installed app's package name (for example, com.example.app) so DCM Android Toolkit can open it after installation.")
            return
        serial = self.install_target_serials.get(self.install_target.get())
        if not serial:
            messagebox.showinfo("Choose an install target", "Refresh devices and select an authorized Android device or emulator first.")
            return
        self._save_config()
        self._async_action(
            f"Installing APK on {self.install_target.get()}…",
            lambda: self._install_and_launch(serial, apk, package),
        )

    def _install_and_launch(self, serial, apk, package):
        install = self.run_adb("-s", serial, "install", "-r", str(apk))
        install_output = (install.stdout + install.stderr).strip()
        if install.returncode or "failure" in install_output.lower():
            raise RuntimeError(install_output or f"ADB could not install {apk.name}.")

        launch = self.run_adb(
            "-s", serial, "shell", "monkey", "-p", package,
            "-c", "android.intent.category.LAUNCHER", "1",
        )
        launch_output = (launch.stdout + launch.stderr).strip()
        if launch.returncode or "no activities found" in launch_output.lower() or "monkey aborted" in launch_output.lower():
            raise RuntimeError(
                f"APK installed successfully, but Android could not open {package}.\n\n"
                f"{launch_output or 'No launchable activity was found.'}\n\n"
                "Check that the package name above matches the installed APK and that the app has a launcher screen."
            )
        return subprocess.CompletedProcess(
            args=launch.args,
            returncode=0,
            stdout=f"{install_output or 'APK installed successfully.'}\nOpened {package}.\n{launch_output}".strip(),
            stderr="",
        )

    def uninstall(self):
        package = self.package.get().strip()
        if not package or any(ch.isspace() for ch in package):
            self.show_error("Package name required", "Enter the Android package name to remove.")
            return
        if not self.connected_serial:
            messagebox.showinfo("Choose a device", "Connect an authorized device on the Connection tab first.")
            return
        serial = self.connected_serial
        if not messagebox.askyesno("Remove app?", f"Uninstall {package} from {serial}? This removes its app data too."):
            return
        self._save_config()
        self._async_action("Removing app…", lambda: self.run_adb("-s", serial, "uninstall", package))

    def _save_config(self):
        if self.debug_reset_config_on_close:
            return
        self._save_profile_values()
        CONFIG.write_text(json.dumps({
            "selected_project": self.active_project_name,
            "projects": list(self.project_profiles.values()),
            "fixed_wifi": self.fixed_wifi.get().strip(),
            "use_fixed_wifi": self.use_fixed_wifi.get(),
            "connection_method": self.connection_method.get(),
            "install_target": self.install_target.get(),
            "last_device": self.connected_serial or self.last_device,
            "last_device_method": self.last_device_method,
            "managed_emulators": [
                {"avd": avd, "serial": serial}
                for avd, serial in sorted(self.managed_emulators)
            ],
            "brightness_level": self.brightness_level.get(),
            "brightness_level_unit": "percent",
            "pending_display_settings": self.pending_display_settings,
            "theme_mode": self.theme_mode,
        }, indent=2) + "\n")
def _validated_update_entries(archive, expected_version):
    with zipfile.ZipFile(archive) as package:
        infos = package.infolist()
        if not infos or len(infos) > 5000:
            raise ValueError("The update archive is empty or contains too many files.")
        script_info = None
        prefix = f"dcm-android-toolkit-{expected_version}"
        for info in infos:
            name = info.filename
            if "\\" in name:
                raise ValueError("The update archive contains an unsafe file path.")
            member = PurePosixPath(name)
            if member.is_absolute() or ".." in member.parts or not member.parts:
                raise ValueError("The update archive contains an unsafe file path.")
            if member.parts[0] != prefix:
                raise ValueError("The update archive does not match the expected release folder.")
            relative_parts = member.parts[1:]
            if relative_parts == ("dcm_android_toolkit.py",):
                script_info = info
        if script_info is None:
            raise ValueError("The update archive is missing the toolkit application source.")
        script = package.read(script_info).decode("utf-8")
        version_match = re.search(r'^APP_VERSION\s*=\s*["\']([^"\']+)["\']', script, re.MULTILINE)
        if not version_match or version_match.group(1) != expected_version:
            raise ValueError("The update source version does not match the GitHub release tag.")

        entries = []
        unpacked_size = 0
        for info in infos:
            member = PurePosixPath(info.filename)
            relative_parts = member.parts[1:]
            if not relative_parts or info.is_dir():
                continue
            mode = info.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise ValueError("The update archive contains a symbolic link and cannot be installed safely.")
            if ":" in relative_parts[0]:
                raise ValueError("The update archive contains an unsafe file path.")
            if any(part in (".git", "data", "__pycache__") for part in relative_parts):
                continue
            relative = PurePosixPath(*relative_parts)
            if relative.as_posix() == "dcm-android-toolkit.json" or relative.suffix in (".pyc", ".pyo"):
                continue
            unpacked_size += info.file_size
            if unpacked_size > MAX_UPDATE_ARCHIVE_BYTES:
                raise ValueError("The expanded update archive exceeds the 100 MB safety limit.")
            entries.append((info, relative, mode))
        if not any(relative.as_posix() == "dcm_android_toolkit.py" for _info, relative, _mode in entries):
            raise ValueError("The update archive does not contain an installable toolkit source file.")
        return entries


def _validate_update_archive(archive, expected_version):
    _validated_update_entries(archive, expected_version)


def _apply_update_archive(archive, target, expected_version):
    archive = Path(archive)
    target = Path(target).resolve()
    if not target.is_dir():
        raise FileNotFoundError(f"Application folder was not found: {target}")
    update_root = Path(tempfile.mkdtemp(prefix=".dcm-update-", dir=target.parent))
    payload_root = update_root / "payload"
    backup_root = update_root / "backup"
    applied = []
    try:
        payload_root.mkdir()
        entries = _validated_update_entries(archive, expected_version)
        with zipfile.ZipFile(archive) as package:
            for info, relative, mode in entries:
                staged = payload_root.joinpath(*relative.parts)
                staged.parent.mkdir(parents=True, exist_ok=True)
                with package.open(info) as source, staged.open("xb") as destination:
                    shutil.copyfileobj(source, destination, length=1024 * 1024)
                permissions = mode & 0o777
                if permissions and os.name != "nt":
                    staged.chmod(permissions)

        root_resolved = target.resolve()
        for _info, relative, _mode in sorted(entries, key=lambda row: row[1].as_posix()):
            destination = target.joinpath(*relative.parts)
            parent = target
            for part in relative.parts[:-1]:
                parent = parent / part
                if parent.is_symlink():
                    raise ValueError(f"Refusing to update through a symbolic link: {parent}")
            if destination.is_symlink():
                raise ValueError(f"Refusing to replace a symbolic link: {destination}")
            if not destination.parent.resolve().is_relative_to(root_resolved):
                raise ValueError(f"Update path escapes the application folder: {destination}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            existed = destination.exists()
            if existed and not destination.is_file():
                raise ValueError(f"Cannot replace a non-file application path: {destination}")
            backup = backup_root.joinpath(*relative.parts)
            if existed:
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(destination, backup)
            staged = payload_root.joinpath(*relative.parts)
            os.replace(staged, destination)
            applied.append((destination, backup, existed))
    except Exception as error:
        rollback_errors = []
        for destination, backup, existed in reversed(applied):
            try:
                if existed and backup.exists():
                    os.replace(backup, destination)
                elif destination.exists():
                    destination.unlink()
            except OSError as rollback_error:
                rollback_errors.append(str(rollback_error))
        if rollback_errors:
            raise RuntimeError(f"{error}\nRollback also failed: {'; '.join(rollback_errors)}") from error
        raise
    finally:
        shutil.rmtree(update_root, ignore_errors=True)


def _wait_for_process_exit(pid, timeout=45):
    if os.name == "nt":
        import ctypes

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = (ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32)
        kernel.OpenProcess.restype = ctypes.c_void_p
        kernel.WaitForSingleObject.argtypes = (ctypes.c_void_p, ctypes.c_uint32)
        kernel.WaitForSingleObject.restype = ctypes.c_uint32
        kernel.CloseHandle.argtypes = (ctypes.c_void_p,)
        kernel.CloseHandle.restype = ctypes.c_int
        process = kernel.OpenProcess(0x00100000, False, int(pid))
        if not process:
            return
        try:
            wait_result = kernel.WaitForSingleObject(process, int(timeout * 1000))
            if wait_result == 0x00000102:
                raise TimeoutError("The toolkit did not close in time for the update.")
            if wait_result != 0:
                raise OSError("Could not wait for the toolkit process to close before updating.")
        finally:
            kernel.CloseHandle(process)
        return

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            os.kill(int(pid), 0)
        except ProcessLookupError:
            return
        except PermissionError:
            raise OSError("Could not verify that the toolkit process closed before updating.")
        time.sleep(0.2)
    raise TimeoutError("The toolkit did not close in time for the update.")


def _run_update_helper(archive, target, parent_pid, expected_version):
    script_path = Path(__file__).resolve()
    restart_args = [sys.executable, str(script_path)]
    try:
        _wait_for_process_exit(parent_pid)
        _apply_update_archive(archive, target, expected_version)
        try:
            Path(archive).unlink()
        except OSError:
            pass
        if os.name == "nt":
            restart_command = [
                "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                str(Path(target) / "setup_windows.ps1"), "-UpdateCompleteVersion", expected_version,
            ]
        elif sys.platform == "darwin":
            restart_command = [
                "/bin/bash", str(Path(target) / "Launch DCM Android Toolkit.command"),
                "--update-complete", expected_version,
            ]
        else:
            restart_command = [
                sys.executable,
                str(Path(target) / "dcm_android_toolkit.py"),
                "--update-complete",
                expected_version,
            ]
    except Exception as error:
        try:
            Path(archive).unlink()
        except OSError:
            pass
        restart_command = [*restart_args, "--update-error", str(error)]

    try:
        flags = getattr(subprocess, "DETACHED_PROCESS", 0) if os.name == "nt" else 0
        subprocess.Popen(
            restart_command,
            cwd=target,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=(os.name != "nt"),
            creationflags=flags,
        )
    except OSError:
        return 1
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--apply-update":
        if len(sys.argv) != 6:
            raise SystemExit("Invalid updater arguments.")
        raise SystemExit(_run_update_helper(*sys.argv[2:]))

    qt_app = QApplication(sys.argv)
    qt_app.setApplicationName("DCM Android Toolkit")
    qt_app.setStyle("Fusion")
    app = Deployer()
    app.show()
    if len(sys.argv) > 1 and sys.argv[1] == "--update-complete":
        updated_version = sys.argv[2] if len(sys.argv) > 2 else APP_VERSION
        app.after(500, lambda: messagebox.showinfo("Update complete", f"DCM Android Toolkit was updated to {updated_version}.", parent=app))
    elif len(sys.argv) > 1 and sys.argv[1] == "--update-error":
        update_error = sys.argv[2] if len(sys.argv) > 2 else "The update could not be applied."
        app.after(500, lambda: app.show_error("Update failed", update_error, parent=app))
    raise SystemExit(qt_app.exec())
