param([string]$UpdateCompleteVersion = '')

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $ProjectRoot

function Get-WinGetPath {
    $command = Get-Command winget.exe -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }

    $path = Join-Path $env:LOCALAPPDATA 'Microsoft\WindowsApps\winget.exe'
    if (Test-Path -LiteralPath $path) { return $path }
    return $null
}

function Install-WinGetPackage([string]$Id, [switch]$UserScope) {
    $arguments = @('install', '--exact', '--id', $Id, '--silent', '--accept-source-agreements', '--accept-package-agreements')
    if ($UserScope) { $arguments += @('--scope', 'user') }
    Write-Host "Installing $Id..."
    & $script:WinGetPath @arguments
    if ($LASTEXITCODE -ne 0) { throw "winget could not install $Id (exit code $LASTEXITCODE)." }
}

function Test-Python([string]$Path) {
    if (-not $Path -or -not (Test-Path -LiteralPath $Path)) { return $null }
    $output = & $Path -c 'import sys; assert sys.version_info >= (3, 9); print(sys.executable)' 2>$null
    if ($LASTEXITCODE -eq 0 -and $output) { return ([string]($output | Select-Object -Last 1)).Trim() }
    return $null
}

function Find-Python {
    $launcher = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($launcher) {
        $output = & $launcher.Source -3 -c 'import sys; assert sys.version_info >= (3, 9); print(sys.executable)' 2>$null
        if ($LASTEXITCODE -eq 0 -and $output) { return ([string]($output | Select-Object -Last 1)).Trim() }
    }

    $candidates = @()
    $commands = Get-Command python.exe -All -ErrorAction SilentlyContinue
    foreach ($command in $commands) {
        if ($command.Source -notmatch '\\Microsoft\\WindowsApps\\') { $candidates += $command.Source }
    }
    $pythonRoot = Join-Path $env:LOCALAPPDATA 'Programs\Python'
    if (Test-Path -LiteralPath $pythonRoot) {
        $candidates += Get-ChildItem -LiteralPath $pythonRoot -Directory -Filter 'Python313*' -ErrorAction SilentlyContinue | ForEach-Object { Join-Path $_.FullName 'python.exe' }
    }
    $candidates += (Join-Path $env:ProgramFiles 'Python313\python.exe')

    foreach ($candidate in $candidates | Select-Object -Unique) {
        $resolved = Test-Python $candidate
        if ($resolved) { return $resolved }
    }
    return $null
}

function Find-WinGetBinary([string]$PackagePrefix, [string]$FileName) {
    $links = Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Links'
    $linkedBinary = Join-Path $links $FileName
    if (Test-Path -LiteralPath $linkedBinary) { return $linkedBinary }

    $packages = Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Packages'
    if (Test-Path -LiteralPath $packages) {
        $packageDirs = Get-ChildItem -LiteralPath $packages -Directory -Filter "$PackagePrefix*" -ErrorAction SilentlyContinue
        foreach ($packageDir in $packageDirs) {
            $binary = Get-ChildItem -LiteralPath $packageDir.FullName -File -Filter $FileName -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($binary) { return $binary.FullName }
        }
    }
    return $null
}

function Find-Adb {
    $command = Get-Command adb.exe -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }

    foreach ($sdk in @($env:ANDROID_SDK_ROOT, $env:ANDROID_HOME, (Join-Path $env:LOCALAPPDATA 'Android\Sdk'))) {
        if ($sdk) {
            $candidate = Join-Path $sdk 'platform-tools\adb.exe'
            if (Test-Path -LiteralPath $candidate) { return $candidate }
        }
    }
    return Find-WinGetBinary 'Google.PlatformTools_' 'adb.exe'
}

function Get-JavaMajor([string]$JavaPath) {
    if (-not $JavaPath -or -not (Test-Path -LiteralPath $JavaPath)) { return 0 }

    # Prefer the JDK's release metadata. `java -version` writes to stderr, and
    # PowerShell can turn that normal output into a NativeCommandError when the
    # script uses $ErrorActionPreference = 'Stop'.
    $javaHome = Split-Path -Parent (Split-Path -Parent $JavaPath)
    $releaseFile = Join-Path $javaHome 'release'
    if (Test-Path -LiteralPath $releaseFile) {
        $versionLine = Get-Content -LiteralPath $releaseFile -ErrorAction SilentlyContinue |
            Where-Object { $_ -match '^JAVA_VERSION=' } |
            Select-Object -First 1
        if ($versionLine -match '^JAVA_VERSION="?(?<version>[0-9]+(?:\.[0-9]+)*)"?$') {
            $parts = $Matches['version'].Split('.')
            if ($parts[0] -eq '1' -and $parts.Count -gt 1) { return [int]$parts[1] }
            return [int]$parts[0]
        }
    }

    $previousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        $output = (& $JavaPath -version 2>&1 | Out-String)
    } catch {
        $output = [string]$_
    } finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
    if ($output -match 'version\s+"?(?<version>(?:1\.)?\d+(?:\.\d+)*)') {
        $parts = $Matches['version'].Split('.')
        if ($parts[0] -eq '1' -and $parts.Count -gt 1) { return [int]$parts[1] }
        return [int]$parts[0]
    }
    return 0
}

