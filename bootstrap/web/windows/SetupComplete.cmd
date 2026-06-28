@ECHO OFF
ECHO+

:: ==============================================================================
:: Example Music Limited
::
:: SetupComplete.cmd
::
:: Version History
:: ---------------
:: 1.0.0   2026-06-28   Initial release
::
:: Purpose
:: -------
:: Executed automatically by Windows Setup after installation completes,
:: as LocalSystem, before the first user login.
::
:: Sequence
:: --------
::   1. Detect-Platform.cmd  - hypervisor detection, guest tools install
::   2. Install-OpenSSH.ps1  - OpenSSH Server install and configuration
::
:: Both scripts are in the same directory as this file:
::   C:\Windows\Setup\Scripts\
::
:: ==============================================================================

setlocal

set "SCRIPTS=%~dp0"
set "PS1=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"

:: ------------------------------------------------------------------------------
:: Step 1: Platform detection and guest tools
:: ------------------------------------------------------------------------------
if not exist "%SCRIPTS%Detect-Platform.cmd" (
    echo [ERROR] Detect-Platform.cmd not found at %SCRIPTS%
) else (
    call "%SCRIPTS%Detect-Platform.cmd"
)

:: ------------------------------------------------------------------------------
:: Step 2: OpenSSH install
:: ------------------------------------------------------------------------------
if not exist "%PS1%" (
    echo [ERROR] PowerShell not found at %PS1%
    exit /b 1
)
if not exist "%SCRIPTS%Install-OpenSSH.ps1" (
    echo [ERROR] Install-OpenSSH.ps1 not found at %SCRIPTS%
    exit /b 1
)

"%PS1%" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%SCRIPTS%Install-OpenSSH.ps1"
exit /b %ERRORLEVEL%
