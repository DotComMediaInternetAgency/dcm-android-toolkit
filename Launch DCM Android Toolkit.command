#!/bin/bash
set -euo pipefail
cd -- "$(dirname -- "$0")"

fail() {
    printf '\nSetup failed: %s\n' "$1" >&2
    read -r -p 'Press Return to close this window. ' _ || true
    exit 1
}

if [[ "$(uname -s)" != "Darwin" ]]; then
    fail 'This launcher is for macOS.'
fi

BREW="$(command -v brew || true)"
if [[ -z "$BREW" ]]; then
    for candidate in /opt/homebrew/bin/brew /usr/local/bin/brew; do
        if [[ -x "$candidate" ]]; then BREW="$candidate"; break; fi
    done
fi

if [[ -z "$BREW" ]]; then
    command -v curl >/dev/null 2>&1 || fail 'curl is required to install Homebrew.'
    echo 'Homebrew was not found. Installing Homebrew...'
    INSTALLER="$(mktemp -t dcm-homebrew-install.XXXXXX)" || fail 'Could not create a temporary installer file.'
    if ! curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh -o "$INSTALLER"; then
        rm -f "$INSTALLER"
        fail 'Could not download the official Homebrew installer.'
    fi
    if ! NONINTERACTIVE=1 /bin/bash "$INSTALLER"; then
        rm -f "$INSTALLER"
        fail 'Homebrew could not be installed. Check the installer output, network access, and macOS administrator or Command Line Tools requirements.'
    fi
    rm -f "$INSTALLER"
    for candidate in /opt/homebrew/bin/brew /usr/local/bin/brew; do
        if [[ -x "$candidate" ]]; then BREW="$candidate"; break; fi
    done
fi
[[ -n "$BREW" ]] || fail 'Homebrew installation finished, but brew was not found in its standard location.'
eval "$("$BREW" shellenv)"

PYTHON_BIN="$(command -v python3 || true)"
python_has_tk() {
    [[ -n "$1" ]] && "$1" -c 'import sys, tkinter; sys.exit(0 if sys.version_info >= (3, 9) else 1)' >/dev/null 2>&1
}
if ! python_has_tk "$PYTHON_BIN"; then
    echo 'Installing Python 3.13 with Tk support...'
    "$BREW" install python@3.13 python-tk@3.13 || fail 'Could not install Python with Tk support.'
    PYTHON_BIN="$("$BREW" --prefix python@3.13)/bin/python3.13"
fi
python_has_tk "$PYTHON_BIN" || fail 'Python 3.9+ with Tk support is required.'

if ! command -v adb >/dev/null 2>&1; then
    for sdk in "${ANDROID_SDK_ROOT:-}" "${ANDROID_HOME:-}" "$HOME/Library/Android/sdk"; do
        if [[ -n "$sdk" && -x "$sdk/platform-tools/adb" ]]; then
            export PATH="$sdk/platform-tools:$PATH"
            break
        fi
    done
fi
if ! command -v adb >/dev/null 2>&1; then
    echo 'Installing Android SDK Platform-Tools...'
    "$BREW" install --cask android-platform-tools || fail 'Could not install Android SDK Platform-Tools.'
    eval "$("$BREW" shellenv)"
fi
command -v adb >/dev/null 2>&1 || fail 'ADB is still unavailable after installation.'

java_is_ready() {
    local candidate version major
    for candidate in "${JAVA_HOME:-}/bin/java" "$(command -v java || true)" "$("$BREW" --prefix openjdk@17 2>/dev/null || true)/bin/java"; do
        [[ -x "$candidate" ]] || continue
        version="$("$candidate" -version 2>&1 | awk -F '"' '/version/ {print $2; exit}')"
        major="${version%%.*}"
        if [[ "$major" =~ ^[0-9]+$ ]] && (( major >= 17 )); then
            return 0
        fi
    done
    return 1
}
if ! java_is_ready; then
    echo 'Installing JDK 17...'
    "$BREW" install openjdk@17 || fail 'Could not install JDK 17.'
fi
JAVA_PREFIX="$("$BREW" --prefix openjdk@17 2>/dev/null || true)"
if [[ -n "$JAVA_PREFIX" && -d "$JAVA_PREFIX/libexec/openjdk.jdk/Contents/Home" ]]; then
    export JAVA_HOME="$JAVA_PREFIX/libexec/openjdk.jdk/Contents/Home"
    export PATH="$JAVA_HOME/bin:$PATH"
fi
java_is_ready || fail 'A JDK 17 or newer is required to build APKs.'

if ! command -v scrcpy >/dev/null 2>&1; then
    echo 'Installing optional scrcpy screen mirroring support...'
    if ! "$BREW" install scrcpy; then
        echo 'scrcpy could not be installed. The app will still start; screen mirroring will be unavailable.' >&2
    fi
    eval "$("$BREW" shellenv)"
fi

exec "$PYTHON_BIN" dcm_android_toolkit.py
