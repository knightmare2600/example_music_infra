:: ==============================================================================
:: Example Music Limited
::
:: Deploy-OpenSSH.cmd
::
:: Version History
:: ---------------
:: 1.0.0   2026-06-28   Initial release
:: 1.1.0   2026-06-28   Added driver copy (X:\Tools\Drivers -> target ProgramData)
::                      Added generation of Detect-Platform.cmd into Setup\Scripts
::                      Updated SetupComplete.cmd to call Detect-Platform.cmd first
::
:: Purpose
:: -------
:: Technician tool intended to be run from WinPE.
::
:: This script:
::
::   1. Enumerates drive letters C: through Z:
::   2. Excludes %SYSTEMDRIVE% (the WinPE RAM disk, typically X:)
::   3. Detects Windows installations by looking for \Windows\System32
::   4. Presents a numbered menu if multiple installations are found,
::      or asks Y/N confirmation if only one is found
::   5. Validates operator input throughout
::   6. Creates \Windows\Setup\Scripts\ on the target if absent
::   7. Creates C:\ProgramData\ExampleMusic\Drivers\ on the target
::   8. Copies X:\Tools\Drivers\* to target ProgramData\ExampleMusic\Drivers\
::   9. Writes Detect-Platform.cmd onto the target
::  10. Writes SetupComplete.cmd onto the target
::  11. Writes Install-OpenSSH.ps1 onto the target
::  12. Logs all activity to %TEMP%\Deploy-OpenSSH.log
::
:: First-boot sequence (driven by SetupComplete.cmd):
::   1. Detect-Platform.cmd  - detects VMware/KVM, installs guest tools/agent
::   2. Install-OpenSSH.ps1  - installs and configures OpenSSH Server
::
:: Driver source (WinPE media)
:: ---------------------------
::   X:\Tools\Drivers\qemu-ga-x86_64.msi
::   X:\Tools\Drivers\virtio-win-gt-x64.msi
::   X:\Tools\Drivers\VMware-tools-13.1.0-25218885-x64.exe
::
:: Driver destination (target disk, used at first boot)
:: -----------------------------------------------------
::   C:\ProgramData\ExampleMusic\Drivers\
::
:: Log file (on WinPE host)
:: ------------------------
::   %TEMP%\Deploy-OpenSSH.log
::
:: Log files (on target, written at first boot)
:: --------------------------------------------
::   C:\ProgramData\ExampleMusic\Logs\Detect-Platform.log
::   C:\ProgramData\ExampleMusic\Logs\Install-OpenSSH.log
::
:: Notes
:: -----
::   - Idempotent: safe to run multiple times against the same target.
::   - Does not modify the running WinPE environment.
::   - Requires no external tools beyond what WinPE provides.
::
:: X:\Sources\setup.exe /noreboot /unattend:x:\headlessunattend.xml
::
:: ==============================================================================

@echo off
setlocal EnableDelayedExpansion

:: ------------------------------------------------------------------------------
:: Script metadata
:: ------------------------------------------------------------------------------
set "SCRIPT_NAME=Deploy-OpenSSH.cmd"
set "SCRIPT_VERSION=1.1.0"
set "ORG_NAME=Example Music Limited"

:: ------------------------------------------------------------------------------
:: Driver source on WinPE media
:: ------------------------------------------------------------------------------
set "DRIVER_SOURCE=X:\Tools\Drivers"

:: ------------------------------------------------------------------------------
:: Log file (on WinPE disk, %TEMP% is writable in WinPE)
:: ------------------------------------------------------------------------------
set "LOGFILE=%TEMP%\Deploy-OpenSSH.log"

:: ------------------------------------------------------------------------------
:: Initialise log
:: ------------------------------------------------------------------------------
call :LOG "============================================================"
call :LOG "%ORG_NAME%"
call :LOG "%SCRIPT_NAME% v%SCRIPT_VERSION%"
call :LOG "Started: %DATE% %TIME%"
call :LOG "WinPE system drive: %SYSTEMDRIVE%"
call :LOG "============================================================"

:: ------------------------------------------------------------------------------
:: Banner
:: ------------------------------------------------------------------------------
cls
echo.
echo  ==============================================================================
echo   %ORG_NAME%
echo   %SCRIPT_NAME% v%SCRIPT_VERSION%
echo  ==============================================================================
echo.

