#!/usr/bin/env python3
"""Desktop toolkit for managing APK builds and Android devices across projects."""
from __future__ import annotations

import json
import os
import shutil
import socket
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
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

APP_ROOT = Path(__file__).resolve().parent
HERE = APP_ROOT
CONFIG = APP_ROOT / "dcm-android-toolkit.json"
APK_ARCHIVE = APP_ROOT / "data" / "apk_versions"
APK_HISTORY = APP_ROOT / "data" / "apk_versions.json"
APP_VERSION = "0.1.1"
GITHUB_REPOSITORY = "DotComMediaInternetAgency/dcm-android-toolkit"
BUG_REPORT_EMAIL = "dotcommediainternetagency@gmail.com"

TAB_ICONS = {
    "connection": "⇄",
    "apk": "▣",
    "sms export": "✉",
    "subnet scan": "⌕",
    "watch screen": "▤",
    "about": "ⓘ",
}

BUTTON_ICONS = {
    "checking…": "⟳",
    "building…": "⟳",
    "check for updates": "⟳",
    "website": "↗",
    "report a bug…": "⚑",
    "copy email address": "⧉",
    "refresh": "⟳",
    "connect usb": "⇄",
    "connect wi-fi": "⇄",
    "usb": "⇄",
    "wi-fi": "⌁",
    "use fixed ip": "⌖",
    "keep screen awake while charging": "☼",
    "pair…": "⌁",
    "scan subnet…": "⌕",
    "disconnect": "⊘",
    "save project": "▣",
    "add project…": "＋",
    "browse…": "▱",
    "choose…": "▱",
    "build apk…": "▶",
    "version history…": "◷",
    "install / overwrite": "⇩",
    "remove app from device": "⊖",
    "choose output folder…": "▱",
    "read sms count": "≡",
    "preview 2 sms": "◉",
    "export sms to json": "⇧",
    "scan subnet": "⌕",
    "open screen window": "▤",
    "copy all output": "⧉",
    "close": "×",
    "use this apk and install…": "⇩",
    "cancel": "×",
    "save note": "✎",
    "remove all builds": "⊖",
    "remove build": "⊖",
    "add / edit note…": "✎",
    "copy apk…": "⧉",
    "show in folder": "▱",
    "select and install…": "⇩",
}


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


