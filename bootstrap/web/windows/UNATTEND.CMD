if "%1"=="noInstallTools" (
   if exist %TEMP%\storePwd.exe start /min %TEMP%\storePwd.exe -i
) else (
   @echo  Installing VMware Tools ...  Please wait a few seconds.
   @echo off

   if exist %TEMP%\storePwd.exe start /min %TEMP%\storePwd.exe -i

   powershell -ExecutionPolicy Bypass -Command "Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0"
   powershell -ExecutionPolicy Bypass -Command "Set-Service sshd -StartupType Automatic"
   powershell -ExecutionPolicy Bypass -Command "Start-Service sshd"
   powershell -ExecutionPolicy Bypass -Command "New-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -DisplayName 'OpenSSH Server' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22"


   :: delay 2 seconds before running upgrader to prevent some timing issue with
   :: mounting iso cd-rom device (because winnt/2k/2003 don't have 'sleep' command
   :: use old trick with 'ping')
   ping 1.1.1.1 -n 1 -w 2000 >nul

   if "%1"=="noautoreboot" (
      start /min %TEMP%\upgrader.exe -p "/s /v\"/qr REBOOT=FORCE\""
   ) else (
      start /min %TEMP%\upgrader.exe -p "/s /v\"/qr REBOOT=FORCE REBOOTPROMPT=S\""
   )
)
