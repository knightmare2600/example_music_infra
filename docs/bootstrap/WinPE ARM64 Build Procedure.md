# WinPE ARM64 Build Procedure

## Prerequisites

- Windows 11 ARM64 VM running in VMware Fusion on M4
- [Windows ADK for Windows 11](https://learn.microsoft.com/en-us/windows-hardware/get-started/adk-install)
- [Windows PE add-on for the ADK](https://learn.microsoft.com/en-us/windows-hardware/get-started/adk-install)
- During ADK install, tick **Deployment Tools** only — nothing else needed
- Install the WinPE add-on immediately after the ADK
- All steps run in **Deployment and Imaging Tools Environment** (run as Administrator) `Start Menu → Windows Kits → Deployment and Imaging Tools Environment`

------

## Step 1 — Scaffold the ARM64 Working Directory

```cmd
copype arm64 C:\WinPE_ARM64
```

This creates the full directory structure and drops in the base ARM64 boot.wim.

------

## Step 2 — Mount the WIM

```cmd
Dism /Mount-Image /ImageFile:"C:\WinPE_ARM64\media\sources\boot.wim" /Index:1 /MountDir:"C:\WinPE_ARM64\mount"
```

------

## Step 3 — Add Core Components

All packages live under the WinPE_OCs folder. Add them in this order as some depend on the previous ones:

```cmd
Dism /Add-Package /Image:"C:\WinPE_ARM64\mount" /PackagePath:"C:\Program Files (x86)\Windows Kits\10\Assessment and Deployment Kit\Windows Preinstallation Environment\arm64\WinPE_OCs\WinPE-WMI.cab"

Dism /Add-Package /Image:"C:\WinPE_ARM64\mount" /PackagePath:"C:\Program Files (x86)\Windows Kits\10\Assessment and Deployment Kit\Windows Preinstallation Environment\arm64\WinPE_OCs\WinPE-NetFX.cab"

Dism /Add-Package /Image:"C:\WinPE_ARM64\mount" /PackagePath:"C:\Program Files (x86)\Windows Kits\10\Assessment and Deployment Kit\Windows Preinstallation Environment\arm64\WinPE_OCs\WinPE-Scripting.cab"

Dism /Add-Package /Image:"C:\WinPE_ARM64\mount" /PackagePath:"C:\Program Files (x86)\Windows Kits\10\Assessment and Deployment Kit\Windows Preinstallation Environment\arm64\WinPE_OCs\WinPE-PowerShell.cab"

Dism /Add-Package /Image:"C:\WinPE_ARM64\mount" /PackagePath:"C:\Program Files (x86)\Windows Kits\10\Assessment and Deployment Kit\Windows Preinstallation Environment\arm64\WinPE_OCs\WinPE-StorageWMI.cab"

Dism /Add-Package /Image:"C:\WinPE_ARM64\mount" /PackagePath:"C:\Program Files (x86)\Windows Kits\10\Assessment and Deployment Kit\Windows Preinstallation Environment\arm64\WinPE_OCs\WinPE-DismCmdlets.cab"
```

------

## Step 4 — Inject NIC Drivers (VMware Fusion)

Extract ARM64 drivers from the VMware Tools ISO and inject them. This prevents the networking stack from coming up blind in the VM:

```cmd
Dism /Add-Driver /Image:"C:\WinPE_ARM64\mount" /Driver:"C:\Path\To\VMwareToolsDrivers\ARM64" /Recurse
```

> If you don't have the VMware Tools ARM64 drivers extracted yet, mount the VMware Tools ISO from Fusion's menu and copy the driver folders out first.

------

## Step 5 — Add Notepad

Copy from the running Windows 11 ARM system. Notepad on modern Windows 11 is the classic win32 binary and carries over cleanly:

```cmd
copy C:\Windows\System32\notepad.exe "C:\WinPE_ARM64\mount\Windows\System32\notepad.exe"
```

> **calc.exe** — skip it. Modern Windows Calculator is a Store/UWP app and won't work in PE. Use PowerShell for any maths you need.

------

## Step 6 — Set Custom Wallpaper

Replace the default WinPE wallpaper with your own. Must be a JPG:

```cmd
copy C:\YourWallpaper.jpg "C:\WinPE_ARM64\mount\Windows\Web\Wallpaper\Windows\img0.jpg"
```

------

## Step 7 — Add RustDesk ARM64

Download the RustDesk ARM64 portable exe (no installer needed) and drop it into System32 so it's on the path without any faff:

```cmd
copy C:\Downloads\rustdesk-arm64.exe "C:\WinPE_ARM64\mount\Windows\System32\rustdesk.exe"
```

You will need either the RustDesk cloud relay or a self-hosted RustDesk server for connections to land. Self-hosted server is a single Linux binary and can live on the ansible node. See self-hosting docs at: https://rustdesk.com/docs/en/self-host/

------

## Step 8 — Add Any Other ARM64 Tools

Anything you want available in the PE shell without path faff goes into System32. Confirmed ARM64 native builds exist for:

```cmd
copy C:\Tools\ARM64\putty.exe      "C:\WinPE_ARM64\mount\Windows\System32\"
copy C:\Tools\ARM64\winscp.exe     "C:\WinPE_ARM64\mount\Windows\System32\"
copy C:\Tools\ARM64\7z.exe         "C:\WinPE_ARM64\mount\Windows\System32\"
```

------

## Step 9 — Write startnet.cmd

This runs automatically on boot after wpeinit initialises hardware. The ping is a deliberate delay to let wpeinit finish bringing networking up before the share map is attempted:

```cmd
notepad "C:\WinPE_ARM64\mount\Windows\System32\startnet.cmd"
```

Contents:

```cmd
@echo off
echo Initialising hardware...
wpeinit

echo Waiting for network...
ping -n 8 127.0.0.1 > nul

echo Starting RustDesk...
start rustdesk.exe --service

echo Mapping deployment share...
net use Z: \\192.168.76.15\windows /user:guest
if %errorlevel% neq 0 (
  echo WARNING: Share map failed - dropping to shell for manual recovery
  cmd.exe
  goto :eof
)

echo Share mapped. Launching setup...
if exist Z:\setup.exe (
  Z:\setup.exe
) else (
    echo setup.exe not found on share - dropping to shell
    cmd.exe
)
```

Adjust the share path and IP to match your environment. The RustDesk --service flag starts it in the background so the rest of startnet.cmd continues unblocked.

------

## Step 10 — Unmount and Commit

When you are happy with the image:

```cmd
Dism /Unmount-Image /MountDir:"C:\WinPE_ARM64\mount" /Commit
```

If something went wrong and you want to discard all changes:

```cmd
Dism /Unmount-Image /MountDir:"C:\WinPE_ARM64\mount" /Discard
```

------

## Step 11 — Build the ISO

For attaching directly to VMs as a virtual DVD:

```cmd
MakeWinPEMedia /ISO C:\WinPE_ARM64 C:\WinPE_ARM64.iso
```

The finished boot.wim (if you want just the WIM for HTTP/network boot) is at:

```
C:\WinPE_ARM64\media\sources\boot.wim
```

------

## Making Changes Later

You do not start over to make changes. Just remount and re-commit:

```cmd
Dism /Mount-Image /ImageFile:"C:\WinPE_ARM64\media\sources\boot.wim" /Index:1 /MountDir:"C:\WinPE_ARM64\mount"

rem ... make your changes ...

Dism /Unmount-Image /MountDir:"C:\WinPE_ARM64\mount" /Commit
```

------

## Notes

- Keep a backup copy of boot.wim before adding tools (Step 8 onwards) so you have a known-good base to roll back to if a tool causes issues
- Expected size of finished minimal image: ~400-600MB
- All tools must be native ARM64 binaries — WinPE has no x64 emulation layer
- If networking does not come up, VMware NIC driver injection (Step 4) is almost certainly the culprit