class Deployer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DCM Android Toolkit")
        screen_width, screen_height = self.winfo_screenwidth(), self.winfo_screenheight()
        width, height = min(900, max(320, screen_width - 64)), min(900, max(360, screen_height - 96))
        self.geometry(f"{width}x{height}+{max(0, (screen_width-width)//2)}+{max(0, (screen_height-height)//2)}")
        self.minsize(min(640, width), min(620, height))
        self.configure(bg="#ffffff")
        self.config_data = load_config()
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
        self.project_name = tk.StringVar(value=self.active_project_name)
        self.project_dir = tk.StringVar(value=str(active_project.get("project_dir", "")))
        self.module = tk.StringVar(value=str(active_project.get("module", "app")))
        self.apk = tk.StringVar(value=str(active_project.get("apk", "")))
        self.package = tk.StringVar(value=str(active_project.get("package", "")))
        self.adb = self._find_adb(self.project_dir.get())
        self.target = tk.StringVar()
        self.wifi = tk.StringVar()
        self.fixed_wifi = tk.StringVar(value=self.config_data.get("fixed_wifi", ""))
        self.use_fixed_wifi = tk.BooleanVar(value=bool(self.config_data.get("use_fixed_wifi", False)))
        self.last_device = str(self.config_data.get("last_device") or self.config_data.get("fixed_wifi", "")).strip()
        self.last_device_method = self.config_data.get("last_device_method", "Wi-Fi" if ":" in self.last_device else "USB")
        self.connection_method = tk.StringVar(value=self.config_data.get("connection_method", "Wi-Fi" if ":" in self.last_device else "USB"))
        if self.connection_method.get() not in ("USB", "Wi-Fi"):
            self.connection_method.set("USB")
        if ":" in self.last_device:
            self.wifi.set(self.last_device)
        self.connected_serial = None
        self.connected_model = ""
        self.keep_awake = tk.BooleanVar(value=False)
        self.keep_awake_original = None
        saved_display_settings = self.config_data.get("pending_display_settings", {})
        self.pending_display_settings = saved_display_settings if isinstance(saved_display_settings, dict) else {}
        has_saved_brightness = "brightness_level" in self.config_data
        saved_brightness = int(self.config_data.get("brightness_level", 78))
        if has_saved_brightness and self.config_data.get("brightness_level_unit") != "percent":
            saved_brightness = round(saved_brightness * 100 / 255)
        self.brightness_level = tk.IntVar(value=max(0, min(100, saved_brightness)))
        self.brightness_text = tk.StringVar(value=f"Brightness while awake: {self.brightness_level.get()}%")
        self.brightness_after_id = None
        self.connection_widgets = []
        self.mirror_process = None
        self.subnet = tk.StringVar(value="192.168.1.0/24")
        self.scan_port = tk.StringVar(value="5555")
        self.export_dir = tk.StringVar(value=str(APP_ROOT / "data"))
        self.sms_count_text = tk.StringVar(value="SMS count not checked yet")
        self.build_type = tk.StringVar(value="debug")
        self.build_status = tk.StringVar(value="Ready to build")
        self.build_running = False
        self.closing = False
        self.build_process = None
        self.build_process_lock = threading.Lock()
        self.project_edit_widgets = []
        self.status = tk.StringVar(value="ADB found" if self.adb else "ADB not found — install Android SDK Platform-Tools")
        self._style()
        self._build()
        self.after(1200, lambda: self.check_for_updates(manual=False))
        if self.adb:
            self.after(150, self.restore_previous_device)

    @staticmethod
    def _version_tuple(value):
        match = re.search(r"(?:^|[^0-9])v?(\d+)\.(\d+)\.(\d+)", str(value))
        return tuple(map(int, match.groups())) if match else None

    @staticmethod
    def _icon_text(text, icons):
        label = str(text)
        icon = icons.get(label.casefold())
        if not icon and label.endswith("%"):
            icon = "☼"
        return f"{icon}  {label}" if icon else label

    def _button(self, master, **options):
        if "text" in options:
            options["text"] = self._icon_text(options["text"], BUTTON_ICONS)
        return ttk.Button(master, **options)

    def check_for_updates(self, manual=False):
        if self.about_update_button and self.about_update_button.winfo_exists():
            self.about_update_button.configure(text=self._icon_text("Checking…", BUTTON_ICONS), state="disabled")

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
                    result = (tag, str(release.get("html_url") or f"https://github.com/{GITHUB_REPOSITORY}/releases/latest"))
                else:
                    result = (None, None)
            except (OSError, urllib.error.URLError, json.JSONDecodeError, ValueError) as exc:
                error = str(exc)
            self.after(0, lambda: self._update_check_finished(result, error, manual))

        threading.Thread(target=worker, daemon=True).start()

    @staticmethod
    def _open_github_request(request):
        """Use system TLS roots, falling back to certifi for incomplete Python CA stores."""
        try:
            return urllib.request.urlopen(request, timeout=8, context=ssl.create_default_context())
        except urllib.error.URLError as exc:
            if not isinstance(exc.reason, ssl.SSLCertVerificationError):
                raise
            try:
                import certifi
            except ImportError:
                raise exc
            context = ssl.create_default_context(cafile=certifi.where())
            return urllib.request.urlopen(request, timeout=8, context=context)

    def _update_check_finished(self, result, error, manual):
        if self.about_update_button and self.about_update_button.winfo_exists():
            self.about_update_button.configure(text=self._icon_text("Check for updates", BUTTON_ICONS), state="normal")
        if result and result[0]:
            tag, url = result
            if messagebox.askyesno("Update available", f"DCM Android Toolkit {tag} is available. Open the GitHub release page?"):
                webbrowser.open(url)
        elif manual:
            if error:
                messagebox.showwarning("Update check failed", f"Could not check GitHub for updates.\n\n{error}")
            else:
                messagebox.showinfo("No updates available", f"You are using the latest version ({APP_VERSION}).")

    def _style(self):
        s = ttk.Style(self)
        self.style = s
        s.theme_use("clam")
        s.configure("TFrame", background="#ffffff")
        s.configure("Card.TFrame", background="#ffffff")
        s.configure("TLabel", background="#ffffff", foreground="#173342", font=("Helvetica Neue", 11))
        s.configure("Card.TLabel", background="#ffffff", foreground="#173342", font=("Helvetica Neue", 11))
        s.configure("Title.TLabel", background="#ffffff", font=("Helvetica Neue", 23, "bold"))
        s.configure("Sub.TLabel", background="#ffffff", foreground="#637780", font=("Helvetica Neue", 10))
        s.configure("Warning.TLabel", background="#ffffff", foreground="#8d5d13", font=("Helvetica Neue", 10))
        s.configure("HighBrightness.TLabel", background="#ffffff", foreground="#c83932", font=("Helvetica Neue", 10, "bold"))
        s.configure("Safe.Horizontal.TScale", troughcolor="#e5ece8", background="#d9e4df", sliderthickness=20)
        s.configure("High.Horizontal.TScale", troughcolor="#f8d8d5", background="#d7473e", sliderthickness=20, bordercolor="#aa302a", darkcolor="#aa302a", lightcolor="#f07a72")
        s.configure("TButton", font=("Helvetica Neue", 10, "bold"), padding=(12, 9))
        s.configure("Accent.TButton", background="#087e78", foreground="white")
        s.map("Accent.TButton", background=[("active", "#06645f")])
        s.configure("Build.TButton", background="#2867a0", foreground="white")
        s.map(
            "Build.TButton",
            background=[("disabled", "#d8e1e8"), ("pressed", "#173f6b"), ("active", "#1d4f80")],
            foreground=[("disabled", "#72808a"), ("!disabled", "white")],
        )
        s.configure("Danger.TButton", background="#fff0ed", foreground="#a43f37")
        s.configure("TEntry", padding=8)
        s.configure("TNotebook", background="#ffffff")
        s.configure("Workspace.Vertical.TPanedwindow", sashthickness=8, sashrelief="raised")

    @staticmethod
    def _fit_dialog(dialog, preferred=(900, 700), minimum=(640, 480)):
        """Size custom windows to the available display while keeping their footer in bounds."""
        screen_width, screen_height = dialog.winfo_screenwidth(), dialog.winfo_screenheight()
        available_width = max(320, screen_width - 64)
        available_height = max(300, screen_height - 96)
        width = min(preferred[0], available_width)
        height = min(preferred[1], available_height)
        dialog.geometry(f"{width}x{height}+{max(0, (screen_width-width)//2)}+{max(0, (screen_height-height)//2)}")
        dialog.minsize(min(minimum[0], width), min(minimum[1], height))
        dialog.resizable(True, True)
        return width, height

    @staticmethod
    def _find_adb(project_dir=""):
        """Prefer the selected Gradle project's SDK, then common SDK locations."""
        candidates = []
        roots = [Path(project_dir).expanduser()] if project_dir else []
        if roots:
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

    def _build(self):
        root = ttk.Frame(self, padding=24)
        root.pack(fill="both", expand=True)
        ttk.Label(root, text="DCM Android Toolkit", style="Title.TLabel").pack(anchor="w")
        ttk.Label(root, text="Connect a device, replace its installed app, or remove the app.", style="Sub.TLabel").pack(anchor="w", pady=(4, 20))
        self.about_update_button = None

        def add_page_header(page, title, description):
            ttk.Label(page, text=title, style="Title.TLabel").pack(anchor="w")
            description_label = ttk.Label(
                page, text=description, style="Sub.TLabel", justify="left", wraplength=760
            )
            description_label.pack(anchor="w", fill="x", pady=(5, 14))
            ttk.Separator(page, orient="horizontal").pack(fill="x", pady=(0, 16))
            page.bind(
                "<Configure>",
                lambda event, label=description_label: label.configure(
                    wraplength=max(220, event.width - 48)
                ),
                add="+",
            )

        workspace = ttk.Panedwindow(root, orient=tk.VERTICAL, style="Workspace.Vertical.TPanedwindow")
        workspace.pack(fill="both", expand=True)
        tabs = ttk.Notebook(workspace)
        self.tabs = tabs
        workspace.add(tabs, weight=5)

        def create_scrollable_tab():
            page = ttk.Frame(tabs, style="TFrame")
            page.grid_rowconfigure(0, weight=1)
            page.grid_columnconfigure(0, weight=1)
            canvas = tk.Canvas(page, background="#ffffff", highlightthickness=0, borderwidth=0)
            scrollbar = ttk.Scrollbar(page, orient="vertical", command=canvas.yview)
            canvas.configure(yscrollcommand=scrollbar.set)
            canvas.grid(row=0, column=0, sticky="nsew")
            scrollbar.grid(row=0, column=1, sticky="ns")

            content = ttk.Frame(canvas, style="TFrame", padding=20)
            content_window = canvas.create_window((0, 0), window=content, anchor="nw")

            def update_scroll_region(_event=None):
                canvas.configure(scrollregion=canvas.bbox("all"))

            content.bind("<Configure>", update_scroll_region, add="+")
            canvas.bind(
                "<Configure>",
                lambda event: canvas.itemconfigure(content_window, width=event.width),
                add="+",
            )

            def scroll_with_wheel(event):
                if not canvas.winfo_ismapped():
                    return
                x = event.x_root - canvas.winfo_rootx()
                y = event.y_root - canvas.winfo_rooty()
                if not (0 <= x < canvas.winfo_width() and 0 <= y < canvas.winfo_height()):
                    return
                number = getattr(event, "num", None)
                if number == 4:
                    units = -1
                elif number == 5:
                    units = 1
                else:
                    delta = getattr(event, "delta", 0)
                    units = -int(delta / 120) if abs(delta) >= 120 else (-1 if delta > 0 else 1 if delta < 0 else 0)
                if units:
                    canvas.yview_scroll(units, "units")
                    return "break"

            self.bind_all("<MouseWheel>", scroll_with_wheel, add="+")
            self.bind_all("<Button-4>", scroll_with_wheel, add="+")
            self.bind_all("<Button-5>", scroll_with_wheel, add="+")
            return page, content

        connection_page, connection_tab = create_scrollable_tab()
        apk_page, apk_tab = create_scrollable_tab()
        sms_page, sms_tab = create_scrollable_tab()
        scan_page, scan_tab = create_scrollable_tab()
        watch_page, watch_tab = create_scrollable_tab()
        about_page, about_tab = create_scrollable_tab()
        tabs.add(connection_page, text=self._icon_text("Connection", TAB_ICONS))
        tabs.add(apk_page, text=self._icon_text("APK", TAB_ICONS))
        tabs.add(sms_page, text=self._icon_text("SMS Export", TAB_ICONS))
        tabs.add(scan_page, text=self._icon_text("Subnet Scan", TAB_ICONS))
        tabs.add(watch_page, text=self._icon_text("Watch Screen", TAB_ICONS))
        tabs.add(about_page, text=self._icon_text("About", TAB_ICONS))

        add_page_header(
            about_tab,
            "About DCM Android Toolkit",
            "Application overview, credits, and release update information.",
        )
        about_card = ttk.Frame(about_tab, style="Card.TFrame", padding=18)
        about_card.pack(anchor="nw", fill="x")
        about_description = ttk.Label(
            about_card,
            text=(
                "DCM Android Toolkit helps Android developers work across multiple Gradle projects. "
                "Build debug or release APKs, connect to devices over USB or Wi-Fi, install apps, "
                "and keep local build history. It also includes device and SMS diagnostic tools."
            ),
            style="Card.TLabel",
            wraplength=760,
            justify="left",
        )
        about_description.pack(anchor="w", fill="x", pady=(0, 16))
        about_tab.bind(
            "<Configure>",
            lambda event: about_description.configure(wraplength=max(220, event.width - 84)),
            add="+",
        )
        ttk.Separator(about_card, orient="horizontal").pack(fill="x", pady=(0, 14))
        ttk.Label(about_card, text=f"Version {APP_VERSION}", style="Sub.TLabel").pack(anchor="w")
        ttk.Label(about_card, text="Made by Emre Demir", style="Card.TLabel").pack(anchor="w", pady=(4, 14))
        ttk.Separator(about_card, orient="horizontal").pack(fill="x", pady=(0, 14))
        about_actions = ttk.Frame(about_card, style="Card.TFrame")
        about_actions.pack(anchor="w")
        self.about_update_button = self._button(
            about_actions, text="Check for updates", command=lambda: self.check_for_updates(manual=True)
        )
        self.about_update_button.pack(side="left")
        self._button(
            about_actions,
            text="Website",
            command=lambda: webbrowser.open("https://dotcommedia.online"),
        ).pack(side="left", padx=(8, 0))
        self._button(
            about_actions,
            text="Report a bug…",
            command=self.export_activity_log_for_bug_report,
        ).pack(side="left", padx=(8, 0))

        add_page_header(
            connection_tab,
            "Connect a device",
            "Connect over USB or Wi-Fi. Disconnect to change connection settings.",
        )
        method_row = ttk.Frame(connection_tab); method_row.pack(fill="x", pady=(0, 12))
        ttk.Label(method_row, text="Connection method", font=("Helvetica Neue", 11, "bold")).pack(side="left", padx=(0, 12))
        for method in ("USB", "Wi-Fi"):
            radio = ttk.Radiobutton(
                method_row,
                text=self._icon_text(method, BUTTON_ICONS),
                value=method,
                variable=self.connection_method,
                command=self._connection_method_changed,
            )
            radio.pack(side="left", padx=(0, 12))
            self.connection_widgets.append(radio)
        ttk.Separator(connection_tab, orient="horizontal").pack(fill="x", pady=(0, 12))
        device_card = ttk.Frame(connection_tab, style="Card.TFrame", padding=18); device_card.pack(fill="x", pady=(0, 14))
        self.device_card = device_card
        ttk.Label(device_card, text="USB connection", style="Card.TLabel", font=("Helvetica Neue", 13, "bold")).pack(anchor="w", pady=(0, 10))
        usbrow = ttk.Frame(device_card, style="Card.TFrame"); usbrow.pack(fill="x")
        self.devices = ttk.Combobox(usbrow, textvariable=self.target, state="readonly", width=32)
        self.devices.pack(side="left", fill="x", expand=True)
        refresh_button = self._button(usbrow, text="Refresh", command=self.refresh_devices); refresh_button.pack(side="left", padx=(8, 0))
        self.connect_usb_button = self._button(usbrow, text="Connect USB", style="Accent.TButton", command=self.connect_usb); self.connect_usb_button.pack(side="left", padx=(8, 0))
        self.connection_widgets.extend([self.devices, refresh_button, self.connect_usb_button])
        ttk.Label(device_card, text="Connect the phone by cable, enable USB debugging, and accept its authorization prompt.", style="Sub.TLabel", wraplength=580).pack(anchor="w", pady=(10, 0))

        wifi_card = ttk.Frame(connection_tab, style="Card.TFrame", padding=18); wifi_card.pack(fill="x", pady=(0, 14))
        self.wifi_card = wifi_card
        ttk.Label(wifi_card, text="Wi-Fi connection", style="Card.TLabel", font=("Helvetica Neue", 13, "bold")).pack(anchor="w", pady=(0, 10))
        fixedrow = ttk.Frame(wifi_card, style="Card.TFrame"); fixedrow.pack(fill="x", pady=(0, 7))
        fixed_check = ttk.Checkbutton(
            fixedrow,
            text=self._icon_text("Use fixed IP", BUTTON_ICONS),
            variable=self.use_fixed_wifi,
            command=self._update_ip_mode,
        )
        fixed_check.pack(side="left")
        self.connection_widgets.append(fixed_check)
        ttk.Label(wifi_card, text="Saved fixed IP and port", style="Card.TLabel").pack(anchor="w")
        self.fixed_entry = ttk.Entry(wifi_card, textvariable=self.fixed_wifi)
        self.fixed_entry.pack(fill="x", pady=(4, 10))
        ttk.Label(wifi_card, text="Manual IP and port (example: 192.168.1.42:5555)", style="Card.TLabel").pack(anchor="w")
        self.manual_entry = ttk.Combobox(wifi_card, textvariable=self.wifi, state="normal", values=())
        self.manual_entry.pack(fill="x", pady=(4, 10))
        self.connection_widgets.extend([self.fixed_entry, self.manual_entry])
        wbuttons = ttk.Frame(wifi_card, style="Card.TFrame"); wbuttons.pack(fill="x")
        self.pair_button = self._button(wbuttons, text="Pair…", command=self.pair_wifi); self.pair_button.pack(side="left")
        self.connect_wifi_button = self._button(wbuttons, text="Connect Wi-Fi", style="Accent.TButton", command=self.connect_wifi); self.connect_wifi_button.pack(side="left", padx=8)
        self.scan_open_button = self._button(wbuttons, text="Scan subnet…", command=self.open_scan_tab); self.scan_open_button.pack(side="left")
        self.connection_widgets.extend([self.pair_button, self.connect_wifi_button, self.scan_open_button])

        self.connected_card = ttk.Frame(connection_tab, style="Card.TFrame", padding=18)
        connected_row = ttk.Frame(self.connected_card, style="Card.TFrame")
        connected_row.pack(fill="x")
        title_block = ttk.Frame(connected_row, style="Card.TFrame")
        title_block.pack(side="left", fill="x", expand=True, padx=(0, 14))
        self.active_label = ttk.Label(title_block, text="Connected device", style="Card.TLabel", font=("Helvetica Neue", 14, "bold"), wraplength=430, justify="left", anchor="w")
        self.active_label.pack(fill="x", anchor="w")
        self.connection_detail_label = ttk.Label(title_block, text="", style="Sub.TLabel", wraplength=430, justify="left", anchor="w")
        self.connection_detail_label.pack(fill="x", anchor="w", pady=(5, 0))
        self.disconnect_button = self._button(connected_row, text="Disconnect", style="Danger.TButton", command=self.disconnect_device)
        self.disconnect_button.configure(width=15)
        self.disconnect_button.pack(side="right", padx=(8, 0))
        self.keep_awake_button = ttk.Checkbutton(
            self.connected_card,
            text=self._icon_text("Keep screen awake while charging", BUTTON_ICONS),
            variable=self.keep_awake,
            command=self.toggle_keep_awake,
            state="disabled",
        )
        self.keep_awake_button.pack(anchor="w", pady=(14, 0))
        ttk.Label(self.connected_card, text="Temporarily disables battery saver and screen dim timeout while enabled. Original settings are restored when you turn it off.", style="Sub.TLabel", wraplength=580).pack(anchor="w", pady=(5, 8))
        self.brightness_value_label = ttk.Label(self.connected_card, textvariable=self.brightness_text, style="Card.TLabel", font=("Helvetica Neue", 10, "bold"))
        self.brightness_value_label.pack(anchor="w")
        self.brightness_scale = ttk.Scale(self.connected_card, from_=0, to=100, variable=self.brightness_level, command=self._brightness_changed, style="Safe.Horizontal.TScale")
        self.brightness_scale.pack(fill="x", pady=(4, 0))
        self._update_brightness_visuals(self.brightness_level.get())
        presets = ttk.Frame(self.connected_card, style="Card.TFrame")
        presets.pack(anchor="w", pady=(7, 0))
        ttk.Label(presets, text="Presets", style="Card.TLabel").pack(side="left", padx=(0, 8))
        for percent in (25, 50, 75):
            self._button(presets, text=f"{percent}%", command=lambda value=percent: self.set_brightness_preset(value)).pack(side="left", padx=(0, 6))
        ttk.Label(self.connected_card, text="AMOLED care: avoid prolonged high brightness with static content; it can increase burn-in risk. No 100% preset is provided.", style="Warning.TLabel", wraplength=580).pack(anchor="w", pady=(8, 0))
        ttk.Label(self.connected_card, text="ADB connection is active. Disconnect to change device or connection settings.", style="Sub.TLabel").pack(anchor="w", pady=(8, 0))
        self.protocol("WM_DELETE_WINDOW", self.close_app)

        add_page_header(
            apk_tab,
            "APK build, install, and removal",
            "Build APKs from a saved Gradle project or manage an APK for the selected device.",
        )
        card2 = ttk.Frame(apk_tab, style="Card.TFrame", padding=18); card2.pack(fill="x", pady=(0, 12))
        ttk.Label(card2, text="Project profile", style="Card.TLabel", font=("Helvetica Neue", 13, "bold")).pack(anchor="w", pady=(0, 10))
        ttk.Separator(card2, orient="horizontal").pack(fill="x", pady=(0, 12))
        profilerow = ttk.Frame(card2, style="Card.TFrame"); profilerow.pack(fill="x", pady=(0, 10))
        self.project_selector = ttk.Combobox(profilerow, textvariable=self.project_name,
                                             values=sorted(self.project_profiles), state="readonly")
        self.project_selector.pack(side="left", fill="x", expand=True)
        self.project_selector.bind("<<ComboboxSelected>>", self._project_profile_selected)
        self.project_edit_widgets.append((self.project_selector, "readonly"))
        save_project_button = self._button(profilerow, text="Save project", command=self.save_project_profile)
        save_project_button.pack(side="left", padx=(8, 0))
        self.project_edit_widgets.append((save_project_button, "normal"))
        self.add_project_button = self._button(profilerow, text="Add project…", command=self.add_project)
        self.add_project_button.pack(side="left", padx=(8, 0))
        self.project_edit_widgets.append((self.add_project_button, "normal"))
        ttk.Label(card2, text="Gradle project folder", style="Card.TLabel").pack(anchor="w")
        projectrow = ttk.Frame(card2, style="Card.TFrame"); projectrow.pack(fill="x", pady=(4, 8))
        project_dir_entry = ttk.Entry(projectrow, textvariable=self.project_dir)
        project_dir_entry.pack(side="left", fill="x", expand=True)
        self.project_edit_widgets.append((project_dir_entry, "normal"))
        choose_project_button = self._button(projectrow, text="Choose…", command=self.choose_project_dir)
        choose_project_button.pack(side="left", padx=(8, 0))
        self.project_edit_widgets.append((choose_project_button, "normal"))
        modulerow = ttk.Frame(card2, style="Card.TFrame"); modulerow.pack(fill="x", pady=(0, 8))
        ttk.Label(modulerow, text="Gradle module", style="Card.TLabel").pack(side="left")
        module_entry = ttk.Entry(modulerow, textvariable=self.module, width=24)
        module_entry.pack(side="left", padx=(8, 0))
        self.project_edit_widgets.append((module_entry, "normal"))
        ttk.Label(modulerow, text="(for example: app or :client:app)", style="Sub.TLabel").pack(side="left", padx=(8, 0))
        ttk.Label(card2, text="APK file", style="Card.TLabel").pack(anchor="w")
        apkrow = ttk.Frame(card2, style="Card.TFrame"); apkrow.pack(fill="x", pady=(4, 10))
        apk_entry = ttk.Entry(apkrow, textvariable=self.apk)
        apk_entry.pack(side="left", fill="x", expand=True)
        self.project_edit_widgets.append((apk_entry, "normal"))
        choose_apk_button = self._button(apkrow, text="Choose…", command=self.choose_apk)
        choose_apk_button.pack(side="left", padx=(8, 0))
        self.project_edit_widgets.append((choose_apk_button, "normal"))
        buildrow = ttk.Frame(card2, style="Card.TFrame"); buildrow.pack(fill="x", pady=(8, 10))
        ttk.Label(buildrow, text="Build type", style="Card.TLabel").pack(side="left")
        build_type_selector = ttk.Combobox(buildrow, textvariable=self.build_type, state="readonly", values=("debug", "release"), width=10)
        build_type_selector.pack(side="left", padx=(8, 10))
        self.project_edit_widgets.append((build_type_selector, "readonly"))
        self.build_button = self._button(buildrow, text="Build APK…", style="Build.TButton", command=self.build_apk)
        self.build_button.pack(side="left")
        self._button(buildrow, text="Version history…", command=self.open_version_history).pack(side="left", padx=(8, 0))
        ttk.Separator(apk_tab, orient="horizontal").pack(fill="x", pady=(4, 14))
        ttk.Label(apk_tab, text="Android package name (for example: com.example.app)", style="Card.TLabel").pack(anchor="w", pady=(0, 0))
        package_entry = ttk.Entry(apk_tab, textvariable=self.package)
        package_entry.pack(fill="x", pady=(4, 10))
        self.project_edit_widgets.append((package_entry, "normal"))
        actions = ttk.Frame(apk_tab); actions.pack(fill="x", pady=5)
        self._button(actions, text="Install / overwrite", style="Accent.TButton", command=self.install).pack(side="left")
        self._button(actions, text="Remove app from device", style="Danger.TButton", command=self.uninstall).pack(side="left", padx=10)

        add_page_header(
            sms_tab,
            "SMS debug export",
            "Read a small sample or export SMS diagnostics from the connected device.",
        )
        card3 = ttk.Frame(sms_tab, style="Card.TFrame", padding=18); card3.pack(fill="x")
        ttk.Label(card3, text="Reads the device SMS database through ADB. Android may restrict this unless the app is the default SMS handler or the device grants shell access.", style="Sub.TLabel", wraplength=580).pack(anchor="w", pady=(0, 12))
        ttk.Entry(card3, textvariable=self.export_dir).pack(fill="x", pady=(0, 8))
        self._button(card3, text="Choose output folder…", command=self.choose_export_dir).pack(anchor="w", pady=(0, 8))
        ttk.Separator(card3, orient="horizontal").pack(fill="x", pady=(4, 12))
        ttk.Label(card3, textvariable=self.sms_count_text, style="Card.TLabel", font=("Helvetica Neue", 11, "bold")).pack(anchor="w", pady=(2, 10))
        ttk.Separator(card3, orient="horizontal").pack(fill="x", pady=(0, 12))
        sms_actions = ttk.Frame(card3, style="Card.TFrame"); sms_actions.pack(anchor="w")
        self.count_button = self._button(sms_actions, text="Read SMS count", command=self.count_sms)
        self.count_button.pack(side="left")
        self.preview_button = self._button(sms_actions, text="Preview 2 SMS", command=self.preview_sms)
        self.preview_button.pack(side="left", padx=(8, 0))
        self.export_button = self._button(sms_actions, text="Export SMS to JSON", style="Accent.TButton", command=self.export_sms)
        self.export_button.pack(side="left", padx=(8, 0))

        add_page_header(
            scan_tab,
            "Find a device on your network",
            "Scan a local subnet for hosts that may be accepting ADB connections.",
        )
        scan_card = ttk.Frame(scan_tab, style="Card.TFrame", padding=18); scan_card.pack(fill="x")
        ttk.Label(scan_card, text="Scan subnet", style="Card.TLabel", font=("Helvetica Neue", 13, "bold")).pack(anchor="w", pady=(0, 8))
        ttk.Label(scan_card, text="Enter a CIDR subnet and ADB port. The result is copied into the manual IP field on the Connection tab.", style="Sub.TLabel", wraplength=580).pack(anchor="w", pady=(0, 12))
        ttk.Separator(scan_card, orient="horizontal").pack(fill="x", pady=(0, 12))
        scanrow = ttk.Frame(scan_card, style="Card.TFrame"); scanrow.pack(fill="x")
        ttk.Entry(scanrow, textvariable=self.subnet, width=24).pack(side="left", padx=(0, 10))
        ttk.Entry(scanrow, textvariable=self.scan_port, width=8).pack(side="left", padx=(0, 10))
        self.scan_button = self._button(scanrow, text="Scan subnet", style="Accent.TButton", command=self.scan_subnet)
        self.scan_button.pack(side="left")
        self.connection_widgets.append(self.scan_button)

        add_page_header(
            watch_tab,
            "Watch your device",
            "View and control the connected Android screen in a separate window.",
        )
        watch_card = ttk.Frame(watch_tab, style="Card.TFrame", padding=18)
        watch_card.pack(fill="x")
        ttk.Label(watch_card, text="Live screen with touch control", style="Card.TLabel", font=("Helvetica Neue", 13, "bold")).pack(anchor="w", pady=(0, 8))
        ttk.Separator(watch_card, orient="horizontal").pack(fill="x", pady=(0, 12))
        ttk.Label(
            watch_card,
            text="Opens the connected Android screen in a separate window. Clicks, taps, swipes, and keyboard input in that window are sent to the phone over ADB.",
            style="Sub.TLabel",
            wraplength=580,
        ).pack(anchor="w", pady=(0, 12))
        self.watch_device_label = ttk.Label(watch_card, text="Connect a device first.", style="Card.TLabel", font=("Helvetica Neue", 10, "bold"))
        self.watch_device_label.pack(anchor="w", pady=(0, 10))
        self.watch_button = self._button(watch_card, text="Open screen window", style="Accent.TButton", command=self.open_screen_mirror, state="disabled")
        self.watch_button.pack(anchor="w")
        ttk.Label(
            watch_card,
            text="Screen mirroring uses scrcpy. Install with `brew install scrcpy` if it is not already available.",
            style="Sub.TLabel",
            wraplength=580,
        ).pack(anchor="w", pady=(12, 0))

        log_frame = ttk.Frame(workspace, padding=(0, 8, 0, 0))
        workspace.add(log_frame, weight=1)
        ttk.Label(log_frame, text="Activity · drag the divider to resize", style="Sub.TLabel").pack(anchor="w", pady=(0, 5))
        log_body = ttk.Frame(log_frame, style="Card.TFrame")
        log_body.pack(fill="both", expand=True)
        self.output = tk.Text(
            log_body,
            height=6,
            bg="#102a3a",
            fg="#d9eeea",
            insertbackground="white",
            relief="flat",
            font=("Menlo", 10),
            padx=12,
            pady=10,
            state="disabled",
        )
        self.activity_scrollbar = ttk.Scrollbar(log_body, orient="vertical", command=self.output.yview)
        self.output.configure(yscrollcommand=self.activity_scrollbar.set)
        self.output.pack(side="left", fill="both", expand=True)
        self.activity_scrollbar.pack(side="right", fill="y")
        self.build_status_row = ttk.Frame(root, style="Card.TFrame", padding=(8, 5))
        self.build_status_label = ttk.Label(
            self.build_status_row,
            textvariable=self.build_status,
            style="Sub.TLabel",
            wraplength=900,
            justify="left",
            anchor="w",
        )
        self.build_status_label.pack(side="left", fill="x", expand=True)
        self.build_progress = ttk.Progressbar(self.build_status_row, mode="indeterminate", length=112)
        self.status_label = ttk.Label(root, textvariable=self.status, style="Sub.TLabel")
        self.status_label.pack(fill="x", pady=(8, 0))
        self.bind(
            "<Configure>",
            lambda _event: self.build_status_label.configure(
                wraplength=max(240, self.winfo_width() - 176)
            ),
            add="+",
        )
        self.after(150, lambda: workspace.sashpos(0, max(240, workspace.winfo_height() - 180)))
        self._update_ip_mode()

    def log(self, text):
        self.output.configure(state="normal")
        self.output.insert("end", text.rstrip() + "\n")
        self.output.see("end")
        self.output.configure(state="disabled")

    def export_activity_log_for_bug_report(self):
        """Save the visible Activity log to Desktop and show support details."""
        desktop = Path.home() / "Desktop"
        if not desktop.is_dir():
            messagebox.showerror(
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
            messagebox.showerror(
                "Could not export Activity log",
                f"Could not save the Activity log to the Desktop.\n\n{exc}",
                parent=self,
            )
            return

        self._show_bug_report_exported(export_path)

    def _show_bug_report_exported(self, export_path):
        dialog = tk.Toplevel(self)
        dialog.title("Activity log exported")
        dialog.transient(self)
        dialog.configure(bg="#ffffff")
        dialog.columnconfigure(0, weight=1)
        dialog.rowconfigure(0, weight=1)

        panel = ttk.Frame(dialog, padding=20)
        panel.grid(row=0, column=0, sticky="nsew")
        panel.columnconfigure(0, weight=1)
        ttk.Label(panel, text="Activity log exported", style="Title.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 10)
        )
        description = ttk.Label(
            panel,
            text="The log is saved on your Desktop. Attach it to an email to support:",
            wraplength=520,
            justify="left",
        )
        description.grid(row=1, column=0, sticky="ew", pady=(0, 6))
        location = ttk.Label(panel, text=str(export_path), style="Sub.TLabel", wraplength=520, justify="left")
        location.grid(
            row=2, column=0, sticky="ew", pady=(0, 8)
        )
        ttk.Label(panel, text=BUG_REPORT_EMAIL, style="Card.TLabel").grid(
            row=3, column=0, sticky="w", pady=(0, 12)
        )

        copied_message = tk.StringVar(value="")
        ttk.Label(panel, textvariable=copied_message, style="Sub.TLabel").grid(
            row=4, column=0, sticky="w", pady=(0, 8)
        )
        footer = ttk.Frame(panel)
        footer.grid(row=5, column=0, sticky="ew")

        def copy_email_address():
            self.clipboard_clear()
            self.clipboard_append(BUG_REPORT_EMAIL)
            copied_message.set("Email address copied to clipboard.")

        self._button(footer, text="Copy email address", command=copy_email_address).pack(side="left")
        self._button(footer, text="Close", command=dialog.destroy).pack(side="right")
        dialog.bind(
            "<Configure>",
            lambda event: (
                description.configure(wraplength=max(260, event.width - 64)),
                location.configure(wraplength=max(260, event.width - 64)),
            ),
            add="+",
        )
        dialog.bind("<Escape>", lambda _event: dialog.destroy())
        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
        self._fit_dialog(dialog, preferred=(620, 300), minimum=(480, 250))
        dialog.grab_set()
        dialog.focus_set()

    def run_adb(self, *args, timeout=90):
        if not self.adb:
            raise RuntimeError("ADB was not found. Install Android SDK Platform-Tools and ensure adb is on PATH.")
        return subprocess.run([self.adb, *args], capture_output=True, text=True, timeout=timeout)

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
        usb_devices = [device for device in devices if ":" not in device]
        self.devices["values"] = usb_devices
        if self.last_device in usb_devices:
            self.target.set(self.last_device)
        elif self.target.get() not in usb_devices:
            self.target.set(usb_devices[0] if usb_devices else "")
        if not self.connected_serial:
            self.status.set(f"{len(devices)} authorized device(s) available" if devices else "No authorized devices. Check the USB prompt or Wi-Fi connection.")
        self.log(output or "No device listed. For Wi-Fi, enable Wireless debugging on the phone.")

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
                widget.configure(state="disabled")
            self.disconnect_button.configure(state="normal", text=self._icon_text("Disconnect", BUTTON_ICONS))
            self.keep_awake_button.configure(state="normal")
            self.brightness_scale.configure(state="normal")
            self._render_connection_state()
            return
        self.disconnect_button.configure(state="disabled", text=self._icon_text("Disconnect", BUTTON_ICONS))
        self.keep_awake_button.configure(state="disabled")
        self.brightness_scale.configure(state="disabled")
        self._render_connection_state()
        self.fixed_entry.configure(state="normal" if self.use_fixed_wifi.get() else "disabled")
        self.manual_entry.configure(state="disabled" if self.use_fixed_wifi.get() else "normal")
        for widget in self.connection_widgets:
            if widget in (self.fixed_entry, self.manual_entry):
                continue
            widget.configure(state="readonly" if widget is self.devices else "normal")

    def _render_connection_state(self):
        self._update_watch_screen_state()
        if not hasattr(self, "connected_card"):
            return
        if self.connected_serial:
            self.device_card.pack_forget()
            self.wifi_card.pack_forget()
            if not self.connected_card.winfo_manager():
                self.connected_card.pack(fill="x", pady=(0, 14))
        else:
            self.connected_card.pack_forget()
            if self.connection_method.get() == "USB":
                self.wifi_card.pack_forget()
                if not self.device_card.winfo_manager():
                    self.device_card.pack(fill="x", pady=(0, 14))
            else:
                self.device_card.pack_forget()
                if not self.wifi_card.winfo_manager():
                    self.wifi_card.pack(fill="x", pady=(0, 14))

    def _update_watch_screen_state(self):
        if not hasattr(self, "watch_button"):
            return
        if self.connected_serial:
            self.watch_device_label.configure(text=f"Ready: {self.connected_model or 'Android device'} · {self.connection_method.get()}")
            self.watch_button.configure(state="normal")
        else:
            self.watch_device_label.configure(text="Connect a device first.")
            self.watch_button.configure(state="disabled")

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
            messagebox.showerror("scrcpy is required", "Install scrcpy to mirror and control the phone screen.\n\nOn macOS, run:\n\nbrew install scrcpy")
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
            messagebox.showerror("Could not open screen window", str(error))
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
        if ":" in serial:
            self.connection_method.set("Wi-Fi")
            self.last_device_method = "Wi-Fi"
            detail = f"Connection: Wi-Fi · {serial}"
        else:
            self.connection_method.set("USB")
            self.last_device_method = "USB"
            detail = "Connection: USB cable"
        self.active_label.configure(text=f"Connected device: {model}")
        self.connection_detail_label.configure(text=detail)
        self.status.set(f"Connected to {model}")
        self._save_config()
        self._update_ip_mode()

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
        self.disconnect_button.configure(state="disabled")
        self.keep_awake_button.configure(state="disabled")
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
        self.disconnect_button.configure(state="normal")
        self.keep_awake_button.configure(state="normal")
        self.status.set("Could not complete disconnect")
        self.log(f"Disconnect error: {message}")
        messagebox.showerror("Disconnect failed", message)

    def _clear_connection(self):
        old = self.connected_serial
        self._stop_screen_mirror()
        keep_active = old in self.pending_display_settings
        self.connected_serial = None
        self.active_label.configure(text="No device connected")
        if keep_active:
            self.keep_awake.set(True)
            self.status.set(f"Disconnected {old} · keep-awake and brightness remain active; reconnect to restore")
        else:
            self.keep_awake.set(False)
            self.keep_awake_original = None
            self.status.set(f"Disconnected {old}")
        self._update_ip_mode()

    def toggle_keep_awake(self):
        serial = self.connected_serial
        if not serial:
            self.keep_awake.set(False)
            return
        enable = self.keep_awake.get()
        brightness = self.brightness_level.get()
        self.keep_awake_button.configure(state="disabled")
        self.brightness_scale.configure(state="disabled")
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
                self.after(0, lambda: self.keep_awake_button.configure(state="normal"))
                self.after(0, lambda: self.brightness_scale.configure(state="normal" if self.connected_serial else "disabled"))
                self.after(0, lambda: self.status.set("Could not change stay-awake setting"))
                self.after(0, lambda: self.log(f"Stay-awake error: {message}"))
                self.after(0, self._save_config)
                self.after(0, lambda: messagebox.showerror("Keep screen awake", message))

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
        if self.brightness_after_id is not None:
            self.after_cancel(self.brightness_after_id)
        self.brightness_after_id = self.after(400, self._commit_brightness_change)

    def _update_brightness_visuals(self, level):
        high = level > 75
        self.brightness_scale.configure(style="High.Horizontal.TScale" if high else "Safe.Horizontal.TScale")
        self.brightness_value_label.configure(style="HighBrightness.TLabel" if high else "Card.TLabel")

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
        self.keep_awake_button.configure(state="normal" if self.connected_serial else "disabled")
        self.brightness_scale.configure(state="normal" if self.connected_serial else "disabled")
        self.status.set(message)
        self.log(message)
        self._save_config()

    def close_app(self):
        self._stop_screen_mirror()
        if self.keep_awake_original is not None and self.connected_serial:
            try:
                self._restore_keep_awake(self.connected_serial)
                self.log("Restored the device stay-awake setting before exit.")
                self._save_config()
            except Exception as e:
                if not messagebox.askyesno("Could not restore setting", f"The previous stay-awake setting could not be restored:\n\n{e}\n\nClose anyway?"):
                    return
        self._save_config()
        self.closing = True
        with self.build_process_lock:
            build_process = self.build_process
        if build_process and build_process.poll() is None:
            self._stop_gradle_process(build_process)
        self.destroy()

    @staticmethod
    def _stop_gradle_process(process):
        """Stop a toolkit-owned Gradle process tree without touching unrelated processes."""
        if os.name == "nt":
            if process.poll() is None:
                try:
                    subprocess.run(
                        ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                        capture_output=True,
                        text=True,
                        timeout=8,
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
                self.after(0, lambda text=message: messagebox.showerror("Wi-Fi connection failed", text))

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
            messagebox.showerror("Invalid scan range", str(e))
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
            self.manual_entry.configure(values=found)
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
            messagebox.showerror("Project name required", "Add a project and give it a name before saving it.", parent=self)
            return
        self._save_profile_values()
        self._save_config()
        self.adb = self._find_adb(self.project_dir.get())
        self.status.set(f"Saved project profile: {self.active_project_name}")

    @staticmethod
    def _gradle_wrapper_name():
        return "gradlew.bat" if os.name == "nt" else "gradlew"

    def add_project(self):
        dialog = tk.Toplevel(self)
        dialog.title("Add Android project")
        dialog.transient(self)
        dialog.configure(background="#ffffff")
        self._fit_dialog(dialog, preferred=(720, 360), minimum=(520, 300))
        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(0, weight=1)

        content = ttk.Frame(dialog, padding=(20, 18, 20, 10))
        content.grid(row=0, column=0, sticky="nsew")
        content.grid_columnconfigure(1, weight=1)
        ttk.Label(content, text="Add Android project", style="Title.TLabel").grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 6))
        ttk.Label(
            content,
            text="Choose the Gradle root folder and give this project a name so you can find it in the project list.",
            style="Sub.TLabel",
            wraplength=640,
        ).grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, 16))

        project_name = tk.StringVar()
        project_folder = tk.StringVar()
        suggested_name = [""]
        ttk.Label(content, text="Project name (required)", style="Card.TLabel").grid(row=2, column=0, columnspan=3, sticky="w")
        name_entry = ttk.Entry(content, textvariable=project_name)
        name_entry.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(4, 12))
        ttk.Label(content, text="Gradle project folder (required)", style="Card.TLabel").grid(row=4, column=0, columnspan=3, sticky="w")
        ttk.Entry(content, textvariable=project_folder).grid(row=5, column=0, columnspan=2, sticky="ew", pady=(4, 0))

        def browse_folder():
            initial_dir = project_folder.get().strip() or self.project_dir.get().strip() or str(Path.home())
            selected = filedialog.askdirectory(title="Choose Gradle project folder", initialdir=initial_dir, parent=dialog)
            if selected:
                project_folder.set(selected)
                current_name = project_name.get().strip()
                if not current_name or current_name == suggested_name[0]:
                    suggested_name[0] = Path(selected).name
                    project_name.set(suggested_name[0])

        self._button(content, text="Browse…", command=browse_folder).grid(row=5, column=2, sticky="e", padx=(8, 0), pady=(4, 0))
        ttk.Label(
            content,
            text=f"Select the folder containing {self._gradle_wrapper_name()}. The Gradle module defaults to app and can be changed after creation.",
            style="Sub.TLabel",
            wraplength=640,
        ).grid(row=6, column=0, columnspan=3, sticky="w", pady=(8, 0))

        footer = ttk.Frame(dialog, padding=(20, 10, 20, 18))
        footer.grid(row=1, column=0, sticky="ew")
        footer.grid_columnconfigure(0, weight=1)

        def create_profile():
            name = project_name.get().strip()
            if not name:
                messagebox.showerror("Project name required", "Enter a name for this project.", parent=dialog)
                name_entry.focus_set()
                return
            folder_text = project_folder.get().strip()
            if not folder_text:
                messagebox.showerror("Project folder required", "Choose the Gradle project folder.", parent=dialog)
                return
            folder = Path(folder_text).expanduser().resolve()
            wrapper = folder / self._gradle_wrapper_name()
            if not folder.is_dir() or not wrapper.is_file():
                messagebox.showerror(
                    "Gradle project folder required",
                    f"Choose a folder containing {self._gradle_wrapper_name()}:\n{folder}",
                    parent=dialog,
                )
                return
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
            self.apk.set(str(folder / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"))
            self.project_profiles[name] = {
                "name": name,
                "project_dir": str(folder),
                "module": "app",
                "apk": self.apk.get(),
                "package": "",
            }
            self.adb = self._find_adb(str(folder))
            self.project_selector.configure(values=sorted(self.project_profiles))
            self._save_config()
            self.status.set(f"Added project profile: {name}")
            dialog.destroy()

        self._button(footer, text="Cancel", command=dialog.destroy).pack(side="right", padx=(8, 0))
        self._button(footer, text="Create project", style="Accent.TButton", command=create_profile).pack(side="right")
        dialog.bind("<Return>", lambda _event: create_profile())
        dialog.bind("<Escape>", lambda _event: dialog.destroy())
        dialog.grab_set()
        name_entry.focus_set()

    def choose_project_dir(self):
        value = filedialog.askdirectory(title="Choose Gradle project folder", initialdir=self.project_dir.get() or str(Path.home()))
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
        module_dir = Path(self.project_dir.get()).expanduser().joinpath(*parts)
        return module_dir / "build/outputs/apk/debug/app-debug.apk"

    def _set_build_running(self, running):
        self.build_running = running
        self.build_button.configure(
            state="disabled" if running else "normal",
            text=self._icon_text("Building…" if running else "Build APK…", BUTTON_ICONS),
        )
        for widget, idle_state in self.project_edit_widgets:
            widget.configure(state="disabled" if running else idle_state)
        if running:
            if not self.build_status_row.winfo_manager():
                self.build_status_row.pack(fill="x", before=self.status_label, pady=(8, 0))
            self.build_progress.pack(side="right")
            self.build_progress.start(12)
        else:
            self.build_progress.stop()
            self.build_progress.pack_forget()
            self.build_status_row.pack_forget()

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

    def _build_succeeded(self, archived):
        self._set_build_running(False)
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
            self.build_status.set("Build failed · review the Gradle output")
        self.status.set("APK build failed")
        self.log("Build failed. See the error details for the complete Gradle output.")
        self._show_build_error(error)

    @staticmethod
    def _find_java_home():
        """Find a real JDK without invoking macOS's missing-Java stub."""
        candidates = []
        configured_home = __import__("os").environ.get("JAVA_HOME", "").strip()
        if configured_home:
            candidates.append(Path(configured_home).expanduser())
        candidates.extend(Path("/Library/Java/JavaVirtualMachines").glob("*/Contents/Home"))
        for prefix in (Path("/opt/homebrew/opt"), Path("/usr/local/opt")):
            for jdk in sorted(prefix.glob("openjdk*")):
                candidates.extend((jdk / "libexec/openjdk.jdk/Contents/Home", jdk / ""))
        java_on_path = shutil.which("java")
        if java_on_path and Path(java_on_path).resolve() != Path("/usr/bin/java"):
            candidates.append(Path(java_on_path).resolve().parent.parent)

        seen = set()
        for home in candidates:
            home = home.resolve()
            if home in seen:
                continue
            seen.add(home)
            java = home / "bin/java"
            release = home / "release"
            if not java.is_file() or not release.is_file():
                continue
            try:
                version_line = next(line for line in release.read_text().splitlines() if line.startswith("JAVA_VERSION="))
                version = version_line.split("=", 1)[1].strip('"')
                major = int(version.split(".", 1)[0])
            except (OSError, StopIteration, ValueError):
                continue
            if major >= 17:
                return home
        return None

    def build_apk(self):
        if not self.active_project_name.strip():
            messagebox.showerror("Project name required", "Add a named project profile before building.", parent=self)
            return
        project_dir = Path(self.project_dir.get()).expanduser().resolve()
        gradlew = project_dir / self._gradle_wrapper_name()
        if not gradlew.is_file():
            messagebox.showerror(
                "Gradle wrapper missing",
                f"Choose a Gradle project folder containing {self._gradle_wrapper_name()}:\n{gradlew}",
                parent=self,
            )
            return
        build_type = self.build_type.get().strip().lower()
        if build_type not in ("debug", "release"):
            messagebox.showerror("Build type", "Choose debug or release.")
            return
        try:
            module_parts = self._module_parts()
        except ValueError as error:
            messagebox.showerror("Gradle module", str(error))
            return
        java_home = self._find_java_home()
        if java_home is None:
            messagebox.showerror(
                "Java 17 or newer is required",
                "Gradle cannot build this Android app because no Java Development Kit (JDK) 17 or newer was found.\n\n"
                "Install a JDK, then reopen DCM Android Toolkit. The app will detect JAVA_HOME and common macOS JDK locations automatically.",
            )
            self.log("Build stopped: no JDK 17+ found. Install a JDK and reopen DCM Android Toolkit.")
            return
        if not messagebox.askyesno(
            "Build APK",
            f"Build the {build_type} APK for {self.active_project_name}? Gradle may download dependencies the first time.",
            parent=self,
        ):
            return
        self._save_config()
        self._set_build_running(True)
        self.build_status.set(f"Starting {build_type} build for {self.active_project_name}…")
        self.status.set(f"Building {self.active_project_name} ({build_type})…")
        module_label = ":" + ":".join(module_parts) if module_parts else "root project"
        task = f"{module_label}:assemble{build_type.title()}" if module_parts else f"assemble{build_type.title()}"
        output_dir = project_dir.joinpath(*module_parts, "build", "outputs", "apk", build_type)
        self.log(f"Running {task} in {project_dir} with Java {java_home}…")

        def worker():
            process = None
            reader_thread = None
            output_events = queue.Queue()
            output_lines = []
            try:
                build_env = os.environ.copy()
                build_env["JAVA_HOME"] = str(java_home)
                build_env["PATH"] = str(java_home / "bin") + os.pathsep + build_env.get("PATH", "")
                gradle_args = [str(gradlew), task, "--console=plain", "--no-daemon"]
                with self.build_process_lock:
                    if self.closing:
                        return
                    process = subprocess.Popen(
                        gradle_args,
                        cwd=gradlew.parent,
                        env=build_env,
                        shell=(os.name == "nt"),
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        bufsize=1,
                        start_new_session=(os.name != "nt"),
                        creationflags=(subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0),
                    )
                    self.build_process = process

                def read_output():
                    try:
                        for line in process.stdout:
                            output_events.put(line)
                    finally:
                        output_events.put(None)

                reader_thread = threading.Thread(target=read_output, daemon=True)
                reader_thread.start()
                output_finished = False
                deadline = time.monotonic() + 900
                while process.poll() is None or not output_finished:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        self._stop_gradle_process(process)
                        reader_thread.join(timeout=2)
                        raise TimeoutError("Gradle build exceeded the 15-minute time limit.")
                    try:
                        line = output_events.get(timeout=min(0.2, remaining))
                    except queue.Empty:
                        continue
                    if line is None:
                        output_finished = True
                        continue
                    output_lines.append(line)
                    clean_line = line.rstrip()
                    if clean_line and not self.closing:
                        self.after(0, self._build_output_received, clean_line)
                return_code = process.wait()
                self._stop_gradle_process(process)
                reader_thread.join(timeout=2)
                with self.build_process_lock:
                    if self.build_process is process:
                        self.build_process = None
                output = "".join(output_lines).strip()
                if return_code:
                    raise RuntimeError(output or f"Gradle exited with {return_code}")
                apks = sorted(output_dir.rglob("*.apk")) if output_dir.is_dir() else []
                if not apks:
                    raise RuntimeError(f"Gradle finished but no APK was found under {output_dir}.")
                archived = self._archive_built_apks(apks, build_type)
                if not self.closing:
                    self.after(0, self._build_succeeded, archived)
            except Exception as e:
                if process and process.poll() is None:
                    self._stop_gradle_process(process)
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
        dialog = tk.Toplevel(self)
        dialog.title("APK build failed")
        dialog.configure(background="#f4f7f5")
        dialog.transient(self)
        window_width, _window_height = self._fit_dialog(dialog, preferred=(1100, 850), minimum=(640, 480))
        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(1, weight=1)

        header = ttk.Frame(dialog, padding=(18, 18, 18, 12))
        header.grid(row=0, column=0, sticky="ew")
        ttk.Label(header, text="APK build failed", style="Title.TLabel").pack(anchor="w", pady=(0, 8))
        ttk.Label(
            header,
            text="Review the Gradle output below. You can scroll through it or close this window to return to DCM Android Toolkit.",
            style="Sub.TLabel",
            wraplength=min(900, window_width - 60),
        ).pack(anchor="w")

        body = ttk.Frame(dialog)
        body.grid(row=1, column=0, sticky="nsew", padx=18)
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=1)
        output = tk.Text(
            body,
            wrap="none",
            bg="#102a3a",
            fg="#d9eeea",
            insertbackground="white",
            selectbackground="#087e78",
            relief="flat",
            font=("Menlo", 10),
            padx=12,
            pady=10,
        )
        y_scroll = ttk.Scrollbar(body, orient="vertical", command=output.yview)
        x_scroll = ttk.Scrollbar(body, orient="horizontal", command=output.xview)
        output.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        output.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        output.insert("1.0", error)
        output.configure(state="disabled")

        footer = ttk.Frame(dialog, padding=(18, 12, 18, 18))
        footer.grid(row=2, column=0, sticky="ew")

        def copy_output():
            dialog.clipboard_clear()
            dialog.clipboard_append(error)
            dialog.update_idletasks()
            self.status.set("Full Gradle output copied to clipboard")
            self.log("Copied the full Gradle failure output to the clipboard.")

        self._button(footer, text="Copy all output", command=copy_output).pack(side="right", padx=(0, 8))
        self._button(footer, text="Close", command=dialog.destroy).pack(side="right")
        dialog.bind("<Escape>", lambda _event: dialog.destroy())

    def _choose_built_apk(self, apks):
        self.status.set(f"Build archived · {len(apks)} APK version(s) available")
        dialog = tk.Toplevel(self)
        dialog.title("Choose APK to install")
        dialog.transient(self)
        dialog.grab_set()
        dialog.configure(background="#f4f7f5")
        self._fit_dialog(dialog, preferred=(900, 560), minimum=(600, 420))
        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(1, weight=1)
        ttk.Label(dialog, text="Build archived. Choose this build to push now; it will remain in Version history:", wraplength=760).grid(row=0, column=0, sticky="w", padx=18, pady=(18, 10))
        listing = tk.Listbox(
            dialog,
            height=7,
            font=("Menlo", 10),
            selectmode="browse",
            background="#ffffff",
            foreground="#173342",
            selectbackground="#087e78",
            selectforeground="#ffffff",
            activestyle="none",
            highlightthickness=1,
            highlightbackground="#d4ded9",
            highlightcolor="#087e78",
            relief="flat",
        )
        listing.grid(row=1, column=0, sticky="nsew", padx=18)
        for entry in apks:
            listing.insert("end", self._version_label(entry))
        listing.selection_set(0)
        listing.activate(0)

        def use_and_install():
            selection = listing.curselection()
            if not selection:
                messagebox.showinfo("Choose an APK", "Select an APK from the list.", parent=dialog)
                return
            self.apk.set(str(APP_ROOT / apks[selection[0]]["apk"]))
            self._save_config()
            dialog.destroy()
            if not self.connected_serial:
                messagebox.showinfo("APK ready", "APK selected. Connect and select a device, then click Install / overwrite.")
                return
            if messagebox.askyesno("Install selected APK?", f"Install this APK on {self.connected_serial}?\n\n{self.apk.get()}"):
                self.install()

        buttons = ttk.Frame(dialog, padding=(18, 12, 18, 16)); buttons.grid(row=2, column=0, sticky="ew")
        self._button(buttons, text="Use this APK and install…", style="Accent.TButton", command=use_and_install).pack(side="right")
        self._button(buttons, text="Cancel", command=dialog.destroy).pack(side="right", padx=8)

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
        dialog = tk.Toplevel(self)
        dialog.title("APK version history")
        dialog.transient(self)
        dialog.configure(background="#f4f7f5")
        self._fit_dialog(dialog, preferred=(1280, 760), minimum=(760, 480))
        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(1, weight=1)

        heading = ttk.Frame(dialog, padding=(18, 16, 18, 12))
        heading.grid(row=0, column=0, sticky="ew")
        ttk.Label(heading, text="APK version history", style="Title.TLabel").pack(side="left")
        count_label = ttk.Label(heading, text="", style="Sub.TLabel")
        count_label.pack(side="right")

        style = ttk.Style(dialog)
        style.configure("History.Treeview", background="#ffffff", fieldbackground="#ffffff", foreground="#173342", rowheight=28, font=("Helvetica Neue", 10))
        style.map("History.Treeview", background=[("selected", "#087e78")], foreground=[("selected", "#ffffff")])
        style.configure("History.Treeview.Heading", background="#e3eae7", foreground="#173342", font=("Helvetica Neue", 10, "bold"))
        table_frame = ttk.Frame(dialog, style="Card.TFrame", padding=8)
        table_frame.grid(row=1, column=0, sticky="nsew", padx=18)
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        columns = ("project", "version", "code", "type", "built", "file", "note")
        table = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse", style="History.Treeview")
        for col, label, col_width in (("project", "Project", 130), ("version", "Version", 120), ("code", "Code", 60), ("type", "Build", 65), ("built", "Built (local time)", 185), ("file", "Archived APK", 300), ("note", "Internal note", 220)):
            table.heading(col, text=label)
            table.column(col, width=col_width, anchor="w")
        table.grid(row=0, column=0, sticky="nsew")
        yscroll = ttk.Scrollbar(table_frame, orient="vertical", command=table.yview)
        yscroll.grid(row=0, column=1, sticky="ns")
        table.configure(yscrollcommand=yscroll.set)
        keys = {}
        action_buttons = {}

        def archive_path(entry):
            if entry is None:
                return None
            path = (APP_ROOT / entry.get("apk", "")).resolve()
            if path.parent != APK_ARCHIVE.resolve() or path.suffix.lower() != ".apk":
                return None
            return path

        def update_action_states(_event=None):
            if not action_buttons:
                return
            entry = selected_entry()
            selected = entry is not None
            file_path = archive_path(entry)
            existing_file = bool(file_path and file_path.is_file())
            for name in ("remove", "note"):
                action_buttons[name].configure(state="normal" if selected else "disabled")
            for name in ("show", "copy", "install"):
                action_buttons[name].configure(state="normal" if existing_file else "disabled")

        def save_history():
            APK_HISTORY.parent.mkdir(parents=True, exist_ok=True)
            temp = APK_HISTORY.with_suffix(APK_HISTORY.suffix + ".tmp")
            temp.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            temp.replace(APK_HISTORY)

        def refresh_table(select_path=None):
            nonlocal entries
            entries = sorted(self._load_apk_history(), key=lambda item: item.get("built_at_utc", ""), reverse=True)
            table.delete(*table.get_children())
            keys.clear()
            target = None
            for index, entry in enumerate(entries):
                iid = f"apk{index}"
                keys[iid] = entry
                table.insert("", "end", iid=iid, values=(entry.get("project_name", "Legacy APK"), entry.get("version_name", "unknown"), entry.get("version_code", ""), entry.get("build_type", ""), self._format_local_timestamp(entry.get("built_at_utc", "")), Path(entry["apk"]).name, entry.get("note", "")))
                if entry.get("apk") == select_path:
                    target = iid
            if target is None and table.get_children():
                target = table.get_children()[0]
            if target:
                table.selection_set(target)
                table.focus(target)
            count_label.configure(text=f"Archived APK builds · {len(entries)} version(s)")
            update_action_states()

        refresh_table()

        def selected_entry():
            selected = table.selection()
            return keys.get(selected[0]) if selected else None

        def edit_note():
            entry = selected_entry()
            if entry is None:
                messagebox.showinfo("Select a build", "Select a build to add or edit its note.", parent=dialog)
                return
            note_dialog = tk.Toplevel(dialog)
            note_dialog.title("Build note")
            note_dialog.transient(dialog)
            note_dialog.configure(background="#f4f7f5")
            self._fit_dialog(note_dialog, preferred=(760, 620), minimum=(520, 420))
            note_dialog.grid_columnconfigure(0, weight=1)
            note_dialog.grid_rowconfigure(1, weight=1)
            ttk.Label(note_dialog, text=f"Internal note · {entry.get('version_name', 'build')}", style="Title.TLabel", wraplength=680).grid(row=0, column=0, sticky="w", padx=18, pady=(18, 10))
            note = tk.Text(note_dialog, wrap="word", bg="#ffffff", fg="#173342", insertbackground="#173342", font=("Helvetica Neue", 11), padx=10, pady=8, relief="flat", highlightthickness=1, highlightbackground="#d4ded9")
            note.grid(row=1, column=0, sticky="nsew", padx=18)
            note.insert("1.0", entry.get("note", ""))
            actions = ttk.Frame(note_dialog, padding=(18, 12, 18, 18))
            actions.grid(row=2, column=0, sticky="ew")

            def save_note():
                entry["note"] = note.get("1.0", "end-1c").strip()
                try:
                    save_history()
                except OSError as error:
                    messagebox.showerror("Could not save note", str(error), parent=note_dialog)
                    return
                path = entry["apk"]
                refresh_table(path)
                note_dialog.destroy()

            self._button(actions, text="Save note", style="Accent.TButton", command=save_note).pack(side="right")
            self._button(actions, text="Cancel", command=note_dialog.destroy).pack(side="right", padx=8)

        def remove_selected():
            nonlocal entries
            entry = selected_entry()
            if entry is None:
                messagebox.showinfo("Select a build", "Select a build to remove.", parent=dialog)
                return
            path = archive_path(entry)
            if path is None:
                messagebox.showerror("Invalid archive entry", "This entry does not point to an APK in the local build archive.", parent=dialog)
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
                messagebox.showerror("Could not remove build", str(error), parent=dialog)

        def remove_all():
            nonlocal entries
            archive = APK_ARCHIVE.resolve()
            try:
                builds = [path for path in archive.glob("*.apk") if path.is_file()]
            except OSError as error:
                messagebox.showerror("Could not list builds", str(error), parent=dialog)
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
                messagebox.showerror("Could not remove all builds", str(error), parent=dialog)

        def use_selected():
            entry = selected_entry()
            path = archive_path(entry)
            if path is None or not path.is_file():
                messagebox.showinfo("Choose an APK", "Select an archived APK file that still exists.", parent=dialog)
                return
            self.apk.set(str(path))
            self._save_config()
            dialog.destroy()
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
                messagebox.showerror("Could not open folder", str(error), parent=dialog)

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
                messagebox.showerror("Could not copy APK", str(error), parent=dialog)

        table.bind("<<TreeviewSelect>>", update_action_states, add="+")
        buttons = ttk.Frame(dialog, padding=(18, 12, 18, 16))
        buttons.grid(row=2, column=0, sticky="ew")
        row_actions = ttk.Frame(buttons)
        row_actions.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        file_actions = ttk.Frame(buttons)
        file_actions.grid(row=1, column=0, sticky="w")
        dialog_actions = ttk.Frame(buttons)
        dialog_actions.grid(row=1, column=1, sticky="e")
        buttons.grid_columnconfigure(0, weight=1)
        self._button(row_actions, text="Remove all builds", style="Danger.TButton", command=remove_all).pack(side="left")
        action_buttons["remove"] = self._button(row_actions, text="Remove build", style="Danger.TButton", command=remove_selected)
        action_buttons["remove"].pack(side="left", padx=8)
        action_buttons["note"] = self._button(row_actions, text="Add / edit note…", command=edit_note)
        action_buttons["note"].pack(side="left")
        action_buttons["copy"] = self._button(file_actions, text="Copy APK…", command=copy_selected_file)
        action_buttons["copy"].pack(side="left")
        action_buttons["show"] = self._button(file_actions, text="Show in folder", command=show_selected_file)
        action_buttons["show"].pack(side="left", padx=(8, 0))
        action_buttons["install"] = self._button(dialog_actions, text="Select and install…", style="Accent.TButton", command=use_selected)
        action_buttons["install"].pack(side="right")
        self._button(dialog_actions, text="Close", command=dialog.destroy).pack(side="right", padx=8)
        update_action_states()

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
        self.count_button.configure(state="disabled")
        self.preview_button.configure(state="disabled")
        self.export_button.configure(state="disabled")
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
                self.after(0, lambda: messagebox.showerror("SMS count check failed", error))
            finally:
                self.after(0, lambda: self.count_button.configure(state="normal"))
                self.after(0, lambda: self.preview_button.configure(state="normal"))
                self.after(0, lambda: self.export_button.configure(state="normal"))

        threading.Thread(target=worker, daemon=True).start()

    def preview_sms(self):
        serial = (self.connected_serial or "").strip()
        if not serial:
            messagebox.showinfo("Choose a device", "Connect an authorized device on the Connection tab first.")
            return
        self.count_button.configure(state="disabled")
        self.preview_button.configure(state="disabled")
        self.export_button.configure(state="disabled")
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
                self.after(0, lambda: messagebox.showerror("SMS content preview failed", error))
            finally:
                self.after(0, lambda: self.count_button.configure(state="normal"))
                self.after(0, lambda: self.preview_button.configure(state="normal"))
                self.after(0, lambda: self.export_button.configure(state="normal"))

        threading.Thread(target=worker, daemon=True).start()

    def _show_sms_preview(self, preview_json, count):
        dialog = tk.Toplevel(self)
        dialog.title("SMS content preview")
        dialog.transient(self)
        self._fit_dialog(dialog, preferred=(1000, 900), minimum=(600, 560))
        dialog.configure(background="#f4f7f5")
        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(0, weight=1)
        panel = ttk.Frame(dialog, style="TFrame", padding=20)
        panel.grid(row=0, column=0, sticky="nsew")
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(2, weight=1)
        ttk.Label(panel, text=f"Read and parsed {count} SMS message(s)", style="Title.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 6))
        ttk.Label(panel, text="This local preview is not saved. Message bodies may contain private information.", style="Sub.TLabel", wraplength=700).grid(row=1, column=0, sticky="w", pady=(0, 14))
        text_frame = ttk.Frame(panel, style="Card.TFrame", padding=8)
        text_frame.grid(row=2, column=0, sticky="nsew")
        content = tk.Text(text_frame, wrap="word", bg="#ffffff", fg="#173342", insertbackground="#173342", selectbackground="#cfe8df", font=("Menlo", 10), padx=12, pady=10, relief="flat", highlightthickness=0)
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=content.yview)
        content.configure(yscrollcommand=scrollbar.set)
        content.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        content.insert("1.0", preview_json)
        content.configure(state="disabled")
        actions = ttk.Frame(panel, style="TFrame")
        actions.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        tk.Button(
            actions,
            text=self._icon_text("Close", BUTTON_ICONS),
            command=dialog.destroy,
            fg="#000000",
            bg="#e3eae7",
            activeforeground="#000000",
            activebackground="#d0ddd7",
            font=("Helvetica Neue", 10, "bold"),
            padx=20,
            pady=10,
            relief="raised",
            cursor="arrow",
        ).pack(side="right")

    def _require_device_online(self, serial):
        result = subprocess.run([self.adb, "devices"], capture_output=True, text=True, timeout=15)
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
        self.export_button.configure(state="disabled")
        self.count_button.configure(state="disabled")
        self.preview_button.configure(state="disabled")
        self.status.set("Starting SMS export…")
        self.log(f"SMS export started for {serial}. Watch the phone for an 'Allow USB debugging' prompt and accept it if shown. Reading the message index…")

        def report(message, status=None):
            self.after(0, lambda: self.log(message))
            if status:
                self.after(0, lambda: self.status.set(status))

        def run_export_adb(*args):
            return subprocess.run([self.adb, *args], capture_output=True, text=True, timeout=60)

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
                self.after(0, lambda: messagebox.showerror("SMS export needs attention", error))
            finally:
                self.after(0, lambda: self.export_button.configure(state="normal"))
                self.after(0, lambda: self.count_button.configure(state="normal"))
                self.after(0, lambda: self.preview_button.configure(state="normal"))

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
            messagebox.showerror("APK missing", f"Could not find APK:\n{apk}")
            return
        package = self.package.get().strip()
        if not package or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+", package):
            messagebox.showerror("Invalid package name", "Enter the installed app's package name (for example, com.example.app) so DCM Android Toolkit can open it after installation.")
            return
        if not self.connected_serial:
            messagebox.showinfo("Choose a device", "Connect an authorized device on the Connection tab first.")
            return
        serial = self.connected_serial
        self._save_config()
        self._async_action("Installing APK with replacement…", lambda: self._install_and_launch(serial, apk, package))

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
            messagebox.showerror("Package name required", "Enter the Android package name to remove.")
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
        self._save_profile_values()
        CONFIG.write_text(json.dumps({
            "selected_project": self.active_project_name,
            "projects": list(self.project_profiles.values()),
            "fixed_wifi": self.fixed_wifi.get().strip(),
            "use_fixed_wifi": self.use_fixed_wifi.get(),
            "connection_method": self.connection_method.get(),
            "last_device": self.connected_serial or self.last_device,
            "last_device_method": self.last_device_method,
            "brightness_level": self.brightness_level.get(),
            "brightness_level_unit": "percent",
            "pending_display_settings": self.pending_display_settings,
        }, indent=2) + "\n")


if __name__ == "__main__":
    Deployer().mainloop()
