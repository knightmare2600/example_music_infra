# Procedure: PVE Auto-Install via klargoring (PXE)

> **Document ref:** NET-PVE-KLARGORING-001
> **Classification:** Internal — Infrastructure
> **Status:** CONFIRMED WORKING — first successful real-hardware test 2026-08-20 (`EXAPVEVRK002`)
> **Reference:** [`klargoring`](https://github.com/knightmare2600/klargoring) (Robert's own live-installer distro), `:klargoring` in `bootstrap/web/menu.ipxe`, `bootstrap/web/proxmox/{VRK,FRD}-{answer,degraded}.toml`

---

## Why this document exists

This estate tried two other approaches to automated PVE installation before this one, and both have their own documented history worth knowing so nobody rediscovers the same dead ends:

1. **The official Proxmox ISO, delivered over PXE or BMC virtual media** (`docs/proxmox/pxe-proxmox-autoinstall-build-log.md`) — built and tested 2026-07-18, then **abandoned outright**. The real test boot gave a blank cursor; the mounted/loaded ISO was never picked up by the installer's init script the way the design assumed.
2. **`select-pve-answer.sh`** (same document, §9) — what replaced approach 1: mount a plain unmodified Proxmox ISO via BMC virtual media, boot to Proxmox's own native install shell, `wget` and run a script that detects site/disk-count and fetches the right answer TOML by hand. Built, but **never actually end-to-end tested** — that document says outright it isn't a finished procedure yet, only a log of how the team got there.

**`klargoring` is a third, different approach — a real PXE boot of Robert's own hand-rolled live installer distro**, entirely separate from both of the above. It was built and staged on the provisioning server (amd64 since before this document existed, arm64 added 2026-08-06) but had never been proven against real hardware until the run this document describes. As of 2026-08-20, it is the **first and only confirmed-working automated PVE install path in this estate** — this document supersedes the other two for any new PVE node build going forward, though their write-ups stay in place for historical reference.

---

## Prerequisites

| Requirement | Detail |
|---|---|
| BIOS storage/controller mode | **AHCI**, not a hardware RAID/RST mode. ZFS needs raw, unabstracted access to every disk it manages — a RAID-controller mode will hide bare disks from the installer entirely. Check this in BIOS/UEFI setup *before* attempting a PXE boot; there's no way to detect or recover from the wrong mode once klargoring is already running. |
| Disks visible at BIOS POST | Confirm the expected disk count shows up in the boot menu / disk list at the BIOS level, not just "assumed present" — see the Real Worked Example below for what this looked like on a genuinely correct board. |
| BMC access | Only needed if you plan to use virtual media or IPMI-based console access instead of a physical crash cart — klargoring itself boots over the network (DHCP + PXE), no BMC involvement required for the install itself. If the BMC's own credentials need resetting first, see `docs/INCIDENT-LOG.md`'s `INC-2026-04-03-BMC-CREDS` for the real, twice-confirmed procedure (crash cart + GParted Live + `ipmitool`, cross-checked with `fyrtaarn` + a second `ipmitool` check from a different machine before trusting the new credentials). |
| Correct site's answer TOML exists | `bootstrap/web/proxmox/<SITE>-answer.toml` (both disks present) or `<SITE>-degraded.toml` (single disk, see `docs/proxmox/zfs-raid0-to-raid1.md` for bringing it up to a real mirror later) — one pair per provisioning server, per `docs/bootstrap/bootstrapping.md` §5.1-5.3. |
| Node on the right network | klargoring's site detection is gateway-based, the same logic `menu.ipxe`/`late_command.sh`/`first-boot.sh` all use — `192.168.139.254` → Edinburgh/VRK, `172.16.124.2` → Fredericia Havn/FRD. Wrong network means the wrong TOML gets requested. |

---

## Procedure

1. PXE-boot the target node. At the estate's boot menu, select **`klargoring`** — shown as *"Projekt klargoring (custom live Proxmox installer, x86_64 or ARM64)"*.
2. The menu entry branches on architecture automatically (`:klargoring-amd64` / `:klargoring-arm64`) and boots the matching kernel/initrd:
   ```
   kernel ${boot-url}/proxmox/klargoring/<arch>/vmlinuz[-arm64] \
       toml_url=${boot-url}/proxmox/${site-prefix}-answer.toml confirm-wipe no-reboot
   initrd ${boot-url}/proxmox/klargoring/<arch>/installer-initrd[-arm64].img
   ```
   `${boot-url}`/`${site-prefix}` are already resolved by the same gateway-detection `iseq` branch every other menu entry uses — nothing to configure per-boot.
3. klargoring fetches the resolved `<SITE>-answer.toml` via the `toml_url` kernel parameter and hands off to the Proxmox automated installer with it.
4. The installer reads `[disk-setup]` from that TOML, detects the real disks present, and provisions ZFS accordingly (`raid1` across both disks for `*-answer.toml`, `raid0`/single-disk for `*-degraded.toml`).
5. Install proceeds fully unattended from there — no console interaction needed.
6. On completion, `[first-boot] url` in the same TOML fires `first-boot.sh`, which creates the `ansible` user, installs its SSH key, and configures `NOPASSWD` sudoers — the minimum surface Ansible needs to take over from here.
7. Once `first-boot.sh` has run, the node is ready for `docs/proxmox/Procedure-PVE-Node-Onboarding.md` (`site.yml`'s ten stages) — not covered by this document, that's the next real step.

---

## Verification checklist

Don't just watch the installer reach 100% and call it done — confirm each of these explicitly:

- [ ] Correct site detected (right `${site-prefix}`, confirmed via the gateway it actually PXE-booted from).
- [ ] Correct disk count detected — genuinely observed doing something (e.g. picking `*-answer.toml`'s RAID-1 path because two real disks were present), not just "the only TOML that happened to be tried."
- [ ] ZFS pool actually built across the expected disks, in the expected RAID level.
- [ ] Installer completes with no further prompts.
- [ ] **`ssh ansible@<node-ip>` works, with the estate's key, after install.** This is the one that actually proves `first-boot.sh` ran — "the installer finished" and "Ansible can manage this node" are two different claims, confirm both separately.

---

## Real worked example — `EXAPVEVRK002`, 2026-08-20 (first confirmed run)

**Node:** `EXAPVEVRK002`, site VRK, `192.168.139.6` — second PVE node at VRK, same Supermicro/Quanta chassis class as `EXAPVEVRK001`.

**Pre-flight (item 1/2 of that build's own plan):**
- BMC (`EXABMCVRK002`, `192.168.139.4`) shipped with default `admin`/`admin` credentials — reset via crash cart + GParted Live + `ipmitool`.
  This is the same procedure as `INC-2026-04-03-BMC-CREDS`, the original incident (a different site) it was written from. Independently cross-checked with `fyrtaarn` plus a separate `ipmitool` check from a different machine before being trusted for the build — second real-world confirmation this procedure generalises past that one incident.
- BIOS storage mode confirmed **AHCI** (matching `EXAPVEVRK001`'s own setting) — no hardware RAID/RST mode involved. Two 2TB WD hard drives visible in Bay #3/#4 at BIOS POST, no controller-side abstraction.

**The klargoring run itself:**
- Booted cleanly — kernel/initrd loaded without issue on the first attempt.
- Correctly detected site `VRK` via the gateway (`192.168.139.254`), obtained a DHCP lease.
- Correctly detected both disks and requested `VRK-answer.toml` (the two-disk, ZFS RAID-1 variant) — confirmed genuine detection, not a lucky default: the resulting pool was built as a real mirror across both disks (`sda`/`sdb`).
- Installer completed fully unattended, produced a working PVE install.
- `first-boot.sh` confirmed: `ssh ansible@192.168.139.6` succeeded with the estate's standard key immediately after.

**Not yet covered by this run** — post-install onboarding (`site.yml`'s stages: management packages, pools, `vmbr1`, PVE clustering with `EXAPVEVRK001`) is tracked separately, see `Procedure-PVE-Node-Onboarding.md` and the wider `PLAN-EXAPVEVRK002-onboarding-2026-08-19.md` at the repo root for the full build's own record.

---

## Related documents

| Need to... | See |
|---|---|
| Understand why the official-ISO / `select-pve-answer.sh` paths aren't used | `docs/proxmox/pxe-proxmox-autoinstall-build-log.md` |
| Bring a single-disk install up to a real RAID-1 mirror later | `docs/proxmox/zfs-raid0-to-raid1.md` |
| Reset BMC credentials that don't authenticate | `docs/INCIDENT-LOG.md` → `INC-2026-04-03-BMC-CREDS` |
| Onboard the node into Ansible management after this procedure | `docs/proxmox/Procedure-PVE-Node-Onboarding.md` |
| See the gateway-based site-detection logic this all depends on | `docs/bootstrap/bootstrapping.md` §4.1 |

---

## Changelog

| Date | Change |
|------|--------|
| 2026-08-20 | Initial version, written immediately after `EXAPVEVRK002`'s first confirmed successful run — the first real proof this path works at all, not a planning document written ahead of testing. |

---

*Example Music Limited — Internal Infrastructure Documentation*
*Do not distribute outside the organisation*
*Credentials: See password manager — never store passwords in this document*
