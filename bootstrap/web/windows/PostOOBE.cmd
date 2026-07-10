@echo off
REM HISTORICAL ARTEFACT (2026-07-10): launcher for Join-DomainAndBootstrap.ps1,
REM itself a historical artefact predating Ansible's windows_bootstrap chain --
REM see that script's own header. Not a live/maintained path.
title Windows Deployment – Domain Bootstrap
color 0B

echo.
echo ==================================================
echo   Windows Post-OOBE Domain Bootstrap
echo ==================================================
echo.

REM Give networking time to settle
timeout /t 8 >nul

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "& '\\DC01\deploytools\Join-DomainAndBootstrap.ps1'"

exit /b 0
