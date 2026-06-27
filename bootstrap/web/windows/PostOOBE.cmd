@echo off
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
