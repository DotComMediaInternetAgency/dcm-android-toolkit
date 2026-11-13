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
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

APP_ROOT = Path(__file__).resolve().parent
HERE = APP_ROOT
CONFIG = APP_ROOT / "dcm-android-toolkit.json"
ERROR_LOG = APP_ROOT / "data" / "logs" / "application-errors.log"
MAX_ERROR_LOG_BYTES = 512 * 1024
APK_ARCHIVE = APP_ROOT / "data" / "apk_versions"
APK_HISTORY = APP_ROOT / "data" / "apk_versions.json"
APP_VERSION = "0.1.4.9"
GITHUB_REPOSITORY = "DotComMediaInternetAgency/dcm-android-toolkit"
BUG_REPORT_EMAIL = "dotcommediainternetagency@gmail.com"

UI_COLORS = {
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
    "danger_border": "#fecaca",
    "high_fg": "#c83932",
    "pill_ok_bg": "#dcfce7",
    "pill_ok_fg": "#166534",
    "pill_idle_bg": "#e2e8f0",
    "pill_idle_fg": "#475569",
    "console_bg": "#0f172a",
    "console_fg": "#e2e8f0",
    "console_error": "#fca5a5",
    "console_warn": "#fcd34d",
    "console_success": "#86efac",
}


ICON_PATHS = {
    "link": [
        ("line", 10, 13, 14, 10),
        ("poly", [(15, 7), (17, 5), (20, 8), (18, 10)], False),
        ("poly", [(9, 17), (7, 19), (4, 16), (6, 14)], False),
        ("line", 14, 10, 17, 13),
        ("line", 7, 11, 10, 14),
    ],
    "wifi": [
        ("arc", 12, 18, 11, 225, 315),
        ("arc", 12, 18, 7.5, 225, 315),
        ("arc", 12, 18, 4, 225, 315),
        ("circle", 12, 19, 1.2),
    ],
    "package": [
        ("poly", [(12, 3), (20, 7.5), (20, 16.5), (12, 21), (4, 16.5), (4, 7.5)], True),
        ("line", 12, 12, 20, 7.5),
        ("line", 12, 12, 4, 7.5),
        ("line", 12, 12, 12, 21),
    ],
    "mail": [
        ("rect", 3, 5, 18, 14, 2),
        ("poly", [(3.5, 6.5), (12, 13), (20.5, 6.5)], False),
    ],
    "search": [
        ("circle", 10.5, 10.5, 6.5),
        ("line", 15.5, 15.5, 20.5, 20.5),
    ],
    "monitor": [
        ("rect", 2.5, 3.5, 19, 13, 2),
        ("line", 8, 20.5, 16, 20.5),
        ("line", 12, 16.5, 12, 20.5),
    ],
    "smartphone": [
        ("rect", 6, 2.5, 12, 19, 2),
        ("line", 11, 18, 13, 18),
    ],
    "sliders": [
        ("line", 4, 6, 20, 6),
        ("line", 4, 12, 20, 12),
        ("line", 4, 18, 20, 18),
        ("circle", 8, 6, 2),
        ("circle", 15, 12, 2),
        ("circle", 10, 18, 2),
    ],
    "info": [
        ("circle", 12, 12, 9),
        ("line", 12, 11.5, 12, 16.5),
        ("circle", 12, 8, 0.9),
    ],
    "refresh": [
        ("arc", 12, 12, 7.5, 35, 325),
        ("poly", [(16.5, 5.5), (19.5, 5.5), (19.5, 8.5)], False),
    ],
    "external": [
        ("poly", [(14, 4), (20, 4), (20, 10)], False),
        ("line", 10, 14, 20, 4),
        ("poly", [(18, 13), (18, 19), (5, 19), (5, 6), (11, 6)], False),
    ],
    "flag": [
        ("line", 5, 3, 5, 21),
        ("poly", [(5, 4), (19, 4), (16, 8.5), (19, 13), (5, 13)], False),
    ],
    "copy": [
        ("rect", 9, 9, 11, 11, 2),
        ("poly", [(6, 15), (4.5, 15), (4.5, 5), (15, 5), (15, 6.5)], False),
    ],
    "play": [
        ("poly", [(7, 4.5), (19, 12), (7, 19.5)], True),
    ],
    "stop": [
        ("rect", 5.5, 5.5, 13, 13, 2),
    ],
    "download": [
        ("line", 12, 4, 12, 15),
        ("poly", [(7.5, 10.5), (12, 15), (16.5, 10.5)], False),
        ("poly", [(4, 16.5), (4, 19.5), (20, 19.5), (20, 16.5)], False),
    ],
    "upload": [
        ("line", 12, 15, 12, 4),
        ("poly", [(7.5, 8.5), (12, 4), (16.5, 8.5)], False),
        ("poly", [(4, 16.5), (4, 19.5), (20, 19.5), (20, 16.5)], False),
    ],
    "crosshair": [
        ("circle", 12, 12, 7.5),
        ("line", 12, 2.5, 12, 6),
        ("line", 12, 18, 12, 21.5),
        ("line", 2.5, 12, 6, 12),
        ("line", 18, 12, 21.5, 12),
    ],
    "sun": [
        ("circle", 12, 12, 4),
        ("line", 12, 2.5, 12, 5),
        ("line", 12, 19, 12, 21.5),
        ("line", 2.5, 12, 5, 12),
        ("line", 19, 12, 21.5, 12),
        ("line", 5.3, 5.3, 7.1, 7.1),
        ("line", 16.9, 16.9, 18.7, 18.7),
        ("line", 5.3, 18.7, 7.1, 16.9),
        ("line", 16.9, 7.1, 18.7, 5.3),
    ],
    "disconnect": [
        ("circle", 12, 12, 8.5),
        ("line", 6.2, 6.2, 17.8, 17.8),
    ],
    "save": [
        ("poly", [(5, 4), (16.5, 4), (19.5, 7), (19.5, 20), (5, 20)], True),
        ("rect", 8, 13, 8, 7, 0.5),
        ("rect", 8.5, 4, 6, 4.5, 0.5),
    ],
    "plus": [
        ("line", 12, 5, 12, 19),
        ("line", 5, 12, 19, 12),
    ],
    "folder": [
        ("poly", [(3.5, 6), (9.5, 6), (11.5, 8.5), (20.5, 8.5), (20.5, 18.5), (3.5, 18.5)], True),
    ],
    "history": [
        ("arc", 12, 12, 8, 25, 315),
        ("poly", [(4.5, 5.5), (4.5, 9.5), (8.5, 9.5)], False),
        ("line", 12, 7.5, 12, 12),
        ("line", 12, 12, 15.5, 14),
    ],
    "trash": [
        ("line", 4.5, 6.5, 19.5, 6.5),
        ("line", 9.5, 4, 14.5, 4),
        ("poly", [(6.5, 6.5), (7.5, 19.5), (16.5, 19.5), (17.5, 6.5)], False),
        ("line", 10, 10, 10, 16),
        ("line", 14, 10, 14, 16),
    ],
    "list": [
        ("line", 8, 6.5, 20, 6.5),
        ("line", 8, 12, 20, 12),
        ("line", 8, 17.5, 20, 17.5),
        ("circle", 4.5, 6.5, 1),
        ("circle", 4.5, 12, 1),
        ("circle", 4.5, 17.5, 1),
    ],
    "eye": [
        ("arc", 12, 16, 10, 220, 320),
        ("arc", 12, 8, 10, 40, 140),
        ("circle", 12, 12, 2.6),
    ],
    "close": [
        ("line", 6, 6, 18, 18),
        ("line", 18, 6, 6, 18),
    ],
    "edit": [
        ("poly", [(15.5, 4.5), (19.5, 8.5), (9, 19), (4.5, 19.5), (5, 15)], True),
        ("line", 13.5, 6.5, 17.5, 10.5),
    ],
    "sparkles": [
        ("line", 12, 3.5, 12, 10.5),
        ("line", 8.5, 7, 15.5, 7),
        ("line", 6, 14, 6, 19),
        ("line", 3.5, 16.5, 8.5, 16.5),
        ("line", 17.5, 13, 17.5, 19),
        ("line", 14.5, 16, 20.5, 16),
    ],
    "rotate_ccw": [
        ("arc", 12, 12, 7.5, 30, 310),
        ("poly", [(4.5, 5.5), (4.5, 9.5), (8.5, 9.5)], False),
    ],
}


class VectorIconLibrary:
    """Renders crisp anti-aliased Lucide-style 24x24 vector icons into tk.PhotoImage."""

    def __init__(self):
        self._cache = {}

    @staticmethod
    def _dist_seg(px, py, x1, y1, x2, y2):
        dx = x2 - x1
        dy = y2 - y1
        len_sq = dx * dx + dy * dy
        if len_sq == 0:
            return math.hypot(px - x1, py - y1)
        t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / len_sq))
        return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))

    @staticmethod
    def _dist_rect(px, py, x, y, w, h, rx):
        cx = x + w * 0.5
        cy = y + h * 0.5
        hw = max(0.0, w * 0.5 - rx)
        hh = max(0.0, h * 0.5 - rx)
        qx = abs(px - cx) - hw
        qy = abs(py - cy) - hh
        outside = math.hypot(max(qx, 0.0), max(qy, 0.0))
        inside = min(max(qx, qy), 0.0)
        return abs(outside + inside - rx)

    @staticmethod
    def _dist_arc(px, py, cx, cy, r, start_deg, end_deg):
        ang = math.degrees(math.atan2(py - cy, px - cx)) % 360.0
        s = start_deg % 360.0
        e = end_deg % 360.0
        in_arc = (s <= ang <= e) if s <= e else (ang >= s or ang <= e)
        if in_arc:
            return abs(math.hypot(px - cx, py - cy) - r)
        sx = cx + r * math.cos(math.radians(start_deg))
        sy = cy + r * math.sin(math.radians(start_deg))
        ex = cx + r * math.cos(math.radians(end_deg))
        ey = cy + r * math.sin(math.radians(end_deg))
        return min(math.hypot(px - sx, py - sy), math.hypot(px - ex, py - ey))

    def _dist_shape(self, px, py, shape):
        kind = shape[0]
        if kind == "line":
            return self._dist_seg(px, py, shape[1], shape[2], shape[3], shape[4])
        if kind == "poly":
            pts, closed = shape[1], shape[2]
            best = 1e9
            count = len(pts)
            limit = count if closed else count - 1
            for idx in range(limit):
                x1, y1 = pts[idx]
                x2, y2 = pts[(idx + 1) % count]
                d = self._dist_seg(px, py, x1, y1, x2, y2)
                if d < best:
                    best = d
            return best
        if kind == "rect":
            return self._dist_rect(px, py, shape[1], shape[2], shape[3], shape[4], shape[5])
        if kind == "circle":
            return abs(math.hypot(px - shape[1], py - shape[2]) - shape[3])
        if kind == "arc":
            return self._dist_arc(px, py, shape[1], shape[2], shape[3], shape[4], shape[5])
        return 1e9

    @staticmethod
    def _encode_png(width, height, rgba_bytes):
        def chunk(tag, data):
            return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

        stride = width * 4
        raw = b"".join(b"\x00" + rgba_bytes[y * stride : (y + 1) * stride] for y in range(height))
        ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
        return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b"")

    def get(self, name, color="#0f172a", size=15):
        key = (name, color, size)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        shapes = ICON_PATHS.get(name)
        if not shapes:
            return None
        hex_color = color.lstrip("#")
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        scale = 24.0 / size
        half_stroke = 1.05
        aa = 0.85 * scale
        buf = bytearray(size * size * 4)
        idx = 0
        for py in range(size):
            vy = (py + 0.5) * scale
            for px in range(size):
                vx = (px + 0.5) * scale
                d = 1e9
                for shape in shapes:
                    sd = self._dist_shape(vx, vy, shape)
                    if sd < d:
                        d = sd
                cov = max(0.0, min(1.0, (half_stroke + aa * 0.5 - d) / aa))
                buf[idx] = r
                buf[idx + 1] = g
                buf[idx + 2] = b
                buf[idx + 3] = int(cov * 255)
                idx += 4
        img = tk.PhotoImage(data=self._encode_png(size, size, bytes(buf)))
        self._cache[key] = img
        return img


