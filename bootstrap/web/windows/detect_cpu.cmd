@echo off
::------------------------------------------------------::
:: Detect CPU architecture and select folder            ::
:: Works in CMD / .bat / .cmd                           ::
::------------------------------------------------------::

REM Detect architecture
IF "%PROCESSOR_ARCHITECTURE%"=="AMD64" SET ARCH=x86_64
IF "%PROCESSOR_ARCHITECTURE%"=="ARM64" SET ARCH=arm64
IF "%PROCESSOR_ARCHITECTURE%"=="x86" SET ARCH=x86

REM Set path to architecture-specific folder (relative to script)
SET ARCH_PATH=%~dp0%ARCH%

ECHO Detected architecture: %ARCH%
ECHO Using binaries from folder: %ARCH_PATH%

:: Example: run a binary dynamically
:: "%ARCH_PATH%\RemoteDesktop_1.2.6228.0_%ARCH%.msi"