# Example Music Limited — Enabling Intel vPro AMT on a 7th-Gen NUC

> **Classification:** Internal — Infrastructure  
> **Forest:** `jukebox.internal`  
> **Domains:** `example.net` · `example.org` · `example.com`  
> **Provisioning network:** `192.168.139.0/24`  
> **Credentials:** See password manager — do **not** store passwords in this document  

**Reference:** https://www.virten.net/2018/05/7th-gen-nuc-remote-management-with-kvm-using-vpro-amt/  
**Scope:** Example Music Limited — Infrastructure  
**Applies to:** `EXAPVEFRD001` (FRD's site-kit NUC, small Intel NUC running Proxmox VE) — or any other 7th-gen Intel NUC in the estate with an i5/i7 CPU

---

## Overview

Intel vPro AMT (Active Management Technology) is BMC-like out-of-band remote management — power control, remote KVM, boot-media redirection — built into the chipset of certain Intel CPUs, but disabled/unconfigured by default. FRD's site kit has no dedicated BMC (`EXARAC`/`EXABMC`) — this is the closest equivalent it can get, if the NUC's CPU actually supports it.

**Not yet exercised — this is a planned procedure, not a confirmed-working one.** `EXAPVEFRD001`'s exact model is TBD in `devices.csv` — verify AMT support before starting (see Prerequisites).

---

## Prerequisites

| Requirement | Detail |
|---|---|
| Supported model | Only i5/i7 7th-gen NUCs support vPro AMT — `NUC7i7DNHE`, `NUC7i7DNKE`, `NUC7i5DNHE`, `NUC7i5DNKE`. i3 models (e.g. `NUC7i3DNHE`) do **not** have this feature at all. Confirm `EXAPVEFRD001`'s exact model before starting — `devices.csv` currently has this as "Vendor/model TBD" |
| Physical/local access | The initial MEBx setup requires a keyboard and display attached directly to the NUC — this cannot be done remotely on first configuration |
| Network reachability | AMT gets its own IP (DHCP by default, same NIC as the host OS but a separate out-of-band stack) — needs to be reachable from wherever it will be managed from |
| Intel AMT SDK | For KVM specifically (not just power control/serial-over-LAN) — see `bootstrap/amt-sdk/` (§5 below) |

---

## 1. Enter the MEBx BIOS

Power on the NUC. At the splash screen, press **Ctrl+P** to enter the Intel Management Engine BIOS Extension (MEBx) — this is separate from the normal F2 BIOS setup.

---

## 2. Set the MEBx password

Default credential is username `admin`, password `admin`. On first login you are forced to set a new password meeting all of:

- Minimum 8 characters
- At least one digit
- At least one lowercase letter
- At least one uppercase letter
- At least one non-alphanumeric character (colons, commas, and quotes are **not** accepted as the special character)

Store the new password in the password manager immediately — per the classification header above, it never goes in this document or any commit.

---

## 3. Configure AMT networking

Navigate: **Intel AMT Configuration → Network Setup → TCP/IP Settings**.

DHCP is the default and is fine for initial testing. For a static IP matching FRD's own addressing convention (`172.16.124.0/24`), assign a free octet here — note this is a **second** IP on the same physical NIC, out-of-band from whatever `EXAPVEFRD001`'s host OS/Proxmox IP is, and needs its own `devices.csv` row if it's made permanent (not yet added — do this once a real IP is assigned and confirmed reachable).

Enable AMT, exit MEBx, save and reboot.

---

## 4. Verify the web interface

From another machine on the same network:

```
http://<amt-ip>:16992/
```

Log in with the AMT credentials set in step 2. This confirms basic out-of-band reachability (power state, event log) before attempting KVM.

---

## 5. Set up remote KVM (optional, needs the SDK)

Basic AMT (power control, serial-over-LAN) works without any extra tooling — this step is only needed for full remote-desktop-style KVM.

1. Download the Intel AMT SDK — `bootstrap/amt-sdk/amt-sdk-21-0-0-1.zip` (git-lfs tracked, see `docs/hardware/README.md`)
2. Install a VNC client that supports Intel's RFB extensions (RealVNC is what the reference article uses)
3. Run `KVMControlApplication.exe` from the SDK's `Windows\Intel_AMT\Bin\KVM\` directory
4. Enter the NUC's hostname/IP and the AMT credentials from step 2, open **Machine Settings**
5. Set KVM status to **Enabled – all ports**, configure an RFB password (exactly 8 characters, same complexity rules as step 2)

### Known caveat — black screen when headless

If no display is physically connected to the NUC, remote KVM shows a black screen — Intel's early vPro generations needed a real display attached to have anything to redirect. Newer BIOS versions add a display-emulation/headless option to work around this; check whether `EXAPVEFRD001`'s BIOS has it before assuming a dummy HDMI plug is needed.

---

## Troubleshooting

### Ctrl+P does nothing at the splash screen

Confirm the model actually supports vPro AMT (see Prerequisites) — i3 NUCs show no MEBx option at all, this is not a misconfiguration.

### AMT web interface unreachable on port 16992

AMT has its own network stack independent of the host OS — check it actually picked up an IP (MEBx → Intel AMT Configuration → Network Setup) rather than troubleshooting the Proxmox host's own networking.

### KVM shows a black screen

See the headless caveat in step 5 above.

---

## Reference

| File | Purpose |
|---|---|
| `bootstrap/amt-sdk/amt-sdk-21-0-0-1.zip` | Intel AMT SDK — KVM control application, git-lfs tracked |
| `benarbejde/devices.csv` | `EXAPVEFRD001`'s row — update model/vendor once confirmed, and add the AMT IP as a note once assigned |
| https://www.virten.net/2018/05/7th-gen-nuc-remote-management-with-kvm-using-vpro-amt/ | Source procedure this document is based on |

---

## Changelog

| Date | Change |
|------|--------|
| 2026-07-30 | Initial document — planned procedure for `EXAPVEFRD001`, not yet exercised against real hardware |