:: ------------------------------------------------------------------------------
:: Verify driver source exists on WinPE media before doing anything else
:: ------------------------------------------------------------------------------
call :LOG "Checking driver source: %DRIVER_SOURCE%"
if NOT exist "%DRIVER_SOURCE%\" (
    call :LOG "ERROR: Driver source not found: %DRIVER_SOURCE%"
    echo  [ERROR] Driver source not found: %DRIVER_SOURCE%
    echo.
    echo  Expected layout:
    echo    %DRIVER_SOURCE%\qemu-ga-x86_64.msi
    echo    %DRIVER_SOURCE%\virtio-win-gt-x64.msi
    echo    %DRIVER_SOURCE%\VMware-tools-13.1.0-25218885-x64.exe
    echo.
    goto :ABORT
)
call :LOG "Driver source verified: %DRIVER_SOURCE%"

:: ------------------------------------------------------------------------------
:: Drive enumeration
:: ------------------------------------------------------------------------------
call :LOG "Beginning drive enumeration..."
echo  Scanning for Windows installations. Please wait...
echo.

set FOUND_COUNT=0

for %%D in (C D E F G H I J K L M N O P Q R S T U V W Y Z) do (
    set "DRIVE=%%D:"

    :: Skip the WinPE system drive
    if /I NOT "%%D:" == "%SYSTEMDRIVE%" (
        if exist "%%D:\Windows\System32\cmd.exe" (
            set /A FOUND_COUNT+=1
            set "DRIVE_!FOUND_COUNT!=%%D:"
            call :LOG "Found Windows installation on %%D:"
        )
    )
)

:: ------------------------------------------------------------------------------
:: No installations found
:: ------------------------------------------------------------------------------
if %FOUND_COUNT% EQU 0 (
    call :LOG "ERROR: No Windows installations found."
    echo  [ERROR] No Windows installations were found.
    echo.
    echo  Drives searched: C: through Z: (excluding %SYSTEMDRIVE%)
    echo.
    echo  Verify that the target disk is connected and visible to WinPE,
    echo  then re-run this script.
    echo.
    goto :ABORT
)

:: ------------------------------------------------------------------------------
:: Single installation found - confirm rather than present a menu
:: ------------------------------------------------------------------------------
if %FOUND_COUNT% EQU 1 (
    set "SELECTED_DRIVE=!DRIVE_1!"
    echo  One Windows installation was found:
    echo.
    echo    !SELECTED_DRIVE!\Windows
    echo.
    choice /C YN /N /M "  Deploy into !SELECTED_DRIVE!\Windows? [Y/N]: "
    if errorlevel 2 (
        call :LOG "Operator declined. Aborting."
        echo.
        echo  Aborted by operator.
        echo.
        goto :ABORT
    )
    call :LOG "Operator confirmed installation into !SELECTED_DRIVE!"
    goto :DEPLOY
)

:: ------------------------------------------------------------------------------
:: Multiple installations found - present numbered menu
:: ------------------------------------------------------------------------------
:MENU
echo  The following Windows installations were found:
echo.
for /L %%N in (1,1,%FOUND_COUNT%) do (
    echo    %%N.  !DRIVE_%%N!\Windows
)
echo.
set "SELECTION="
set /P SELECTION="  Select installation [1-%FOUND_COUNT%]: "

:: Validate: must be a number
echo !SELECTION!| findstr /R "^[0-9][0-9]*$" >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [ERROR] Invalid input. Enter a number between 1 and %FOUND_COUNT%.
    echo.
    goto :MENU
)

:: Validate: must be within range
if !SELECTION! LSS 1 (
    echo.
    echo  [ERROR] Selection out of range.
    echo.
    goto :MENU
)
if !SELECTION! GTR %FOUND_COUNT% (
    echo.
    echo  [ERROR] Selection out of range.
    echo.
    goto :MENU
)

set "SELECTED_DRIVE=!DRIVE_%SELECTION%!"
call :LOG "Operator selected !SELECTED_DRIVE!"

echo.
choice /C YN /N /M "  Deploy into !SELECTED_DRIVE!\Windows? [Y/N]: "
if errorlevel 2 (
    echo.
    echo  Returning to menu...
    echo.
    goto :MENU
)
call :LOG "Operator confirmed installation into !SELECTED_DRIVE!"

