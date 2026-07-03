# Example Music Limited — cecho + dartparse Build Procedure

> **Classification:** Internal — Infrastructure  
> **Applies to:** Build box (fresh Win11, 60 GB+ free disk, Chocolatey installed)  
> **Covers:** MSVC (x64 + ARM64) · MinGW (x64 + ARM64) · Ubuntu cross-compile · GitHub Actions CI  
> **Formatting style:** 2-space indentation, concise, ops-friendly  
> **Credentials:** See password manager — do **not** store passwords in this document  

---

## Overview

Provides a from-zero (fresh Win11) setup, build, and CI pipeline for `cecho.cpp` and `dartparse.cpp`. Both binaries are required by the WinPE `startnet.cmd` startup script and must be placed in `tools\amd64\Windows\System32\` so they land on `PATH` in the live PE environment.

- **`cecho.exe`** — colour console output using Windows console API colour codes
- **`dartparse.exe`** — extracts fields from DaRT's `inv32.xml` (ticket ID, port)

---

## 0. Prerequisites — Fresh Windows 11

> Assumes Chocolatey is already installed

### Install core toolchains

```powershell
choco install visualstudio2022buildtools -y
choco install visualstudio2022-workload-vctools -y
choco install windows-sdk-10-version-2004-all -y
choco install mingw -y
choco install msys2 -y
```

### Install missing MSVC ARM64 + static CRT components

> **This fixes `libcpmt` / ARM64 link errors**

```cmd
"C:\Program Files (x86)\Microsoft Visual Studio\Installer\vs_installer.exe" modify ^
  --installPath "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools" ^
  --add Microsoft.VisualStudio.Component.VC.Tools.ARM64 ^
  --add Microsoft.VisualStudio.Component.VC.ATL.ARM64 ^
  --add Microsoft.VisualStudio.Component.VC.Spectre.ARM64 ^
  --add Microsoft.VisualStudio.Component.Windows11SDK.22621 ^
  --passive --norestart
```

### MSYS2 setup (ARM64 MinGW)

Open MSYS2 shell and run:

```bash
pacman -S mingw-w64-x86_64-gcc
pacman -S mingw-w64-aarch64-gcc
```

---

## 1. MSVC Command Prompt Usage

### Start x64 prompt

```cmd
"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\Common7\Tools\VsDevCmd.bat" -arch=x64
```

### Start ARM64 prompt (cross-compile)

```cmd
"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvarsall.bat" x64_arm64
```

### Verify

```cmd
where cl
```

---

## 2. Build Commands

### MSVC x64

```cmd
cl cecho.cpp /O2 /MT /EHsc /Fe:cecho-x64.exe
```

### MSVC ARM64

```cmd
vcvarsall.bat x64_arm64
cl cecho.cpp /O2 /MT /EHsc /Fe:cecho-arm64.exe
```

### MinGW x64

```bash
g++ cecho.cpp -O2 -s -static -o cecho-x64.exe
```

### MinGW ARM64

```bash
aarch64-w64-mingw32-g++ cecho.cpp -O2 -s -static -o cecho-arm64.exe
```

> **Note:** `/MT` (static CRT) is required for WinPE — there is no runtime DLL available. Verify with `dumpbin /imports cecho.exe` — only `kernel32.dll` and
> `user32.dll` should appear.

---

## 3. dartparse Usage

`dartparse` parses `inv32.xml` written by DaRT's `RemoteRecovery.exe` and extracts named fields. Called in `startnet.cmd` as:

```cmd
for /f "delims=" %%A in ('dartparse.exe /g ID /b /f inv32.xml') do set "ID=%%A"
```

| Flag | Meaning |
|------|---------|
| `/g ID` | Get field named `ID` (ticket number) |
| `/g P` | Get field named `P` (port) |
| `/b` | Bare output — value only, no labels |
| `/f inv32.xml` | Input file (filename only — file is in System32, globally available) |

Build commands are identical to cecho — substitute `dartparse.cpp` for `cecho.cpp` and adjust the output filename accordingly.

---

## 4. Ubuntu Linux Setup

```bash
sudo apt update
sudo apt install build-essential g++ gcc
sudo apt install mingw-w64
sudo apt install gcc-aarch64-linux-gnu g++-aarch64-linux-gnu
```

---

## 5. Ubuntu Build Commands

### Native x64

```bash
g++ cecho.cpp -O2 -s -o cecho-linux-x64
```

### ARM64 Linux

```bash
aarch64-linux-gnu-g++ cecho.cpp -O2 -s -o cecho-linux-arm64
```

### Windows x64

```bash
x86_64-w64-mingw32-g++ cecho.cpp -O2 -s -static -o cecho-win-x64.exe
```

### Windows ARM64 (if toolchain present)

```bash
aarch64-w64-mingw32-g++ cecho.cpp -O2 -s -static -o cecho-win-arm64.exe
```

---

## 6. cecho.cpp Reference Source

```cpp
// minimal cecho v1.3 (truncated header)
#include <windows.h>
#include <iostream>
#include <string>
#include <cctype>
#include <cstdlib>

