:: ==============================================================================
:: Example Music Limited
::
:: Detect-Platform.cmd
::
:: Version History
:: ---------------
:: 1.0.0   2026-06-28   Initial release
::
:: Purpose
:: -------
:: Called by SetupComplete.cmd on first boot after Windows Setup.
:: Runs as LocalSystem before any user logs in.
::
:: Detects CPU architecture and hypervisor platform via SMBIOS and driver
:: signatures, then silently installs the appropriate guest tools from:
::   C:\ProgramData\ExampleMusic\Drivers\
::
:: No network access is required - all installers are pre-staged to disk
:: by Deploy-OpenSSH.cmd during the WinPE phase, precisely because network
:: drivers are not yet available at first boot.
::
:: Supported combinations
:: ----------------------
::   x86_64 + KVM/Proxmox  - virtio-win-gt-x64.msi + qemu-ga-x86_64.msi
::   x86_64 + VMware        - VMware-tools-13.0.10-25056151-x64.exe
::   arm64  + VMware        - VMware-tools-13.0.10-25056151-arm.exe
::   arm64  + KVM/Proxmox   - not supported (logged and skipped)
::
:: Log file
:: --------
::   C:\ProgramData\ExampleMusic\Logs\Detect-Platform.log
::
:: ==============================================================================

@echo off
setlocal EnableDelayedExpansion

set "SCRIPT_NAME=Detect-Platform.cmd"
set "SCRIPT_VERSION=1.0.0"
set "DRIVER_DIR=C:\ProgramData\ExampleMusic\Drivers"
set "LOG_DIR=C:\ProgramData\ExampleMusic\Logs"
set "LOGFILE=%LOG_DIR%\Detect-Platform.log"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

call :LOG "============================================================"
call :LOG "%ORG_NAME%  -  %SCRIPT_NAME% v%SCRIPT_VERSION%"
call :LOG "Started: %DATE% %TIME%"
call :LOG "============================================================"

echo.
echo  ==============================================================================
echo   Example Music Limited  -  %SCRIPT_NAME% v%SCRIPT_VERSION%
echo  ==============================================================================
echo.

:: ------------------------------------------------------------------------------
:: 1. Architecture detection
:: ------------------------------------------------------------------------------
set "ARCH=unknown"
if /i "%PROCESSOR_ARCHITECTURE%"=="AMD64" set "ARCH=x86_64"
if /i "%PROCESSOR_ARCHITECTURE%"=="ARM64" set "ARCH=arm64"
call :LOG "ARCH=%ARCH%"
echo   Architecture : %ARCH%

:: ------------------------------------------------------------------------------
:: 2. SMBIOS detection
:: ------------------------------------------------------------------------------
set "BIOS="
set "PLATFORM=unknown"
for /f "tokens=1,2,*" %%A in ('reg query "HKLM\HARDWARE\DESCRIPTION\System\BIOS" /v SystemManufacturer 2^>nul') do set "BIOS=%%C"
call :LOG "BIOS=%BIOS%"

echo %BIOS% | findstr /i "vmware"         >nul && set "PLATFORM=vmware"
echo %BIOS% | findstr /i "qemu bochs kvm" >nul && set "PLATFORM=kvm"
call :LOG "After SMBIOS: PLATFORM=%PLATFORM%"

:: ------------------------------------------------------------------------------
:: 3. Driver query override (stronger signal than SMBIOS alone)
:: ------------------------------------------------------------------------------
driverquery 2>nul | findstr /i "vmxnet vmware"                 >nul && set "PLATFORM=vmware"
driverquery 2>nul | findstr /i "virtio vioscsi balloon viostor" >nul && set "PLATFORM=kvm"
call :LOG "After driverquery: PLATFORM=%PLATFORM%"

echo   Platform     : %PLATFORM%
echo.
call :LOG "FINAL  ARCH=%ARCH%  PLATFORM=%PLATFORM%"

:: ------------------------------------------------------------------------------
:: 4. Route to installer
:: ------------------------------------------------------------------------------
if /i "%PLATFORM%"=="kvm"    goto :KVM
if /i "%PLATFORM%"=="vmware" goto :VMWARE

