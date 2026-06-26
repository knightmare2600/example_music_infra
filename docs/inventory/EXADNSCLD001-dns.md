# EXADNSCLD001 — DNS Server Operations Guide

**Hostname:** `exadnscld001.jukebox.internal`
**Role:** Authoritative DNS — `jukebox.internal`
**OS:** Debian trixie
**IP:** `192.168.139.8/24` (provisioning network, CLD site octet `.10`)
**Provisioned by:** `bindme.sh`

---

## Contents

1. [What This Server Does](#1-what-this-server-does)
2. [Zone Structure](#2-zone-structure)
3. [Day-to-Day Operations](#3-day-to-day-operations)
4. [Adding or Changing a Site](#4-adding-or-changing-a-site)
5. [Adding a One-Off Record](#5-adding-a-one-off-record)
6. [Aliases Quick Reference](#6-aliases-quick-reference)
7. [Troubleshooting](#7-troubleshooting)
8. [File Locations](#8-file-locations)
9. [How the Addressing Scheme Works](#9-how-the-addressing-scheme-works)

---

## 1. What This Server Does

EXADNSCLD001 is the authoritative DNS server for the `jukebox.internal` private zone. It runs BIND9 on Debian trixie and sits on the provisioning network (`192.168.139.0/24`).

It answers two types of query:

- **Authoritative** — `jukebox.internal` names and reverse PTR lookups for all site subnets. Any client anywhere on any site subnet can query it for these.
- **Recursive** — External names (e.g. `debian.org`) forwarded to `1.1.1.1` / `9.9.9.9`. Recursion is only permitted from `192.168.139.0/24` (the provisioning network). Site clients that need external resolution use their local firewall or ISP DNS.

The zone content is generated entirely from `sites.csv` — the same single source of truth used by `firewallme.sh` and `site-inventory-audit.py`. You do not edit zone files by hand except to add one-off records at the bottom (see [Section 5](#5-adding-a-one-off-record)).

---

## 2. Zone Structure

### Forward zone — `jukebox.internal`

File: `/etc/bind/db.jukebox.internal`

Contains one A record per standard role address per site. The host-to-suffix mapping is identical to the `SUFFIX_MAP` in `site-inventory-audit.py`:

| Suffix | Role     | Example (GLA, octet 141)          |
|--------|----------|-----------------------------------|
| `.1`   | EXARTR   | `exartrgla001.jukebox.internal`   |
| `.2`   | EXARAC   | `exaracgla001.jukebox.internal`   |
| `.3`   | EXARAC   | `exaracgla002.jukebox.internal`   |
| `.4`   | EXARAC   | `exaracgla003.jukebox.internal`   |
| `.5`   | EXAPVE   | `exapvegla001.jukebox.internal`   |
| `.6`   | EXAPVE   | `exapvegla002.jukebox.internal`   |
| `.7`   | EXAPVE   | `exapvegla003.jukebox.internal`   |
| `.10`  | EXADCS   | `exadcsgla001.jukebox.internal`   |
| `.11`  | EXADCS   | `exadcsgla002.jukebox.internal`   |
| `.48`  | EXASBC   | `exasbcgla001.jukebox.internal`   |
| `.250` | EXASWI   | `exaswigla001.jukebox.internal`   |
| `.251` | EXASWI   | `exaswigla002.jukebox.internal`   |
| `.252` | EXASWI   | `exaswigla003.jukebox.internal`   |
| `.253` | EXAFWL   | `exafwlgla001.jukebox.internal`   |

CLD is a special case: suffix `.48` resolves to `exapbxcld001` (PBX), not `exasbc`.

The forward zone also contains **firewall WAN addresses** — see [Section 9](#9-how-the-addressing-scheme-works) — and the provisioning ancillary hosts:

| Name                               | IP               | Purpose                   |
|------------------------------------|------------------|---------------------------|
| `exadnscld001.jukebox.internal`    | `192.168.139.8` | DNS/BIND server (this host)       |
| `exasvrcld002.jukebox.internal`    | `192.168.139.20` | Windows Admin Centre              |
| `exasvrcld003.jukebox.internal`    | `192.168.139.49` | Ansible control node              |
| `exasvrcld004.jukebox.internal`    | `192.168.139.22` | Rudder configuration management   |
| `exacldpbx001.jukebox.internal`    | `192.168.139.48` | Central 3CX PBX                   |
| `exaprvcld001.jukebox.internal`    | `192.168.139.50` | Provisioning / PXE server         |
| `exafwl{site}001-wan.jukebox.internal` | `192.168.139.{octet}` | Each site's FWL WAN face  |

### Reverse zone — provisioning network

File: `/etc/bind/db.192.168.139`
Zone: `139.168.192.in-addr.arpa`

This is a **dedicated, hand-built zone** — it is not produced by the per-site loop.
It contains:

- PTR records for the three ancillary hosts (`.10`, `.50`, `.69`)
- PTR records for every site firewall's WAN address on the provisioning network
  (`192.168.139.{octet}` → `exafwl{site}001-wan.jukebox.internal.`)

It does **not** duplicate the site-level PTR records for `192.168.139.x` addresses that happen to fall in the normal SUFFIX_MAP (e.g. `.1`, `.253`). Those belong in the site's own reverse zone.

### Reverse zones — per site

Files: `/etc/bind/db.192.168.{octet}` (one per site)
Zones: `{octet}.168.192.in-addr.arpa`

One zone file per site, generated from `sites.csv`. Each contains PTR records for the standard SUFFIX_MAP suffixes (`.1` through `.253`).

CLD is **excluded** from this loop — its `192.168.139.0/24` subnet is the provisioning network and is handled by the dedicated `139` zone above.

Total zones: 1 forward + 1 provisioning reverse + ~43 site reverse zones.

---

## 3. Day-to-Day Operations

### Check whether named is running

```
bindstatus
```

### Reload the forward zone after a manual edit

```
reloadbind
```

This runs `rndc reload jukebox.internal`. It reloads only the forward zone. If you have edited a reverse zone file directly, reload named fully:

```
sudo systemctl reload named
```

### Syntax-check the forward zone without reloading

```
checkbind
```

### Edit the forward zone, check it, and reload in one step

```
editzone
```

This opens `vim /etc/bind/db.jukebox.internal`, then on write/quit runs `named-checkzone` and `rndc reload` automatically. If the check fails, the reload does not happen.

### Watch the BIND log live

```
bindlog
```

### Show the current serial and record count

```
grep -E 'serial|IN  A' /etc/bind/db.jukebox.internal | head -5
```

---

## 4. Adding or Changing a Site

All site data lives in `sites.csv` (single source of truth). To add a site or change a subnet:

1. Edit `sites.csv` — add or update the site row.
2. Re-run `bindme.sh` from the provisioning server, or run the zone regeneration helper:
   
   ```
   sudo /usr/local/sbin/regen-zone.sh
   ```
   
   This regenerates `/etc/bind/db.jukebox.internal` and all reverse zones, validates them with `named-checkzone`, and calls `rndc reload`.
   
3. Confirm the new records are visible:

   ```
   dig @192.168.139.8 exafwl{SITE}001.jukebox.internal
   ```

Do **not** edit the generated sections of the zone file by hand — your changes will be overwritten on the next regeneration. Use the one-off section at the bottom for anything not covered by the standard SUFFIX_MAP (see Section 5).

---

## 5. Adding a One-Off Record

For hosts that are not in the SUFFIX_MAP (specialist devices, temporary VMs, extra management addresses, etc.) add records at the **bottom** of the zone file, below the generated block. The section is labelled clearly in the file.

```
editzone
```

Then scroll to the bottom and add your record, e.g.:

```
; ── One-off records -- add below, DO NOT edit above ──────────
exacofcly001      IN  A   192.168.41.100   ; coffee machine, CLY
vpn-gateway       IN  A   192.168.139.200  ; temporary VPN endpoint
```

Increment the serial manually when editing by hand:

```
; Current serial in SOA:  2026032901
; After your edit, change it to:  2026032902
```

Then save, let `editzone` check and reload, or run `checkbind` then `reloadbind`.

> **Important:** `bindme.sh` and `regen-zone.sh` overwrite the zone file completely. Back up your one-off records before re-running either script. The bottom of the file has a clearly marked one-off section — keep records there and note them somewhere safe (e.g. a comment in `sites.csv` or a brief note in this doc).

---

## 6. Aliases Quick Reference

These are available in both **bash** and **zsh** for `root` and `ansible` users, sourced from `/etc/profile.d/bind-aliases.sh` and embedded in `.zshrc`.

| Alias         | What it does                                              |
|---------------|-----------------------------------------------------------|
| `reloadbind`  | `rndc reload jukebox.internal` — live zone reload         |
| `checkbind`   | `named-checkzone` — syntax check, no reload               |
| `editzone`    | `vim` + check + reload in one step                        |
| `bindstatus`  | `systemctl status named`                                  |
| `bindlog`     | `journalctl -u named -f` — follow the BIND log            |

---

## 7. Troubleshooting

### named won't start

```
journalctl -u named -n 50
named-checkconf /etc/bind/named.conf
named-checkzone jukebox.internal /etc/bind/db.jukebox.internal
```

Common causes: syntax error in a zone file (missing trailing dot on a hostname, incorrect serial format, duplicate record). `named-checkzone` will point to the
exact line.

### A record not resolving

```
dig @192.168.139.8 exafwledi001.jukebox.internal
```

If `NXDOMAIN` — check the zone file contains the record, and that the serial was incremented and a reload was done. If `SERVFAIL` — check `bindlog` for errors.

### PTR lookup failing

```
dig @192.168.139.8 -x 192.168.139.131
```

For the provisioning network (`.139`), check `/etc/bind/db.192.168.139`. For site subnets, check `/etc/bind/db.192.168.{octet}`.

The zone name for a PTR lookup on `192.168.X.Y` is `X.168.192.in-addr.arpa`. A missing PTR record in the correct file means either the zone wasn't regenerated after a `sites.csv` change, or the address falls outside the SUFFIX_MAP.

### Serial not updating

`bindme.sh` always writes serial `YYYYMMDDnn` where `nn=01`. If you run it twice on the same day the serial will not increment. Increment `nn` manually:

```
editzone
# Change e.g. 2026032901 to 2026032902 in the SOA block
```

### named is running but returning stale data

```
rndc flush
reloadbind
```

`rndc flush` clears the cache. `reloadbind` forces a zone reload from disk.

### Checking what BIND thinks it has loaded

```
rndc status
rndc zonestatus jukebox.internal
```

---

## 8. File Locations

| Path                                  | Purpose                                      |
|---------------------------------------|----------------------------------------------|
| `/etc/bind/named.conf`                | BIND main config (includes the two below)    |
| `/etc/bind/named.conf.options`        | Forwarders, recursion policy, listen address |
| `/etc/bind/named.conf.local`          | Zone declarations (all zones listed here)    |
| `/etc/bind/db.jukebox.internal`       | Forward zone file                            |
| `/etc/bind/db.192.168.139`            | Provisioning network reverse zone            |
| `/etc/bind/db.192.168.{octet}`        | Per-site reverse zone (one per site)         |
| `/etc/profile.d/bind-aliases.sh`      | Bash/dash aliases                            |
| `/root/.zshrc`                        | zsh config including aliases for root        |
| `/home/ansible/.zshrc`                | zsh config including aliases for ansible     |
| `/usr/local/sbin/bindme.sh`           | Copy of setup script (for regen-zone.sh)     |
| `/usr/local/sbin/regen-zone.sh`       | Zone regeneration helper                     |
| `/etc/example-music/nodeinfo.json`    | Node info file (read-only, install record)   |

---

## 9. How the Addressing Scheme Works

Each site has a `/24` subnet in `192.168.0.0/16`. The third octet is the site's unique identifier — referred to as the **site octet**. Everything derives from it:

```
GLA  →  192.168.141.0/24   →  site octet: 141
         ├─ .1    exartrgla001    (hardware router)
         ├─ .10   exadcsgla001    (domain controller)
         ├─ .253  exafwlgla001    (firewall LAN address)
         └─ ...
```

The provisioning network is `192.168.139.0/24`. Every site firewall has a **WAN interface** on this network, and its host address on the provisioning network uses the same site octet as its host part:

```
GLA site octet = 141
  →  Firewall LAN address:  192.168.141.253
  →  Firewall WAN address:  192.168.139.141   ← host octet = site octet
```

This gives you a deterministic, memorable mapping: if you know a site's octet, you know its firewall's WAN IP on the provisioning network without looking anything up.

The `139` reverse zone exploits this to provide PTR records for all firewall WAN addresses in one place, while each site's own `/24` reverse zone covers the LAN side.

**Examples:**

| Site | Site subnet         | FWL LAN IP        | FWL WAN IP (prov.) |
|------|---------------------|-------------------|--------------------|
| LND  | 192.168.20.0/24     | 192.168.20.253    | 192.168.139.20     |
| FAL  | 192.168.76.0/24     | 192.168.76.253    | 192.168.139.76     |
| EDI  | 192.168.131.0/24    | 192.168.131.253   | 192.168.139.131    |
| GLA  | 192.168.141.0/24    | 192.168.141.253   | 192.168.139.141    |
| ABD  | 192.168.224.0/24    | 192.168.224.253   | 192.168.139.224    |
| CLD  | 192.168.139.0/24    | 192.168.139.253   | 192.168.139.139    |

CLD's own subnet **is** the provisioning network, so its firewall WAN address (`.139`) is unusual but consistent — and is included in the `139` reverse zone.
