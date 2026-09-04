@ECHO OFF
:: ==============================================================================
:: Example Music Limited
::
:: Deploy-OpenSSH.cmd
::
:: Version History
:: ---------------
:: 1.0.0   2026-06-28   Initial release
:: 1.1.0   2026-06-28   Inlined LOG and arch detection - removed unnecessary subroutines
:: 1.2.0   2026-06-28   Restructured for full OS install workflow:
::  - Find installer media (Sources\Setup.exe)
::  - Download headlessunattend.xml to WinPE disk
::  - Launch Setup.exe /unattend /noreboot
::  - PAUSE for PFY to confirm install complete
::  - Enumerate target AFTER install, excluding WinPE RAM disk, WinPE CD & install media
::  - Download scripts and drivers to target
:: 1.2.1   2026-06-28   Replaced %%D loop variable with named variables
::  - SCANDRIVE / INSTALLDRIVE / WINDRIVE to avoid
::  - delayed expansion conflicts
:: 1.3.0   2026-06-28   Swapped plain echo for cecho - colourised output
::  - Errors: red  {04}
::  - Warnings: yellow  {0e}
::  - OK/success: green  {0a}
::  - Info/banners: cyan  {03}
:: 1.4.0   2026-08-15   Robert: two fixes.
::  - Server layout's x86_64/ folder was renamed to amd64/ (matches the real
::    bootstrap/web/windows/ layout) -- every download path here still said
::    x86_64/, so every architecture's downloads were broken, not just arm64.
::  - arm64 now also stages qemu-ga-x86_64.msi + virtio-win-gt-x64.msi (same
::    amd64 builds as x86_64 -- Windows 11/Server 2025 ARM64 run them fine
::    under x64 emulation, confirmed live; no native arm64 build exists yet
::    from either upstream project). Detect-Platform.cmd installs them
::    unconditionally now -- see that file's own 1.1.0 changelog entry.
::  - Prompts: white  {0f}
:: 1.5.0   2026-08-15   Robert: real native arm64 MSIs now exist (see
::                      Detect-Platform.cmd's own 1.2.0 changelog entry for the
::                      full verification). arm64 now also fetches
::                      virtio-win-gt-arm64.msi + qemu-ga-arm64.msi -- explicitly
::                      experimental/untested on real hardware, so a download
::                      failure here logs a warning and continues rather than
::                      :ABORT like every other download in this script;
::                      Detect-Platform.cmd falls back to the amd64 builds if
::                      these never landed or the install itself fails.
:: 1.6.0   2026-08-18   arm64 Proxmox host support, sweep item 3: headlessunattend.xml's
::                      <component> blocks are all processorArchitecture="amd64" --
::                      Windows Setup silently skips any component that doesn't match the
::                      image being installed, so this file was applying NONE of its
::                      settings (not just OpenSSH/RDP, DiskConfiguration/ImageInstall
::                      too) on an arm64 install. Step 3 now fetches
::                      headlessunattend-arm64.xml instead when %ARCH%==arm64 (same
::                      settings, processorArchitecture="arm64" throughout) -- same
::                      %ARCH% variable Step 1 already detects, destination path on the
::                      WinPE disk unchanged either way.
:: 1.6.1   2026-09-04   Robert: live crash on a real x86_64 install --
::                      ". was unexpected at this time." right after Step 10's driver
::                      downloads. Root cause: CMD's parser tokenises an entire
::                      parenthesised ( ... ) block before running any of it, and a `::`
::                      comment inside one breaks that tokenisation -- `::` only works
::                      as a comment at the top level, never nested inside a block. Step
::                      11's x86_64 verification block had one (the exact block Robert
::                      hit live); the arm64 driver-download block in Step 10 had two
::                      more of the same mistake, latent and untriggered so far since
::                      only x86_64 has been tested live. All three changed `::` -> REM,
::                      the only comment marker that's actually safe inside a block.
:: 1.7.0   2026-09-04   Robert: deploy.cmd (a separate script covering WinPE-side driver
::                      injection this file never did) was mostly duplicating this
::                      script's own job, less robustly (hardcoded Y:/C: drives, no error
::                      handling, no verification). Merged its two genuinely unique steps
::                      in here and retired it: new Step 2 injects drivers into the
::                      running WinPE environment itself (pnputil), and Step 9 now also
::                      injects drivers into the offline target image via DISM,
::                      immediately after the real detected target drive is confirmed --
::                      critical for boot-time drivers (e.g. VirtIO storage) that must
::                      already be present before Windows can even boot, which this
::                      script's existing post-boot msiexec-based installs (Detect-
::                      Platform.cmd/Install-OpenSSH.ps1, run by SetupComplete.cmd) can't
::                      help with. Both assume X:\Tools\Drivers already exists in the
::                      running WinPE session (same assumption deploy.cmd made) -- nothing
::                      in this repo documents how that path gets staged onto the WinPE
::                      boot media itself, presumed to be a manual step outside this
::                      repo's tracked automation, flagged rather than guessed at.
:: 1.7.1   2026-09-04   Robert: Step 9's DISM call needs /ForceUnsigned -- some of the
::                      kernel-mode drivers in X:\Tools\Drivers aren't WHQL-signed, and
::                      DISM silently skips unsigned drivers rather than installing them
::                      without it. Also updated to match the reference DISM command in
::                      headlessunattend.xml/headlessunattend-arm64.xml's own header
::                      comments, kept as source-of-truth documentation for this exact
::                      command.
::
:: Purpose
:: -------
:: Technician tool run from WinPE. Covers the full provisioning workflow from bare disk through to
:: a bootstrapped Windows installation ready for Ansible to take over.
::
:: Sequence
:: --------
::   1.  Arch detection
::   2.  Inject drivers into the running WinPE environment (pnputil)
::   3.  Find Windows installer media (Sources\Setup.exe)
::   4.  Download headlessunattend.xml to %SYSTEMDRIVE%\ (WinPE RAM disk)
::   5.  Launch Sources\Setup.exe /unattend /noreboot
::   6.  PAUSE - PFY watches install and hits a key when complete
::   7.  Enumerate drives for freshly installed Windows, excluding:
::         %SYSTEMDRIVE%                      - WinPE RAM disk
::         drives with \Sources\Setup.exe     - installer media
::         drives with \Sources\boot.wim      - WinPE CD/USB
::   8.  Menu/confirm target drive
::   9.  Create \Windows\Setup\Scripts\ and ProgramData\ExampleMusic\Drivers\,
::       inject drivers into the offline target image (DISM)
::  10.  Download Detect-Platform.cmd, SetupComplete.cmd, Install-OpenSSH.ps1
::  11.  Download arch-appropriate guest tool installers
::  12.  Verify all files present
::
:: Driver note
:: -----------
:: Drivers are staged to ProgramData at deploy time because the target has no network drivers on
:: first boot - that is precisely what we are fixing.
::
:: Setup.exe invocation note
:: -------------------------
:: IMPORTANT: \Setup.exe in the root of the installer media is a stub launcher & does NOT accept
:: /unattend or other CLI parameters. You MUST use \Sources\Setup.exe which is the actual Windows
:: Setup engine & does accept /unattend, /noreboot, /quiet etc. Using the root stub with params,
:: it silently ignores them and launches an interactive install.
::
:: First-boot sequence (driven by SetupComplete.cmd)
:: --------------------------------------------------
::   1. Detect-Platform.cmd  - hypervisor detect, installs guest tools from disk
::   2. Install-OpenSSH.ps1  - installs and configures OpenSSH Server
::
:: Provisioning server layout expected
:: ------------------------------------
::   http://<SERVER>/windows/unattend/headlessunattend.xml         (amd64)
::   http://<SERVER>/windows/unattend/headlessunattend-arm64.xml   (arm64)
::   http://<SERVER>/windows/Detect-Platform.cmd
::   http://<SERVER>/windows/SetupComplete.cmd
::   http://<SERVER>/windows/Install-OpenSSH.ps1
::   http://<SERVER>/windows/amd64/qemu-ga-x86_64.msi
::   http://<SERVER>/windows/amd64/virtio-win-gt-x64.msi
::   http://<SERVER>/windows/amd64/VMware-tools-13.0.10-25056151-x64.exe
::   http://<SERVER>/windows/arm64/VMware-tools-13.0.10-25056151-arm.exe
::   http://<SERVER>/windows/arm64/virtio-win-gt-arm64.msi   (native, experimental, optional)
::   http://<SERVER>/windows/arm64/qemu-ga-arm64.msi          (native, experimental, optional)
::
:: Log file (WinPE)
:: ----------------
::   %TEMP%\Deploy-OpenSSH.log
::
:: Log files (target, written at first boot)
:: ------------------------------------------
::   C:\ProgramData\ExampleMusic\Logs\Detect-Platform.log
::   C:\ProgramData\ExampleMusic\Logs\Install-OpenSSH.log
::
:: ==============================================================================

