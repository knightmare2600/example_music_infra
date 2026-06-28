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
::  - Prompts: white  {0f}
::
:: Purpose
:: -------
:: Technician tool run from WinPE. Covers the full provisioning workflow
:: from bare disk through to a bootstrapped Windows installation ready for
:: Ansible to take over.
::
:: Sequence
:: --------
::   1.  Arch detection
::   2.  Find Windows installer media (Sources\Setup.exe)
::   3.  Download headlessunattend.xml to %SYSTEMDRIVE%\ (WinPE RAM disk)
::   4.  Launch Sources\Setup.exe /unattend /noreboot
::   5.  PAUSE - PFY watches install and hits a key when complete
::   6.  Enumerate drives for freshly installed Windows, excluding:
::         %SYSTEMDRIVE%                      - WinPE RAM disk
::         drives with \Sources\Setup.exe     - installer media
::         drives with \Sources\boot.wim      - WinPE CD/USB
::   7.  Menu/confirm target drive
::   8.  Create \Windows\Setup\Scripts\ and ProgramData\ExampleMusic\Drivers\
::   9.  Download Detect-Platform.cmd, SetupComplete.cmd, Install-OpenSSH.ps1
::  10.  Download arch-appropriate guest tool installers
::  11.  Verify all files present
::
:: Driver note
:: -----------
:: Drivers are staged to ProgramData at deploy time because the target has
:: no network drivers on first boot - that is precisely what we are fixing.
::
:: Setup.exe invocation note
:: -------------------------
:: IMPORTANT: \Setup.exe in the root of the installer media is a stub launcher
:: and does NOT accept /unattend or other CLI parameters. You MUST use
:: \Sources\Setup.exe which is the actual Windows Setup engine and does
:: accept /unattend, /noreboot, /quiet etc. Using the root stub with
:: parameters silently ignores them and launches an interactive install.
::
:: First-boot sequence (driven by SetupComplete.cmd)
:: --------------------------------------------------
::   1. Detect-Platform.cmd  - hypervisor detect, installs guest tools from disk
::   2. Install-OpenSSH.ps1  - installs and configures OpenSSH Server
::
:: Provisioning server layout expected
:: ------------------------------------
::   http://<SERVER>/windows/unattend/headlessunattend.xml
::   http://<SERVER>/windows/Detect-Platform.cmd
::   http://<SERVER>/windows/SetupComplete.cmd
::   http://<SERVER>/windows/Install-OpenSSH.ps1
::   http://<SERVER>/windows/x86_64/qemu-ga-x86_64.msi
::   http://<SERVER>/windows/x86_64/virtio-win-gt-x64.msi
::   http://<SERVER>/windows/x86_64/VMware-tools-13.0.10-25056151-x64.exe
::   http://<SERVER>/windows/arm64/VMware-tools-13.0.10-25056151-arm.exe
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
set "SCRIPT_VERSION=1.3.0"
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
:: Step 2: Find Windows installer media
:: Identified by the presence of \Sources\Setup.exe.
:: See header note on why \Sources\Setup.exe and NOT \Setup.exe.
:: ------------------------------------------------------------------------------
cecho.exe {03} "[INFO] Searching for Windows installer media (Sources\Setup.exe)..." {\n}{##}
echo [%DATE% %TIME%] Searching for installer media... >> "%LOGFILE%"

set "INSTALLDRIVE="

for %%LETTER in (C D E F G H I J K L M N O P Q R S T U V W Y Z) do (
  set "SCANDRIVE=%%LETTER:"
  if /I NOT "!SCANDRIVE!" == "%SYSTEMDRIVE%" (
    if exist "!SCANDRIVE!\Sources\Setup.exe" (
      set "INSTALLDRIVE=!SCANDRIVE!"
      echo [%DATE% %TIME%] Found installer media on !SCANDRIVE! >> "%LOGFILE%"
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
:: Step 3: Download headlessunattend.xml to WinPE RAM disk
:: ------------------------------------------------------------------------------
cecho.exe {03} "[INFO] Downloading headlessunattend.xml..." {\n}{##}
echo [%DATE% %TIME%] Fetching headlessunattend.xml >> "%LOGFILE%"

certutil.exe -urlcache -f "%BASE_URL%/unattend/headlessunattend.xml" "%SYSTEMDRIVE%\headlessunattend.xml" >> "%LOGFILE%" 2>&1
if errorlevel 1 (
  echo [%DATE% %TIME%] ERROR: Failed to download headlessunattend.xml >> "%LOGFILE%"
  cecho.exe {04} "[ERROR] Failed to download headlessunattend.xml" {\n}{##}
  goto :ABORT
)
cecho.exe {0a} "[ OK ] %SYSTEMDRIVE%\headlessunattend.xml" {\n}{##}
echo [%DATE% %TIME%] headlessunattend.xml saved to %SYSTEMDRIVE%\headlessunattend.xml >> "%LOGFILE%"
echo+

:: ------------------------------------------------------------------------------
:: Step 4: Launch Windows Setup
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
cecho.exe {03} "==============================================================================" {\n}{##}
echo+
echo [%DATE% %TIME%] Launching: %INSTALLDRIVE%\Sources\Setup.exe >> "%LOGFILE%"

"%INSTALLDRIVE%\Sources\Setup.exe" /noreboot /unattend:"%SYSTEMDRIVE%\headlessunattend.xml"

echo [%DATE% %TIME%] Setup.exe returned. Exit code: %ERRORLEVEL% >> "%LOGFILE%"
echo+

:: ------------------------------------------------------------------------------
:: Step 5: PAUSE - wait for PFY to confirm install is complete
:: ------------------------------------------------------------------------------
cecho.exe {03} "==============================================================================" {\n}{##}
cecho.exe {0f} "  Windows Setup has returned." {\n}{##}
cecho.exe {0f} "  Verify the installation completed successfully before continuing." {\n}{##}
cecho.exe {0e} "  Press any key to proceed with post-install configuration..." {\n}{##}
cecho.exe {03} "==============================================================================" {\n}{##}
pause >nul
echo+
echo [%DATE% %TIME%] Operator confirmed setup complete. Proceeding. >> "%LOGFILE%"

:: ------------------------------------------------------------------------------
:: Step 6: Enumerate drives for freshly installed Windows
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
echo+
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
:: Step 7a: Single install found - Y/N confirm
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
:: Step 7b: Multiple installs found - numbered menu
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
:: Step 8: Create directories on target
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
echo+

:: ------------------------------------------------------------------------------
:: Step 9: Download scripts to target
:: ------------------------------------------------------------------------------
cecho.exe {03} "[INFO] Downloading setup scripts..." {\n}{##}
echo+

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
echo+

:: ------------------------------------------------------------------------------
:: Step 10: Download arch-appropriate drivers to target
:: ------------------------------------------------------------------------------
cecho.exe {03} "[INFO] Downloading drivers for %ARCH%..." {\n}{##}
echo+

if "%ARCH%"=="x86_64" (
  echo [%DATE% %TIME%] Fetching qemu-ga-x86_64.msi >> "%LOGFILE%"
  certutil.exe -urlcache -f "%BASE_URL%/x86_64/qemu-ga-x86_64.msi" "!TARGET_DRIVERS!\qemu-ga-x86_64.msi" >> "%LOGFILE%" 2>&1
  if errorlevel 1 (
    echo [%DATE% %TIME%] ERROR: Failed to download qemu-ga-x86_64.msi >> "%LOGFILE%"
    cecho.exe {04} "[ERROR] Failed to download qemu-ga-x86_64.msi" {\n}{##}
    goto :ABORT
  )
  cecho.exe {0a} "[ OK ] qemu-ga-x86_64.msi" {\n}{##}

  echo [%DATE% %TIME%] Fetching virtio-win-gt-x64.msi >> "%LOGFILE%"
  certutil.exe -urlcache -f "%BASE_URL%/x86_64/virtio-win-gt-x64.msi" "!TARGET_DRIVERS!\virtio-win-gt-x64.msi" >> "%LOGFILE%" 2>&1
  if errorlevel 1 (
    echo [%DATE% %TIME%] ERROR: Failed to download virtio-win-gt-x64.msi >> "%LOGFILE%"
    cecho.exe {04} "[ERROR] Failed to download virtio-win-gt-x64.msi" {\n}{##}
    goto :ABORT
  )
  cecho.exe {0a} "[ OK ] virtio-win-gt-x64.msi" {\n}{##}

  echo [%DATE% %TIME%] Fetching VMware-tools-13.0.10-25056151-x64.exe >> "%LOGFILE%"
  certutil.exe -urlcache -f "%BASE_URL%/x86_64/VMware-tools-13.0.10-25056151-x64.exe" "!TARGET_DRIVERS!\VMware-tools-13.0.10-25056151-x64.exe" >> "%LOGFILE%" 2>&1
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
)
echo+

:: ------------------------------------------------------------------------------
:: Step 11: Verify all expected files landed on target
:: ------------------------------------------------------------------------------
echo [%DATE% %TIME%] Verifying files on target... >> "%LOGFILE%"
set VERIFY_OK=1

if NOT exist "!TARGET_SCRIPTS!\Detect-Platform.cmd"  set VERIFY_OK=0
if NOT exist "!TARGET_SCRIPTS!\SetupComplete.cmd"     set VERIFY_OK=0
if NOT exist "!TARGET_SCRIPTS!\Install-OpenSSH.ps1"  set VERIFY_OK=0

if "%ARCH%"=="x86_64" (
  if NOT exist "!TARGET_DRIVERS!\qemu-ga-x86_64.msi"                    set VERIFY_OK=0
  if NOT exist "!TARGET_DRIVERS!\virtio-win-gt-x64.msi"                 set VERIFY_OK=0
  if NOT exist "!TARGET_DRIVERS!\VMware-tools-13.0.10-25056151-x64.exe" set VERIFY_OK=0
)
if "%ARCH%"=="arm64" (
  if NOT exist "!TARGET_DRIVERS!\VMware-tools-13.0.10-25056151-arm.exe" set VERIFY_OK=0
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
echo+
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
