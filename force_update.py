#!/usr/bin/env python3
"""Dependency-free recovery updater used by the platform force-update launchers."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import ssl
import stat
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

APP_ROOT = Path(__file__).resolve().parent
GITHUB_REPOSITORY = "DotComMediaInternetAgency/dcm-android-toolkit"
MAX_ARCHIVE_BYTES = 100 * 1024 * 1024
USER_AGENT = "DCM-Android-Toolkit-Force-Updater"


def _open_url(request, timeout=30):
    try:
        return urllib.request.urlopen(request, timeout=timeout)
    except urllib.error.URLError as error:
        if not isinstance(error.reason, ssl.SSLCertVerificationError):
            raise
        try:
            import certifi
        except ImportError:
            raise error
        return urllib.request.urlopen(
            request,
            timeout=timeout,
            context=ssl.create_default_context(cafile=certifi.where()),
        )


def _assert_app_closed():
    app_script = str((APP_ROOT / "dcm_android_toolkit.py").resolve()).casefold()
    if os.name == "nt":
        command = (
            "$target = '" + app_script.replace("'", "''") + "'; "
            "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and "
            "$_.CommandLine.ToLowerInvariant().Contains($target) } | "
            "Select-Object -ExpandProperty ProcessId"
        )
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0 and result.stdout.strip():
            raise RuntimeError("Close DCM Android Toolkit before running the force updater, then try again.")
    elif sys.platform == "darwin":
        result = subprocess.run(["ps", "-A", "-o", "pid=,command="], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                fields = line.strip().split(None, 1)
                if len(fields) == 2 and fields[0].isdigit() and int(fields[0]) != os.getpid():
                    if app_script in fields[1].casefold():
                        raise RuntimeError("Close DCM Android Toolkit before running the force updater, then try again.")


def _fetch_release():
    request = urllib.request.Request(
        f"https://api.github.com/repos/{GITHUB_REPOSITORY}/releases/latest",
        headers={"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT},
    )
    with _open_url(request) as response:
        if not response.geturl().startswith("https://api.github.com/"):
            raise ValueError("GitHub redirected the release check to an unexpected URL.")
        release = json.loads(response.read().decode("utf-8"))

    tag = str(release.get("tag_name", ""))
    version = tag[1:] if tag.lower().startswith("v") else tag
    if not re.fullmatch(r"\d+(?:\.\d+)+", version):
        raise ValueError(f"GitHub returned an invalid release version: {tag!r}.")
    expected_name = f"dcm-android-toolkit-{version}-source.zip"
    asset = next((item for item in release.get("assets", []) if item.get("name") == expected_name), None)
    if not asset:
        raise ValueError(f"The latest GitHub release is missing {expected_name}.")
    digest = str(asset.get("digest", ""))
    url = str(asset.get("browser_download_url", ""))
    if not re.fullmatch(r"sha256:[0-9a-fA-F]{64}", digest) or not url.startswith("https://github.com/"):
        raise ValueError("The latest GitHub release does not contain a secure, verifiable source ZIP.")
    return version, digest.split(":", 1)[1].lower(), url


def _download_archive(url, expected_digest):
    handle, archive_name = tempfile.mkstemp(prefix="dcm-force-update-", suffix=".zip", dir=APP_ROOT)
    archive = Path(archive_name)
    digest = hashlib.sha256()
    total = 0
    try:
        request = urllib.request.Request(url, headers={"Accept": "application/octet-stream", "User-Agent": USER_AGENT})
        with os.fdopen(handle, "wb") as output:
            with _open_url(request, timeout=60) as response:
                if not response.geturl().startswith("https://"):
                    raise ValueError("GitHub redirected the source ZIP download to an insecure URL.")
                content_length = response.headers.get("Content-Length")
                if content_length and int(content_length) > MAX_ARCHIVE_BYTES:
                    raise ValueError("The source ZIP exceeds the 100 MB download limit.")
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > MAX_ARCHIVE_BYTES:
                        raise ValueError("The source ZIP exceeded the 100 MB download limit.")
                    digest.update(chunk)
                    output.write(chunk)
                    print(f"Downloaded {total / (1024 * 1024):.1f} MB", flush=True)
        if digest.hexdigest() != expected_digest:
            raise ValueError("The source ZIP failed GitHub's SHA-256 digest verification.")
        return archive
    except Exception:
        try:
            archive.unlink()
        except OSError:
            pass
        raise


def _validated_entries(archive, expected_version):
    prefix = f"dcm-android-toolkit-{expected_version}"
    entries = []
    unpacked = 0
    seen = set()
    has_app = False
    with zipfile.ZipFile(archive) as package:
        for info in package.infolist():
            raw_name = info.filename
            member = PurePosixPath(raw_name)
            if "\\" in raw_name or member.is_absolute() or ".." in member.parts or not member.parts:
                raise ValueError("The source ZIP contains an unsafe path.")
            if member.parts[0] != prefix:
                raise ValueError("The source ZIP does not match the expected release folder.")
            parts = member.parts[1:]
            if not parts or info.is_dir():
                continue
            mode = info.external_attr >> 16
            if stat.S_ISLNK(mode) or (stat.S_IFMT(mode) not in (0, stat.S_IFREG)):
                raise ValueError("The source ZIP contains a non-regular file.")
            if ":" in parts[0] or any(part in (".git", "data", "__pycache__", ".venv") for part in parts):
                continue
            relative = PurePosixPath(*parts)
            if relative.as_posix() == "dcm-android-toolkit.json" or relative.suffix.lower() in (".pyc", ".pyo"):
                continue
            normalized = relative.as_posix()
            if normalized in seen:
                raise ValueError(f"The source ZIP contains a duplicate path: {normalized}")
            seen.add(normalized)
            unpacked += info.file_size
            if unpacked > MAX_ARCHIVE_BYTES:
                raise ValueError("The expanded source ZIP exceeds the 100 MB safety limit.")
            if normalized == "dcm_android_toolkit.py":
                source = package.read(info).decode("utf-8")
                version_match = re.search(r'^APP_VERSION\s*=\s*["\']([^"\']+)["\']', source, re.MULTILINE)
                if not version_match or version_match.group(1) != expected_version:
                    raise ValueError("The source code version does not match the GitHub release tag.")
                has_app = True
            entries.append((info, relative, mode))
    if not has_app:
        raise ValueError("The source ZIP does not contain the toolkit application source.")
    return entries


def _apply_archive(archive, expected_version):
    target = APP_ROOT.resolve()
    stage_root = Path(tempfile.mkdtemp(prefix=".dcm-force-update-", dir=target.parent))
    payload_root = stage_root / "payload"
    backup_root = stage_root / "backup"
    applied = []
    try:
        entries = _validated_entries(archive, expected_version)
        with zipfile.ZipFile(archive) as package:
            for info, relative, mode in entries:
                staged = payload_root.joinpath(*relative.parts)
                staged.parent.mkdir(parents=True, exist_ok=True)
                with package.open(info) as source, staged.open("xb") as output:
                    shutil.copyfileobj(source, output, length=1024 * 1024)
                if mode & 0o777 and os.name != "nt":
                    staged.chmod(mode & 0o777)

        for _info, relative, _mode in sorted(entries, key=lambda row: row[1].as_posix()):
            destination = target.joinpath(*relative.parts)
            parent = target
            for part in relative.parts[:-1]:
                parent = parent / part
                if parent.is_symlink():
                    raise ValueError(f"Refusing to update through a symbolic link: {parent}")
            if destination.is_symlink() or not destination.parent.resolve().is_relative_to(target):
                raise ValueError(f"Refusing an unsafe update destination: {destination}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            exists = destination.exists()
            if exists and not destination.is_file():
                raise ValueError(f"Cannot replace a non-file application path: {destination}")
            backup = backup_root.joinpath(*relative.parts)
            if exists:
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(destination, backup)
            os.replace(payload_root.joinpath(*relative.parts), destination)
            applied.append((destination, backup, exists))
    except Exception as error:
        failures = []
        for destination, backup, existed in reversed(applied):
            try:
                if existed and backup.exists():
                    os.replace(backup, destination)
                elif destination.exists():
                    destination.unlink()
            except OSError as rollback_error:
                failures.append(str(rollback_error))
        if failures:
            raise RuntimeError(f"{error}\nRollback also failed: {'; '.join(failures)}") from error
        raise
    finally:
        shutil.rmtree(stage_root, ignore_errors=True)


def main():
    _assert_app_closed()
    version, digest, url = _fetch_release()
    print(f"Downloading DCM Android Toolkit {version}…", flush=True)
    archive = _download_archive(url, digest)
    try:
        print("Verifying and applying the official source archive…", flush=True)
        _apply_archive(archive, version)
    finally:
        try:
            archive.unlink()
        except OSError:
            pass
    print(f"Force update complete: {version}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Force update failed: {error}", file=sys.stderr)
        raise SystemExit(1)