call :LOG "WARNING: Unknown platform. No guest tools installed."
echo  [WARN] Unknown platform detected. No guest tools installed.
goto :DETECT_END

:: ------------------------------------------------------------------------------
:: KVM / Proxmox  (x86_64 only - arm64 not supported)
:: ------------------------------------------------------------------------------
:KVM
if /i "%ARCH%"=="arm64" (
    call :LOG "WARNING: KVM/Proxmox detected on arm64 - no guest tools available for this combination."
    echo  [WARN] KVM/Proxmox on arm64 is not supported. No guest tools installed.
    goto :DETECT_END
)

call :LOG "KVM/Proxmox + x86_64 detected."

call :MSI "%DRIVER_DIR%\virtio-win-gt-x64.msi" "%LOG_DIR%\virtio-win-gt-x64.log" "VirtIO guest tools"
call :MSI "%DRIVER_DIR%\qemu-ga-x86_64.msi"    "%LOG_DIR%\qemu-ga-x86_64.log"   "QEMU guest agent"
goto :DETECT_END

:: ------------------------------------------------------------------------------
:: VMware  (x86_64 and arm64)
:: ------------------------------------------------------------------------------
:VMWARE
call :LOG "VMware detected. ARCH=%ARCH%"

if /i "%ARCH%"=="x86_64" (
    set "VMWARE_EXE=%DRIVER_DIR%\VMware-tools-13.0.10-25056151-x64.exe"
)
if /i "%ARCH%"=="arm64" (
    set "VMWARE_EXE=%DRIVER_DIR%\VMware-tools-13.0.10-25056151-arm.exe"
)

if not exist "%VMWARE_EXE%" (
    call :LOG "ERROR: VMware Tools installer not found: %VMWARE_EXE%"
    echo  [ERROR] VMware Tools installer not found: %VMWARE_EXE%
    goto :DETECT_END
)

call :LOG "Installing VMware Tools: %VMWARE_EXE%"
echo   Installing VMware Tools...
"%VMWARE_EXE%" /S /v"/qn /norestart /l*v \"%LOG_DIR%\vmware-tools.log\""
if errorlevel 1 (
    call :LOG "ERROR: VMware Tools installation failed. Exit code: %ERRORLEVEL%"
    echo  [ERROR] VMware Tools installation failed.
) else (
    call :LOG "VMware Tools installed successfully."
    echo   VMware Tools installed.
)
goto :DETECT_END

:: ------------------------------------------------------------------------------
:: End
:: ------------------------------------------------------------------------------
:DETECT_END
call :LOG "Finished: %DATE% %TIME%"
call :LOG "============================================================"
echo.
endlocal
exit /b 0

:: ------------------------------------------------------------------------------
:: Subroutine: MSI
:: Installs an MSI silently, logs result.
:: Usage: call :MSI "<msi_path>" "<log_path>" "<friendly_name>"
:: ------------------------------------------------------------------------------
:MSI
set "M_MSI=%~1"
set "M_LOG=%~2"
set "M_NAME=%~3"
if not exist "%M_MSI%" (
    call :LOG "ERROR: %M_NAME% installer not found: %M_MSI%"
    echo  [ERROR] %M_NAME% installer not found: %M_MSI%
    exit /b 1
)
call :LOG "Installing %M_NAME%: %M_MSI%"
echo   Installing %M_NAME%...
msiexec /i "%M_MSI%" /qn /norestart /l*v "%M_LOG%"
if errorlevel 1 (
    call :LOG "ERROR: %M_NAME% installation failed. Exit code: %ERRORLEVEL%"
    echo  [ERROR] %M_NAME% installation failed.
) else (
    call :LOG "%M_NAME% installed successfully."
    echo   %M_NAME% installed.
)
exit /b 0

:: ------------------------------------------------------------------------------
:: Subroutine: LOG
:: ------------------------------------------------------------------------------
:LOG
echo [%DATE% %TIME%] %~1 >> "%LOGFILE%"
exit /b 0
