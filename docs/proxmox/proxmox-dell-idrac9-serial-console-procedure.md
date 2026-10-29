# Proxmox VE Serial Console and Dell iDRAC9 SOL
## Configuration procedure — `EXAPVEFAL001`

**Document status:** Configuration and SOL login tested; post-reboot kernel-console verification still required  
**Last evidence captured:** 28 October 2026  
**Host:** Dell PowerEdge T140  
**Proxmox node:** `EXAPVEFAL001`  
**Proxmox management URL:** `https://192.168.76.5:8006/`  
**iDRAC address:** `192.168.76.2`

---

## 1. Purpose

Configure the Proxmox VE host so that:

- Linux console output is directed to the local VGA console (`tty0`) and the first hardware serial port (`ttyS0`).
- A login prompt is available through the serial getty on `ttyS0`.
- The second hardware serial port (`ttyS1`) also has a serial getty available if it is needed for a separate physical serial connection.
- Dell iDRAC9 Serial Over LAN (SOL) can connect to the host and provide a remote serial login.

**Important distinction:** enabling a serial getty provides a login prompt on a serial device. Kernel output during boot is controlled separately by the kernel `console=` parameters. The GRUB configuration has been updated, but the captured `/proc/cmdline` still reflects the currently running kernel before a reboot. The dual-console kernel arguments therefore remain pending reboot verification.

## 2. Host details captured

The PuTTY session reported:

| Property | Observed value |
|---|---|
| Hostname | `EXAPVEFAL001` |
| Manufacturer / model | Dell Inc. PowerEdge T140 |
| OS | Debian GNU/Linux 13 (trixie) |
| Proxmox VE | `proxmox-ve 9.2.0` |
| Proxmox manager | `pve-manager 9.2.2` |
| Running kernel at capture | `7.0.2-6-pve` |
| Firmware boot mode | UEFI |
| UEFI boot entry | `proxmox`, `\EFI\proxmox\shimx64.efi` |
| Proxmox management IP | `192.168.76.5` |
| iDRAC IP | `192.168.76.2` |

The session also showed that `/etc/kernel/cmdline` does not exist and `proxmox-boot-tool status` reports:

```text
E: /etc/kernel/proxmox-boot-uuids does not exist.
```

The machine is using GRUB configuration at `/etc/default/grub`, and `update-grub` successfully generated `/boot/grub/grub.cfg`. Do not switch this host to a `proxmox-boot-tool` configuration as part of this procedure.

## 3. Serial port mapping

The host's kernel detected these conventional PC UARTs:

```text
[    0.520177] 00:00: ttyS1 at I/O 0x2f8 (irq = 3, base_baud = 115200) is a 16550A
[    0.542699] 00:01: ttyS0 at I/O 0x3f8 (irq = 4, base_baud = 115200) is a 16550A
```

For this host:

- `ttyS0` is the first serial port, conventional COM1 (`0x3f8`).
- `ttyS1` is the second serial port, conventional COM2 (`0x2f8`).
- `tty0` is the active local virtual terminal console.

A separate `ttyS4` MMIO UART also appeared in `dmesg`; it is not the conventional COM1/COM2 pair used in this procedure.

## 4. Dell iDRAC web interface settings

The following settings were the GUI changes specified during setup. Menu wording can vary slightly by iDRAC9 firmware version.

### 4.1 Enable IPMI over LAN

In the iDRAC web interface:

1. Sign in to `https://192.168.76.2/`.
2. Navigate to **iDRAC Settings → Connectivity → Network → IPMI Settings**.
3. Enable **IPMI Over LAN**.
4. Set **Channel Privilege Limit** to **Administrator**.
5. Apply/save the changes.

Keep the iDRAC credentials secure. Do not place passwords or the IPMI encryption key in this document or in command history.

### 4.2 Enable Serial Over LAN

Navigate to **iDRAC Settings → Connectivity → Serial Over LAN**:

1. Enable SOL.
2. Set the SOL baud rate to **115200**.
3. Apply/save the changes.

### 4.3 Configure BIOS serial communication and redirection

Navigate to **BIOS Settings → Serial Communication**. The exact labels can vary with BIOS version. On the Dell PowerEdge T140, configure the serial device mapping for iDRAC SOL as follows:

| Setting | Required value |
|---|---|
| Serial Communication | **On with Console Redirection using COM1** (or the equivalent enabled option) |
| Serial Port Address | **Serial Device 2 = COM1** |
| External Serial Connector | **Serial Device 2** |
| Failsafe Baud Rate | **115200** |
| Remote Terminal Type | **VT100/VT220** |
| Redirection After Boot | **Disabled** |

**Correction to the earlier settings:** do not use **Serial Device 1** for the external serial connector on this T140 SOL setup. The earlier procedure specified Serial Device 1 and Redirection After Boot Enabled; those values are superseded by the table above. The intended mapping is **Serial Device 2 → COM1**. Keeping Redirection After Boot disabled avoids firmware redirection competing with the boot loader/operating system after the BIOS stage.

Save/apply the BIOS settings. If iDRAC schedules a configuration job, check its status and reboot when the firmware requests it. Make sure the job has completed before judging the result.

**What these settings do:** SOL transports serial data over the iDRAC network interface. BIOS serial redirection controls pre-OS firmware output; GRUB and Linux have their own serial-console settings. Seeing GRUB over SOL does not prove that BIOS/POST redirection is configured correctly.

## 5. Configure Linux serial login services

The session enabled both serial getty units:

```bash
systemctl enable serial-getty@ttyS0.service
systemctl enable serial-getty@ttyS1.service
```

`enable` configures the units to start at boot. The first attempt left `ttyS0` inactive, so it was explicitly started as well:

```bash
systemctl enable --now serial-getty@ttyS0.service
systemctl enable --now serial-getty@ttyS1.service
```

Check both services:

```bash
systemctl status serial-getty@ttyS0.service --no-pager
systemctl status serial-getty@ttyS1.service --no-pager
```

Expected status includes `Loaded: ... enabled` and `Active: active (running)` for each unit. The recorded session showed both units active; `ttyS0` was later shown with a root login session.

### Root login and `/etc/securetty`

The captured checks showed:

```text
/etc/securetty does not exist
```

No `/etc/securetty` file was created. A successful root login was subsequently completed through the SOL session, so no additional `securetty` change was required for the tested login path.

Do not create `/etc/securetty` merely because it is absent. PAM configuration determines whether `pam_securetty` is being used; the session's grep produced no matching lines in `/etc/pam.d/login` or `/etc/pam.d/common-auth`.

## 6. Configure GRUB for local and serial kernel console output

### 6.1 Back up the existing configuration

The session created a timestamped backup before changing GRUB:

```bash
cp -a /etc/default/grub /etc/default/grub.bak.$(date +%F-%H%M%S)
```

To list backups:

```bash
ls -l /etc/default/grub.bak.*
```

### 6.2 Set the kernel console arguments

The current configured line is:

```bash
GRUB_CMDLINE_LINUX_DEFAULT="console=tty0 console=ttyS0,115200n8"
```

The session changed it with:

```bash
sed -i 's/^GRUB_CMDLINE_LINUX_DEFAULT=.*/GRUB_CMDLINE_LINUX_DEFAULT="console=tty0 console=ttyS0,115200n8"/' /etc/default/grub
```

The other line remained:

```bash
GRUB_CMDLINE_LINUX=""
```

### 6.3 Set the GRUB menu timeout to 30 seconds

Set GRUB to display its menu and wait **30 seconds** before automatically booting the default entry. This provides time to select an alternate kernel or the UEFI firmware setup during a remote-console session.

Edit `/etc/default/grub` and ensure these settings are present exactly once:

```bash
GRUB_TIMEOUT_STYLE=menu
GRUB_TIMEOUT=30
```

For an interactive edit:

```bash
nano /etc/default/grub
```

If either setting already exists, change its value rather than adding a duplicate. If it is absent, add it as a new line. Keep the existing `GRUB_CMDLINE_LINUX_DEFAULT` and `GRUB_CMDLINE_LINUX` settings described above.

Verify the relevant settings:

```bash
grep -nE '^(GRUB_TIMEOUT_STYLE|GRUB_TIMEOUT|GRUB_CMDLINE_LINUX(_DEFAULT)?)=' /etc/default/grub
```

Expected key values include:

```text
GRUB_TIMEOUT_STYLE=menu
GRUB_TIMEOUT=30
GRUB_CMDLINE_LINUX_DEFAULT="console=tty0 console=ttyS0,115200n8"
GRUB_CMDLINE_LINUX=""
```

`GRUB_TIMEOUT=30` controls the menu wait in seconds; `GRUB_TIMEOUT_STYLE=menu` ensures the menu is shown during that interval. The timeout does not guarantee BIOS/POST output over SOL; that is controlled separately by the Dell firmware serial-redirection settings.

The intended kernel arguments are:

- `console=tty0` — send kernel console output to the local virtual terminal.
- `console=ttyS0,115200n8` — send kernel console output to the first serial port at 115200 baud, 8 data bits, no parity.

Linux sends kernel console output to the specified consoles. The ordering can affect which console is treated as `/dev/console`; this configuration places `ttyS0` last. If your design requires the local console to be the primary `/dev/console`, review the desired ordering before changing it. Do not change the ordering without testing the result.

### 6.4 Regenerate GRUB configuration

The session ran:

```bash
update-grub
```

Recorded output:

```text
Generating grub configuration file ...
Found linux image: /boot/vmlinuz-7.0.2-6-pve
Found initrd image: /boot/initrd.img-7.0.2-6-pve
Found memtest86+ 64bit EFI image: /boot/memtest86+x64.efi
Found memtest86+ 64bit image: /boot/memtest86+x64.bin
Adding boot menu entry for UEFI Firmware Settings ...
done
```

Then verify the saved configuration:

```bash
grep -nE '^(GRUB_TIMEOUT_STYLE|GRUB_TIMEOUT|GRUB_CMDLINE_LINUX(_DEFAULT)?)=' /etc/default/grub
grep -nE 'set timeout=|set timeout_style=' /boot/grub/grub.cfg | head -5
grep -nE '^[[:space:]]*linux[[:space:]]+/.*vmlinuz' /boot/grub/grub.cfg | head -5
```

The captured output confirmed the generated GRUB entries included:

```text
linux /boot/vmlinuz-7.0.2-6-pve root=/dev/mapper/pve-root ro console=tty0 console=ttyS0,115200n8
```

### 6.5 Reboot and verify the running kernel

**A reboot is still required to verify the new kernel arguments.** The captured `/proc/cmdline` was:

```text
BOOT_IMAGE=/boot/vmlinuz-7.0.2-6-pve root=/dev/mapper/pve-root ro quiet
```

and `/sys/class/tty/console/active` showed:

```text
tty0
```

Those values were captured after regenerating GRUB but before a reboot into the updated configuration. They are not proof that the new arguments have taken effect.

Before rebooting, ensure you have working access to the Proxmox host through SSH or the local console, and retain iDRAC access. Schedule the reboot during an appropriate maintenance window.

After reboot, run:

```bash
echo '===== Running kernel arguments ====='
cat /proc/cmdline

echo '===== Active kernel consoles ====='
cat /sys/class/tty/console/active

echo '===== Serial console messages ====='
dmesg | grep -E 'console \[tty(S[01]|tty0)|console \[ttyS[01]\]|ttyS[01] at'

echo '===== Serial gettys ====='
systemctl --no-pager --full status serial-getty@ttyS0.service
systemctl --no-pager --full status serial-getty@ttyS1.service
```

