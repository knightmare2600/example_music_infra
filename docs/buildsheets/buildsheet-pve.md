# Build Sheet — Proxmox VE Nodes (EXAPVE*00X*)

**Document ID:** NET-BUILD-PVE-001  
**Classification:** Internal — Network Operations  
**Last Updated:** 2026-03-04  
**Signed off by:** ___________________________  Date: ___________

> **Note (2026-07-15):** the BMC/ISO/answer-file steps below (1-13) remain the accurate manual,
> hardware-side procedure. Steps 14-15 (Python scripts, Ansible SSH key) are superseded — both
> are now automated by `ansible/playbooks/proxmox/site.yml` (specifically
> `20-ansible-access.yml`/`40-scripts.yml`). See `docs/proxmox/Procedure-PVE-Node-Onboarding.md`
> for the current, authoritative end-to-end procedure, including the single-command
> `bootstrap-new-node.yml` → `site.yml` chain that now covers everything from step 8 onward.

---

## Standard Build Reference

### Node IP Convention
```
Node 1 (primary)  : 192.168.<site-octet>.5
Node 2            : 192.168.<site-octet>.6
Node 3            : 192.168.<site-octet>.7

BMC / iDRAC / iLO : 192.168.<site-octet>.2  (node 1)
                    192.168.<site-octet>.3  (node 2)
                    192.168.<site-octet>.4  (node 3)
```

### BMC Default Credentials by Vendor
```
Dell    iDRAC      : root       / calvin
SuperMicro BMC     : admin      / admin
HP      iLO        : Administrator / <8-digit uppercase hex — see node record below>
```

> **Fredericia Havn note:** `192.168.139.50` is Edinburgh's provisioning server. If you're
> building at Fredericia Havn instead, the server is `172.16.124.1:8000` (gateway `172.16.124.2`)
> — see `docs/bootstrap/bootstrapping.md` §4.1. The `menu.ipxe`/`first-boot.sh` boot flow
> detects this automatically, including selecting the right site's TOML file below (§5.1) —
> only matters if you're fetching something by hand (as below), where you must pick the
> matching filename yourself.

### TOML Answer Files

Site-prefixed as of 2026-07-11 — there's no bare `answer.toml`/`degraded.toml` any more, one
correctly-pinned file per provisioning server (`docs/bootstrap/bootstrapping.md` §5.1):

```
Edinburgh (VRK)        : http://192.168.139.50/proxmox/
  VRK-answer.toml       — standard build, 2-disk ZFS mirror  ← USE THIS for production
  VRK-degraded.toml     — single-disk ZFS pool, NOT production ready

Fredericia Havn (FRD)  : http://172.16.124.1:8000/proxmox/
  FRD-answer.toml       — standard build, 2-disk ZFS mirror  ← USE THIS for production
  FRD-degraded.toml     — single-disk ZFS pool, NOT production ready

Preferred: from the "failed" shell, fetch and run bootstrap/web/proxmox/select-pve-answer.sh
instead of picking the filename by hand — it detects which provisioning network you're on and
suggests answer/degraded from the real disk count, then fetches and verifies the right file
itself (see docs/proxmox/pxe-proxmox-autoinstall-build-log.md 9 for the full detail):
  wget http://192.168.139.50/proxmox/select-pve-answer.sh
  sh select-pve-answer.sh
  (follow the prompts)
  exit

Manual fallback, if you'd rather pick the file yourself (Edinburgh example — substitute FRD-
and the Fredericia Havn URL above if building there):
  wget -O /run/automatic-installer-answers http://192.168.139.50/proxmox/VRK-answer.toml
  exit
```

### Python Scripts — deployed to /usr/local/bin/ automatically

> Historical: this used to be a manual per-node copy step. As of `ansible/playbooks/proxmox/playbooks/40-scripts.yml`,
> `site.yml` deploys these automatically on every run — no manual action needed. Listed here for
> reference only.

```
convert-v2v.py     — VMware to Proxmox VM conversion
create-vm.py       — VM creation and provisioning
manage-pool.py     — ZFS pool management
```

### Firstboot Script
```bash
bash /var/lib/proxmox-first-boot/proxmox-first-boot/
```

### Post-Install Backup (run before production handover)
```bash
tar czf /root/pve-host-backup-$(date +%F).tar.gz /etc/pve /etc/network/interfaces /etc/hosts /etc/fstab

cp /var/lib/pve-cluster/config.db  /root/pve-config-db-backup-$(date +%F).db
```

---

## Installation Flow (per node)

