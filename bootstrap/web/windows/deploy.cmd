@ECHO OFF
CLS

ECHO Injecting drivers into running WinPE
pnputil /add-driver X:\Tools\Drivers\*.inf /subdirs /install

ECHO Setting constant variables
set "SERVER=192.168.139.50"
set "BASE=http://%SERVER%/windows"
set "SCRIPTS=C:\Windows\Setup\Scripts"

ECHO Downloading windows Unattended XML file
certutil.exe -urlcache -f "%BASE%/unattend/headlessunattend.xml" X:\headlessunattend.xml

ECHO "Swap the CD for a windows Install CD and"
pause
Y:\Sources\setup.exe /unattend:X:\headlessunattend.xml /noreboot

ECHO Adding post install Panther files
MKDIR "%SCRIPTS%"
dism /Image:C:\ /Add-Driver /Driver:X:\Tools\Drivers /Recurse

certutil.exe -urlcache -f "%BASE%/SetupComplete.cmd" "%SCRIPTS%\SetupComplete.cmd"
certutil.exe -urlcache -f "%BASE%/Detect-Platform.cmd" "%SCRIPTS%\Detect-Platform.cmd"
certutil.exe -urlcache -f "%BASE%/SetupComplete.cmd" "%SCRIPTS%\SetupComplete.cmd"
certutil.exe -urlcache -f "%BASE%/Install-OpenSSH.ps1" "%SCRIPTS%\Install-OpenSSH.ps1"

ECHO Setting up Scratch Directory C:\ProgramData\ExampleMusic
mkdir C:\ProgramData\ExampleMusic
C:\ProgramData\ExampleMusic\Drivers
C:\ProgramData\ExampleMusic\Logs
certutil.exe -urlcache -f "%BASE%/x86_64/qemu-ga-x86_64.si" C:\ProgramData\ExampleMusic\Drivers\qemu-ga-x86_64.msi
certutil.exe -urlcache -f "%BASE%/x86_64/virtio-win-gt-x64.msi C:\ProgramData\ExampleMusic\Drivers\virtio-win-gt-x64.msi