:: ------------------------------------------------------------------------------
:: Deploy
:: ------------------------------------------------------------------------------
:DEPLOY
echo.
echo  ------------------------------------------------------------------------------
echo   Deploying to !SELECTED_DRIVE!
echo  ------------------------------------------------------------------------------
echo.

set "TARGET_SCRIPTS=!SELECTED_DRIVE!\Windows\Setup\Scripts"
set "TARGET_DRIVERS=!SELECTED_DRIVE!\ProgramData\ExampleMusic\Drivers"
set "TARGET_DETECT=!TARGET_SCRIPTS!\Detect-Platform.cmd"
set "TARGET_SETUPCOMPLETE=!TARGET_SCRIPTS!\SetupComplete.cmd"
set "TARGET_POWERSHELL=!TARGET_SCRIPTS!\Install-OpenSSH.ps1"

:: Verify Windows installation looks intact
call :LOG "Verifying target Windows installation..."
if NOT exist "!SELECTED_DRIVE!\Windows\System32" (
    call :LOG "ERROR: !SELECTED_DRIVE!\Windows\System32 not found. Target may be corrupt."
    echo  [ERROR] !SELECTED_DRIVE!\Windows\System32 not found.
    echo  The selected drive may not contain a valid Windows installation.
    goto :ABORT
)
call :LOG "Target verified: !SELECTED_DRIVE!\Windows\System32 exists."

:: ------------------------------------------------------------------------------
:: Create directories
:: ------------------------------------------------------------------------------
if NOT exist "!TARGET_SCRIPTS!" (
    call :LOG "Creating: !TARGET_SCRIPTS!"
    echo   Creating !TARGET_SCRIPTS!...
    mkdir "!TARGET_SCRIPTS!"
    if errorlevel 1 (
        call :LOG "ERROR: Failed to create !TARGET_SCRIPTS!"
        echo  [ERROR] Failed to create !TARGET_SCRIPTS!
        goto :ABORT
    )
    call :LOG "Created: !TARGET_SCRIPTS!"
) else (
    call :LOG "Exists: !TARGET_SCRIPTS!"
    echo   Exists: !TARGET_SCRIPTS!
)

if NOT exist "!TARGET_DRIVERS!" (
    call :LOG "Creating: !TARGET_DRIVERS!"
    echo   Creating !TARGET_DRIVERS!...
    mkdir "!TARGET_DRIVERS!"
    if errorlevel 1 (
        call :LOG "ERROR: Failed to create !TARGET_DRIVERS!"
        echo  [ERROR] Failed to create !TARGET_DRIVERS!
        goto :ABORT
    )
    call :LOG "Created: !TARGET_DRIVERS!"
) else (
    call :LOG "Exists: !TARGET_DRIVERS!"
    echo   Exists: !TARGET_DRIVERS!
)
echo.

:: ------------------------------------------------------------------------------
:: Copy drivers from WinPE media to target
:: ------------------------------------------------------------------------------
call :LOG "Copying drivers from %DRIVER_SOURCE% to !TARGET_DRIVERS!..."
echo   Copying drivers...
echo   Source : %DRIVER_SOURCE%
echo   Dest   : !TARGET_DRIVERS!
echo.

xcopy "%DRIVER_SOURCE%\*" "!TARGET_DRIVERS!\" /E /I /H /Y /Q >> "%LOGFILE%" 2>&1
if errorlevel 1 (
    call :LOG "ERROR: xcopy failed copying drivers."
    echo  [ERROR] Failed to copy drivers from %DRIVER_SOURCE%
    goto :ABORT
)
call :LOG "Drivers copied successfully."
echo   Drivers copied.
echo.

:: ------------------------------------------------------------------------------
:: Write Detect-Platform.cmd onto the target drive
:: ------------------------------------------------------------------------------
call :LOG "Writing Detect-Platform.cmd..."
echo   Writing Detect-Platform.cmd...