class SidebarNavigator:
    """Left navigation rail implementing the subset of ttk.Notebook used by Deployer."""

    def __init__(self, rail_parent, stage_parent):
        self.rail_parent = rail_parent
        self.stage_parent = stage_parent
        self._pages = []
        self._id_to_index = {}
        self._nav_items = []
        self._current_index = None
        self._change_callbacks = []

    def add_section(self, title):
        top_pad = 14 if self._nav_items else 6
        label = tk.Label(
            self.rail_parent,
            text=title.upper(),
            bg=UI_COLORS["bg_surface"],
            fg=UI_COLORS["text_muted"],
            font=("Helvetica Neue", 9, "bold"),
            anchor="w",
            padx=14,
            pady=4,
        )
        label.pack(fill="x", pady=(top_pad, 2))

    def add(self, page, text="", icon=None, active_icon=None):
        page_id = str(page)
        index = len(self._pages)
        self._pages.append((page_id, page))
        self._id_to_index[page_id] = index

        row = tk.Frame(self.rail_parent, bg=UI_COLORS["bg_surface"], cursor="hand2")
        row.pack(fill="x", padx=8, pady=1)

        indicator = tk.Frame(row, bg=UI_COLORS["bg_surface"], width=3)
        indicator.pack(side="left", fill="y")

        label_text = f"  {text}" if icon is not None else text
        btn = tk.Label(
            row,
            text=label_text,
            image=icon if icon is not None else "",
            compound="left",
            bg=UI_COLORS["bg_surface"],
            fg=UI_COLORS["text_secondary"],
            font=("Helvetica Neue", 11),
            anchor="w",
            padx=10,
            pady=8,
        )
        btn.pack(side="left", fill="x", expand=True)

        def on_click(_event=None, idx=index):
            self.select(idx)

        def on_enter(_event=None, idx=index):
            if self._current_index != idx:
                row.configure(bg=UI_COLORS["bg_nav_hover"])
                indicator.configure(bg=UI_COLORS["bg_nav_hover"])
                btn.configure(bg=UI_COLORS["bg_nav_hover"])

        def on_leave(_event=None, idx=index):
            if self._current_index != idx:
                row.configure(bg=UI_COLORS["bg_surface"])
                indicator.configure(bg=UI_COLORS["bg_surface"])
                btn.configure(bg=UI_COLORS["bg_surface"])

        for widget in (row, indicator, btn):
            widget.bind("<Button-1>", on_click)
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)

        self._nav_items.append((row, indicator, btn, icon, active_icon or icon))
        if self._current_index is None:
            self.select(0)

    def select(self, target=None):
        if target is None:
            if self._current_index is None:
                return ""
            return self._pages[self._current_index][0]
        if isinstance(target, int):
            index = target
        else:
            index = self._id_to_index.get(str(target))
        if index is None or not (0 <= index < len(self._pages)):
            return ""
        if self._current_index == index:
            return self._pages[index][0]

        if self._current_index is not None:
            self._pages[self._current_index][1].pack_forget()
        self._current_index = index
        self._pages[index][1].pack(in_=self.stage_parent, fill="both", expand=True)

        for idx, (row, indicator, btn, icon, active_icon) in enumerate(self._nav_items):
            if idx == index:
                row.configure(bg=UI_COLORS["bg_nav_active"])
                indicator.configure(bg=UI_COLORS["accent"])
                btn.configure(
                    bg=UI_COLORS["bg_nav_active"],
                    fg=UI_COLORS["accent"],
                    font=("Helvetica Neue", 11, "bold"),
                    image=active_icon if active_icon is not None else "",
                )
            else:
                row.configure(bg=UI_COLORS["bg_surface"])
                indicator.configure(bg=UI_COLORS["bg_surface"])
                btn.configure(
                    bg=UI_COLORS["bg_surface"],
                    fg=UI_COLORS["text_secondary"],
                    font=("Helvetica Neue", 11),
                    image=icon if icon is not None else "",
                )

        for cb in self._change_callbacks:
            cb(None)
        return self._pages[index][0]

    def bind(self, sequence, callback, add=None):
        if sequence == "<<NotebookTabChanged>>":
            self._change_callbacks.append(callback)
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

TAB_ICONS = {
    "connection": "link",
    "apk": "package",
    "sms export": "mail",
    "subnet scan": "search",
    "watch screen": "monitor",
    "emulator": "smartphone",
    "debug": "sliders",
    "about": "info",
}