::@echo off
setlocal EnableDelayedExpansion

:: ------------------------------------------------------------------------------
:: Script metadata
:: ------------------------------------------------------------------------------
set "SCRIPT_NAME=Deploy-OpenSSH.cmd"
set "SCRIPT_VERSION=1.7.1"
set "ORG_NAME=Example Music Limited"

:: ------------------------------------------------------------------------------
:: Provisioning server - adjust if the server address changes
:: ------------------------------------------------------------------------------
set "BASE_URL=http://192.168.139.50/windows"

:: ------------------------------------------------------------------------------
:: Log file on WinPE (%TEMP% is writable in WinPE)
:: ------------------------------------------------------------------------------
set "LOGFILE=%TEMP%\Deploy-OpenSSH.log"

echo [%DATE% %TIME%] ============================================================ >> "%LOGFILE%"
echo [%DATE% %TIME%] %ORG_NAME% >> "%LOGFILE%"
echo [%DATE% %TIME%] %SCRIPT_NAME% v%SCRIPT_VERSION% >> "%LOGFILE%"
echo [%DATE% %TIME%] Started >> "%LOGFILE%"
echo [%DATE% %TIME%] WinPE system drive: %SYSTEMDRIVE% >> "%LOGFILE%"
echo [%DATE% %TIME%] ============================================================ >> "%LOGFILE%"