(
echo :: ==============================================================================
echo :: Example Music Limited
echo ::
echo :: Detect-Platform.cmd
echo ::
echo :: Version History
echo :: ---------------
echo :: 1.0.0   2026-06-28   Initial release
echo ::
echo :: Purpose
echo :: -------
echo :: Called by SetupComplete.cmd on first boot after Windows Setup.
echo :: Runs as LocalSystem before any user logs in.
echo ::
echo :: Detects the hypervisor platform via SMBIOS and driver signatures,
echo :: then silently installs the appropriate guest tools from:
echo ::   C:\ProgramData\ExampleMusic\Drivers\
echo ::
echo :: Supported platforms
echo :: -------------------
echo ::   KVM / Proxmox  - virtio-win-gt-x64.msi + qemu-ga-x86_64.msi
echo ::   VMware         - VMware-tools-13.1.0-25218885-x64.exe
echo ::
echo :: Log file
echo :: --------
echo ::   C:\ProgramData\ExampleMusic\Logs\Detect-Platform.log
echo ::
echo :: ==============================================================================
echo.
echo @echo off
echo setlocal EnableDelayedExpansion
echo.
echo set "SCRIPT_NAME=Detect-Platform.cmd"
echo set "SCRIPT_VERSION=1.0.0"
echo set "DRIVER_DIR=C:\ProgramData\ExampleMusic\Drivers"
echo set "LOG_DIR=C:\ProgramData\ExampleMusic\Logs"
echo set "LOGFILE=%%LOG_DIR%%\Detect-Platform.log"
echo.
echo if not exist "%%LOG_DIR%%" mkdir "%%LOG_DIR%%"
echo.
echo call :LOG "============================================================"
echo call :LOG "Example Music Limited"
echo call :LOG "%%SCRIPT_NAME%% v%%SCRIPT_VERSION%%"
echo call :LOG "Started: %%DATE%% %%TIME%%"
echo call :LOG "============================================================"
echo.
echo echo.
echo echo  ==============================================================================
echo echo   Example Music Limited  -  Detect-Platform.cmd v%%SCRIPT_VERSION%%
echo echo  ==============================================================================
echo echo.
echo.
echo :: --------------------------------------------------------------------------
echo :: 1. ARCH DETECTION
echo :: --------------------------------------------------------------------------
echo set "ARCH=unknown"
echo for /f "tokens=2 delims==" %%%%A in ^('wmic os get osarchitecture /value 2^^^>nul ^| find "="'^) do set "OSARCH=%%%%A"
echo echo %%OSARCH%%  ^| findstr /i "64"  ^>nul ^&^& set "ARCH=x64"
echo echo %%OSARCH%%  ^| findstr /i "ARM" ^>nul ^&^& set "ARCH=arm64"
echo call :LOG "ARCH=%%ARCH%%"
echo.
echo :: --------------------------------------------------------------------------
echo :: 2. SMBIOS DETECTION
echo :: --------------------------------------------------------------------------
echo set "BIOS="
echo set "PLATFORM=unknown"
echo for /f "tokens=1,2,*" %%%%A in ^('reg query "HKLM\HARDWARE\DESCRIPTION\System\BIOS" /v SystemManufacturer 2^^^>nul'^) do set "BIOS=%%%%C"
echo call :LOG "BIOS=%%BIOS%%"
echo.
echo echo %%BIOS%% ^| findstr /i "vmware"         ^>nul ^&^& set "PLATFORM=vmware"
echo echo %%BIOS%% ^| findstr /i "qemu bochs kvm" ^>nul ^&^& set "PLATFORM=kvm"
echo call :LOG "After SMBIOS: PLATFORM=%%PLATFORM%%"
echo.
echo :: --------------------------------------------------------------------------
echo :: 3. DRIVER OVERRIDE (stronger signal than SMBIOS alone)
echo :: --------------------------------------------------------------------------
echo driverquery 2^^^>nul ^| findstr /i "vmxnet vmware"              ^>nul ^&^& set "PLATFORM=vmware"
echo driverquery 2^^^>nul ^| findstr /i "virtio vioscsi balloon viostor" ^>nul ^&^& set "PLATFORM=kvm"
echo call :LOG "After driverquery: PLATFORM=%%PLATFORM%%"
echo.
echo :: --------------------------------------------------------------------------
echo :: 4. RESULT
echo :: --------------------------------------------------------------------------
echo call :LOG "FINAL PLATFORM=%%PLATFORM%%  ARCH=%%ARCH%%"
echo echo   Platform : %%PLATFORM%%
echo echo   Arch     : %%ARCH%%
echo echo.
echo.
echo if /i "%%PLATFORM%%"=="vmware" goto :VMWARE
echo if /i "%%PLATFORM%%"=="kvm"    goto :KVM
echo.
echo call :LOG "WARNING: Unknown platform. No guest tools installed."
echo echo  [WARN] Unknown platform detected. No guest tools installed.
echo goto :DETECT_END
echo.
echo :: --------------------------------------------------------------------------
echo :: KVM / Proxmox
echo :: --------------------------------------------------------------------------
echo :KVM
echo call :LOG "KVM/Proxmox detected. Installing VirtIO guest tools and QEMU agent..."
echo echo   Installing VirtIO guest tools...
echo.
echo if not exist "%%DRIVER_DIR%%\virtio-win-gt-x64.msi" ^(
echo   call :LOG "ERROR: virtio-win-gt-x64.msi not found in %%DRIVER_DIR%%"
echo   echo  [ERROR] virtio-win-gt-x64.msi not found in %%DRIVER_DIR%%
echo   goto :DETECT_END
echo ^)
echo msiexec /i "%%DRIVER_DIR%%\virtio-win-gt-x64.msi" /qn /norestart /l*v "%%LOG_DIR%%\virtio-win-gt-x64.log"
echo if errorlevel 1 ^(
echo   call :LOG "ERROR: virtio-win-gt-x64.msi install failed. Exit code: %%ERRORLEVEL%%"
echo   echo  [ERROR] VirtIO guest tools installation failed.
echo ^) else ^(
echo   call :LOG "virtio-win-gt-x64.msi installed successfully."
echo   echo   VirtIO guest tools installed.
echo ^)
echo.
echo echo   Installing QEMU guest agent...
echo if not exist "%%DRIVER_DIR%%\qemu-ga-x86_64.msi" ^(
echo   call :LOG "ERROR: qemu-ga-x86_64.msi not found in %%DRIVER_DIR%%"
echo   echo  [ERROR] qemu-ga-x86_64.msi not found in %%DRIVER_DIR%%
echo   goto :DETECT_END
echo ^)
echo msiexec /i "%%DRIVER_DIR%%\qemu-ga-x86_64.msi" /qn /norestart /l*v "%%LOG_DIR%%\qemu-ga-x86_64.log"
echo if errorlevel 1 ^(
echo   call :LOG "ERROR: qemu-ga-x86_64.msi install failed. Exit code: %%ERRORLEVEL%%"
echo   echo  [ERROR] QEMU guest agent installation failed.
echo ^) else ^(
echo   call :LOG "qemu-ga-x86_64.msi installed successfully."
echo   echo   QEMU guest agent installed.
echo ^)
echo goto :DETECT_END
echo.
echo :: --------------------------------------------------------------------------
echo :: VMware
echo :: --------------------------------------------------------------------------
echo :VMWARE
echo call :LOG "VMware detected. Installing VMware Tools..."
echo echo   Installing VMware Tools...
echo.
echo if not exist "%%DRIVER_DIR%%\VMware-tools-13.1.0-25218885-x64.exe" ^(
echo   call :LOG "ERROR: VMware-tools-13.1.0-25218885-x64.exe not found in %%DRIVER_DIR%%"
echo   echo  [ERROR] VMware Tools installer not found in %%DRIVER_DIR%%
echo   goto :DETECT_END
echo ^)
echo "%%DRIVER_DIR%%\VMware-tools-13.1.0-25218885-x64.exe" /S /v"/qn /norestart /l*v \"%%LOG_DIR%%\vmware-tools.log\""
echo if errorlevel 1 ^(
echo   call :LOG "ERROR: VMware Tools install failed. Exit code: %%ERRORLEVEL%%"
echo   echo  [ERROR] VMware Tools installation failed.
echo ^) else ^(
echo   call :LOG "VMware Tools installed successfully."
echo   echo   VMware Tools installed.
echo ^)
echo goto :DETECT_END
echo.
echo :: --------------------------------------------------------------------------
echo :: End
echo :: --------------------------------------------------------------------------
echo :DETECT_END
echo call :LOG "Finished: %%DATE%% %%TIME%%"
echo call :LOG "============================================================"
echo endlocal
echo exit /b 0
echo.
echo :LOG
echo echo [%%DATE%% %%TIME%%] %%~1 ^>^> "%%LOGFILE%%"
echo exit /b 0
) > "!TARGET_DETECT!"