BUTTON_ICONS = {
    "checking…": "refresh",
    "building…": "refresh",
    "check for updates": "refresh",
    "website": "external",
    "report a bug…": "flag",
    "copy email address": "copy",
    "refresh": "refresh",
    "refresh emulators": "refresh",
    "start emulator": "play",
    "stop emulator": "stop",
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
    "disconnect": "disconnect",
    "save project": "save",
    "add project…": "plus",
    "browse…": "folder",
    "choose…": "folder",
    "build apk…": "play",
    "version history…": "history",
    "install / overwrite": "download",
    "remove app from device": "trash",
    "choose output folder…": "folder",
    "read sms count": "list",
    "preview 2 sms": "eye",
    "export sms to json": "upload",
    "scan subnet": "search",
    "open screen window": "monitor",
    "copy all output": "copy",
    "close": "close",
    "use this apk and install…": "download",
    "cancel": "close",
    "save note": "edit",
    "remove all builds": "trash",
    "remove build": "trash",
    "add / edit note…": "edit",
    "copy apk…": "copy",
    "show in folder": "folder",
    "select and install…": "download",
    "scan debug state": "search",
    "clean stale temporary files…": "sparkles",
    "remove emulator package…": "trash",
    "remove bootstrap tools…": "trash",
    "clear apk history…": "trash",
    "reset settings and profiles…": "rotate_ccw",
    "export diagnostic report and error log…": "upload",
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
        width, height = min(1080, max(320, screen_width - 64)), min(900, max(360, screen_height - 96))
        self.geometry(f"{width}x{height}+{max(0, (screen_width-width)//2)}+{max(0, (screen_height-height)//2)}")
        self.minsize(min(720, width), min(620, height))
        self.configure(bg=UI_COLORS["bg_canvas"])
        self._icons = VectorIconLibrary()
        self.config_data = load_config()
        self.error_log_lock = threading.Lock()
        self.recent_errors = []
        self.report_callback_exception = self._report_callback_exception
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
        self.project_name = tk.StringVar(value=self.active_project_name)
        self.project_dir = tk.StringVar(value=str(active_project.get("project_dir", "")))
        self.module = tk.StringVar(value=str(active_project.get("module", "app")))
        self.apk = tk.StringVar(value=str(active_project.get("apk", "")))
        self.package = tk.StringVar(value=str(active_project.get("package", "")))
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
        self.target = tk.StringVar()
        self.install_target = tk.StringVar(value=self.config_data.get("install_target", ""))
        self.available_device_serials = []
        self.install_target_serials = {}
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
        self.emulator_avd = tk.StringVar()
        self.emulator_status = tk.StringVar(value="Checking for Android Emulator…")
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
        self.status = tk.StringVar(value="ADB found" if self.adb else "ADB not found — install Android SDK Platform-Tools")
        self._style()
        self._build()
        self.after(250, self.refresh_emulators)
        self.after(1200, lambda: self.check_for_updates(manual=False))
        if self.adb:
            self.after(150, self.restore_previous_device)

    @staticmethod
    def _version_tuple(value):
        match = re.search(r"(?:^|[^0-9])v?(\d+(?:\.\d+)+)", str(value))
        if not match:
            return None
        parts = [int(part) for part in match.group(1).split(".")]
        return tuple(parts + [0] * max(0, 4 - len(parts)))

    @staticmethod
    def _icon_text(text, icons):
        return str(text)

    def _icon_for_label(self, text, icons, color="#0f172a", size=15):
        label = str(text).strip()
        icon_name = icons.get(label.casefold())
        if not icon_name and label.endswith("%"):
            icon_name = "sun"
        if not icon_name:
            return None
        return self._icons.get(icon_name, color=color, size=size)

    def _icon_color_for_style(self, style_name):
        if style_name in ("Accent.TButton", "Build.TButton", "Info.TButton"):
            return "#ffffff"
        if style_name == "Danger.TButton":
            return UI_COLORS["danger_fg"]
        if style_name == "Warning.TButton":
            return UI_COLORS["warning_fg"]
        return UI_COLORS["text_primary"]

    def _disabled_icon_color_for_style(self, style_name):
        if style_name in ("Accent.TButton", "Build.TButton", "Info.TButton"):
            return "#64748b"
        return "#94a3b8"

    def _button(self, master, **options):
        if "text" in options and "image" not in options:
            label = str(options["text"])
            style_name = options.get("style", "TButton")
            img = self._icon_for_label(label, BUTTON_ICONS, color=self._icon_color_for_style(style_name), size=15)
            if img is not None:
                disabled_img = self._icon_for_label(
                    label, BUTTON_ICONS, color=self._disabled_icon_color_for_style(style_name), size=15
                )
                options["image"] = (img, "disabled", disabled_img) if disabled_img is not None else img
                options.setdefault("compound", "left")
                options["text"] = f" {label}"
            else:
                options["text"] = label
        return ttk.Button(master, **options)

    def _set_button_label(self, button, text, style=None):
        if style is None:
            style = str(button.cget("style") or "TButton")
        label = str(text)
        img = self._icon_for_label(label, BUTTON_ICONS, color=self._icon_color_for_style(style), size=15)
        if img is not None:
            disabled_img = self._icon_for_label(
                label, BUTTON_ICONS, color=self._disabled_icon_color_for_style(style), size=15
            )
            image_spec = (img, "disabled", disabled_img) if disabled_img is not None else img
            button.configure(text=f" {label}", image=image_spec, compound="left")
        else:
            button.configure(text=label)

    def check_for_updates(self, manual=False):
        if self.about_update_button and self.about_update_button.winfo_exists():
            self._set_button_label(self.about_update_button, "Checking…")
            self.about_update_button.configure(state="disabled")

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
        if self.about_update_button and self.about_update_button.winfo_exists():
            self._set_button_label(self.about_update_button, "Check for updates")
            self.about_update_button.configure(state="normal")
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
        if self.about_update_button and self.about_update_button.winfo_exists():
            self.about_update_button.configure(text="Downloading update…", state="disabled")
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
            if self.about_update_button and self.about_update_button.winfo_exists():
                self._set_button_label(self.about_update_button, "Check for updates")
            self.about_update_button.configure(state="normal")
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
            if self.about_update_button and self.about_update_button.winfo_exists():
                self._set_button_label(self.about_update_button, "Check for updates")
            self.about_update_button.configure(state="normal")
            self.show_error("Could not start updater", str(start_error), parent=self)

    @staticmethod
    def _ui_font(size=11, weight="normal", mono=False):
        if mono:
            family = "Consolas" if os.name == "nt" else "Menlo"
        elif os.name == "nt":
            family = "Segoe UI"
        else:
            family = "Helvetica Neue"
        return (family, size, weight) if weight != "normal" else (family, size)

    def _style(self):
        s = ttk.Style(self)
        self.style = s
        s.theme_use("clam")
        c = UI_COLORS
        base_font = self._ui_font(11)
        bold_font = self._ui_font(10, "bold")

        s.configure("TFrame", background=c["bg_canvas"])
        s.configure("Card.TFrame", background=c["bg_surface"])
        s.configure("Subtle.TFrame", background=c["bg_subtle"])
        s.configure("TLabel", background=c["bg_canvas"], foreground=c["text_primary"], font=base_font)
        s.configure("Card.TLabel", background=c["bg_surface"], foreground=c["text_primary"], font=base_font)
        s.configure("Title.TLabel", background=c["bg_canvas"], foreground=c["text_primary"], font=self._ui_font(17, "bold"))
        s.configure("PageTitle.TLabel", background=c["bg_canvas"], foreground=c["text_primary"], font=self._ui_font(16, "bold"))
        s.configure("Section.TLabel", background=c["bg_surface"], foreground=c["text_primary"], font=self._ui_font(12, "bold"))
        s.configure("Sub.TLabel", background=c["bg_canvas"], foreground=c["text_muted"], font=self._ui_font(10))
        s.configure("CardSub.TLabel", background=c["bg_surface"], foreground=c["text_muted"], font=self._ui_font(10))
        s.configure("Warning.TLabel", background=c["bg_surface"], foreground=c["warning_fg"], font=self._ui_font(10))
        s.configure("HighBrightness.TLabel", background=c["bg_surface"], foreground=c["high_fg"], font=self._ui_font(10, "bold"))

        s.configure("TCheckbutton", background=c["bg_surface"], foreground=c["text_primary"], font=base_font, padding=(4, 4))
        s.map("TCheckbutton", background=[("active", c["bg_surface"])])
        s.configure("TRadiobutton", background=c["bg_canvas"], foreground=c["text_primary"], font=base_font, padding=(6, 4))
        s.map("TRadiobutton", background=[("active", c["bg_canvas"])])

        s.configure("Safe.Horizontal.TScale", troughcolor="#e2e8f0", background=c["accent"], sliderthickness=18, borderwidth=0)
        s.configure("High.Horizontal.TScale", troughcolor="#fee2e2", background="#dc2626", sliderthickness=18, borderwidth=0)

        s.configure(
            "TButton",
            font=bold_font,
            padding=(13, 8),
            background=c["bg_subtle"],
            foreground=c["text_primary"],
            bordercolor=c["border_strong"],
            lightcolor=c["bg_subtle"],
            darkcolor=c["bg_subtle"],
            borderwidth=1,
            focusthickness=0,
            relief="flat",
        )
        s.map(
            "TButton",
            background=[("disabled", "#f1f5f9"), ("pressed", "#cbd5e1"), ("active", "#e2e8f0")],
            foreground=[("disabled", "#94a3b8"), ("!disabled", c["text_primary"])],
        )

        s.configure(
            "Accent.TButton",
            font=bold_font,
            padding=(14, 8),
            background=c["accent"],
            foreground="#ffffff",
            bordercolor=c["accent"],
            lightcolor=c["accent"],
            darkcolor=c["accent"],
            borderwidth=0,
            focusthickness=0,
        )
        s.map(
            "Accent.TButton",
            background=[("disabled", "#cbd5e1"), ("pressed", c["accent_pressed"]), ("active", c["accent_hover"])],
            foreground=[("disabled", "#64748b"), ("!disabled", "#ffffff")],
        )

        s.configure(
            "Build.TButton",
            font=bold_font,
            padding=(14, 8),
            background=c["build"],
            foreground="#ffffff",
            bordercolor=c["build"],
            lightcolor=c["build"],
            darkcolor=c["build"],
            borderwidth=0,
            focusthickness=0,
        )
        s.map(
            "Build.TButton",
            background=[("disabled", "#cbd5e1"), ("pressed", c["build_pressed"]), ("active", c["build_hover"])],
            foreground=[("disabled", "#64748b"), ("!disabled", "#ffffff")],
        )

        s.configure(
            "Danger.TButton",
            font=bold_font,
            padding=(13, 8),
            background=c["danger_bg"],
            foreground=c["danger_fg"],
            bordercolor=c["danger_border"],
            lightcolor=c["danger_bg"],
            darkcolor=c["danger_bg"],
            borderwidth=1,
            focusthickness=0,
        )
        s.map(
            "Danger.TButton",
            background=[("disabled", "#f1f5f9"), ("pressed", "#fecaca"), ("active", c["danger_hover"])],
            foreground=[("disabled", "#94a3b8"), ("!disabled", c["danger_fg"])],
        )

        s.configure(
            "Info.TButton",
            font=bold_font,
            padding=(14, 8),
            background=c["info_btn"],
            foreground="#ffffff",
            bordercolor=c["info_btn"],
            lightcolor=c["info_btn"],
            darkcolor=c["info_btn"],
            borderwidth=0,
            focusthickness=0,
        )
        s.map(
            "Info.TButton",
            background=[("disabled", "#cbd5e1"), ("pressed", c["info_btn_pressed"]), ("active", c["info_btn_hover"])],
            foreground=[("disabled", "#64748b"), ("!disabled", "#ffffff")],
        )

        s.configure(
            "Warning.TButton",
            font=bold_font,
            padding=(13, 8),
            background=c["warning_bg"],
            foreground=c["warning_fg"],
            bordercolor=c["warning_border"],
            lightcolor=c["warning_bg"],
            darkcolor=c["warning_bg"],
            borderwidth=1,
            focusthickness=0,
        )
        s.map(
            "Warning.TButton",
            background=[("disabled", "#f1f5f9"), ("pressed", c["warning_pressed"]), ("active", c["warning_hover"])],
            foreground=[("disabled", "#94a3b8"), ("!disabled", c["warning_fg"])],
        )

        s.configure(
            "TEntry",
            fieldbackground=c["bg_input"],
            foreground=c["text_primary"],
            bordercolor=c["border_strong"],
            lightcolor=c["border_strong"],
            darkcolor=c["border_strong"],
            insertcolor=c["text_primary"],
            padding=(10, 7),
        )
        s.map(
            "TEntry",
            bordercolor=[("focus", c["accent"]), ("!focus", c["border_strong"])],
            lightcolor=[("focus", c["accent"]), ("!focus", c["border_strong"])],
        )

        s.configure(
            "TCombobox",
            fieldbackground=c["bg_input"],
            background=c["bg_subtle"],
            foreground=c["text_primary"],
            bordercolor=c["border_strong"],
            arrowcolor=c["text_secondary"],
            padding=(10, 7),
        )
        s.map(
            "TCombobox",
            fieldbackground=[("readonly", c["bg_input"])],
            bordercolor=[("focus", c["accent"]), ("!focus", c["border_strong"])],
        )

        s.configure(
            "Vertical.TScrollbar",
            background="#94a3b8",
            troughcolor=c["bg_subtle"],
            bordercolor=c["border"],
            arrowcolor=c["text_secondary"],
            borderwidth=1,
            arrowsize=13,
        )
        s.map(
            "Vertical.TScrollbar",
            background=[("active", "#64748b"), ("pressed", "#475569")],
            arrowcolor=[("active", c["text_primary"]), ("pressed", c["text_primary"])],
        )

        s.configure(
            "Horizontal.TProgressbar",
            troughcolor=c["bg_subtle"],
            background=c["accent"],
            borderwidth=0,
            thickness=6,
        )
        s.configure(
            "Treeview",
            background=c["bg_surface"],
            fieldbackground=c["bg_surface"],
            foreground=c["text_primary"],
            rowheight=30,
            font=base_font,
            bordercolor=c["border"],
        )
        s.configure(
            "Treeview.Heading",
            background=c["bg_subtle"],
            foreground=c["text_primary"],
            font=bold_font,
            padding=(8, 6),
            relief="flat",
        )
        s.map("Treeview", background=[("selected", c["accent"])], foreground=[("selected", "#ffffff")])

        s.configure("TNotebook", background=c["bg_canvas"], borderwidth=0)
        s.configure("TSeparator", background=c["border"])
        s.configure("Workspace.Vertical.TPanedwindow", background=c["border"], sashthickness=6, sashrelief="flat")

    def _card(self, parent, title=None, subtitle=None, padding=18):
        """Create a crisp 1px-bordered white surface card on the slate canvas."""
        outer = tk.Frame(
            parent,
            bg=UI_COLORS["bg_surface"],
            highlightthickness=1,
            highlightbackground=UI_COLORS["border"],
            bd=0,
        )
        body = ttk.Frame(outer, style="Card.TFrame", padding=padding)
        body.pack(fill="both", expand=True)
        body.card_frame = outer
        if title:
            ttk.Label(body, text=title, style="Section.TLabel").pack(anchor="w", pady=(0, 2 if subtitle else 10))
        if subtitle:
            ttk.Label(body, text=subtitle, style="CardSub.TLabel", wraplength=640, justify="left").pack(anchor="w", pady=(0, 10))
        return body

    def _wrap_row(self, parent, *, style="Card.TFrame", gap_x=8, gap_y=8):
        """Create a container that wraps child widgets across rows when horizontal space is narrow."""
        container = ttk.Frame(parent, style=style)
        items = []
        last_width = [0]

        def relayout(event=None):
            width = event.width if event is not None else container.winfo_width()
            if width <= 1:
                return
            if width == last_width[0] and event is not None:
                return
            last_width[0] = width
            for widget in items:
                widget.grid_forget()
            row = 0
            col = 0
            used_w = 0
            for widget in items:
                req_w = widget.winfo_reqwidth()
                if col > 0 and used_w + gap_x + req_w > width:
                    row += 1
                    col = 0
                    used_w = 0
                widget.grid(
                    row=row,
                    column=col,
                    sticky="w",
                    padx=(0 if col == 0 else gap_x, 0),
                    pady=(0 if row == 0 else gap_y, 0),
                )
                used_w = req_w if col == 0 else used_w + gap_x + req_w
                col += 1

        def add_widget(widget):
            items.append(widget)
            return widget

        container.add_widget = add_widget
        container.relayout = relayout
        container.bind("<Configure>", relayout, add="+")
        return container

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
        c = UI_COLORS
        self.about_update_button = None

        # Top app bar with live project and device status pills
        header_bar = tk.Frame(self, bg=c["bg_surface"], highlightthickness=0, bd=0)
        header_bar.pack(fill="x")
        header_inner = tk.Frame(header_bar, bg=c["bg_surface"], padx=20, pady=12)
        header_inner.pack(fill="x")

        title_col = tk.Frame(header_inner, bg=c["bg_surface"])
        title_col.pack(side="left", fill="x", expand=True)
        title_line = tk.Frame(title_col, bg=c["bg_surface"])
        title_line.pack(anchor="w")
        tk.Label(
            title_line,
            text="DCM Android Toolkit",
            bg=c["bg_surface"],
            fg=c["text_primary"],
            font=self._ui_font(16, "bold"),
        ).pack(side="left")
        tk.Label(
            title_line,
            text=f"v{APP_VERSION}",
            bg=c["bg_subtle"],
            fg=c["text_secondary"],
            font=self._ui_font(9, "bold"),
            padx=7,
            pady=2,
        ).pack(side="left", padx=(10, 0))
        tk.Label(
            title_col,
            text="Build, install, and manage Android APKs across Gradle & Expo projects",
            bg=c["bg_surface"],
            fg=c["text_muted"],
            font=self._ui_font(10),
        ).pack(anchor="w", pady=(2, 0))

        pills_col = tk.Frame(header_inner, bg=c["bg_surface"])
        pills_col.pack(side="right")
        self.header_project_pill = tk.Label(
            pills_col,
            text=f"▣  {self.project_name.get() or 'No project'}",
            bg=c["bg_subtle"],
            fg=c["text_primary"],
            font=self._ui_font(10, "bold"),
            padx=10,
            pady=5,
        )
        self.header_project_pill.pack(side="left", padx=(0, 8))
        self.header_device_pill = tk.Label(
            pills_col,
            text="○  No device",
            bg=c["pill_idle_bg"],
            fg=c["pill_idle_fg"],
            font=self._ui_font(10, "bold"),
            padx=10,
            pady=5,
        )
        self.header_device_pill.pack(side="left")
        tk.Frame(header_bar, bg=c["border"], height=1).pack(fill="x")

        root = ttk.Frame(self, padding=(16, 14, 16, 12))
        root.pack(fill="both", expand=True)

        def add_page_header(page, title, description):
            ttk.Label(page, text=title, style="PageTitle.TLabel").pack(anchor="w")
            description_label = ttk.Label(
                page, text=description, style="Sub.TLabel", justify="left", wraplength=760
            )
            description_label.pack(anchor="w", fill="x", pady=(4, 12))
            ttk.Separator(page, orient="horizontal").pack(fill="x", pady=(0, 14))
            page.bind(
                "<Configure>",
                lambda event, label=description_label: label.configure(
                    wraplength=max(220, event.width - 48)
                ),
                add="+",
            )

        workspace = ttk.Panedwindow(root, orient=tk.VERTICAL, style="Workspace.Vertical.TPanedwindow")
        self.workspace = workspace
        self.workspace_sash_initialized = False
        self.workspace_sash_pending = False
        workspace.bind("<Configure>", self._workspace_configured, add="+")
        workspace.pack(fill="both", expand=True)

        shell_border = tk.Frame(
            workspace,
            bg=c["bg_canvas"],
            highlightthickness=1,
            highlightbackground=c["border"],
            bd=0,
        )
        workspace.add(shell_border, weight=5)

        rail_frame = tk.Frame(shell_border, bg=c["bg_surface"], width=196)
        rail_frame.pack(side="left", fill="y")
        rail_frame.pack_propagate(False)
        tk.Frame(shell_border, bg=c["border"], width=1).pack(side="left", fill="y")
        stage_frame = ttk.Frame(shell_border, style="TFrame")
        stage_frame.pack(side="left", fill="both", expand=True)

        tabs = SidebarNavigator(rail_frame, stage_frame)
        self.tabs = tabs

        def create_scrollable_tab():
            page = ttk.Frame(stage_frame, style="TFrame")
            page.grid_rowconfigure(0, weight=1)
            page.grid_columnconfigure(0, weight=1)
            canvas = tk.Canvas(
                page,
                background=c["bg_canvas"],
                highlightthickness=0,
                borderwidth=0,
                yscrollincrement=8,
            )
            scrollbar = ttk.Scrollbar(page, orient="vertical", command=canvas.yview)
            canvas.configure(yscrollcommand=scrollbar.set)
            canvas.grid(row=0, column=0, sticky="nsew")
            scrollbar.grid(row=0, column=1, sticky="ns")

            content = ttk.Frame(canvas, style="TFrame", padding=20)
            content_window = canvas.create_window((0, 0), window=content, anchor="nw")

            def update_scroll_region(_event=None):
                bbox = canvas.bbox("all")
                if not bbox:
                    return
                viewport_h = canvas.winfo_height()
                content_h = max(content.winfo_reqheight(), bbox[3] - bbox[1])
                if viewport_h > 1 and content_h <= viewport_h:
                    canvas.configure(scrollregion=(0, 0, bbox[2], viewport_h))
                    canvas.yview_moveto(0.0)
                    scrollbar.grid_remove()
                else:
                    canvas.configure(scrollregion=bbox)
                    scrollbar.grid(row=0, column=1, sticky="ns")

            def on_canvas_configure(event):
                canvas.itemconfigure(content_window, width=event.width)
                update_scroll_region()

            content.bind("<Configure>", update_scroll_region, add="+")
            canvas.bind("<Configure>", on_canvas_configure, add="+")

            touchpad_accum = [0.0]

            def can_scroll_canvas(event):
                if not canvas.winfo_ismapped():
                    return False
                if content.winfo_reqheight() <= canvas.winfo_height():
                    return False
                x = event.x_root - canvas.winfo_rootx()
                y = event.y_root - canvas.winfo_rooty()
                if not (0 <= x < canvas.winfo_width() and 0 <= y < canvas.winfo_height()):
                    return False
                widget = getattr(event, "widget", None)
                if isinstance(widget, (tk.Text, tk.Listbox, ttk.Treeview)):
                    try:
                        first, last = widget.yview()
                        if first > 0.0 or last < 1.0:
                            return False
                    except tk.TclError:
                        pass
                return True

            def scroll_canvas_units(units):
                if not units:
                    return None
                first, last = canvas.yview()
                if units < 0 and first <= 0.0:
                    return "break"
                if units > 0 and last >= 1.0:
                    return "break"
                canvas.yview_scroll(units, "units")
                return "break"

            def scroll_with_wheel(event):
                if not can_scroll_canvas(event):
                    return
                number = getattr(event, "num", None)
                if number == 4:
                    units = -5
                elif number == 5:
                    units = 5
                else:
                    delta = getattr(event, "delta", 0)
                    if abs(delta) >= 120:
                        units = -int(delta / 120) * 5
                    elif delta > 0:
                        units = -max(1, int(delta) * 2)
                    elif delta < 0:
                        units = max(1, int(-delta) * 2)
                    else:
                        units = 0
                return scroll_canvas_units(units)

            def scroll_with_touchpad(event):
                if not can_scroll_canvas(event):
                    return
                try:
                    _dx, dy = self.tk.call("tk::PreciseScrollDeltas", event.delta)
                    dy = float(dy)
                except (tk.TclError, ValueError, TypeError):
                    dy = float(getattr(event, "delta", 0))
                if dy == 0:
                    return
                touchpad_accum[0] += -dy
                step = int(touchpad_accum[0] / 8)
                if step:
                    touchpad_accum[0] -= step * 8
                    return scroll_canvas_units(step)

            self.bind_all("<MouseWheel>", scroll_with_wheel, add="+")
            self.bind_all("<Button-4>", scroll_with_wheel, add="+")
            self.bind_all("<Button-5>", scroll_with_wheel, add="+")
            try:
                self.bind_all("<TouchpadScroll>", scroll_with_touchpad, add="+")
            except tk.TclError:
                pass
            return page, content

        connection_page, connection_tab = create_scrollable_tab()
        apk_page, apk_tab = create_scrollable_tab()
        sms_page, sms_tab = create_scrollable_tab()
        scan_page, scan_tab = create_scrollable_tab()
        watch_page, watch_tab = create_scrollable_tab()
        emulator_page, emulator_tab = create_scrollable_tab()
        debug_page, debug_tab = create_scrollable_tab()
        about_page, about_tab = create_scrollable_tab()
        self.emulator_tab_id = str(emulator_page)
        def add_nav_tab(page, title):
            icon_name = TAB_ICONS.get(title.casefold())
            default_icon = self._icons.get(icon_name, color=UI_COLORS["text_secondary"], size=16) if icon_name else None
            active_icon = self._icons.get(icon_name, color=UI_COLORS["accent"], size=16) if icon_name else None
            tabs.add(page, text=title, icon=default_icon, active_icon=active_icon)

        tabs.add_section("Workspace")
        add_nav_tab(connection_page, "Connection")
        add_nav_tab(apk_page, "APK")
        tabs.add_section("Tools")
        add_nav_tab(sms_page, "SMS Export")
        add_nav_tab(scan_page, "Subnet Scan")
        add_nav_tab(watch_page, "Watch Screen")
        add_nav_tab(emulator_page, "Emulator")
        tabs.add_section("System")
        add_nav_tab(debug_page, "Debug")
        add_nav_tab(about_page, "About")
        self.debug_tab_id = str(debug_page)
        tabs.bind("<<NotebookTabChanged>>", self._debug_tab_selected, add="+")
        self.project_name.trace_add("write", lambda *_args: self._update_header_pills())

        self._build_debug_tab(debug_tab)

        add_page_header(
            about_tab,
            "About DCM Android Toolkit",
            "Application overview, credits, and release update information.",
        )
        about_card = self._card(about_tab)
        about_card.card_frame.pack(anchor="nw", fill="x")
        ttk.Label(about_card, text="Application overview", style="Section.TLabel").pack(anchor="w", pady=(0, 8))
        ttk.Separator(about_card, orient="horizontal").pack(fill="x", pady=(0, 12))
        about_description = ttk.Label(
            about_card,
            text=(
                "DCM Android Toolkit helps Android developers work across Gradle and Expo projects. "
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
        ttk.Label(about_card, text=f"Version {APP_VERSION}", style="CardSub.TLabel").pack(anchor="w")
        ttk.Label(about_card, text="Made by Emre Demir", style="Card.TLabel").pack(anchor="w", pady=(4, 14))
        ttk.Separator(about_card, orient="horizontal").pack(fill="x", pady=(0, 14))
        about_actions = self._wrap_row(about_card, style="Card.TFrame")
        about_actions.pack(fill="x")
        self.about_update_button = about_actions.add_widget(
            self._button(
                about_actions,
                text="Check for updates",
                style="Info.TButton",
                command=lambda: self.check_for_updates(manual=True),
            )
        )
        about_actions.add_widget(
            self._button(
                about_actions,
                text="Website",
                command=lambda: webbrowser.open("https://dotcommedia.online"),
            )
        )
        about_actions.add_widget(
            self._button(
                about_actions,
                text="Report a bug…",
                command=self.export_activity_log_for_bug_report,
            )
        )

        add_page_header(
            connection_tab,
            "Connect a device",
            "Connect over USB or Wi-Fi. Disconnect to change connection settings.",
        )
        method_row = ttk.Frame(connection_tab); method_row.pack(fill="x", pady=(0, 12))
        ttk.Label(method_row, text="Connection method", font=("Helvetica Neue", 11, "bold")).pack(side="left", padx=(0, 12))
        for method in ("USB", "Wi-Fi"):
            method_icon = self._icon_for_label(method, BUTTON_ICONS, color=UI_COLORS["text_primary"], size=14)
            radio = ttk.Radiobutton(
                method_row,
                text=f" {method}" if method_icon else method,
                image=method_icon or "",
                compound="left",
                value=method,
                variable=self.connection_method,
                command=self._connection_method_changed,
            )
            radio.pack(side="left", padx=(0, 12))
            self.connection_widgets.append(radio)
        ttk.Separator(connection_tab, orient="horizontal").pack(fill="x", pady=(0, 12))
        device_body = self._card(connection_tab)
        self.device_card = device_body.card_frame
        self.device_card.pack(fill="x", pady=(0, 14))
        ttk.Label(device_body, text="USB connection", style="Section.TLabel").pack(anchor="w", pady=(0, 10))
        usbrow = ttk.Frame(device_body, style="Card.TFrame"); usbrow.pack(fill="x")
        self.devices = ttk.Combobox(usbrow, textvariable=self.target, state="readonly", width=32)
        self.devices.pack(side="left", fill="x", expand=True)
        refresh_button = self._button(usbrow, text="Refresh", command=self.refresh_devices); refresh_button.pack(side="left", padx=(8, 0))
        self.connect_usb_button = self._button(usbrow, text="Connect USB", style="Accent.TButton", command=self.connect_usb); self.connect_usb_button.pack(side="left", padx=(8, 0))
        self.connection_widgets.extend([self.devices, refresh_button, self.connect_usb_button])
        ttk.Label(device_body, text="Connect the phone by cable, enable USB debugging, and accept its authorization prompt.", style="CardSub.TLabel", wraplength=580).pack(anchor="w", pady=(10, 0))

        wifi_body = self._card(connection_tab)
        self.wifi_card = wifi_body.card_frame
        self.wifi_card.pack(fill="x", pady=(0, 14))
        ttk.Label(wifi_body, text="Wi-Fi connection", style="Section.TLabel").pack(anchor="w", pady=(0, 10))
        fixedrow = ttk.Frame(wifi_body, style="Card.TFrame"); fixedrow.pack(fill="x", pady=(0, 7))
        fixed_icon = self._icon_for_label("Use fixed IP", BUTTON_ICONS, color=UI_COLORS["text_primary"], size=14)
        fixed_check = ttk.Checkbutton(
            fixedrow,
            text=" Use fixed IP" if fixed_icon else "Use fixed IP",
            image=fixed_icon or "",
            compound="left",
            variable=self.use_fixed_wifi,
            command=self._update_ip_mode,
        )
        fixed_check.pack(side="left")
        self.connection_widgets.append(fixed_check)
        ttk.Label(wifi_body, text="Saved fixed IP and port", style="Card.TLabel").pack(anchor="w")
        self.fixed_entry = ttk.Entry(wifi_body, textvariable=self.fixed_wifi)
        self.fixed_entry.pack(fill="x", pady=(4, 10))
        ttk.Label(wifi_body, text="Manual IP and port (example: 192.168.1.42:5555)", style="Card.TLabel").pack(anchor="w")
        self.manual_entry = ttk.Combobox(wifi_body, textvariable=self.wifi, state="normal", values=())
        self.manual_entry.pack(fill="x", pady=(4, 10))
        self.connection_widgets.extend([self.fixed_entry, self.manual_entry])
        wbuttons = self._wrap_row(wifi_body, style="Card.TFrame"); wbuttons.pack(fill="x")
        self.pair_button = wbuttons.add_widget(self._button(wbuttons, text="Pair…", command=self.pair_wifi))
        self.connect_wifi_button = wbuttons.add_widget(self._button(wbuttons, text="Connect Wi-Fi", style="Accent.TButton", command=self.connect_wifi))
        self.scan_open_button = wbuttons.add_widget(self._button(wbuttons, text="Scan subnet…", command=self.open_scan_tab))
        self.connection_widgets.extend([self.pair_button, self.connect_wifi_button, self.scan_open_button])

        connected_body = self._card(connection_tab)
        self.connected_card = connected_body.card_frame
        connected_row = ttk.Frame(connected_body, style="Card.TFrame")
        connected_row.pack(fill="x")
        title_block = ttk.Frame(connected_row, style="Card.TFrame")
        title_block.pack(side="left", fill="x", expand=True, padx=(0, 14))
        self.active_label = ttk.Label(title_block, text="Connected device", style="Card.TLabel", font=self._ui_font(14, "bold"), wraplength=430, justify="left", anchor="w")
        self.active_label.pack(fill="x", anchor="w")
        self.connection_detail_label = ttk.Label(title_block, text="", style="CardSub.TLabel", wraplength=430, justify="left", anchor="w")
        self.connection_detail_label.pack(fill="x", anchor="w", pady=(5, 0))
        self.disconnect_button = self._button(connected_row, text="Disconnect", style="Danger.TButton", command=self.disconnect_device)
        self.disconnect_button.configure(width=15)
        self.disconnect_button.pack(side="right", padx=(8, 0))
        awake_icon = self._icon_for_label("Keep screen awake while charging", BUTTON_ICONS, color=UI_COLORS["text_primary"], size=14)
        self.keep_awake_button = ttk.Checkbutton(
            connected_body,
            text=" Keep screen awake while charging" if awake_icon else "Keep screen awake while charging",
            image=awake_icon or "",
            compound="left",
            variable=self.keep_awake,
            command=self.toggle_keep_awake,
            state="disabled",
        )
        self.keep_awake_button.pack(anchor="w", pady=(14, 0))
        ttk.Label(connected_body, text="Temporarily disables battery saver and screen dim timeout while enabled. Original settings are restored when you turn it off.", style="CardSub.TLabel", wraplength=580).pack(anchor="w", pady=(5, 8))
        self.brightness_value_label = ttk.Label(connected_body, textvariable=self.brightness_text, style="Card.TLabel", font=self._ui_font(10, "bold"))
        self.brightness_value_label.pack(anchor="w")
        self.brightness_scale = ttk.Scale(connected_body, from_=0, to=100, variable=self.brightness_level, command=self._brightness_changed, style="Safe.Horizontal.TScale")
        self.brightness_scale.pack(fill="x", pady=(4, 0))
        self._update_brightness_visuals(self.brightness_level.get())
        presets = ttk.Frame(connected_body, style="Card.TFrame")
        presets.pack(anchor="w", pady=(7, 0))
        ttk.Label(presets, text="Presets", style="Card.TLabel").pack(side="left", padx=(0, 8))
        for percent in (25, 50, 75):
            self._button(presets, text=f"{percent}%", command=lambda value=percent: self.set_brightness_preset(value)).pack(side="left", padx=(0, 6))
        ttk.Label(connected_body, text="AMOLED care: avoid prolonged high brightness with static content; it can increase burn-in risk. No 100% preset is provided.", style="Warning.TLabel", wraplength=580).pack(anchor="w", pady=(8, 0))
        ttk.Label(connected_body, text="ADB connection is active. Disconnect to change device or connection settings.", style="CardSub.TLabel").pack(anchor="w", pady=(8, 0))
        self.protocol("WM_DELETE_WINDOW", self.close_app)

        add_page_header(
            apk_tab,
            "APK build, install, and removal",
            "Build APKs from Gradle or Expo projects, then install them on a device or emulator.",
        )
        card2 = self._card(apk_tab)
        card2.card_frame.pack(fill="x", pady=(0, 14))
        ttk.Label(card2, text="Project profile", style="Section.TLabel").pack(anchor="w", pady=(0, 10))
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
        ttk.Label(card2, text="Project folder (Gradle or Expo)", style="Card.TLabel").pack(anchor="w")
        projectrow = ttk.Frame(card2, style="Card.TFrame"); projectrow.pack(fill="x", pady=(4, 8))
        project_dir_entry = ttk.Entry(projectrow, textvariable=self.project_dir)
        project_dir_entry.pack(side="left", fill="x", expand=True)
        self.project_edit_widgets.append((project_dir_entry, "normal"))
        choose_project_button = self._button(projectrow, text="Choose…", command=self.choose_project_dir)
        choose_project_button.pack(side="left", padx=(8, 0))
        self.project_edit_widgets.append((choose_project_button, "normal"))
        modulerow = ttk.Frame(card2, style="Card.TFrame"); modulerow.pack(fill="x", pady=(0, 8))
        ttk.Label(modulerow, text="Android module", style="Card.TLabel").pack(side="left")
        module_entry = ttk.Entry(modulerow, textvariable=self.module, width=24)
        module_entry.pack(side="left", padx=(8, 0))
        self.project_edit_widgets.append((module_entry, "normal"))
        ttk.Label(modulerow, text="(for example: app or :client:app)", style="CardSub.TLabel").pack(side="left", padx=(8, 0))
        ttk.Label(card2, text="APK file", style="Card.TLabel").pack(anchor="w")
        apkrow = ttk.Frame(card2, style="Card.TFrame"); apkrow.pack(fill="x", pady=(4, 10))
        apk_entry = ttk.Entry(apkrow, textvariable=self.apk)
        apk_entry.pack(side="left", fill="x", expand=True)
        self.project_edit_widgets.append((apk_entry, "normal"))
        choose_apk_button = self._button(apkrow, text="Choose…", command=self.choose_apk)
        choose_apk_button.pack(side="left", padx=(8, 0))
        self.project_edit_widgets.append((choose_apk_button, "normal"))
        buildtyperow = ttk.Frame(card2, style="Card.TFrame")
        buildtyperow.pack(fill="x", pady=(0, 10))
        ttk.Label(buildtyperow, text="Build type", style="Card.TLabel").pack(side="left")
        build_type_selector = ttk.Combobox(buildtyperow, textvariable=self.build_type, state="readonly", values=("debug", "release"), width=10)
        build_type_selector.pack(side="left", padx=(8, 0))
        self.project_edit_widgets.append((build_type_selector, "readonly"))
        buildrow = self._wrap_row(card2, style="Card.TFrame")
        buildrow.pack(fill="x", pady=(2, 0))
        self.build_button = buildrow.add_widget(self._button(buildrow, text="Build APK…", style="Build.TButton", command=self.build_apk))
        buildrow.add_widget(self._button(buildrow, text="Install / overwrite", style="Accent.TButton", command=self.install))
        buildrow.add_widget(self._button(buildrow, text="Remove app from device", style="Danger.TButton", command=self.uninstall))
        buildrow.add_widget(self._button(buildrow, text="Version history…", command=self.open_version_history))

        install_card = self._card(apk_tab)
        install_card.card_frame.pack(fill="x")
        ttk.Label(install_card, text="Install & target", style="Section.TLabel").pack(anchor="w", pady=(0, 8))
        ttk.Separator(install_card, orient="horizontal").pack(fill="x", pady=(0, 12))
        ttk.Label(install_card, text="Android package name (for example: com.example.app)", style="Card.TLabel").pack(anchor="w")
        package_entry = ttk.Entry(install_card, textvariable=self.package)
        package_entry.pack(fill="x", pady=(4, 10))
        self.project_edit_widgets.append((package_entry, "normal"))
        install_target_row = ttk.Frame(install_card, style="Card.TFrame")
        install_target_row.pack(fill="x")
        ttk.Label(install_target_row, text="Install target", style="Card.TLabel").pack(side="left", padx=(0, 10))
        self.install_target_selector = ttk.Combobox(
            install_target_row, textvariable=self.install_target, state="readonly"
        )
        self.install_target_selector.pack(side="left", fill="x", expand=True)
        self._button(install_target_row, text="Refresh devices", command=self.refresh_devices).pack(side="left", padx=(8, 0))
        add_page_header(
            sms_tab,
            "SMS debug export",
            "Read a small sample or export SMS diagnostics from the connected device.",
        )
        card3 = self._card(sms_tab)
        card3.card_frame.pack(fill="x")
        ttk.Label(card3, text="Export configuration", style="Section.TLabel").pack(anchor="w", pady=(0, 8))
        ttk.Separator(card3, orient="horizontal").pack(fill="x", pady=(0, 12))
        ttk.Label(card3, text="Reads the device SMS database through ADB. Android may restrict this unless the app is the default SMS handler or the device grants shell access.", style="CardSub.TLabel", wraplength=580).pack(anchor="w", pady=(0, 12))
        ttk.Label(card3, text="Output folder", style="Card.TLabel").pack(anchor="w")
        export_row = ttk.Frame(card3, style="Card.TFrame")
        export_row.pack(fill="x", pady=(4, 12))
        ttk.Entry(export_row, textvariable=self.export_dir).pack(side="left", fill="x", expand=True)
        self._button(export_row, text="Choose output folder…", command=self.choose_export_dir).pack(side="left", padx=(8, 0))
        sms_actions = self._wrap_row(card3, style="Card.TFrame"); sms_actions.pack(fill="x")
        self.count_button = sms_actions.add_widget(self._button(sms_actions, text="Read SMS count", command=self.count_sms))
        self.preview_button = sms_actions.add_widget(self._button(sms_actions, text="Preview 2 SMS", command=self.preview_sms))
        self.export_button = sms_actions.add_widget(self._button(sms_actions, text="Export SMS to JSON", style="Accent.TButton", command=self.export_sms))
        ttk.Separator(card3, orient="horizontal").pack(fill="x", pady=(14, 10))
        ttk.Label(card3, textvariable=self.sms_count_text, style="CardSub.TLabel").pack(anchor="w")

        add_page_header(
            scan_tab,
            "Find a device on your network",
            "Scan a local subnet for hosts that may be accepting ADB connections.",
        )
        scan_card = self._card(scan_tab)
        scan_card.card_frame.pack(fill="x")
        ttk.Label(scan_card, text="Scan subnet", style="Section.TLabel").pack(anchor="w", pady=(0, 8))
        ttk.Label(scan_card, text="Enter a CIDR subnet and ADB port. The result is copied into the manual IP field on the Connection tab.", style="CardSub.TLabel", wraplength=580).pack(anchor="w", pady=(0, 12))
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
        watch_card = self._card(watch_tab)
        watch_card.card_frame.pack(fill="x")
        ttk.Label(watch_card, text="Live screen with touch control", style="Section.TLabel").pack(anchor="w", pady=(0, 8))
        ttk.Separator(watch_card, orient="horizontal").pack(fill="x", pady=(0, 12))
        ttk.Label(
            watch_card,
            text="Opens the connected Android screen in a separate window. Clicks, taps, swipes, and keyboard input in that window are sent to the phone over ADB.",
            style="CardSub.TLabel",
            wraplength=580,
        ).pack(anchor="w", pady=(0, 12))
        self.watch_button = self._button(watch_card, text="Open screen window", style="Accent.TButton", command=self.open_screen_mirror, state="disabled")
        self.watch_button.pack(anchor="w")
        ttk.Label(
            watch_card,
            text="Screen mirroring uses scrcpy. Install with brew install scrcpy if it is not already available.",
            style="CardSub.TLabel",
            wraplength=580,
        ).pack(anchor="w", pady=(10, 0))
        ttk.Separator(watch_card, orient="horizontal").pack(fill="x", pady=(14, 10))
        self.watch_device_label = ttk.Label(watch_card, text="Connect a device first.", style="CardSub.TLabel")
        self.watch_device_label.pack(anchor="w")

        add_page_header(
            emulator_tab,
            "Android emulator",
            "Start and stop Android Virtual Devices installed in your Android SDK, then connect one to the toolkit.",
        )
        emulator_card = self._card(emulator_tab)
        emulator_card.card_frame.pack(fill="x")
        ttk.Label(
            emulator_card,
            text="Virtual devices on this computer",
            style="Section.TLabel",
        ).pack(anchor="w", pady=(0, 8))
        ttk.Separator(emulator_card, orient="horizontal").pack(fill="x", pady=(0, 12))
        ttk.Label(
            emulator_card,
            text=(
                "The Android Emulator opens in its own window. Download & create AVD installs the Emulator, "
                "Platform-Tools, and an Android 16 Google APIs system image, then creates a default Pixel AVD. "
                "Android Studio is not required. The system image is a large download and requires an internet connection."
            ),
            style="CardSub.TLabel",
            wraplength=680,
            justify="left",
        ).pack(anchor="w", fill="x", pady=(0, 12))
        emulator_select_row = ttk.Frame(emulator_card, style="Card.TFrame")
        emulator_select_row.pack(fill="x", pady=(0, 10))
        ttk.Label(emulator_select_row, text="Android Virtual Device", style="Card.TLabel").pack(side="left", padx=(0, 10))
        self.emulator_selector = ttk.Combobox(
            emulator_select_row,
            textvariable=self.emulator_avd,
            values=(),
            state="readonly",
        )
        self.emulator_selector.pack(side="left", fill="x", expand=True)
        self.emulator_selector.bind("<<ComboboxSelected>>", lambda _event: self._update_emulator_controls())
        emulator_actions = self._wrap_row(emulator_card, style="Card.TFrame")
        emulator_actions.pack(fill="x")
        self.emulator_download_button = emulator_actions.add_widget(
            self._button(
                emulator_actions,
                text="Download & create AVD",
                style="Build.TButton",
                command=self.download_emulator_package,
            )
        )
        self.emulator_refresh_button = emulator_actions.add_widget(
            self._button(
                emulator_actions,
                text="Refresh emulators",
                command=self.refresh_emulators,
            )
        )
        self.emulator_start_button = emulator_actions.add_widget(
            self._button(
                emulator_actions,
                text="Start emulator",
                style="Accent.TButton",
                command=self.start_selected_emulator,
            )
        )
        self.emulator_stop_button = emulator_actions.add_widget(
            self._button(
                emulator_actions,
                text="Stop emulator",
                style="Danger.TButton",
                command=self.stop_selected_emulator,
            )
        )
        self.emulator_connect_button = emulator_actions.add_widget(
            self._button(
                emulator_actions,
                text="Connect emulator",
                style="Info.TButton",
                command=self.connect_selected_emulator,
            )
        )
        ttk.Separator(emulator_card, orient="horizontal").pack(fill="x", pady=(14, 10))
        self.emulator_status_label = ttk.Label(
            emulator_card, textvariable=self.emulator_status, style="CardSub.TLabel", wraplength=680, justify="left"
        )
        self.emulator_status_label.pack(anchor="w", fill="x")

        log_frame = ttk.Frame(workspace, padding=(0, 8, 0, 0))
        workspace.add(log_frame, weight=1)
        log_shell = tk.Frame(
            log_frame,
            bg=c["console_bg"],
            highlightthickness=1,
            highlightbackground=c["border_strong"],
            bd=0,
        )
        log_shell.pack(fill="both", expand=True)

        log_header = tk.Frame(log_shell, bg="#162033", padx=12, pady=6)
        log_header.pack(fill="x")
        tk.Label(
            log_header,
            text="ACTIVITY",
            bg="#162033",
            fg="#94a3b8",
            font=self._ui_font(9, "bold"),
        ).pack(side="left")
        tk.Label(
            log_header,
            text="· drag divider above to resize",
            bg="#162033",
            fg="#64748b",
            font=self._ui_font(9),
        ).pack(side="left", padx=(6, 0))

        self.activity_autoscroll = tk.BooleanVar(value=True)
        log_controls = tk.Frame(log_header, bg="#162033")
        log_controls.pack(side="right")

        def make_console_btn(label, cmd):
            btn = tk.Label(
                log_controls,
                text=label,
                bg="#1e293b",
                fg="#cbd5e1",
                font=self._ui_font(9, "bold"),
                padx=8,
                pady=2,
                cursor="hand2",
            )
            btn.bind("<Button-1>", lambda _e: cmd())
            btn.bind("<Enter>", lambda _e: btn.configure(bg="#334155", fg="#ffffff"))
            btn.bind("<Leave>", lambda _e: btn.configure(bg="#1e293b", fg="#cbd5e1"))
            return btn

        make_console_btn("Copy", self._copy_activity_log).pack(side="left", padx=(0, 6))
        make_console_btn("Clear", self._clear_activity_log).pack(side="left", padx=(0, 8))
        autoscroll_chk = tk.Checkbutton(
            log_controls,
            text="Auto-scroll",
            variable=self.activity_autoscroll,
            bg="#162033",
            fg="#cbd5e1",
            selectcolor="#0f172a",
            activebackground="#162033",
            activeforeground="#ffffff",
            font=self._ui_font(9),
            highlightthickness=0,
            bd=0,
        )
        autoscroll_chk.pack(side="left")

        log_body = tk.Frame(log_shell, bg=c["console_bg"])
        log_body.pack(fill="both", expand=True)
        self.output = tk.Text(
            log_body,
            height=6,
            bg=c["console_bg"],
            fg=c["console_fg"],
            insertbackground="white",
            relief="flat",
            font=self._ui_font(10, mono=True),
            padx=12,
            pady=10,
            state="disabled",
        )
        self.output.tag_configure("error", foreground=c["console_error"])
        self.output.tag_configure("warn", foreground=c["console_warn"])
        self.output.tag_configure("success", foreground=c["console_success"])
        self.output.tag_configure("info", foreground=c["console_fg"])
        self.activity_scrollbar = ttk.Scrollbar(log_body, orient="vertical", command=self.output.yview)
        self.output.configure(yscrollcommand=self.activity_scrollbar.set)
        self.output.pack(side="left", fill="both", expand=True)
        self.activity_scrollbar.pack(side="right", fill="y")

        self.build_status_row = ttk.Frame(root, style="Card.TFrame", padding=(10, 6))
        self.build_status_label = ttk.Label(
            self.build_status_row,
            textvariable=self.build_status,
            style="CardSub.TLabel",
            wraplength=900,
            justify="left",
            anchor="w",
        )
        self.build_status_label.pack(side="left", fill="x", expand=True)
        self.build_progress = ttk.Progressbar(self.build_status_row, mode="indeterminate", length=128)

        footer_bar = tk.Frame(self, bg=c["bg_surface"], highlightthickness=0, bd=0)
        footer_bar.pack(fill="x", side="bottom")
        tk.Frame(footer_bar, bg=c["border"], height=1).pack(fill="x")
        self.status_label = tk.Label(
            footer_bar,
            textvariable=self.status,
            bg=c["bg_surface"],
            fg=c["text_secondary"],
            font=self._ui_font(10),
            anchor="w",
            padx=16,
            pady=7,
        )
        self.status_label.pack(fill="x")
        self.bind(
            "<Configure>",
            lambda _event: self.build_status_label.configure(
                wraplength=max(240, self.winfo_width() - 176)
            ),
            add="+",
        )
        if not self.emulator_executable:
            tabs.select(self.emulator_tab_id)
        self.after_idle(self._schedule_initial_workspace_sash)
        self.after(250, self._schedule_initial_workspace_sash)
        self._update_ip_mode()
        self._update_header_pills()

    def _workspace_configured(self, event=None):
        if event is None or event.height >= 320:
            self._schedule_initial_workspace_sash()

    def _schedule_initial_workspace_sash(self):
        if self.workspace_sash_initialized or self.workspace_sash_pending:
            return
        if not self.workspace.winfo_exists() or self.workspace.winfo_height() < 320:
            self.after(120, self._schedule_initial_workspace_sash)
            return
        self.workspace_sash_pending = True
        self.after_idle(self._set_initial_workspace_sash)

    def _set_initial_workspace_sash(self):
        self.workspace_sash_pending = False
        if self.workspace_sash_initialized or not self.workspace.winfo_exists():
            return
        available_height = self.workspace.winfo_height()
        if available_height < 320:
            self.after(120, self._schedule_initial_workspace_sash)
            return
        position = min(max(220, int(available_height * 0.72)), max(200, available_height - 120))
        try:
            self.workspace.sashpos(0, position)
            actual_position = int(self.workspace.sashpos(0))
        except (tk.TclError, ValueError):
            actual_position = 0
        if actual_position >= 180:
            self.workspace_sash_initialized = True
        else:
            self.after(150, self._schedule_initial_workspace_sash)

    def _build_debug_tab(self, page):
        ttk.Label(page, text="Debug and cleanup", style="PageTitle.TLabel").pack(anchor="w")
        ttk.Label(
            page,
            text="Inspect toolkit and Android SDK files, clean stale temporary data, or remove selected toolkit data.",
            style="Sub.TLabel",
            wraplength=760,
            justify="left",
        ).pack(anchor="w", fill="x", pady=(4, 12))
        ttk.Separator(page, orient="horizontal").pack(fill="x", pady=(0, 14))

        inventory_card = self._card(page)
        inventory_card.card_frame.pack(fill="x", pady=(0, 14))
        ttk.Label(inventory_card, text="System and toolkit inventory", style="Section.TLabel").pack(anchor="w")
        ttk.Label(
            inventory_card,
            text="The export includes detected tools, the selected project folder, and recent application errors. Local paths are included; device addresses and SMS details are redacted.",
            style="CardSub.TLabel",
            wraplength=760,
            justify="left",
        ).pack(anchor="w", fill="x", pady=(4, 10))
        inventory_body = ttk.Frame(inventory_card, style="Card.TFrame")
        inventory_body.pack(fill="x")
        self.debug_inventory_text = tk.Text(
            inventory_body,
            height=13,
            wrap="word",
            bg="#f8fafc",
            fg=UI_COLORS["text_primary"],
            insertbackground=UI_COLORS["text_primary"],
            font=self._ui_font(9, mono=True),
            padx=10,
            pady=8,
            relief="flat",
            highlightthickness=1,
            highlightbackground=UI_COLORS["border"],
            state="disabled",
        )
        inventory_scrollbar = ttk.Scrollbar(inventory_body, orient="vertical", command=self.debug_inventory_text.yview)
        self.debug_inventory_text.configure(yscrollcommand=inventory_scrollbar.set)
        self.debug_inventory_text.pack(side="left", fill="both", expand=True)
        inventory_scrollbar.pack(side="right", fill="y")
        inventory_actions = self._wrap_row(inventory_card, style="Card.TFrame")
        inventory_actions.pack(fill="x", pady=(10, 0))
        inventory_actions.add_widget(
            self._button(
                inventory_actions,
                text="Scan debug state",
                command=lambda: self._refresh_debug_inventory(scan_versions=True),
            )
        )
        inventory_actions.add_widget(
            self._button(
                inventory_actions,
                text="Export diagnostic report and error log…",
                style="Info.TButton",
                command=self._export_debug_report,
            )
        )

        temporary_card = self._card(page)
        temporary_card.card_frame.pack(fill="x", pady=(0, 14))
        ttk.Label(temporary_card, text="Temporary files", style="Section.TLabel").pack(anchor="w")
        ttk.Label(
            temporary_card,
            text="Finds toolkit-owned temporary downloads and abandoned staging folders older than 24 hours. It skips active operations and user-selected export folders.",
            style="CardSub.TLabel",
            wraplength=760,
            justify="left",
        ).pack(anchor="w", fill="x", pady=(4, 10))
        self.debug_cleanup_button = self._button(
            temporary_card,
            text="Clean stale temporary files…",
            style="Warning.TButton",
            command=self._debug_clean_temporary_files,
        )
        self.debug_cleanup_button.pack(anchor="w")

        sdk_card = self._card(page)
        sdk_card.card_frame.pack(fill="x", pady=(0, 14))
        ttk.Label(sdk_card, text="Android SDK components", style="Section.TLabel").pack(anchor="w")
        ttk.Label(
            sdk_card,
            text="SDK packages may be shared with Android Studio and other projects. Removal shows the selected SDK path and requires confirmation.",
            style="CardSub.TLabel",
            wraplength=760,
            justify="left",
        ).pack(anchor="w", fill="x", pady=(4, 10))
        sdk_actions = self._wrap_row(sdk_card, style="Card.TFrame")
        sdk_actions.pack(fill="x")
        self.debug_remove_emulator_button = sdk_actions.add_widget(
            self._button(
                sdk_actions,
                text="Remove emulator package…",
                style="Danger.TButton",
                command=self._debug_remove_emulator_package,
            )
        )
        self.debug_remove_bootstrap_button = sdk_actions.add_widget(
            self._button(
                sdk_actions,
                text="Remove bootstrap tools…",
                style="Danger.TButton",
                command=self._debug_remove_bootstrap_tools,
            )
        )

        data_card = self._card(page)
        data_card.card_frame.pack(fill="x", pady=(0, 14))
        ttk.Label(data_card, text="Toolkit local data", style="Section.TLabel").pack(anchor="w")
        ttk.Label(
            data_card,
            text="Clear archived APK builds or reset saved toolkit settings and project profiles. SMS exports and files outside the toolkit archive are preserved.",
            style="CardSub.TLabel",
            wraplength=760,
            justify="left",
        ).pack(anchor="w", fill="x", pady=(4, 10))
        data_actions = self._wrap_row(data_card, style="Card.TFrame")
        data_actions.pack(fill="x")
        self.debug_clear_history_button = data_actions.add_widget(
            self._button(
                data_actions,
                text="Clear APK history…",
                style="Danger.TButton",
                command=self._debug_clear_apk_history,
            )
        )
        data_actions.add_widget(
            self._button(
                data_actions,
                text="Reset settings and profiles…",
                style="Danger.TButton",
                command=self._debug_reset_settings,
            )
        )
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
        self.debug_inventory_text.configure(state="normal")
        self.debug_inventory_text.delete("1.0", "end")
        self.debug_inventory_text.insert("1.0", text)
        self.debug_inventory_text.configure(state="disabled")
        busy = (
            self.build_running
            or self.update_running
            or self.emulator_download_running
            or self.emulator_busy
            or self.debug_sdk_remove_running
            or self.debug_cleanup_running
        )
        if hasattr(self, "debug_cleanup_button"):
            self.debug_cleanup_button.configure(state="disabled" if busy else "normal")
        if hasattr(self, "debug_clear_history_button"):
            self.debug_clear_history_button.configure(state="disabled" if busy else "normal")
        if hasattr(self, "debug_remove_emulator_button"):
            sdk_manager_ready = bool(self.android_sdk_root and self.sdkmanager_executable)
            emulator_installed = bool(
                self.android_sdk_root
                and (self.android_sdk_root / "emulator" / ("emulator.exe" if os.name == "nt" else "emulator")).is_file()
            )
            running_emulator = bool(self.emulator_states)
            self.debug_remove_emulator_button.configure(
                state="normal" if sdk_manager_ready and emulator_installed and not busy and not running_emulator else "disabled"
            )
        if hasattr(self, "debug_remove_bootstrap_button"):
            self.debug_remove_bootstrap_button.configure(
                state="normal" if self._debug_bootstrap_directories() and not busy else "disabled"
            )

    def _debug_tab_selected(self, _event=None):
        if getattr(self, "debug_tab_id", None) == self.tabs.select():
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
        c = UI_COLORS
        if hasattr(self, "header_project_pill") and self.header_project_pill.winfo_exists():
            project = (self.project_name.get() or "").strip() or "No project"
            self.header_project_pill.configure(text=f"▣  {project}")
        if hasattr(self, "header_device_pill") and self.header_device_pill.winfo_exists():
            serial = self.connected_serial
            if serial:
                label = self.connected_model or serial
                self.header_device_pill.configure(
                    text=f"●  {label}",
                    bg=c["pill_ok_bg"],
                    fg=c["pill_ok_fg"],
                )
            else:
                self.header_device_pill.configure(
                    text="○  No device",
                    bg=c["pill_idle_bg"],
                    fg=c["pill_idle_fg"],
                )

    def _copy_activity_log(self):
        text = self.output.get("1.0", "end-1c")
        self.clipboard_clear()
        self.clipboard_append(text)
        self.status.set("Activity log copied to clipboard.")

    def _clear_activity_log(self):
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.configure(state="disabled")
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
            tag = "error"
        elif re.search(r"\b(warning|warn|caution|stopped|disconnected)\b", line, re.IGNORECASE):
            tag = "warn"
        elif re.search(r"\b(succeeded|installed|connected|saved|complete|completed|ready)\b", line, re.IGNORECASE):
            tag = "success"
        else:
            tag = "info"
        self.output.configure(state="normal")
        self.output.insert("end", line + "\n", tag)
        if getattr(self, "activity_autoscroll", None) is None or self.activity_autoscroll.get():
            self.output.see("end")
        self.output.configure(state="disabled")

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
        dialog = tk.Toplevel(self)
        dialog.title("Activity log exported")
        dialog.transient(self)
        dialog.configure(bg=UI_COLORS["bg_canvas"])
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
        ttk.Label(panel, text=BUG_REPORT_EMAIL, style="TLabel").grid(
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
        self.emulator_selector.configure(values=avds)
        if self.emulator_avd.get() not in avds:
            self.emulator_avd.set(avds[0] if avds else "")
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
        self.emulator_selector.configure(state="disabled" if operation_active or not self.emulator_avds else "readonly")
        self.emulator_download_button.configure(
            state="disabled"
            if operation_active or setup_complete or not (self.android_sdk_root and self._cmdline_tools_download_info())
            else "normal",
            text="Setting up…" if self.emulator_download_running else "Download & create AVD",
        )
        self.emulator_refresh_button.configure(state="disabled" if operation_active else "normal")
        self.emulator_start_button.configure(
            state="normal" if not operation_active and avd and not state and self.emulator_executable and self.adb else "disabled"
        )
        self.emulator_stop_button.configure(
            state="normal" if not operation_active and state and state.get("managed") else "disabled"
        )
        self.emulator_connect_button.configure(
            state="normal" if not operation_active and state and state["device_state"] == "device" else "disabled"
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
        self.devices["values"] = usb_devices
        if self.last_device in usb_devices:
            self.target.set(self.last_device)
        elif self.target.get() not in usb_devices:
            self.target.set(usb_devices[0] if usb_devices else "")
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
        self.install_target_selector.configure(values=labels)
        current_serial = target_serials.get(self.install_target.get())
        if current_serial not in self.available_device_serials:
            preferred = self.connected_serial if self.connected_serial in self.available_device_serials else ""
            if not preferred:
                preferred = next(iter(target_serials.values()), "")
            selected_label = next((label for label, serial in target_serials.items() if serial == preferred), "")
            self.install_target.set(selected_label)

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
            self._set_button_label(self.disconnect_button, "Disconnect", style="Danger.TButton")
            self.disconnect_button.configure(state="normal")
            self.keep_awake_button.configure(state="normal")
            self.brightness_scale.configure(state="normal")
            self._render_connection_state()
            return
        self._set_button_label(self.disconnect_button, "Disconnect", style="Danger.TButton")
        self.disconnect_button.configure(state="disabled")
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
            connection_type = "Android Emulator" if self.connected_serial.startswith("emulator-") else self.connection_method.get()
            self.watch_device_label.configure(text=f"Ready: {self.connected_model or 'Android device'} · {connection_type}")
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
        self.active_label.configure(text=f"Connected device: {model}")
        self.connection_detail_label.configure(text=detail)
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
        self.show_error("Disconnect failed", message)

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
        self._update_header_pills()

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
        self.destroy()

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
        dialog = tk.Toplevel(self)
        dialog.title("Add Android project")
        dialog.transient(self)
        dialog.configure(background=UI_COLORS["bg_canvas"])
        self._fit_dialog(dialog, preferred=(720, 360), minimum=(520, 300))
        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(0, weight=1)

        content = ttk.Frame(dialog, padding=(20, 18, 20, 10))
        content.grid(row=0, column=0, sticky="nsew")
        content.grid_columnconfigure(1, weight=1)
        ttk.Label(content, text="Add Android project", style="Title.TLabel").grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 6))
        ttk.Label(
            content,
            text="Choose a Gradle Android project root or an Expo project root, then give it a name so you can find it in the project list.",
            style="Sub.TLabel",
            wraplength=640,
        ).grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, 16))

        project_name = tk.StringVar()
        project_folder = tk.StringVar()
        suggested_name = [""]
        ttk.Label(content, text="Project name (required)", style="TLabel").grid(row=2, column=0, columnspan=3, sticky="w")
        name_entry = ttk.Entry(content, textvariable=project_name)
        name_entry.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(4, 12))
        ttk.Label(content, text="Project folder (Gradle or Expo, required)", style="TLabel").grid(row=4, column=0, columnspan=3, sticky="w")
        ttk.Entry(content, textvariable=project_folder).grid(row=5, column=0, columnspan=2, sticky="ew", pady=(4, 0))

        def browse_folder():
            initial_dir = project_folder.get().strip() or self.project_dir.get().strip() or str(Path.home())
            selected = filedialog.askdirectory(title="Choose Gradle or Expo project folder", initialdir=initial_dir, parent=dialog)
            if selected:
                project_folder.set(selected)
                current_name = project_name.get().strip()
                if not current_name or current_name == suggested_name[0]:
                    suggested_name[0] = Path(selected).name
                    project_name.set(suggested_name[0])

        self._button(content, text="Browse…", command=browse_folder).grid(row=5, column=2, sticky="e", padx=(8, 0), pady=(4, 0))
        ttk.Label(
            content,
            text=f"Select the Gradle root containing {self._gradle_wrapper_name()}, or the Expo root containing package.json and the expo dependency. Expo projects generate android/ during the first build.",
            style="Sub.TLabel",
            wraplength=640,
        ).grid(row=6, column=0, columnspan=3, sticky="w", pady=(8, 0))

        footer = ttk.Frame(dialog, padding=(20, 10, 20, 18))
        footer.grid(row=1, column=0, sticky="ew")
        footer.grid_columnconfigure(0, weight=1)

        def create_profile():
            name = project_name.get().strip()
            if not name:
                self.show_error("Project name required", "Enter a name for this project.", parent=dialog)
                name_entry.focus_set()
                return
            folder_text = project_folder.get().strip()
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
        self.build_button.configure(
            state="disabled" if running else "normal",
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
        dialog = tk.Toplevel(self)
        dialog.title("APK build failed")
        dialog.configure(background=UI_COLORS["bg_canvas"])
        dialog.transient(self)
        window_width, _window_height = self._fit_dialog(dialog, preferred=(1100, 850), minimum=(640, 480))
        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(1, weight=1)

        header = ttk.Frame(dialog, padding=(18, 18, 18, 12))
        header.grid(row=0, column=0, sticky="ew")
        ttk.Label(header, text="APK build failed", style="Title.TLabel").pack(anchor="w", pady=(0, 8))
        ttk.Label(
            header,
            text="Review the build output below. You can scroll through it or close this window to return to DCM Android Toolkit.",
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
            bg="#0f172a",
            fg="#e2e8f0",
            insertbackground="white",
            selectbackground=UI_COLORS["accent"],
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
            self.status.set("Full build output copied to clipboard")
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
        dialog.configure(background=UI_COLORS["bg_canvas"])
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
        dialog.configure(background=UI_COLORS["bg_canvas"])
        self._fit_dialog(dialog, preferred=(1280, 760), minimum=(760, 480))
        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(1, weight=1)

        heading = ttk.Frame(dialog, padding=(18, 16, 18, 12))
        heading.grid(row=0, column=0, sticky="ew")
        ttk.Label(heading, text="APK version history", style="Title.TLabel").pack(side="left")
        count_label = ttk.Label(heading, text="", style="Sub.TLabel")
        count_label.pack(side="right")

        style = ttk.Style(dialog)
        style.configure("History.Treeview", background=UI_COLORS["bg_surface"], fieldbackground=UI_COLORS["bg_surface"], foreground=UI_COLORS["text_primary"], rowheight=28, font=self._ui_font(10))
        style.map("History.Treeview", background=[("selected", UI_COLORS["accent"])], foreground=[("selected", "#ffffff")])
        style.configure("History.Treeview.Heading", background=UI_COLORS["bg_subtle"], foreground=UI_COLORS["text_primary"], font=self._ui_font(10, "bold"))
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
            note_dialog.configure(background=UI_COLORS["bg_canvas"])
            self._fit_dialog(note_dialog, preferred=(760, 620), minimum=(520, 420))
            note_dialog.grid_columnconfigure(0, weight=1)
            note_dialog.grid_rowconfigure(1, weight=1)
            ttk.Label(note_dialog, text=f"Internal note · {entry.get('version_name', 'build')}", style="Title.TLabel", wraplength=680).grid(row=0, column=0, sticky="w", padx=18, pady=(18, 10))
            note = tk.Text(note_dialog, wrap="word", bg=UI_COLORS["bg_surface"], fg=UI_COLORS["text_primary"], insertbackground=UI_COLORS["text_primary"], font=self._ui_font(11), padx=10, pady=8, relief="flat", highlightthickness=1, highlightbackground=UI_COLORS["border"])
            note.grid(row=1, column=0, sticky="nsew", padx=18)
            note.insert("1.0", entry.get("note", ""))
            actions = ttk.Frame(note_dialog, padding=(18, 12, 18, 18))
            actions.grid(row=2, column=0, sticky="ew")

            def save_note():
                entry["note"] = note.get("1.0", "end-1c").strip()
                try:
                    save_history()
                except OSError as error:
                    self.show_error("Could not save note", str(error), parent=note_dialog)
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
                self.after(0, lambda: self.count_button.configure(state="normal"))
                self.after(0, lambda: self.preview_button.configure(state="normal"))
                self.after(0, lambda: self.export_button.configure(state="normal"))

        threading.Thread(target=worker, daemon=True).start()

    def _show_sms_preview(self, preview_json, count):
        dialog = tk.Toplevel(self)
        dialog.title("SMS content preview")
        dialog.transient(self)
        self._fit_dialog(dialog, preferred=(1000, 900), minimum=(600, 560))
        dialog.configure(background=UI_COLORS["bg_canvas"])
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
        content = tk.Text(text_frame, wrap="word", bg=UI_COLORS["bg_surface"], fg=UI_COLORS["text_primary"], insertbackground=UI_COLORS["text_primary"], selectbackground=UI_COLORS["accent_soft"], font=("Menlo", 10), padx=12, pady=10, relief="flat", highlightthickness=0)
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=content.yview)
        content.configure(yscrollcommand=scrollbar.set)
        content.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        content.insert("1.0", preview_json)
        content.configure(state="disabled")
        actions = ttk.Frame(panel, style="TFrame")
        actions.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        self._button(actions, text="Close", command=dialog.destroy).pack(side="right")

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

    app = Deployer()
    if len(sys.argv) > 1 and sys.argv[1] == "--update-complete":
        updated_version = sys.argv[2] if len(sys.argv) > 2 else APP_VERSION
        app.after(500, lambda: messagebox.showinfo("Update complete", f"DCM Android Toolkit was updated to {updated_version}.", parent=app))
    elif len(sys.argv) > 1 and sys.argv[1] == "--update-error":
        update_error = sys.argv[2] if len(sys.argv) > 2 else "The update could not be applied."
        app.after(500, lambda: app.show_error("Update failed", update_error, parent=app))
    app.mainloop()