:: ------------------------------------------------------------------------------
:: Banner
:: ------------------------------------------------------------------------------
cls
echo+
cecho.exe {03} "==============================================================================" {\n}{##}
cecho.exe {03} "  %ORG_NAME%" {\n}{##}
cecho.exe {03} "  %SCRIPT_NAME% v%SCRIPT_VERSION%" {\n}{##}
cecho.exe {03} "==============================================================================" {\n}{##}
echo+

:: ------------------------------------------------------------------------------
:: Step 1: Architecture detection
:: ------------------------------------------------------------------------------
set "ARCH=unknown"
if /i "%PROCESSOR_ARCHITECTURE%"=="AMD64" set "ARCH=x86_64"
if /i "%PROCESSOR_ARCHITECTURE%"=="ARM64" set "ARCH=arm64"
if /i "%PROCESSOR_ARCHITECTURE%"=="x86"   set "ARCH=x86"

echo [%DATE% %TIME%] PROCESSOR_ARCHITECTURE=%PROCESSOR_ARCHITECTURE%  ARCH=%ARCH% >> "%LOGFILE%"
cecho.exe {03} "[INFO] Architecture : %ARCH%" {\n}{##}
echo+

:: ------------------------------------------------------------------------------
:: Step 2: Inject drivers into the running WinPE environment
::
:: WinPE's own stock boot image doesn't natively include every storage/network
:: driver real hardware needs -- without this, WinPE itself might not even see
:: the installer media or target drive the next two steps scan for. Not treated
:: as fatal (matches the source this was merged from, deploy.cmd 1.1.1): a
:: pnputil failure here doesn't necessarily mean no usable drivers were found,
:: and WinPE's own boot image already worked well enough to get this script
:: running in the first place.
:: ------------------------------------------------------------------------------
cecho.exe {03} "[INFO] Injecting drivers into running WinPE (pnputil)..." {\n}{##}
echo [%DATE% %TIME%] Injecting drivers into WinPE via pnputil >> "%LOGFILE%"
pnputil /add-driver X:\Tools\Drivers\*.inf /subdirs /install >> "%LOGFILE%" 2>&1
cecho.exe {0a} "[ OK ] WinPE driver injection complete" {\n}{##}
echo+

:: ------------------------------------------------------------------------------
:: Step 3: Find Windows installer media
:: Identified by the presence of \Sources\Setup.exe.
:: See header note on why \Sources\Setup.exe and NOT \Setup.exe.
:: ------------------------------------------------------------------------------
cecho.exe {03} "[INFO] Searching for Windows installer media (Sources\Setup.exe)..." {\n}{##}
echo [%DATE% %TIME%] Searching for installer media... >> "%LOGFILE%"

set "INSTALLDRIVE="

for %%A in (C D E F G H I J K L M N O P Q R S T U V W Y Z) do (
  if /I NOT "%%A:" == "%SYSTEMDRIVE%" (
    if exist "%%A:\Sources\Setup.exe" (
      set "INSTALLDRIVE=%%A"
      echo [%DATE% %TIME%] Found installer media on "%INSTALLDRIVE%" >> "%LOGFILE%"
    )
  )
)

if not defined INSTALLDRIVE (
  echo [%DATE% %TIME%] ERROR: No installer media found. >> "%LOGFILE%"
  cecho.exe {04} "[ERROR] Could not find Windows installer media." {\n}{##}
  cecho.exe {04} "        Searched C: through Z: for \Sources\Setup.exe (excluding %SYSTEMDRIVE%)" {\n}{##}
  cecho.exe {04} "        Verify the installer USB or ISO is attached and visible to WinPE." {\n}{##}
  echo+
  goto :ABORT
)

cecho.exe {0a} "[ OK ] Installer media found : %INSTALLDRIVE%" {\n}{##}
echo [%DATE% %TIME%] Installer media confirmed: %INSTALLDRIVE% >> "%LOGFILE%"
echo+

:: ------------------------------------------------------------------------------
:: Step 4: Download headlessunattend.xml to WinPE RAM disk
::
:: arm64 (2026-08-18, sweep item 3): headlessunattend.xml's <component> blocks are all
:: processorArchitecture="amd64" -- Windows Setup silently skips any component that
:: doesn't match the image being installed, so on an arm64 target this file was applying
:: NONE of its settings at all. headlessunattend-arm64.xml is the arm64 twin (identical
:: settings, processorArchitecture="arm64" throughout). Same %ARCH% variable Step 1
:: already detected -- source filename picked here, destination stays
:: %SYSTEMDRIVE%\headlessunattend.xml either way (Setup.exe /unattend: doesn't care what
:: it was called on the server).
:: ------------------------------------------------------------------------------
set "UNATTEND_SRC=headlessunattend.xml"
if "%ARCH%"=="arm64" set "UNATTEND_SRC=headlessunattend-arm64.xml"

cecho.exe {03} "[INFO] Downloading %UNATTEND_SRC%..." {\n}{##}
echo [%DATE% %TIME%] Fetching %UNATTEND_SRC% >> "%LOGFILE%"

certutil.exe -urlcache -f "%BASE_URL%/unattend/%UNATTEND_SRC%" "%SYSTEMDRIVE%\headlessunattend.xml" >> "%LOGFILE%" 2>&1
if errorlevel 1 (
  echo [%DATE% %TIME%] ERROR: Failed to download %UNATTEND_SRC% >> "%LOGFILE%"
  cecho.exe {04} "[ERROR] Failed to download %UNATTEND_SRC%" {\n}{##}
  goto :ABORT
)
cecho.exe {0a} "[ OK ] %SYSTEMDRIVE%\headlessunattend.xml (from %UNATTEND_SRC%)" {\n}{##}
echo [%DATE% %TIME%] %UNATTEND_SRC% saved to %SYSTEMDRIVE%\headlessunattend.xml >> "%LOGFILE%"
echo+

:: ------------------------------------------------------------------------------
:: Step 5: Launch Windows Setup
::
:: IMPORTANT: \Sources\Setup.exe is the actual Windows Setup engine and is
:: the only binary that accepts CLI parameters such as /unattend and /noreboot.
:: \Setup.exe in the media root is a stub launcher that silently ignores all
:: parameters and launches an interactive install - do NOT use it here.
::
:: /noreboot  - Setup does not reboot automatically on completion.
::              Control returns here so the PFY can confirm before we continue.
:: /unattend  - Provides the answer file for a fully headless install.
:: ------------------------------------------------------------------------------
cecho.exe {03} "==============================================================================" {\n}{##}
cecho.exe {0f} "  Launching Windows Setup. This will take some time." {\n}{##}
cecho.exe {0f} "  Do NOT close this window." {\n}{##}
echo [%DATE% %TIME%] Launching: "%INSTALLDRIVE%:\Sources\Setup.exe" >> "%LOGFILE%"

"%INSTALLDRIVE%:\Sources\Setup.exe" /noreboot /unattend:"%SYSTEMDRIVE%\headlessunattend.xml"
echo [%DATE% %TIME%] Setup.exe returned. Exit code: %ERRORLEVEL% >> "%LOGFILE%"

:: ------------------------------------------------------------------------------
:: Step 6: PAUSE - wait for PFY to confirm install is complete
:: ------------------------------------------------------------------------------
echo+
cecho.exe {0f} "  Windows Setup has returned." {\n}{##}
cecho.exe {0f} "  Verify the installation completed successfully before continuing." {\n}{##}
cecho.exe {0e} "  Press any key to proceed with post-install configuration..." {\n}{##}
cecho.exe {03} "==============================================================================" {\n}{##}
pause >nul
echo [%DATE% %TIME%] Operator confirmed setup complete. Proceeding. >> "%LOGFILE%"

:: ------------------------------------------------------------------------------
:: Step 7: Enumerate drives for freshly installed Windows
::
:: Exclude:
::   %SYSTEMDRIVE%                       - WinPE RAM disk
::   drives with \Sources\Setup.exe      - installer media
::   drives with \Sources\boot.wim       - WinPE CD or USB boot media
::
:: Accept:
::   drives with \Windows\System32\cmd.exe that pass all exclusions above
:: ------------------------------------------------------------------------------
cecho.exe {03} "[INFO] Scanning for installed Windows..." {\n}{##}
echo [%DATE% %TIME%] Enumerating drives for installed Windows... >> "%LOGFILE%"
set FOUND_COUNT=0

for %%L in (C D E F G H I J K L M N O P Q R S T U V W Y Z) do (
  set "SCANDRIVE=%%L:"
  if /I NOT "!SCANDRIVE!" == "%SYSTEMDRIVE%" (
    if not exist "!SCANDRIVE!\Sources\Setup.exe" (
      if not exist "!SCANDRIVE!\Sources\boot.wim" (
        if exist "!SCANDRIVE!\Windows\System32\cmd.exe" (
          set /A FOUND_COUNT+=1
          set "WINDRIVE_!FOUND_COUNT!=!SCANDRIVE!"
          echo [%DATE% %TIME%] Found installed Windows on !SCANDRIVE! >> "%LOGFILE%"
        )
      )
    )
  )
)

:: ------------------------------------------------------------------------------
:: No installed Windows found
:: ------------------------------------------------------------------------------
if %FOUND_COUNT% EQU 0 (
  echo [%DATE% %TIME%] ERROR: No installed Windows found after setup. >> "%LOGFILE%"
  cecho.exe {04} "[ERROR] Could not find an installed Windows on any drive." {\n}{##}
  cecho.exe {04} "        Exclusions: %SYSTEMDRIVE% (WinPE), drives with \Sources\Setup.exe, \Sources\boot.wim" {\n}{##}
  cecho.exe {04} "        If the install failed, resolve the issue and re-run this script." {\n}{##}
  echo+
  goto :ABORT
)

:: ------------------------------------------------------------------------------
:: Step 8a: Single install found - Y/N confirm
:: ------------------------------------------------------------------------------
if %FOUND_COUNT% EQU 1 (
  set "SELECTED_DRIVE=!WINDRIVE_1!"
  cecho.exe {0a} "[ OK ] Installed Windows found: !SELECTED_DRIVE!\Windows" {\n}{##}
  echo+
  choice /C YN /N /M "  Deploy post-install files into !SELECTED_DRIVE!\Windows? [Y/N]: "
  if errorlevel 2 (
    echo [%DATE% %TIME%] Operator declined. Aborting. >> "%LOGFILE%"
    echo+
    cecho.exe {0e} "[WARN] Aborted by operator." {\n}{##}
    echo+
    goto :ABORT
  )
  echo [%DATE% %TIME%] Operator confirmed: !SELECTED_DRIVE! >> "%LOGFILE%"
  goto :DEPLOY
)

:: ------------------------------------------------------------------------------
:: Step 8b: Multiple installs found - numbered menu
:: ------------------------------------------------------------------------------
:MENU
cecho.exe {0f} "  Multiple Windows installations were found. Select the target:" {\n}{##}
echo+
for /L %%N in (1,1,%FOUND_COUNT%) do (
  cecho.exe {0e} "    %%N.  !WINDRIVE_%%N!\Windows" {\n}{##}
)
echo+
set "SELECTION="
set /P SELECTION="  Select installation [1-%FOUND_COUNT%]: "

echo !SELECTION!| findstr /R "^[0-9][0-9]*$" >nul 2>&1
if errorlevel 1 (
  echo+
  cecho.exe {04} "[ERROR] Invalid input. Enter a number between 1 and %FOUND_COUNT%." {\n}{##}
  echo+
  goto :MENU
)
if !SELECTION! LSS 1 (
  echo+
  cecho.exe {04} "[ERROR] Selection out of range." {\n}{##}
  echo+
  goto :MENU
)
if !SELECTION! GTR %FOUND_COUNT% (
  echo+
  cecho.exe {04} "[ERROR] Selection out of range." {\n}{##}
  echo+
  goto :MENU
)

set "SELECTED_DRIVE=!WINDRIVE_%SELECTION%!"
echo [%DATE% %TIME%] Operator selected !SELECTED_DRIVE! >> "%LOGFILE%"

echo+
choice /C YN /N /M "  Deploy post-install files into !SELECTED_DRIVE!\Windows? [Y/N]: "
if errorlevel 2 (
  echo+
  cecho.exe {0e} "[WARN] Returning to menu..." {\n}{##}
  echo+
  goto :MENU
)
echo [%DATE% %TIME%] Operator confirmed: !SELECTED_DRIVE! >> "%LOGFILE%"

:: ------------------------------------------------------------------------------
:: Step 9: Create directories on target, inject drivers into offline image
:: ------------------------------------------------------------------------------
:DEPLOY
echo+
cecho.exe {03} "------------------------------------------------------------------------------" {\n}{##}
cecho.exe {03} "  Deploying post-install files to !SELECTED_DRIVE!" {\n}{##}
cecho.exe {03} "------------------------------------------------------------------------------" {\n}{##}
echo+

set "TARGET_SCRIPTS=!SELECTED_DRIVE!\Windows\Setup\Scripts"
set "TARGET_DRIVERS=!SELECTED_DRIVE!\ProgramData\ExampleMusic\Drivers"

if NOT exist "!SELECTED_DRIVE!\Windows\System32" (
  echo [%DATE% %TIME%] ERROR: !SELECTED_DRIVE!\Windows\System32 not found. >> "%LOGFILE%"
  cecho.exe {04} "[ERROR] !SELECTED_DRIVE!\Windows\System32 not found. Target may be invalid." {\n}{##}
  goto :ABORT
)
echo [%DATE% %TIME%] Target verified: !SELECTED_DRIVE! >> "%LOGFILE%"

:: ------------------------------------------------------------------------------
:: Inject drivers into the offline target image via DISM.
::
:: There is no in-target equivalent for this against an unbooted image (Windows
:: Installer/msiexec needs a live OS) -- must run here, against the just-applied
:: image, before the target ever reboots. Critical for boot-time drivers (e.g.
:: VirtIO storage) that must already be present the moment Windows first
:: starts; this script's later post-boot installs (Detect-Platform.cmd/
:: Install-OpenSSH.ps1, run by SetupComplete.cmd) can't help with that, since
:: the OS has to already be able to boot and reach its own storage first.
:: Treated as fatal, unlike WinPE's own pnputil injection in Step 2 -- a
:: missing boot-critical driver here risks an unbootable target, not just a
:: WinPE inconvenience. /ForceUnsigned (Robert, 2026-09-04): some of the
:: kernel-mode drivers in X:\Tools\Drivers aren't WHQL-signed -- without it,
:: DISM silently skips them rather than installing them.
:: ------------------------------------------------------------------------------
cecho.exe {03} "[INFO] Injecting drivers into offline target image (DISM)..." {\n}{##}
echo [%DATE% %TIME%] Running: dism /Image:!SELECTED_DRIVE!\ /Add-Driver /Driver:X:\Tools\Drivers /Recurse /ForceUnsigned >> "%LOGFILE%"
dism /Image:!SELECTED_DRIVE!\ /Add-Driver /Driver:X:\Tools\Drivers /Recurse /ForceUnsigned >> "%LOGFILE%" 2>&1
if errorlevel 1 (
  echo [%DATE% %TIME%] ERROR: DISM driver injection into !SELECTED_DRIVE! failed. >> "%LOGFILE%"
  cecho.exe {04} "[ERROR] DISM driver injection into !SELECTED_DRIVE! failed." {\n}{##}
  goto :ABORT
)
cecho.exe {0a} "[ OK ] Offline image driver injection complete" {\n}{##}
echo+

if NOT exist "!TARGET_SCRIPTS!" (
  cecho.exe {03} "[INFO] Creating !TARGET_SCRIPTS!..." {\n}{##}
  mkdir "!TARGET_SCRIPTS!"
  if errorlevel 1 (
    echo [%DATE% %TIME%] ERROR: Failed to create !TARGET_SCRIPTS! >> "%LOGFILE%"
    cecho.exe {04} "[ERROR] Failed to create !TARGET_SCRIPTS!" {\n}{##}
    goto :ABORT
  )
  echo [%DATE% %TIME%] Created: !TARGET_SCRIPTS! >> "%LOGFILE%"
) else (
  cecho.exe {03} "[INFO] Exists: !TARGET_SCRIPTS!" {\n}{##}
  echo [%DATE% %TIME%] Exists: !TARGET_SCRIPTS! >> "%LOGFILE%"
)

if NOT exist "!TARGET_DRIVERS!" (
  cecho.exe {03} "[INFO] Creating !TARGET_DRIVERS!..." {\n}{##}
  mkdir "!TARGET_DRIVERS!"
  if errorlevel 1 (
    echo [%DATE% %TIME%] ERROR: Failed to create !TARGET_DRIVERS! >> "%LOGFILE%"
    cecho.exe {04} "[ERROR] Failed to create !TARGET_DRIVERS!" {\n}{##}
    goto :ABORT
  )
  echo [%DATE% %TIME%] Created: !TARGET_DRIVERS! >> "%LOGFILE%"
) else (
  cecho.exe {03} "[INFO] Exists: !TARGET_DRIVERS!" {\n}{##}
  echo [%DATE% %TIME%] Exists: !TARGET_DRIVERS! >> "%LOGFILE%"
)

:: ------------------------------------------------------------------------------
:: Step 10: Download scripts to target
:: ------------------------------------------------------------------------------
cecho.exe {03} "[INFO] Downloading setup scripts..." {\n}{##}
echo [%DATE% %TIME%] Fetching Detect-Platform.cmd >> "%LOGFILE%"
certutil.exe -urlcache -f "%BASE_URL%/Detect-Platform.cmd" "!TARGET_SCRIPTS!\Detect-Platform.cmd" >> "%LOGFILE%" 2>&1
if errorlevel 1 (
  echo [%DATE% %TIME%] ERROR: Failed to download Detect-Platform.cmd >> "%LOGFILE%"
  cecho.exe {04} "[ERROR] Failed to download Detect-Platform.cmd" {\n}{##}
  goto :ABORT
)
cecho.exe {0a} "[ OK ] Detect-Platform.cmd" {\n}{##}

echo [%DATE% %TIME%] Fetching SetupComplete.cmd >> "%LOGFILE%"
certutil.exe -urlcache -f "%BASE_URL%/SetupComplete.cmd" "!TARGET_SCRIPTS!\SetupComplete.cmd" >> "%LOGFILE%" 2>&1
if errorlevel 1 (
  echo [%DATE% %TIME%] ERROR: Failed to download SetupComplete.cmd >> "%LOGFILE%"
  cecho.exe {04} "[ERROR] Failed to download SetupComplete.cmd" {\n}{##}
  goto :ABORT
)
cecho.exe {0a} "[ OK ] SetupComplete.cmd" {\n}{##}
echo [%DATE% %TIME%] Fetching Install-OpenSSH.ps1 >> "%LOGFILE%"
certutil.exe -urlcache -f "%BASE_URL%/Install-OpenSSH.ps1" "!TARGET_SCRIPTS!\Install-OpenSSH.ps1" >> "%LOGFILE%" 2>&1
if errorlevel 1 (
  echo [%DATE% %TIME%] ERROR: Failed to download Install-OpenSSH.ps1 >> "%LOGFILE%"
  cecho.exe {04} "[ERROR] Failed to download Install-OpenSSH.ps1" {\n}{##}
  goto :ABORT
)
cecho.exe {0a} "[ OK ] Install-OpenSSH.ps1" {\n}{##}

:: ------------------------------------------------------------------------------
:: Step 11: Download arch-appropriate drivers to target
:: ------------------------------------------------------------------------------
echo+
cecho.exe {03} "[INFO] Downloading drivers for %ARCH%..." {\n}{##}


if "%ARCH%"=="x86_64" (
  echo [%DATE% %TIME%] Fetching qemu-ga-x86_64.msi >> "%LOGFILE%"
  certutil.exe -urlcache -f "%BASE_URL%/amd64/qemu-ga-x86_64.msi" "!TARGET_DRIVERS!\qemu-ga-x86_64.msi" >> "%LOGFILE%" 2>&1
  if errorlevel 1 (
    echo [%DATE% %TIME%] ERROR: Failed to download qemu-ga-x86_64.msi >> "%LOGFILE%"
    cecho.exe {04} "[ERROR] Failed to download qemu-ga-x86_64.msi" {\n}{##}
    goto :ABORT
  )
  cecho.exe {0a} "[ OK ] qemu-ga-x86_64.msi" {\n}{##}

  echo [%DATE% %TIME%] Fetching virtio-win-gt-x64.msi >> "%LOGFILE%"
  certutil.exe -urlcache -f "%BASE_URL%/amd64/virtio-win-gt-x64.msi" "!TARGET_DRIVERS!\virtio-win-gt-x64.msi" >> "%LOGFILE%" 2>&1
  if errorlevel 1 (
    echo [%DATE% %TIME%] ERROR: Failed to download virtio-win-gt-x64.msi >> "%LOGFILE%"
    cecho.exe {04} "[ERROR] Failed to download virtio-win-gt-x64.msi" {\n}{##}
    goto :ABORT
  )
  cecho.exe {0a} "[ OK ] virtio-win-gt-x64.msi" {\n}{##}

  echo [%DATE% %TIME%] Fetching VMware-tools-13.0.10-25056151-x64.exe >> "%LOGFILE%"
  certutil.exe -urlcache -f "%BASE_URL%/amd64/VMware-tools-13.0.10-25056151-x64.exe" "!TARGET_DRIVERS!\VMware-tools-13.0.10-25056151-x64.exe" >> "%LOGFILE%" 2>&1
  if errorlevel 1 (
    echo [%DATE% %TIME%] ERROR: Failed to download VMware-tools-13.0.10-25056151-x64.exe >> "%LOGFILE%"
    cecho.exe {04} "[ERROR] Failed to download VMware-tools-13.0.10-25056151-x64.exe" {\n}{##}
    goto :ABORT
  )
  cecho.exe {0a} "[ OK ] VMware-tools-13.0.10-25056151-x64.exe" {\n}{##}
)

if "%ARCH%"=="arm64" (
  echo [%DATE% %TIME%] Fetching VMware-tools-13.0.10-25056151-arm.exe >> "%LOGFILE%"
  certutil.exe -urlcache -f "%BASE_URL%/arm64/VMware-tools-13.0.10-25056151-arm.exe" "!TARGET_DRIVERS!\VMware-tools-13.0.10-25056151-arm.exe" >> "%LOGFILE%" 2>&1
  if errorlevel 1 (
    echo [%DATE% %TIME%] ERROR: Failed to download VMware-tools-13.0.10-25056151-arm.exe >> "%LOGFILE%"
    cecho.exe {04} "[ERROR] Failed to download VMware-tools-13.0.10-25056151-arm.exe" {\n}{##}
    goto :ABORT
  )
  cecho.exe {0a} "[ OK ] VMware-tools-13.0.10-25056151-arm.exe" {\n}{##}

  REM KVM/Proxmox on arm64: try the real native arm64 MSIs first (2026-08-15,
  REM github.com/knightmare2600/virtio-win-guest-tools-installer arm64-preview-0.1.0
  REM -- verified for real: SHA256 matched, PE header machine field of the binaries
  REM inside confirmed genuine ARM64 code). Explicitly experimental/untested on real
  REM hardware, so download failure here is NOT fatal, unlike every other download
  REM in this script -- log and continue rather than :ABORT. Detect-Platform.cmd's
  REM own `if exist` check (1.2.0 changelog entry) falls back to the amd64 builds
  REM below if these never landed or the install itself fails on the box.
  echo [%DATE% %TIME%] Fetching virtio-win-gt-arm64.msi (native, experimental) >> "%LOGFILE%"
  certutil.exe -urlcache -f "%BASE_URL%/arm64/virtio-win-gt-arm64.msi" "!TARGET_DRIVERS!\virtio-win-gt-arm64.msi" >> "%LOGFILE%" 2>&1
  if errorlevel 1 (
    echo [%DATE% %TIME%] WARNING: Failed to download virtio-win-gt-arm64.msi -- Detect-Platform.cmd will fall back to the amd64 build. >> "%LOGFILE%"
    cecho.exe {0e} "[ WARN ] Failed to download virtio-win-gt-arm64.msi -- will fall back to amd64 at first boot." {\n}{##}
  ) else (
    cecho.exe {0a} "[ OK ] virtio-win-gt-arm64.msi (native, experimental)" {\n}{##}
  )

  echo [%DATE% %TIME%] Fetching qemu-ga-arm64.msi (native, experimental) >> "%LOGFILE%"
  certutil.exe -urlcache -f "%BASE_URL%/arm64/qemu-ga-arm64.msi" "!TARGET_DRIVERS!\qemu-ga-arm64.msi" >> "%LOGFILE%" 2>&1
  if errorlevel 1 (
    echo [%DATE% %TIME%] WARNING: Failed to download qemu-ga-arm64.msi -- Detect-Platform.cmd will fall back to the amd64 build. >> "%LOGFILE%"
    cecho.exe {0e} "[ WARN ] Failed to download qemu-ga-arm64.msi -- will fall back to amd64 at first boot." {\n}{##}
  ) else (
    cecho.exe {0a} "[ OK ] qemu-ga-arm64.msi (native, experimental)" {\n}{##}
  )

  REM amd64 fallback builds -- always staged regardless of whether the native
  REM arm64 downloads above succeeded, since Detect-Platform.cmd needs them
  REM available either way (missing/failed native install falls back to these).
  echo [%DATE% %TIME%] Fetching qemu-ga-x86_64.msi (amd64 build, arm64 runs it under x64 emulation) >> "%LOGFILE%"
  certutil.exe -urlcache -f "%BASE_URL%/amd64/qemu-ga-x86_64.msi" "!TARGET_DRIVERS!\qemu-ga-x86_64.msi" >> "%LOGFILE%" 2>&1
  if errorlevel 1 (
    echo [%DATE% %TIME%] ERROR: Failed to download qemu-ga-x86_64.msi >> "%LOGFILE%"
    cecho.exe {04} "[ERROR] Failed to download qemu-ga-x86_64.msi" {\n}{##}
    goto :ABORT
  )
  cecho.exe {0a} "[ OK ] qemu-ga-x86_64.msi" {\n}{##}

  echo [%DATE% %TIME%] Fetching virtio-win-gt-x64.msi (amd64 build, arm64 runs it under x64 emulation) >> "%LOGFILE%"
  certutil.exe -urlcache -f "%BASE_URL%/amd64/virtio-win-gt-x64.msi" "!TARGET_DRIVERS!\virtio-win-gt-x64.msi" >> "%LOGFILE%" 2>&1
  if errorlevel 1 (
    echo [%DATE% %TIME%] ERROR: Failed to download virtio-win-gt-x64.msi >> "%LOGFILE%"
    cecho.exe {04} "[ERROR] Failed to download virtio-win-gt-x64.msi" {\n}{##}
    goto :ABORT
  )
  cecho.exe {0a} "[ OK ] virtio-win-gt-x64.msi" {\n}{##}
)
echo+

:: ------------------------------------------------------------------------------
:: Step 12: Verify all expected files landed on target
:: ------------------------------------------------------------------------------
echo [%DATE% %TIME%] Verifying files on target... >> "%LOGFILE%"
set VERIFY_OK=1

if NOT exist "!TARGET_SCRIPTS!\Detect-Platform.cmd"  set VERIFY_OK=0
if NOT exist "!TARGET_SCRIPTS!\SetupComplete.cmd"     set VERIFY_OK=0
if NOT exist "!TARGET_SCRIPTS!\Install-OpenSSH.ps1"  set VERIFY_OK=0

if "%ARCH%"=="x86_64" (
  if NOT exist "!TARGET_DRIVERS!\qemu-ga-x86_64.msi"                    set VERIFY_OK=0
  if NOT exist "!TARGET_DRIVERS!\virtio-win-gt-x64.msi"                 set VERIFY_OK=0
REM Certutil.exe being obtuse about exe files
REM  if NOT exist "!TARGET_DRIVERS!\VMware-tools-13.0.10-25056151-x64.exe" set VERIFY_OK=0
echo+
)

if "%ARCH%"=="arm64" (
  if NOT exist "!TARGET_DRIVERS!\VMware-tools-13.0.10-25056151-arm.exe" set VERIFY_OK=0
  if NOT exist "!TARGET_DRIVERS!\qemu-ga-x86_64.msi"                    set VERIFY_OK=0
  if NOT exist "!TARGET_DRIVERS!\virtio-win-gt-x64.msi"                 set VERIFY_OK=0
echo+
)

if !VERIFY_OK! EQU 0 (
  echo [%DATE% %TIME%] ERROR: Verification failed - one or more files missing. >> "%LOGFILE%"
  cecho.exe {04} "[ERROR] Verification failed. One or more expected files are missing." {\n}{##}
  goto :ABORT
)
echo [%DATE% %TIME%] Verification passed. >> "%LOGFILE%"

:: ------------------------------------------------------------------------------
:: Success
:: ------------------------------------------------------------------------------
cecho.exe {03} "==============================================================================" {\n}{##}
cecho.exe {0a} "  Deployment complete." {\n}{##}
cecho.exe {03} "==============================================================================" {\n}{##}
echo+
cecho.exe {0f} "  Target drive  :  !SELECTED_DRIVE!" {\n}{##}
cecho.exe {0f} "  Architecture  :  %ARCH%" {\n}{##}
cecho.exe {0f} "  Scripts       :  !TARGET_SCRIPTS!" {\n}{##}
cecho.exe {0f} "  Drivers       :  !TARGET_DRIVERS!" {\n}{##}
echo+
cecho.exe {03} "  On next boot Windows will automatically run SetupComplete.cmd which:" {\n}{##}
cecho.exe {0a} "    1. Detects platform and installs guest tools  (Detect-Platform.cmd)" {\n}{##}
cecho.exe {0a} "    2. Installs and configures OpenSSH Server     (Install-OpenSSH.ps1)" {\n}{##}
echo+
cecho.exe {0e} "  You may now reboot the target machine." {\n}{##}
echo+
cecho.exe {03} "  WinPE log  :  %LOGFILE%" {\n}{##}
echo+
echo [%DATE% %TIME%] Deployment completed successfully. Target: !SELECTED_DRIVE! Arch: %ARCH% >> "%LOGFILE%"
goto :END

:: ------------------------------------------------------------------------------
:: Abort
:: ------------------------------------------------------------------------------
:ABORT
echo+
cecho.exe {04} "==============================================================================" {\n}{##}
cecho.exe {04} "  Deployment aborted." {\n}{##}
cecho.exe {04} "==============================================================================" {\n}{##}
echo+
cecho.exe {04} "  WinPE log  :  %LOGFILE%" {\n}{##}
echo+
echo [%DATE% %TIME%] Deployment aborted. >> "%LOGFILE%"
endlocal
exit /b 1

:: ------------------------------------------------------------------------------
:: End
:: ------------------------------------------------------------------------------
:END
echo [%DATE% %TIME%] Finished. >> "%LOGFILE%"
echo [%DATE% %TIME%] ============================================================ >> "%LOGFILE%"
endlocal
exit /b 0

