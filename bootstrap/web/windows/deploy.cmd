:: ==============================================================================
:: Example Music Limited
::
:: deploy.cmd
::
:: Version History
:: ---------------
:: 1.0.0   2026-09-03   Initial draft (Robert)
:: 1.1.0   2026-09-04   Real fixes + Robert's own requested changes:
::  - Architecture detection via %PROCESSOR_ARCHITECTURE% (the same real,
::    already-proven pattern Detect-Platform.cmd/Deploy-OpenSSH.cmd both
::    use) -- "Pre-flight checks" section at the top, adapted from
::    Detect-Platform.cmd's own Section 1 per Robert's request.
::  - Confirmed against Deploy-OpenSSH.cmd's own dated changelog
::    (2026-08-15) and the real repo layout that the server directory is
::    amd64/, not x86_64/ -- x86_64/ was a real bug already found and
::    fixed once in that sibling script; using it here would have
::    silently reintroduced it. (Robert confirmed amd64/ directly.)
::  - Fixed real syntax bugs: two bare paths (ProgramData\...\Drivers,
::    ...\Logs) with no `mkdir` keyword in front of them -- CMD would
::    have tried to "run" the path as a command and failed; an
::    unbalanced quote around the virtio-win-gt-x64.msi URL that broke
::    certutil's whole argument; a ".si" extension that should have
::    been ".msi"; a duplicate SetupComplete.cmd download where
::    Detect-Platform.cmd was meant to be fetched instead.
::  - Now arch-aware for BOTH the unattend XML (headlessunattend.xml vs
::    headlessunattend-arm64.xml -- same real reason Deploy-OpenSSH.cmd
::    already picks per-arch: Windows Setup silently skips any
::    processorArchitecture-tagged <component> that doesn't match the
::    image being installed) and the driver downloads (amd64 vs arm64
::    filenames, arm64 also staging the amd64 fallback builds --
::    Detect-Platform.cmd's own :KVM logic tries the native arm64 MSIs
::    first and falls back to these if either is missing or fails, so
::    they need to already be on disk either way).
::  - Directory creation + driver downloads confirmed to run AFTER
::    setup.exe -- C:\ProgramData\ExampleMusic doesn't exist as a real
::    path until the image has actually been applied to that partition,
::    so this was already structurally necessary, now made explicit.
::
:: Purpose
:: -------
:: Covers WinPE-side driver injection this repo doesn't otherwise have
:: anywhere:
::   1. Injects drivers into the RUNNING WinPE environment itself
::      (pnputil), for hardware WinPE's own stock boot image doesn't
::      natively see.
::   2. Injects drivers directly into the OFFLINE target image via DISM,
::      immediately after Setup.exe applies it and before first boot --
::      critical for boot-time drivers (e.g. VirtIO storage) that must
::      already be present the moment the new Windows first starts,
::      which Deploy-OpenSSH.cmd/Detect-Platform.cmd's post-boot
::      msiexec-based installs can't help with (the OS has to already be
::      able to boot and reach its own storage before either of those
::      ever runs).
:: Deploy-OpenSSH.cmd (a separate, more complete script) already covers
:: drive enumeration/menu selection, Detect-Platform.cmd/
:: Install-OpenSSH.ps1 staging, and post-boot guest-tool installs --
:: this script is a narrower complement to it, not a replacement.
:: Assumes the install media is Y: and the target is C: (matches this
:: script's own existing manual, technician-guided "swap the CD" flow,
:: unlike Deploy-OpenSSH.cmd's automated drive-enumeration/menu) --
:: not touched here since fixing that wasn't asked for.
::
:: ==============================================================================

@ECHO OFF
setlocal EnableDelayedExpansion
CLS

:: ------------------------------------------------------------------------------
:: Pre-flight checks (elements of Detect-Platform.cmd's own Section 1, per
:: Robert's request -- architecture only, not the SMBIOS/platform detection
:: further down in that file, since this script's own downloads are already
:: fixed to KVM/Proxmox guest tools regardless of platform, matching this
:: estate's Proxmox-only reality).
:: ------------------------------------------------------------------------------
set "ARCH=unknown"
if /i "%PROCESSOR_ARCHITECTURE%"=="AMD64" set "ARCH=x86_64"
if /i "%PROCESSOR_ARCHITECTURE%"=="ARM64" set "ARCH=arm64"

echo  ==============================================================================
echo   Example Music Limited - deploy.cmd
echo  ==============================================================================
echo.
echo   Architecture : %ARCH%
echo.

if "%ARCH%"=="unknown" (
    echo  [ERROR] Could not determine architecture from PROCESSOR_ARCHITECTURE=%PROCESSOR_ARCHITECTURE%.
    echo          Aborting rather than guessing which driver set to stage.
    exit /b 1
)

ECHO Injecting drivers into running WinPE
pnputil /add-driver X:\Tools\Drivers\*.inf /subdirs /install

ECHO Setting constant variables
set "SERVER=192.168.139.50"
set "BASE=http://%SERVER%/windows"
set "SCRIPTS=C:\Windows\Setup\Scripts"

:: Arch-appropriate unattend file -- same real reason Deploy-OpenSSH.cmd
:: already does this (see that file's own 1.6.0 changelog entry): Windows
:: Setup silently skips any <component> whose processorArchitecture doesn't
:: match the image being installed, so an amd64-only answer file applies
:: NONE of its settings on an arm64 target.
set "UNATTEND_SRC=headlessunattend.xml"
if "%ARCH%"=="arm64" set "UNATTEND_SRC=headlessunattend-arm64.xml"

ECHO Downloading windows Unattended XML file
certutil.exe -urlcache -f "%BASE%/unattend/%UNATTEND_SRC%" X:\headlessunattend.xml

ECHO Swap the CD for a windows Install CD and
pause
Y:\Sources\setup.exe /unattend:X:\headlessunattend.xml /noreboot

:: ------------------------------------------------------------------------------
:: Everything below here runs against the just-installed image on C:\ -- it
:: does not exist as a real path until Setup.exe has actually applied it, so
:: this must stay after the setup.exe call above, not before it.
:: ------------------------------------------------------------------------------

ECHO Adding post install Panther files
MKDIR "%SCRIPTS%"
dism /Image:C:\ /Add-Driver /Driver:X:\Tools\Drivers /Recurse

certutil.exe -urlcache -f "%BASE%/SetupComplete.cmd" "%SCRIPTS%\SetupComplete.cmd"
certutil.exe -urlcache -f "%BASE%/Detect-Platform.cmd" "%SCRIPTS%\Detect-Platform.cmd"
certutil.exe -urlcache -f "%BASE%/Install-OpenSSH.ps1" "%SCRIPTS%\Install-OpenSSH.ps1"

ECHO Setting up Scratch Directory C:\ProgramData\ExampleMusic
mkdir C:\ProgramData\ExampleMusic
mkdir C:\ProgramData\ExampleMusic\Drivers
mkdir C:\ProgramData\ExampleMusic\Logs

if "%ARCH%"=="x86_64" (
    certutil.exe -urlcache -f "%BASE%/amd64/qemu-ga-x86_64.msi" C:\ProgramData\ExampleMusic\Drivers\qemu-ga-x86_64.msi
    certutil.exe -urlcache -f "%BASE%/amd64/virtio-win-gt-x64.msi" C:\ProgramData\ExampleMusic\Drivers\virtio-win-gt-x64.msi
)

if "%ARCH%"=="arm64" (
    certutil.exe -urlcache -f "%BASE%/arm64/qemu-ga-arm64.msi" C:\ProgramData\ExampleMusic\Drivers\qemu-ga-arm64.msi
    certutil.exe -urlcache -f "%BASE%/arm64/virtio-win-gt-arm64.msi" C:\ProgramData\ExampleMusic\Drivers\virtio-win-gt-arm64.msi
    :: amd64 fallback builds -- Detect-Platform.cmd's own :KVM logic (1.2.0)
    :: tries the native arm64 MSIs above first and falls back to these if
    :: either is missing or fails, same as Deploy-OpenSSH.cmd already stages
    :: both for the same reason.
    certutil.exe -urlcache -f "%BASE%/amd64/qemu-ga-x86_64.msi" C:\ProgramData\ExampleMusic\Drivers\qemu-ga-x86_64.msi
    certutil.exe -urlcache -f "%BASE%/amd64/virtio-win-gt-x64.msi" C:\ProgramData\ExampleMusic\Drivers\virtio-win-gt-x64.msi
)

echo.
echo  [OK] deploy.cmd complete.