The running command line should contain both `console=tty0` and `console=ttyS0,115200n8`. Record the actual output; do not treat it as verified until the post-reboot check has been run.

## 7. Check iDRAC SOL settings from the host

The host now has `ipmitool` installed. To inspect SOL configuration:

```bash
ipmitool -I lanplus -H 192.168.76.2 -U root sol info
```

The command prompts for the iDRAC password. Do not put the password directly on the command line.

Recorded successful output:

```text
Info: SOL parameter 'Payload Channel (7)' not supported - defaulting to 0x0e
Set in progress                 : set-complete
Enabled                         : true
Force Encryption                : true
Force Authentication            : false
Privilege Level                 : ADMINISTRATOR
Character Accumulate Level (ms) : 50
Character Send Threshold        : 255
Retry Count                     : 7
Retry Interval (ms)             : 480
Volatile Bit Rate (kbps)        : 115.2
Non-Volatile Bit Rate (kbps)    : 115.2
Payload Channel                 : 14 (0x0e)
Payload Port                    : 623
```

The `Payload Channel (7) not supported` message was followed by a successful SOL configuration report and is not, by itself, a failure in this recorded session.

## 8. Connect to the console through SOL

From a system with `ipmitool` installed and network access to the iDRAC:

```bash
ipmitool -I lanplus -H 192.168.76.2 -U root sol activate
```

Enter the iDRAC password when prompted.

The session successfully reached:

```text
[SOL Session operational.  Use ~? for help]

Welcome to the Proxmox Virtual Environment. Please use your web browser to
configure this server - connect to:

  https://192.168.76.5:8006/

EXAPVEFAL001 login:
```

A root login was subsequently successful, and the shell identified the running kernel:

```text
Linux EXAPVEFAL001 7.0.2-6-pve #1 SMP PREEMPT_DYNAMIC PMX 7.0.2-6 (2026-05-20T08:55Z) x86_64
```

### SOL escape sequence

At the SOL prompt, `~?` displays escape-sequence help. To disconnect from SOL, use the `~.` escape sequence at the start of a new line (press Enter, then type `~.`). This closes the SOL client session; it does not shut down the server.

## 9. Troubleshooting

### SOL cannot establish an IPMI session

The session initially returned:

```text
Error: Unable to establish IPMI v2 / RMCP+ session
```

A later retry succeeded and returned the SOL settings. If this recurs:

1. Verify the iDRAC IP address and network reachability.
2. Verify **IPMI Over LAN** is enabled in the iDRAC web interface.
3. Verify the username, password, and channel privilege.
4. Confirm the iDRAC SOL settings and check whether iDRAC is busy or has an active SOL session.
5. Retry without exposing credentials in shell history.

### SOL connects but shows no Linux login prompt

Check the relevant getty:

```bash
systemctl enable --now serial-getty@ttyS0.service
systemctl status serial-getty@ttyS0.service --no-pager
```

Then confirm that BIOS **Serial Port Address** is set to **Serial Device 2 = COM1**, **External Serial Connector** is set to **Serial Device 2**, and the failsafe baud rate is **115200**.

### BIOS/POST output is missing, but GRUB is visible over SOL

GRUB output and BIOS/POST redirection are separate stages. If GRUB appears in SOL but BIOS setup/POST messages do not, check the T140 BIOS settings before changing Proxmox:

1. Open **iDRAC → Configuration → BIOS Settings → Serial Communication**.
2. Set **Serial Communication** to **On with Console Redirection using COM1** (or the equivalent enabled option).
3. Set **Serial Port Address** to **Serial Device 2 = COM1**.
4. Set **External Serial Connector** to **Serial Device 2**.
5. Set **Failsafe Baud Rate** to **115200** and **Remote Terminal Type** to **VT100/VT220**.
6. Set **Redirection After Boot** to **Disabled**.
7. Apply the settings, confirm any BIOS configuration job completes, then reboot and observe SOL from power-on.