if errorlevel 1 (
    call :LOG "ERROR: Failed to write Detect-Platform.cmd"
    echo  [ERROR] Failed to write Detect-Platform.cmd
    goto :ABORT
)
call :LOG "Detect-Platform.cmd written successfully."
echo   Detect-Platform.cmd written.
echo.

:: ------------------------------------------------------------------------------
:: Write SetupComplete.cmd onto the target drive
:: Calls Detect-Platform.cmd first, then Install-OpenSSH.ps1
:: ------------------------------------------------------------------------------
call :LOG "Writing SetupComplete.cmd..."
echo   Writing SetupComplete.cmd...

(
echo :: ==============================================================================
echo :: Example Music Limited
echo ::
echo :: SetupComplete.cmd
echo ::
echo :: Version History
echo :: ---------------
echo :: 1.0.0   2026-06-28   Initial release
echo :: 1.1.0   2026-06-28   Added call to Detect-Platform.cmd before OpenSSH setup
echo ::
echo :: Purpose
echo :: -------
echo :: Executed automatically by Windows Setup after installation completes,
echo :: as LocalSystem, before the first user login.
echo ::
echo :: Sequence
echo :: --------
echo ::   1. Detect-Platform.cmd  - hypervisor detection, guest tools install
echo ::   2. Install-OpenSSH.ps1  - OpenSSH Server install and configuration
echo ::
echo :: ==============================================================================
echo.
echo @echo off
echo setlocal
echo.
echo set "SCRIPTS=%~dp0"
echo set "PS1=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
echo.
echo :: --------------------------------------------------------------------------
echo :: Step 1: Platform detection and guest tools
echo :: --------------------------------------------------------------------------
echo if not exist "%%SCRIPTS%%Detect-Platform.cmd" (
echo     echo [ERROR] Detect-Platform.cmd not found at %%SCRIPTS%%
echo ) else (
echo     call "%%SCRIPTS%%Detect-Platform.cmd"
echo )
echo.
echo :: --------------------------------------------------------------------------
echo :: Step 2: OpenSSH install
echo :: --------------------------------------------------------------------------
echo if not exist "%%PS1%%" (
echo     echo [ERROR] PowerShell not found at %%PS1%%
echo     exit /b 1
echo )
echo if not exist "%%SCRIPTS%%Install-OpenSSH.ps1" (
echo     echo [ERROR] Install-OpenSSH.ps1 not found at %%SCRIPTS%%
echo     exit /b 1
echo )
echo "%%PS1%%" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%%SCRIPTS%%Install-OpenSSH.ps1"
echo exit /b %%ERRORLEVEL%%
) > "!TARGET_SETUPCOMPLETE!"

