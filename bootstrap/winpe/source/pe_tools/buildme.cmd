:: Full build script for cecho, respe and dartparse
@echo off
setlocal

set VSDEV="C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\Common7\Tools\VsDevCmd.bat"

echo ========================= Building ResPE (C), cEcho (C++) and DartParse (C++) =========================

:: ------------------------- Build x64 -------------------------
echo.
echo [x64]

call %VSDEV% -arch=x64 >nul

echo Compiling cEcho - Colour Echo (C++ amd64)...
cd cecho
rc.exe cecho.rc
cl.exe /O1 /MT /nologo cecho_v2.cpp cecho.res user32.lib /link /SUBSYSTEM:CONSOLE /Fe:cecho-arm64.exe
rename cecho_v2.exe cecho-arm64.exe
del *.obj *.res 2>nul
cd ..

echo Compiling DartParse - Microsoft DART XML Parser (amd64)
cd cecho
rc.exe dartparse.rc
cl /O2 /EHsc dartparse.cpp dartparse.res
rename dartparse.exe dartparse-arm64.exe
del *.obj *.res 2>nul
cd ..

echo Compiling resPE - Screen Resolution Change For WinPE (C amd64)...
cd dartparse
rc.exe respe.rc
cl.exe /O1 /MT /nologo respe.c respe.res user32.lib /link /SUBSYSTEM:CONSOLE /Fe:respe-arm64.exe
rename respe.exe respe-arm64.exe
del *.obj *.res 2>nul
cd ..

echo.
echo.
echo ========================= Build complete =========================
pause
:: ------------------------- Build ARM64 -------------------------
echo.
echo [ARM64]

call %VSDEV% -arch=arm64 >nul

echo Compiling cEcho - Colour Echo (C++ arm64)...
cd cecho
rc.exe cecho.rc
cl.exe /O1 /MT /nologo cecho_v2.cpp cecho.res user32.lib /link /SUBSYSTEM:CONSOLE /Fe:cecho-arm64.exe
rename cecho_v2.exe cecho-arm64.exe
del *.obj *.res 2>nul
cd ..

echo Compiling DartParse - Microsoft DART XML Parser (arm64)
cd cecho
rc.exe dartparse.rc
cl /O2 /EHsc dartparse.cpp dartparse.res
rename dartparse.exe dartparse-arm64.exe
del *.obj *.res 2>nul
cd ..

echo Compiling resPE - Screen Resolution Change For WinPE (C arm64)...
cd dartparse
rc.exe respe.rc
cl.exe /O1 /MT /nologo respe.c respe.res user32.lib /link /SUBSYSTEM:CONSOLE /Fe:respe-arm64.exe
rename respe.exe respe-arm64.exe
del *.obj *.res 2>nul
cd ..

echo.
echo ========================= Build complete =========================
pause