```
1.  Open BMC console (iDRAC / iLO / BMC) in browser
2.  Add credentials to keystore and verify access
3.  Mount Proxmox ISO via Virtual Media
4.  Boot → Advanced → Automated Install
5.  Node "fails" to a shell — this is expected
6.  wget the appropriate site-prefixed .toml file (VRK-answer.toml / FRD-answer.toml for production)
7.  Type 'exit' — installation proceeds
8.  On first boot: log in as root, run firstboot script
9.  Confirm hostname, IP, site, entity displayed correctly
10. Acknowledge ZFS warning if single-disk (*-degraded.toml only)
11. Reboot when prompted (or run: ifreload -a to apply network without reboot)
12. Reconnect on site LAN IP — verify web UI at https://<ip>:8006
13. Install ipmitool, set BMC password via ipmitool
14. Run `ansible-playbook -i "<node-ip>," -i configs/inventory -e target="<node-ip>" playbooks/proxmox/bootstrap-new-node.yml`
    (the ad-hoc `-i "<node-ip>,"` source is required — the node's fresh DHCP IP isn't in
    `configs/inventory` yet, and without it `hosts: "{{ target }}"` matches zero hosts and the
    play silently does nothing; see `bootstrap-new-node.yml`'s own header for the full reasoning.
    Deploys Ansible SSH key + python scripts + everything else in one automated pass — see
    `docs/proxmox/Procedure-PVE-Node-Onboarding.md`)
15. Run post-install backup
```

---

## Build Checklist

## Proxmox Node Build Checklist

| Hostname | Vendor | Node IP Suffix | BMC IP Suffix | BMC Console Opened | BMC Credentials Stored in Keystore and Login Verified | Proxmox ISO Mounted via Virtual Media and Booted | Answer File Retrieved (VRK/FRD-answer.toml or -degraded.toml) | ZFS Pool Confirmed After Install | ZFS 2-Disk Mirror Confirmed | Firstboot Script Ran Successfully | Node Rebooted and Site LAN IP Reachable | IPMI Verified (ipmitool installed + BMC password changed) | Hostname Correctly Set | DNS Updated and Verified | Ansible SSH Key Installed and Login Verified | Post-Install Backup Taken | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

### UK

| Hostname | Vendor | Node IP Suffix | BMC IP Suffix | BMC Console Opened | BMC Credentials Stored in Keystore and Login Verified | Proxmox ISO Mounted via Virtual Media and Booted | Answer File Retrieved (VRK/FRD-answer.toml or -degraded.toml) | ZFS Pool Confirmed After Install | ZFS 2-Disk Mirror Confirmed | Firstboot Script Ran Successfully | Node Rebooted and Site LAN IP Reachable | IPMI Verified (ipmitool installed + BMC password changed) | Hostname Correctly Set | DNS Updated and Verified | Ansible SSH Key Installed and Login Verified | Post-Install Backup Taken | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| EXAPVEFAL001 | | .5 | .2 | [ ] | [ ] | [ ] | | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| EXAPVEFAL002 | | .6 | .3 | [ ] | [ ] | [ ] | | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| EXAPVEFAL003 | | .7 | .4 | [ ] | [ ] | [ ] | | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| EXAPVEEDI001 | | .5 | .2 | [ ] | [ ] | [ ] | | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| EXAPVEGLA001 | | .5 | .2 | [ ] | [ ] | [ ] | | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| EXAPVEABD001 | | .5 | .2 | [ ] | [ ] | [ ] | | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| EXAPVEMCR001 | | .5 | .2 | [ ] | [ ] | [ ] | | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| EXAPVELND001 | | .5 | .2 | [ ] | [ ] | [ ] | | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| EXAPVEBIR001 | | .5 | .2 | [ ] | [ ] | [ ] | | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| EXAPVELIV001 | | .5 | .2 | [ ] | [ ] | [ ] | | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| EXAPVENEW001 | | .5 | .2 | [ ] | [ ] | [ ] | | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| EXAPVESHE001 | | .5 | .2 | [ ] | [ ] | [ ] | | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| EXAPVEHUL001 | | .5 | .2 | [ ] | [ ] | [ ] | | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| EXAPVECOV001 | | .5 | .2 | [ ] | [ ] | [ ] | | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| EXAPVEHAL001 | | .5 | .2 | [ ] | [ ] | [ ] | | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |

### Scandinavia
| Hostname | Vendor | Node IP Suffix | BMC IP Suffix | BMC Console Opened | BMC Credentials Stored in Keystore and Login Verified | Proxmox ISO Mounted via Virtual Media and Booted | Answer File Retrieved (VRK/FRD-answer.toml or -degraded.toml) | ZFS Pool Confirmed After Install | ZFS 2-Disk Mirror Confirmed | Firstboot Script Ran Successfully | Node Rebooted and Site LAN IP Reachable | IPMI Verified (ipmitool installed + BMC password changed) | Hostname Correctly Set | DNS Updated and Verified | Ansible SSH Key Installed and Login Verified | Post-Install Backup Taken | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| EXAPVEOSL001 | | .5 | .2 | [ ] | [ ] | [ ] | | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| EXAPVEGOT001 | | .5 | .2 | [ ] | [ ] | [ ] | | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |

### Europe

| Hostname | Vendor | Node IP Suffix | BMC IP Suffix | BMC Console Opened | BMC Credentials Stored in Keystore and Login Verified | Proxmox ISO Mounted via Virtual Media and Booted | Answer File Retrieved (VRK/FRD-answer.toml or -degraded.toml) | ZFS Pool Confirmed After Install | ZFS 2-Disk Mirror Confirmed | Firstboot Script Ran Successfully | Node Rebooted and Site LAN IP Reachable | IPMI Verified (ipmitool installed + BMC password changed) | Hostname Correctly Set | DNS Updated and Verified | Ansible SSH Key Installed and Login Verified | Post-Install Backup Taken | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| EXAPVECPH001 | | .5 | .2 | [ ] | [ ] | [ ] | | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | ORIG PVE node |
| EXAPVEODE001 | | .5 | .2 | [ ] | [ ] | [ ] | | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | EU HUB |
| EXAPVEODE002 | | .6 | .3 | [ ] | [ ] | [ ] | | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| EXAPVEMUN001 | | .5 | .2 | [ ] | [ ] | [ ] | | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| EXAPVEBON001 | | .5 | .2 | [ ] | [ ] | [ ] | | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| EXAPVEBER001 | | .5 | .2 | [ ] | [ ] | [ ] | | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| EXAPVEMIL001 | | .5 | .2 | [ ] | [ ] | [ ] | | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| EXAPVEAMS001 | | .5 | .2 | [ ] | [ ] | [ ] | | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| EXAPVEVIE001 | | .5 | .2 | [ ] | [ ] | [ ] | | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |

### North America

| Hostname | Vendor | Node IP Suffix | BMC IP Suffix | BMC Console Opened | BMC Credentials Stored in Keystore and Login Verified | Proxmox ISO Mounted via Virtual Media and Booted | Answer File Retrieved (VRK/FRD-answer.toml or -degraded.toml) | ZFS Pool Confirmed After Install | ZFS 2-Disk Mirror Confirmed | Firstboot Script Ran Successfully | Node Rebooted and Site LAN IP Reachable | IPMI Verified (ipmitool installed + BMC password changed) | Hostname Correctly Set | DNS Updated and Verified | Ansible SSH Key Installed and Login Verified | Post-Install Backup Taken | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| EXAPVEBRK001 | | .5 | .2 | [ ] | [ ] | [ ] | | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | NA HUB |
| EXAPVEBRK002 | | .6 | .3 | [ ] | [ ] | [ ] | | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| EXAPVETOR001 | | .5 | .2 | [ ] | [ ] | [ ] | | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| EXAPVEMTL001 | | .5 | .2 | [ ] | [ ] | [ ] | | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| EXAPVENYC001 | | .5 | .2 | [ ] | [ ] | [ ] | | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |

### Pacific

| Hostname | Vendor | Node IP Suffix | BMC IP Suffix | BMC Console Opened | BMC Credentials Stored in Keystore and Login Verified | Proxmox ISO Mounted via Virtual Media and Booted | Answer File Retrieved (VRK/FRD-answer.toml or -degraded.toml) | ZFS Pool Confirmed After Install | ZFS 2-Disk Mirror Confirmed | Firstboot Script Ran Successfully | Node Rebooted and Site LAN IP Reachable | IPMI Verified (ipmitool installed + BMC password changed) | Hostname Correctly Set | DNS Updated and Verified | Ansible SSH Key Installed and Login Verified | Post-Install Backup Taken | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| EXAPVESYD001 | | .5 | .2 | [ ] | [ ] | [ ] | | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| EXAPVEMEL001 | | .5 | .2 | [ ] | [ ] | [ ] | | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| EXAPVEAKL001 | | .5 | .2 | [ ] | [ ] | [ ] | | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |

---

## Python Scripts — per node checklist

> These are deployed automatically to `/usr/local/bin/` by `ansible/playbooks/proxmox/playbooks/40-scripts.yml`
> on every `site.yml` run — this checklist is now a verification record, not a manual task list.
> Tick each when deployed and verified executable.