if errorlevel 1 (
    call :LOG "ERROR: Failed to write SetupComplete.cmd"
    echo  [ERROR] Failed to write SetupComplete.cmd
    goto :ABORT
)
call :LOG "SetupComplete.cmd written successfully."
echo   SetupComplete.cmd written.
echo.

:: ------------------------------------------------------------------------------
:: Write Install-OpenSSH.ps1 onto the target drive
:: ------------------------------------------------------------------------------
call :LOG "Writing Install-OpenSSH.ps1..."
echo   Writing Install-OpenSSH.ps1...

(
echo # ==============================================================================
echo # Example Music Limited
echo #
echo # Install-OpenSSH.ps1
echo #
echo # Version History
echo # ---------------
echo # 1.0.0   2026-06-28   Initial release
echo #
echo # Purpose
echo # -------
echo # Called by SetupComplete.cmd on first boot after Windows Setup.
echo # Runs as LocalSystem before any user logs in.
echo #
echo # Installs OpenSSH Client + Server, configures sshd, opens firewall TCP/22.
echo # Idempotent: safe to run multiple times.
echo #
echo # Log file
echo # --------
echo #   C:\ProgramData\ExampleMusic\Logs\Install-OpenSSH.log
echo #
echo # ==============================================================================
echo.
echo #Requires -Version 5.1
echo.
echo $ScriptVersion = '1.0.0'
echo $LogDir  = 'C:\ProgramData\ExampleMusic\Logs'
echo $LogFile = "$LogDir\Install-OpenSSH.log"
echo.
echo if (-not (Test-Path -Path $LogDir)) {
echo   New-Item -ItemType Directory -Path $LogDir -Force ^| Out-Null
echo }
echo.
echo Start-Transcript -Path $LogFile -Append -Force
echo.
echo Write-Host ''
echo Write-Host '============================================================' -ForegroundColor Cyan
echo Write-Host '  Example Music Limited' -ForegroundColor Cyan
echo Write-Host "  Install-OpenSSH.ps1 v$ScriptVersion" -ForegroundColor Cyan
echo Write-Host "  $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Cyan
echo Write-Host '============================================================' -ForegroundColor Cyan
echo Write-Host ''
echo.
echo function Write-Status {
echo   param([string]$Message, [string]$Colour = 'White')
echo   Write-Host "  $Message" -ForegroundColor $Colour
echo }
echo.
echo # ------------------------------------------------------------------------------
echo # OpenSSH Client
echo # ------------------------------------------------------------------------------
echo Write-Status 'Checking OpenSSH Client...' Cyan
echo $cap = Get-WindowsCapability -Online -Name 'OpenSSH.Client~~~~0.0.1.0' -ErrorAction SilentlyContinue
echo if ($cap.State -eq 'Installed') {
echo   Write-Status 'OpenSSH Client already installed.' Green
echo } else {
echo   Write-Status 'Installing OpenSSH Client...' Yellow
echo   Add-WindowsCapability -Online -Name 'OpenSSH.Client~~~~0.0.1.0' ^| Out-Null
echo   Write-Status 'OpenSSH Client installed.' Green
echo }
echo Write-Host ''
echo.
echo # ------------------------------------------------------------------------------
echo # OpenSSH Server
echo # ------------------------------------------------------------------------------
echo Write-Status 'Checking OpenSSH Server...' Cyan
echo $cap = Get-WindowsCapability -Online -Name 'OpenSSH.Server~~~~0.0.1.0' -ErrorAction SilentlyContinue
echo if ($cap.State -eq 'Installed') {
echo   Write-Status 'OpenSSH Server already installed.' Green
echo } else {
echo   Write-Status 'Installing OpenSSH Server...' Yellow
echo   Add-WindowsCapability -Online -Name 'OpenSSH.Server~~~~0.0.1.0' ^| Out-Null
echo   Write-Status 'OpenSSH Server installed.' Green
echo }
echo Write-Host ''
echo.
echo # ------------------------------------------------------------------------------
echo # sshd service
echo # ------------------------------------------------------------------------------
echo Write-Status 'Configuring sshd...' Cyan
echo $svc = Get-Service -Name sshd -ErrorAction SilentlyContinue
echo if ($null -eq $svc) {
echo   Write-Status 'WARNING: sshd not found. OpenSSH Server may not have installed.' Red
echo } else {
echo   Set-Service -Name sshd -StartupType Automatic
echo   Write-Status 'sshd set to Automatic.' Green
echo   if ($svc.Status -ne 'Running') {
echo     Start-Service -Name sshd
echo     Write-Status 'sshd started.' Green
echo   } else {
echo     Write-Status 'sshd already running.' Green
echo   }
echo }
echo Write-Host ''
echo.
echo # ------------------------------------------------------------------------------
echo # Firewall rule TCP/22
echo # ------------------------------------------------------------------------------
echo Write-Status 'Checking firewall rule for TCP/22...' Cyan
echo $fw = Get-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -ErrorAction SilentlyContinue
echo if ($null -ne $fw) {
echo   Write-Status 'Firewall rule already exists.' Green
echo } else {
echo   Write-Status 'Creating firewall rule...' Yellow
echo   New-NetFirewallRule `
echo     -Name        'OpenSSH-Server-In-TCP' `
echo     -DisplayName 'OpenSSH Server (TCP/22)' `
echo     -Description 'Created by Example Music Install-OpenSSH.ps1' `
echo     -Direction   Inbound `
echo     -Protocol    TCP `
echo     -LocalPort   22 `
echo     -Action      Allow `
echo     -Profile     Any ^| Out-Null
echo   Write-Status 'Firewall rule created.' Green
echo }
echo Write-Host ''
echo.
echo Write-Host '============================================================' -ForegroundColor Cyan
echo Write-Host '  Install-OpenSSH complete.' -ForegroundColor Green
echo Write-Host "  Log: $LogFile" -ForegroundColor Cyan
echo Write-Host '============================================================' -ForegroundColor Cyan
echo Write-Host ''
echo.
echo Stop-Transcript
echo exit 0
) > "!TARGET_POWERSHELL!"