static WORD g_defaultColor = 7;

WORD HexToColor(const std::string& hex) {
  return (WORD)strtol(hex.c_str(), nullptr, 16);
}

std::string ReadArgs(int argc, char* argv[]) {
  std::string input;
  for (int i = 1; i < argc; i++) {
    input += argv[i];
    if (i < argc - 1) input += " ";
  }
  return input;
}

void Process(const std::string& input, HANDLE hConsole) {
  for (size_t i = 0; i < input.size();) {
    if (input[i] == '{') {
      if (i + 2 < input.size() && input.substr(i, 3) == "{n}") {
        std::cout << "\r\n";
        i += 3;
        continue;
      }
      if (i + 3 < input.size() && input.substr(i, 4) == "{##}") {
        SetConsoleTextAttribute(hConsole, g_defaultColor);
        i += 4;
        continue;
      }
      if (i + 3 < input.size() && input[i + 3] == '}') {
        std::string code = input.substr(i + 1, 2);
        if (isxdigit(code[0]) && isxdigit(code[1])) {
          WORD color = HexToColor(code);
          SetConsoleTextAttribute(hConsole, color);
          i += 4;
          continue;
        }
      }
    }
    std::cout << input[i];
    i++;
  }
}

int main(int argc, char* argv[]) {
  HANDLE hConsole = GetStdHandle(STD_OUTPUT_HANDLE);
  CONSOLE_SCREEN_BUFFER_INFO csbi;
  GetConsoleScreenBufferInfo(hConsole, &csbi);
  g_defaultColor = csbi.wAttributes;
  std::string input = ReadArgs(argc, argv);
  if (input.empty()) return 0;
  Process(input, hConsole);
  SetConsoleTextAttribute(hConsole, g_defaultColor);
  return 0;
}
```

---

## 7. GitHub Actions CI Pipeline

Create `.github/workflows/build.yml`:

```yaml
name: build-cecho

on:
  push:
  pull_request:

jobs:
  build-windows:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup MSVC
        uses: ilammy/msvc-dev-cmd@v1

      - name: Build x64
        run: cl cecho.cpp /O2 /MT /EHsc /Fe:cecho-x64.exe

      - name: Build ARM64
        run: |
          call "%ProgramFiles(x86)%\\Microsoft Visual Studio\\2022\\BuildTools\\VC\\Auxiliary\\Build\\vcvarsall.bat" x64_arm64
          cl cecho.cpp /O2 /MT /EHsc /Fe:cecho-arm64.exe

      - uses: actions/upload-artifact@v4
        with:
          name: windows-builds
          path: |
            cecho-x64.exe
            cecho-arm64.exe

  build-linux:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install toolchains
        run: |
          sudo apt update
          sudo apt install -y build-essential mingw-w64 gcc-aarch64-linux-gnu g++-aarch64-linux-gnu

      - name: Build Linux x64
        run: g++ cecho.cpp -O2 -s -o cecho-linux-x64

      - name: Build Linux ARM64
        run: aarch64-linux-gnu-g++ cecho.cpp -O2 -s -o cecho-linux-arm64

      - name: Build Windows x64 (MinGW)
        run: x86_64-w64-mingw32-g++ cecho.cpp -O2 -s -static -o cecho-win-x64.exe

      - uses: actions/upload-artifact@v4
        with:
          name: linux-builds
          path: |
            cecho-linux-x64
            cecho-linux-arm64
            cecho-win-x64.exe