Do not change the working GRUB/Linux serial configuration just to fix missing BIOS output. If BIOS output still does not appear, compare against the iDRAC **Virtual Console**: whether the Dell logo/POST appears there helps distinguish a BIOS redirection issue from a SOL-specific issue.

### Login prompt works, but boot output is missing

A getty and a kernel console are separate settings. Verify the GRUB line and generated configuration, reboot, then inspect `/proc/cmdline` and `/sys/class/tty/console/active` as described in Section 6. Do not infer that boot output is configured correctly solely because the post-boot login prompt works.

### `proxmox-boot-tool status` reports a missing UUID file

The recorded host is booted through UEFI and uses GRUB entries under `/boot/grub/grub.cfg`; the command returned:

```text
E: /etc/kernel/proxmox-boot-uuids does not exist.
```

`update-grub` succeeded and generated entries for the installed kernel. Do not try to repair the missing UUID file as part of the serial-console procedure without separately establishing that this host is intended to use `proxmox-boot-tool`.

## 10. Rollback

If the updated GRUB configuration causes a problem and you can still access the host, restore a known backup:

```bash
ls -lt /etc/default/grub.bak.*
cp -a /etc/default/grub.bak.YYYY-MM-DD-HHMMSS /etc/default/grub
update-grub
```

Replace the example backup filename with the exact file present on the host. Reboot only when you have confirmed the restored configuration and have a suitable maintenance window.

To stop a serial getty without deleting its configuration:

```bash
systemctl disable --now serial-getty@ttyS0.service
```

For `ttyS1`, use:

```bash
systemctl disable --now serial-getty@ttyS1.service
```

Disabling a getty removes the serial login prompt for that port; it does not undo the BIOS or iDRAC SOL settings.

## 11. Verification checklist

Mark each item complete only after observing it on the host.

- [x] iDRAC SOL is enabled according to `ipmitool sol info`.
- [x] SOL client connects and displays the Proxmox login prompt.
- [x] Root login through the tested SOL session succeeds.
- [x] `serial-getty@ttyS0.service` is enabled and was observed running.
- [x] `serial-getty@ttyS1.service` is enabled and was observed running.
- [x] `/etc/default/grub` contains `console=tty0 console=ttyS0,115200n8`.
- [ ] `/etc/default/grub` sets `GRUB_TIMEOUT_STYLE=menu` and `GRUB_TIMEOUT=30`.
- [ ] `update-grub` generated a visible GRUB menu with a 30-second timeout.
- [x] `update-grub` completed successfully and generated entries with both console arguments.
- [ ] Rebooted into the updated GRUB configuration.
- [ ] Confirmed `/proc/cmdline` after reboot contains both console arguments.
- [ ] Confirmed BIOS/POST redirection over SOL from power-on.
- [ ] Confirmed console output on both the local display and SOL during boot.
- [ ] Confirmed SOL login after reboot.

## 12. Security notes

- Treat iDRAC as a privileged out-of-band management plane. Restrict access to its management network.
- Use a strong iDRAC password and do not save passwords in this document, shell history, scripts, or screenshots.
- SOL can provide privileged console access. Keep it enabled only for the intended administration use.
- The recorded configuration reports `Force Encryption: true` and `Force Authentication: false`. Preserve the actual observed settings in records; evaluate any policy change separately rather than changing it casually during troubleshooting.
- The SSH host-key warning and changed host key seen earlier in the PuTTY session concerned SSH access to `192.168.76.5`, not SOL configuration. Verify SSH host-key changes through a trusted channel if they occur again.

---

## Source and evidence notes

This procedure was assembled from the supplied PuTTY session and the previously discussed iDRAC web-interface settings. It distinguishes completed actions and captured outputs from post-reboot checks that have not yet been demonstrated. Example outputs above are from the session and may differ after a kernel or firmware update.