if errorlevel 1 (
    call :LOG "ERROR: Failed to write Install-OpenSSH.ps1"
    echo  [ERROR] Failed to write Install-OpenSSH.ps1
    goto :ABORT
)
call :LOG "Install-OpenSSH.ps1 written successfully."
echo   Install-OpenSSH.ps1 written.
echo.

:: ------------------------------------------------------------------------------
:: Verify all four artefacts are present on target
:: ------------------------------------------------------------------------------
call :LOG "Verifying written files..."
set VERIFY_OK=1

if NOT exist "!TARGET_DETECT!" (
    call :LOG "ERROR: Detect-Platform.cmd missing after write."
    echo  [ERROR] Verify failed: Detect-Platform.cmd not present.
    set VERIFY_OK=0
)
if NOT exist "!TARGET_SETUPCOMPLETE!" (
    call :LOG "ERROR: SetupComplete.cmd missing after write."
    echo  [ERROR] Verify failed: SetupComplete.cmd not present.
    set VERIFY_OK=0
)
if NOT exist "!TARGET_POWERSHELL!" (
    call :LOG "ERROR: Install-OpenSSH.ps1 missing after write."
    echo  [ERROR] Verify failed: Install-OpenSSH.ps1 not present.
    set VERIFY_OK=0
)
if NOT exist "!TARGET_DRIVERS!\virtio-win-gt-x64.msi" (
    call :LOG "ERROR: virtio-win-gt-x64.msi missing from target Drivers folder."
    echo  [ERROR] Verify failed: virtio-win-gt-x64.msi not in !TARGET_DRIVERS!
    set VERIFY_OK=0
)
if NOT exist "!TARGET_DRIVERS!\qemu-ga-x86_64.msi" (
    call :LOG "ERROR: qemu-ga-x86_64.msi missing from target Drivers folder."
    echo  [ERROR] Verify failed: qemu-ga-x86_64.msi not in !TARGET_DRIVERS!
    set VERIFY_OK=0
)

