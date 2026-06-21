@echo off
setlocal ENABLEEXTENSIONS

echo ==========================================
echo   WinPE Hypervisor Detect + Driver Loader
echo ==========================================

set ARCH=unknown
set PLATFORM=unknown
set LOG=X:\vm_detect.log

echo [INFO] Starting detection... > %LOG%

:: ==================================================
:: 1. ARCH DETECTION
:: ==================================================
for /f "tokens=2 delims==" %%A in ('wmic os get osarchitecture /value 2^>nul ^| find "="') do set OSARCH=%%A

echo %OSARCH% | findstr /i "64" >nul && set ARCH=x64
echo %OSARCH% | findstr /i "ARM" >nul && set ARCH=arm64

echo [INFO] ARCH=%ARCH% >> %LOG%

:: ==================================================
:: 2. SMBIOS DETECTION
:: ==================================================
set BIOS=

for /f "tokens=1,2,*" %%A in ('reg query "HKLM\HARDWARE\DESCRIPTION\System\BIOS" /v SystemManufacturer 2^>nul') do set BIOS=%%C

echo [INFO] BIOS=%BIOS% >> %LOG%

:: ==================================================
:: 3. BASE PLATFORM DETECTION (SMBIOS)
:: ==================================================
set PLATFORM=unknown

echo %BIOS% | findstr /i "vmware" >nul && set PLATFORM=vmware
echo %BIOS% | findstr /i "qemu bochs kvm" >nul && set PLATFORM=kvm
echo %BIOS% | findstr /i "microsoft hyper-v" >nul && set PLATFORM=hyperv

echo [INFO] After SMBIOS PLATFORM=%PLATFORM% >> %LOG%

:: ==================================================
:: 4. DRIVER OVERRIDE (STRONG SIGNALS)
:: ==================================================

driverquery | findstr /i "vmxnet vmware" >nul && set PLATFORM=vmware
driverquery | findstr /i "virtio vioscsi balloon viostor" >nul && set PLATFORM=kvm

:: IMPORTANT FIX:
:: Hyper-V is ONLY valid if explicitly detected after everything else
driverquery | findstr /i "hvboot hvsi vmbus" >nul && set HV_HINT=1

echo [INFO] Driver check complete >> %LOG%

:: ==================================================
:: 5. HYPER-V VALIDATION (FIXED LOGIC)
:: ==================================================
if "%PLATFORM%"=="unknown" (
    if "%HV_HINT%"=="1" set PLATFORM=hyperv
)

echo [INFO] FINAL PLATFORM=%PLATFORM% >> %LOG%

:: ==================================================
:: 6. OUTPUT
:: ==================================================
echo.
echo ==========================
echo ARCH     : %ARCH%
echo PLATFORM : %PLATFORM%
echo ==========================

echo [RESULT] ARCH=%ARCH% PLATFORM=%PLATFORM% >> %LOG%

:: ==================================================
:: 7. DRIVER LOADING
:: ==================================================

if /i "%PLATFORM%"=="vmware" goto vmware
if /i "%PLATFORM%"=="kvm" goto kvm
if /i "%PLATFORM%"=="hyperv" goto hyperv

echo [WARN] Unknown platform - no drivers loaded >> %LOG%
goto end

:: ---------------- VMware ----------------
:vmware
echo [INFO] VMware detected - loading drivers...

if /i "%ARCH%"=="x64" drvload X:\Drivers\VMware\x64\vmxnet3.inf
if /i "%ARCH%"=="arm64" drvload X:\Drivers\VMware\arm64\vmxnet3.inf

goto end

:: ---------------- KVM / Proxmox ----------------
:kvm
echo [INFO] KVM/Proxmox detected - loading VirtIO drivers...

if /i "%ARCH%"=="x64" drvload X:\Drivers\VirtIO\x64\viostor.inf
if /i "%ARCH%"=="arm64" drvload X:\Drivers\VirtIO\arm64\viostor.inf

goto end

:: ---------------- Hyper-V ----------------
:hyperv
echo [INFO] Hyper-V detected - loading drivers...

drvload X:\Drivers\HyperV\vmbus.inf

goto end

:end
echo [INFO] Done.
echo [INFO] Log: %LOG%
endlocal