function Find-JavaHome {
    $homes = @()
    if ($env:JAVA_HOME) { $homes += $env:JAVA_HOME }

    foreach ($pattern in @('Eclipse Adoptium\jdk-*', 'Microsoft\jdk-*')) {
        $parent = Join-Path $env:ProgramFiles (Split-Path $pattern -Parent)
        if (Test-Path -LiteralPath $parent) {
            $leaf = Split-Path $pattern -Leaf
            $homes += Get-ChildItem -LiteralPath $parent -Directory -Filter $leaf -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName }
        }
    }

    foreach ($javaDirectory in $homes | Select-Object -Unique) {
        $javaPath = Join-Path $javaDirectory 'bin\java.exe'
        if ((Test-Path -LiteralPath (Join-Path $javaDirectory 'release')) -and (Get-JavaMajor $javaPath) -ge 17) { return $javaDirectory }
    }

    $javaCommand = Get-Command java.exe -ErrorAction SilentlyContinue
    if ($javaCommand -and (Get-JavaMajor $javaCommand.Source) -ge 17) {
        $javaDirectory = Split-Path -Parent (Split-Path -Parent $javaCommand.Source)
        if (Test-Path -LiteralPath (Join-Path $javaDirectory 'release')) { return $javaDirectory }
    }
    return $null
}

try {
    $script:WinGetPath = Get-WinGetPath
    if (-not $script:WinGetPath) {
        try {
            Add-AppxPackage -RegisterByFamilyName -MainPackage Microsoft.DesktopAppInstaller_8wekyb3d8bbwe -ErrorAction Stop
        } catch { }
        $script:WinGetPath = Get-WinGetPath
    }
    if (-not $script:WinGetPath) {
        try { Start-Process 'ms-windows-store://pdp/?ProductId=9NBLGGH4NNS1' } catch { }
        throw 'Windows App Installer (winget) is missing. Install it from the opened Microsoft Store page, then launch again.'
    }

    $python = Find-Python
    if (-not $python) {
        Install-WinGetPackage 'Python.Python.3.13' -UserScope
        $python = Find-Python
    }
    if (-not $python) { throw 'Python 3.9+ could not be found after installation.' }

    $adb = Find-Adb
    if (-not $adb) {
        Install-WinGetPackage 'Google.PlatformTools'
        $adb = Find-Adb
    }
    if (-not $adb) { throw 'Android SDK Platform-Tools (adb) could not be found after installation.' }
    $env:PATH = "$(Split-Path -Parent $adb);$(Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Links');$env:PATH"

    $javaHome = Find-JavaHome
    if (-not $javaHome) {
        Install-WinGetPackage 'EclipseAdoptium.Temurin.17.JDK'
        $javaHome = Find-JavaHome
    }
    if (-not $javaHome) { throw 'A JDK 17 or newer could not be found after installation.' }
    $env:JAVA_HOME = $javaHome
    $env:PATH = "$(Join-Path $javaHome 'bin');$env:PATH"

    if (-not (Get-Command scrcpy.exe -ErrorAction SilentlyContinue)) {
        try {
            Install-WinGetPackage 'Genymobile.scrcpy'
            $scrcpy = Find-WinGetBinary 'Genymobile.scrcpy_' 'scrcpy.exe'
            if ($scrcpy) { $env:PATH = "$(Split-Path -Parent $scrcpy);$env:PATH" }
        } catch {
            Write-Warning 'Optional scrcpy could not be installed. Screen mirroring will remain unavailable.'
        }
    }

    $venvPython = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
    $venvPythonW = Join-Path $ProjectRoot '.venv\Scripts\pythonw.exe'
    if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
        Write-Host 'Creating local Python virtual environment (.venv)...'
        & $python -m venv (Join-Path $ProjectRoot '.venv')
        if ($LASTEXITCODE -ne 0) { throw 'Could not create .venv virtual environment.' }
    }
    & $venvPython -c 'import PySide6.QtWidgets, PySide6.QtSvg' 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host 'Installing PySide6 desktop UI dependencies...'
        & $venvPython -m pip install -r (Join-Path $ProjectRoot 'requirements.txt')
        if ($LASTEXITCODE -ne 0) { throw 'Could not install PySide6 dependencies.' }
    }

    Write-Host 'All required tools are ready. Starting DCM Android Toolkit...'
    $appPath = Join-Path $ProjectRoot 'dcm_android_toolkit.py'
    $appArguments = @($appPath)
    if ($UpdateCompleteVersion) { $appArguments += @('--update-complete', $UpdateCompleteVersion) }
    $argumentLine = ($appArguments | ForEach-Object { '"{0}"' -f $_ }) -join ' '
    if (Test-Path -LiteralPath $venvPythonW -PathType Leaf) {
        Start-Process -FilePath $venvPythonW -ArgumentList $argumentLine -WorkingDirectory $ProjectRoot
    } else {
        Start-Process -FilePath $venvPython -ArgumentList $argumentLine -WorkingDirectory $ProjectRoot -WindowStyle Hidden
    }
    exit 0
} catch {
    Write-Host "`nSetup failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
