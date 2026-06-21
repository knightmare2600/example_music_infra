# Using TFTPD64 to Provide DHCP, DNS, TFTP (PXE) and Auto-Launch a Debian Rescue Console via SSH

This guide explains how to use TFTPD64 on Windows to:

-   Provide DHCP
-   Provide DNS
-   Serve TFTP / PXE boot files
-   Automatically boot a Debian rescue environment
-   Automatically start an SSH server with no local input required
-   Use ipmitool inside the rescue environment

Designed for completely headless servers with: - No monitor - No serial console - No keyboard - Network-only access

------------------------------------------------------------------------

# 1. Network Example

  Component            IP Address
-------------------- ----------------
  Windows PXE Server   192.168.1.10
  Headless Target      DHCP
  Network              192.168.1.0/24

------------------------------------------------------------------------

# 2. Configure TFTPD64

Run TFTPD64 as Administrator.

## TFTP Tab

Base Directory: C:`\TFTP`{=tex}-Root

Enable: - TFTP Server

Place all boot files in C:`\TFTP`{=tex}-Root

------------------------------------------------------------------------

## DHCP Server Tab

Enable DHCP Server.

Example configuration:

IP pool starting address: 192.168.1.100\
Size of pool: 50\
Boot file (BIOS): pxelinux.0\
Boot file (UEFI): ipxe.efi\
Default router: 192.168.1.1\
DNS Server: 192.168.1.10\
Mask: 255.255.255.0

------------------------------------------------------------------------

## DNS Server Tab

Enable DNS Server.

Optional: Add static A records if required.

------------------------------------------------------------------------

# 3. Debian Netboot Files

Download from:

https://deb.debian.org/debian/dists/stable/main/installer-amd64/current/images/netboot/

Extract:

debian-installer/linux\
debian-installer/initrd.gz

Copy both to:

C:`\TFTP`{=tex}-Root

------------------------------------------------------------------------

# 4. Auto-Start SSH With No Interaction

We boot the installer in network-console mode so SSH starts
automatically.

Create:

`C:`\TFTP`{=tex}-Root`\pxelinux`{=tex}.cfg`\default`{=tex}`

Content:

```
DEFAULT rescue PROMPT 0 TIMEOUT 0

LABEL rescue KERNEL linux INITRD initrd.gz APPEND auto=true
priority=critical\
anna/choose_modules=network-console\
network-console/password=RescuePass\
network-console/password-again=RescuePass\
netcfg/disable_dhcp=false\
netcfg/get_hostname=debian-rescue\
netcfg/get_domain=local\
console=tty0
```

After boot:

`ssh installer@192.168.1.xxx`

`Password: RescuePass`

------------------------------------------------------------------------

# 5. Using ipmitool Inside the Rescue Environment

After connecting via SSH, first check if ipmitool exists:

which ipmitool\
ipmitool -V

If not installed, verify networking:

ip a\
ping 8.8.8.8

Then update and install:

apt-get update\
apt-get install ipmitool

If kernel modules are required:

modprobe ipmi_si\
modprobe ipmi_devintf

Verify modules:

lsmod \| grep ipmi

Common commands:

ipmitool -I open mc info\
ipmitool -I open lan print\
ipmitool -I open chassis power cycle\
ipmitool -I open mc reset cold

------------------------------------------------------------------------

# 6. If apt Is Not Available

Mount required filesystems:

mount -t proc proc /proc\
mount -t sysfs sysfs /sys\
mount -t devtmpfs devtmpfs /dev

Then retry:

apt-get update

------------------------------------------------------------------------

# 7. Alternative: Inject ipmitool Into initrd

Unpack:

mkdir work\
cd work\
gzip -dc ../initrd.gz \| cpio -id

Copy binary:

cp /usr/bin/ipmitool ./usr/bin/

Repack:

find . \| cpio -H newc -o \| gzip -9 \> ../initrd-custom.gz

Then use:

INITRD initrd-custom.gz

------------------------------------------------------------------------

# 8. Alternative: Run ipmitool Remotely

From another machine:

ipmitool -I lanplus -H 192.168.1.50 -U ADMIN -P password chassis power
status

------------------------------------------------------------------------

# 9. Windows Firewall Ports

Allow:

UDP 67 (DHCP)\
UDP 69 (TFTP)\
UDP/TCP 53 (DNS)

------------------------------------------------------------------------

# 10. Security Warning

This configuration exposes DHCP, DNS and SSH.\
Use only on isolated lab networks or trusted VLANs.\
Do not expose to public networks.

------------------------------------------------------------------------

# 11. Summary

This setup allows a completely headless machine to:

-   PXE boot
-   Obtain DHCP automatically
-   Launch Debian rescue
-   Start SSH automatically
-   Install and use ipmitool
-   Be fully controlled remotely

No monitor.\
No serial.\
No keyboard.\
Network only.
