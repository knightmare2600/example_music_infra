# Build Sheet — Proxmox VE Nodes (EXAPVE*00X*)

**Document ID:** NET-BUILD-PVE-001  
**Classification:** Internal — Network Operations  
**Last Updated:** 2026-03-04  
**Signed off by:** ___________________________  Date: ___________

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

### TOML Answer Files
```
Provisioning server : http://192.168.139.50/proxmox/

answers.toml        — standard build, 2-disk ZFS mirror  ← USE THIS for production
degraded.toml       — single-disk ZFS pool, NOT production ready

Fetch from the "failed" shell:
  wget -O /run/automatic-installer-answers http://192.168.139.50/proxmox/answers.toml
  exit
```

### Python Scripts — deploy to /usr/local/bin/
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
6.  wget the appropriate .toml file (answers.toml for production)
7.  Type 'exit' — installation proceeds
8.  On first boot: log in as root, run firstboot script
9.  Confirm hostname, IP, site, entity displayed correctly
10. Acknowledge ZFS warning if single-disk (degraded.toml only)
11. Reboot when prompted (or run: ifreload -a to apply network without reboot)
12. Reconnect on site LAN IP — verify web UI at https://<ip>:8006
13. Install ipmitool, set BMC password via ipmitool
14. Deploy python scripts to /usr/local/bin/
15. Verify ansible SSH key
16. Run post-install backup
```

---

## Build Checklist

## Proxmox Node Build Checklist

| Hostname | Vendor | Node IP Suffix | BMC IP Suffix | BMC Console Opened | BMC Credentials Stored in Keystore and Login Verified | Proxmox ISO Mounted via Virtual Media and Booted | Answer File Retrieved (answers.toml / degraded.toml) | ZFS Pool Confirmed After Install | ZFS 2-Disk Mirror Confirmed | Firstboot Script Ran Successfully | Node Rebooted and Site LAN IP Reachable | IPMI Verified (ipmitool installed + BMC password changed) | Hostname Correctly Set | DNS Updated and Verified | Ansible SSH Key Installed and Login Verified | Post-Install Backup Taken | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

### UK

| Hostname | Vendor | Node IP Suffix | BMC IP Suffix | BMC Console Opened | BMC Credentials Stored in Keystore and Login Verified | Proxmox ISO Mounted via Virtual Media and Booted | Answer File Retrieved (answers.toml / degraded.toml) | ZFS Pool Confirmed After Install | ZFS 2-Disk Mirror Confirmed | Firstboot Script Ran Successfully | Node Rebooted and Site LAN IP Reachable | IPMI Verified (ipmitool installed + BMC password changed) | Hostname Correctly Set | DNS Updated and Verified | Ansible SSH Key Installed and Login Verified | Post-Install Backup Taken | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| EXAPVEFAL001 | | .5 | .2 | [ ] | [ ] | [ ] | | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| EXAPVEFAL002 | | .6 | .3 | [ ] | [ ] | [ ] | | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| EXAPVEFAL003 | | .7 | .4 | [ ] | [ ] | [ ] | | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| EXAPVEEDI001 | | .5 | .2 | [ ] | [ ] | [ ] | | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| EXAPVEGLA001 | | .5 | .2 | [ ] | [ ] | [ ] | | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| EXAPVEABR001 | | .5 | .2 | [ ] | [ ] | [ ] | | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
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
| Hostname | Vendor | Node IP Suffix | BMC IP Suffix | BMC Console Opened | BMC Credentials Stored in Keystore and Login Verified | Proxmox ISO Mounted via Virtual Media and Booted | Answer File Retrieved (answers.toml / degraded.toml) | ZFS Pool Confirmed After Install | ZFS 2-Disk Mirror Confirmed | Firstboot Script Ran Successfully | Node Rebooted and Site LAN IP Reachable | IPMI Verified (ipmitool installed + BMC password changed) | Hostname Correctly Set | DNS Updated and Verified | Ansible SSH Key Installed and Login Verified | Post-Install Backup Taken | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| EXAPVEOSL001 | | .5 | .2 | [ ] | [ ] | [ ] | | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| EXAPVEGOT001 | | .5 | .2 | [ ] | [ ] | [ ] | | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |

### Europe

| Hostname | Vendor | Node IP Suffix | BMC IP Suffix | BMC Console Opened | BMC Credentials Stored in Keystore and Login Verified | Proxmox ISO Mounted via Virtual Media and Booted | Answer File Retrieved (answers.toml / degraded.toml) | ZFS Pool Confirmed After Install | ZFS 2-Disk Mirror Confirmed | Firstboot Script Ran Successfully | Node Rebooted and Site LAN IP Reachable | IPMI Verified (ipmitool installed + BMC password changed) | Hostname Correctly Set | DNS Updated and Verified | Ansible SSH Key Installed and Login Verified | Post-Install Backup Taken | Notes |
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

| Hostname | Vendor | Node IP Suffix | BMC IP Suffix | BMC Console Opened | BMC Credentials Stored in Keystore and Login Verified | Proxmox ISO Mounted via Virtual Media and Booted | Answer File Retrieved (answers.toml / degraded.toml) | ZFS Pool Confirmed After Install | ZFS 2-Disk Mirror Confirmed | Firstboot Script Ran Successfully | Node Rebooted and Site LAN IP Reachable | IPMI Verified (ipmitool installed + BMC password changed) | Hostname Correctly Set | DNS Updated and Verified | Ansible SSH Key Installed and Login Verified | Post-Install Backup Taken | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| EXAPVEBRK001 | | .5 | .2 | [ ] | [ ] | [ ] | | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | NA HUB |
| EXAPVEBRK002 | | .6 | .3 | [ ] | [ ] | [ ] | | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| EXAPVETOR001 | | .5 | .2 | [ ] | [ ] | [ ] | | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| EXAPVEMTL001 | | .5 | .2 | [ ] | [ ] | [ ] | | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| EXAPVENYC001 | | .5 | .2 | [ ] | [ ] | [ ] | | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |

### Pacific

| Hostname | Vendor | Node IP Suffix | BMC IP Suffix | BMC Console Opened | BMC Credentials Stored in Keystore and Login Verified | Proxmox ISO Mounted via Virtual Media and Booted | Answer File Retrieved (answers.toml / degraded.toml) | ZFS Pool Confirmed After Install | ZFS 2-Disk Mirror Confirmed | Firstboot Script Ran Successfully | Node Rebooted and Site LAN IP Reachable | IPMI Verified (ipmitool installed + BMC password changed) | Hostname Correctly Set | DNS Updated and Verified | Ansible SSH Key Installed and Login Verified | Post-Install Backup Taken | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| EXAPVESYD001 | | .5 | .2 | [ ] | [ ] | [ ] | | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| EXAPVEMEL001 | | .5 | .2 | [ ] | [ ] | [ ] | | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| EXAPVEAKL001 | | .5 | .2 | [ ] | [ ] | [ ] | | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |

---

## Python Scripts — per node checklist

> These are deployed once per physical node to `/usr/local/bin/`.  
> Tick each when deployed and verified executable.

| Hostname | convert-v2v.py Deployed and Executable | create-vm.py Deployed and Executable | manage-pool.py Deployed and Executable | Notes |
|----------|-----------------------------------------|--------------------------------------|----------------------------------------|------|
| EXAPVEFAL001 | - [ ] | - [ ] | - [ ] | |
| EXAPVEFAL002 | - [ ] | - [ ] | - [ ] | |
| EXAPVEFAL003 | - [ ] | - [ ] | - [ ] | |
| EXAPVEEDI001 | - [ ] | - [ ] | - [ ] | |
| EXAPVEGLA001 | - [ ] | - [ ] | - [ ] | |
| EXAPVEABR001 | - [ ] | - [ ] | - [ ] | |
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
| EXAPVEGAA001 | - [ ] | - [ ] | - [ ] | |
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