```

---

## 8. Test Examples

```cmd
cecho.exe "{0A}GREEN{n}{0F}WHITE{##}"
```

```cmd
cecho.exe "{01}BLUE{n}{02}GREEN{n}{04}RED{n}{0E}YELLOW{##}DONE"
```

---

## 9. Key Takeaways

- MSVC failures = environment not loaded — use the VS command prompt shortcut
- ARM64 requires extra components installed via `vs_installer.exe modify` (Step 0)
- MinGW = easiest cross-compile path
- Linux = best automation / CI platform

---

## 10. Full Build Script (x64 + ARM64, cecho + dartparse)

```cmd
@echo off
setlocal

set VSDEV="C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\Common7\Tools\VsDevCmd.bat"

echo ========================= Building cEcho + dartparse =========================

:: ------------------------- Build x64 -------------------------
echo.
echo [x64]

call %VSDEV% -arch=x64

echo Compiling resources...
rc.exe respe.rc
rc.exe cecho.rc

echo Building ResPE (C)...
cl.exe /O1 /MT /nologo respe.c respe.res user32.lib /link /SUBSYSTEM:CONSOLE /Fe:respe-x64.exe

echo Building cEcho (C++)...
cl.exe /O1 /MT /nologo cecho_v2.cpp cecho.res user32.lib /link /SUBSYSTEM:CONSOLE /Fe:cecho-x64.exe

rename cecho_v2.exe cecho-x64.exe
rename respe.exe respe-x64.exe

del *.obj *.res 2>nul

:: ------------------------- Build ARM64 -------------------------
echo.
echo [ARM64]

call %VSDEV% -arch=arm64 >nul

echo Compiling resources...
rc.exe respe.rc
rc.exe cecho.rc

echo Building ResPE (C)...
cl.exe /O1 /MT /nologo respe.c respe.res user32.lib /link /SUBSYSTEM:CONSOLE /Fe:respe-arm64.exe

echo Building cEcho (C++)...
cl.exe /O1 /MT /nologo cecho_v2.cpp cecho.res user32.lib /link /SUBSYSTEM:CONSOLE /Fe:cecho-arm64.exe

rename cecho_v2.exe cecho-arm64.exe
rename respe.exe respe-arm64.exe

del *.obj *.res

echo.
echo ========================= Build complete =========================
pause
```

---

## Colour Code Reference

| Code | Colour | Code | Colour |
|------|--------|------|--------|
| `{00}` | Black | `{08}` | Dark grey |
| `{01}` | Dark blue | `{09}` | Bright blue |
| `{02}` | Dark green | `{0A}` | Bright green |
| `{03}` | Dark cyan | `{0B}` | Bright cyan |
| `{04}` | Dark red | `{0C}` | Bright red |
| `{05}` | Dark purple | `{0D}` | Bright purple |
| `{06}` | Dark yellow | `{0E}` | Bright yellow |
| `{07}` | Light grey | `{0F}` | Bright white |

Special sequences: `{n}` = newline · `{##}` = reset to default colour

---

## Changelog

| Date | Change |
|------|--------|
| 2025-04-06 | Initial document |

---

*Example Music Limited — Internal Infrastructure Documentation*  
*Do not distribute outside the organisation*  
*Credentials: See password manager — never store passwords in this document*