if !VERIFY_OK! EQU 0 goto :ABORT

call :LOG "Verification passed."

:: ------------------------------------------------------------------------------
:: Success
:: ------------------------------------------------------------------------------
echo  ==============================================================================
echo   Deployment complete.
echo  ==============================================================================
echo.
echo   Target drive    :  !SELECTED_DRIVE!
echo   Scripts         :  !TARGET_SCRIPTS!
echo   Drivers         :  !TARGET_DRIVERS!
echo.
echo   Files in Scripts\:
echo     Detect-Platform.cmd
echo     SetupComplete.cmd
echo     Install-OpenSSH.ps1
echo.
echo   Files in Drivers\:
echo     qemu-ga-x86_64.msi
echo     virtio-win-gt-x64.msi
echo     VMware-tools-13.1.0-25218885-x64.exe
echo.
echo   First-boot sequence:
echo     1. Detect-Platform.cmd  (hypervisor detect + guest tools)
echo     2. Install-OpenSSH.ps1  (OpenSSH Server)
echo.
echo   WinPE log  :  %LOGFILE%
echo.
call :LOG "Deployment completed successfully."
call :LOG "Target: !SELECTED_DRIVE!"
goto :END

:: ------------------------------------------------------------------------------
:: Abort
:: ------------------------------------------------------------------------------
:ABORT
echo.
echo  ==============================================================================
echo   Deployment aborted.
echo  ==============================================================================
echo.
echo   WinPE log  :  %LOGFILE%
echo.
call :LOG "Deployment aborted."
endlocal
exit /b 1

:: ------------------------------------------------------------------------------
:: End
:: ------------------------------------------------------------------------------
:END
call :LOG "Finished: %DATE% %TIME%"
call :LOG "============================================================"
endlocal
exit /b 0

:: ------------------------------------------------------------------------------
:: Subroutine: LOG
:: Writes a timestamped line to the WinPE log file.
:: ------------------------------------------------------------------------------
:LOG
echo [%DATE% %TIME%] %~1 >> "%LOGFILE%"
exit /b 0