| Hostname | convert-v2v.py Deployed and Executable | create-vm.py Deployed and Executable | manage-pool.py Deployed and Executable | Notes |
|----------|-----------------------------------------|--------------------------------------|----------------------------------------|------|
| EXAPVEFAL001 | - [ ] | - [ ] | - [ ] | |
| EXAPVEFAL002 | - [ ] | - [ ] | - [ ] | |
| EXAPVEFAL003 | - [ ] | - [ ] | - [ ] | |
| EXAPVEEDI001 | - [ ] | - [ ] | - [ ] | |
| EXAPVEGLA001 | - [ ] | - [ ] | - [ ] | |
| EXAPVEABD001 | - [ ] | - [ ] | - [ ] | |
| EXAPVEMCR001 | - [ ] | - [ ] | - [ ] | |
| EXAPVELND001 | - [ ] | - [ ] | - [ ] | |
| EXAPVEBIR001 | - [ ] | - [ ] | - [ ] | |
| EXAPVELIV001 | - [ ] | - [ ] | - [ ] | |
| EXAPVENEW001 | - [ ] | - [ ] | - [ ] | |
| EXAPVESHE001 | - [ ] | - [ ] | - [ ] | |
| EXAPVEHUL001 | - [ ] | - [ ] | - [ ] | |
| EXAPVECOV001 | - [ ] | - [ ] | - [ ] | |
| EXAPVEHAL001 | - [ ] | - [ ] | - [ ] | |
| EXAPVEOSL001 | - [ ] | - [ ] | - [ ] | |
| EXAPVEGOT001 | - [ ] | - [ ] | - [ ] | |
| EXAPVECPH001 | - [ ] | - [ ] | - [ ] | |
| EXAPVEODE001 | - [ ] | - [ ] | - [ ] | |
| EXAPVEODE002 | - [ ] | - [ ] | - [ ] | |
| EXAPVEMUN001 | - [ ] | - [ ] | - [ ] | |
| EXAPVEBON001 | - [ ] | - [ ] | - [ ] | |
| EXAPVEBER001 | - [ ] | - [ ] | - [ ] | |
| EXAPVEMIL001 | - [ ] | - [ ] | - [ ] | |
| EXAPVEAMS001 | - [ ] | - [ ] | - [ ] | |
| EXAPVEVIE001 | - [ ] | - [ ] | - [ ] | |
| EXAPVEFAX001 | - [ ] | - [ ] | - [ ] | |
| EXAPVEKGE001 | - [ ] | - [ ] | - [ ] | |
| EXAPVEKOR001 | - [ ] | - [ ] | - [ ] | |
| EXAPVEBRK001 | - [ ] | - [ ] | - [ ] | |
| EXAPVEBRK002 | - [ ] | - [ ] | - [ ] | |
| EXAPVETOR001 | - [ ] | - [ ] | - [ ] | |
| EXAPVEMTL001 | - [ ] | - [ ] | - [ ] | |
| EXAPVENYC001 | - [ ] | - [ ] | - [ ] | |
| EXAPVELAX001 | - [ ] | - [ ] | - [ ] | |
| EXAPVEMIA001 | - [ ] | - [ ] | - [ ] | |
| EXAPVENJC001 | - [ ] | - [ ] | - [ ] | |
| EXAPVEATL001 | - [ ] | - [ ] | - [ ] | |
| EXAPVESYD001 | - [ ] | - [ ] | - [ ] | |
| EXAPVEMEL001 | - [ ] | - [ ] | - [ ] | |
| EXAPVEAKL001 | - [ ] | - [ ] | - [ ] | |
| EXAPVECLD001 | - [ ] | - [ ] | - [ ] | |
| EXAPVECLD002 | - [ ] | - [ ] | - [ ] | |

---

## iLO Password Reference (HP nodes only)

> Generated 8-character uppercase hex passwords for iLO accounts.  
> Replace with actual passwords from your password manager — these are placeholders to be set during BMC configuration and stored in the keystore.

| Hostname | iLO Password | Keystore Entry Confirmed |
|----------|-------------|--------------------------|
| (fill as needed) | A3F7C2E9 | - [ ] |
| | B81D4F6A | - [ ] |
| | E5C09A3D | - [ ] |
| | 2F7B8E1C | - [ ] |
| | 94D6A0F3 | - [ ] |
| | C1E38B7D | - [ ] |
| | 6A2F0C4E | - [ ] |
| | F09D5B82 | - [ ] |
| | 3E7A1C6F | - [ ] |
| | D4B80E29 | - [ ] |

---

## Sign Off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Build engineer | | | |
| Network lead | | | |
| Operations manager | | | |

---

*Internal Use Only — Network Engineering*  
*Proxmox VE 9.1 — jukebox.internal*
