# Arch Linux PXE Boot Setup
## Example Music Limited -- Infrastructure Provisioning

---

## File Layout on Provisioning Server (192.168.139.50)

```
/var/www/html/                          (or wherever your HTTP root is)
  arch/
    x86_64/
      vmlinuz-linux                     <- from Arch ISO: arch/boot/x86_64/vmlinuz-linux
      initramfs-linux.img               <- from Arch ISO: arch/boot/x86_64/initramfs-linux.img
      airootfs.sfs                      <- from Arch ISO: arch/x86_64/airootfs.sfs
      airootfs.sfs.sha512               <- from Arch ISO: arch/x86_64/airootfs.sfs.sha512
    aarch64/
      vmlinuz-linux                     <- from Arch ISO (aarch64 build)
      initramfs-linux.img
      airootfs.sfs
      airootfs.sfs.sha512
    archinstall-config.json             <- the config file (this repo)
    arch-autoinstall.sh                 <- the bootstrap script (this repo)
  ansible_sshkey.pub                    <- Ansible public key (already present for Debian)
```

---

## How to Extract Files from the Arch ISO

Download the latest Arch ISO (or aarch64 ISO) and extract:

```bash
# Mount the ISO
mount -o loop archlinux-x86_64.iso /mnt/iso

# Copy the three files needed for PXE
cp /mnt/iso/arch/boot/x86_64/vmlinuz-linux   /var/www/html/arch/x86_64/
cp /mnt/iso/arch/boot/x86_64/initramfs-linux.img /var/www/html/arch/x86_64/
cp /mnt/iso/arch/x86_64/airootfs.sfs         /var/www/html/arch/x86_64/
cp /mnt/iso/arch/x86_64/airootfs.sfs.sha512  /var/www/html/arch/x86_64/

umount /mnt/iso
```

Repeat for aarch64 using the aarch64 ISO.

---

## How the Auto-Install Works

1. Machine PXE boots, iPXE loads `vmlinuz-linux` + `initramfs-linux.img`
2. Kernel parameter `archiso_http_srv=http://192.168.139.50/` tells the live env
   where to fetch `airootfs.sfs` from -- this becomes the root filesystem
3. `copytoram` loads the squashfs into RAM so the HTTP server is no longer needed
4. Kernel parameter `arch-autoinstall` is detected by the systemd service baked
   into the custom airootfs (see Custom Airootfs section below)
5. The service runs: `curl http://192.168.139.50/arch/arch-autoinstall.sh | bash`
6. The bootstrap script fetches `archinstall-config.json` and `archinstall-creds.json`
7. archinstall runs, prompting for hostname, ansible password, and root password
8. `post_install` script runs inside the new system -- sets up ansible user,
   SSH keys, sudoers, hardens sshd (PermitRootLogin no, PasswordAuthentication no)
9. Machine reboots into the installed system

---

## Custom Airootfs Overlay (Required for Auto-Install)

The `:arch-auto` and `:arch-auto-serial` entries require a custom airootfs with
the autoinstall systemd service baked in. Without this the `arch-autoinstall`
kernel parameter does nothing.

Build the custom airootfs once and host it alongside the standard files.

### Build Steps

```bash
# Install archiso on an Arch machine
pacman -S archiso

# Copy the baseline profile
cp -r /usr/share/archiso/configs/releng /tmp/archiso-examplemusic
cd /tmp/archiso-examplemusic

# Create the systemd service overlay
mkdir -p airootfs/etc/systemd/system/multi-user.target.wants

cat > airootfs/etc/systemd/system/arch-autoinstall.service << 'SERVICE'
[Unit]
Description=Example Music Arch Linux Auto-Install
After=network-online.target
Wants=network-online.target
ConditionKernelCommandLine=arch-autoinstall

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/bin/bash -c 'curl -fsSL http://192.168.139.50/arch/arch-autoinstall.sh | bash'
StandardOutput=journal+console
StandardError=journal+console
TTYPath=/dev/tty1

[Install]
WantedBy=multi-user.target
SERVICE

# Symlink to enable it
ln -sf /etc/systemd/system/arch-autoinstall.service \
       airootfs/etc/systemd/system/multi-user.target.wants/arch-autoinstall.service

# Also set a root password for the live env SSH console entries
# (this is the LIVE env password, not the installed system)
# Generate hash: openssl passwd -6 'install'
echo 'root:$6$yourhashhere' > airootfs/etc/shadow

# Build the ISO (takes a few minutes)
mkarchiso -v -o /tmp/archiso-output /tmp/archiso-examplemusic

# Extract the new airootfs.sfs from the built ISO
mount -o loop /tmp/archiso-output/archlinux-*.iso /mnt/iso
cp /mnt/iso/arch/x86_64/airootfs.sfs      /var/www/html/arch/x86_64/
cp /mnt/iso/arch/x86_64/airootfs.sfs.sha512 /var/www/html/arch/x86_64/
cp /mnt/iso/arch/boot/x86_64/vmlinuz-linux /var/www/html/arch/x86_64/
cp /mnt/iso/arch/boot/x86_64/initramfs-linux.img /var/www/html/arch/x86_64/
umount /mnt/iso
```

> The vmlinuz and initramfs from your custom build may differ from the upstream
> ones -- always copy them from the same build as airootfs.sfs or you risk
> version mismatches.

---

## SSH Console Install (no custom airootfs needed)

The `:arch-ssh` and `:arch-ssh-serial` entries boot the standard upstream
airootfs. SSH is enabled by default in the Arch live environment.

Connect after boot:
```bash
ssh root@<machine-ip>
# Password: (set in airootfs -- 'install' in the upstream archiso)
```

Then run the installer manually or trigger the bootstrap:
```bash
curl -fsSL http://192.168.139.50/arch/arch-autoinstall.sh | bash
```

---

## iPXE Menu Integration

Add the entries from `arch-ipxe-entries.ipxe` to your existing iPXE menu script.
The `${arch}` variable should already be set in your menu (x86_64 or aarch64).

If `${arch}` isn't already set, add this near the top of your iPXE script:
```
cpuid --ext 29 && set arch x86_64 || set arch aarch64
```

---

## Security Notes

- `PermitRootLogin no` is set in the **installed system** by `post_install`
- The **live environment** still has root SSH enabled -- this is intentional
  for the SSH console install entries and is unavoidable with the upstream archiso
- Passwords are prompted interactively and never written to disk or the provisioning server
- Restrict HTTP access to the provisioning VLAN to prevent config.json being fetched externally
