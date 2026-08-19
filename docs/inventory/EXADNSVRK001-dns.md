# EXADNSVRK001 — DNS Server Operations Guide

**Hostname:** `exadnsvrk001.jukebox.internal`
**Role:** Authoritative DNS — `jukebox.internal`
**OS:** Debian trixie
**IP:** `192.168.139.8/24` (the vRACK, site code `VRK` — not `CLD`, which is CLD's own separate LAN)
**Provisioned by:** `playbooks/bind9/bind9-dns.yml` (Ansible — mirrors `bindme.sh` exactly, packages through service). `bindme.sh` is the break-glass fallback for when Ansible can't reach the box yet (dead/replaced DNS server, or the very first build at a brand-new site with no Ansible control node reachable at all).

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

EXADNSVRK001 is the authoritative DNS server for the `jukebox.internal` private zone. It runs BIND9 on Debian trixie and sits on the provisioning network (`192.168.139.0/24`).

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
| `.253` | EXAFWL   | `exafwlgla001-lan.jukebox.internal` |

CLD is a special case: suffix `.48` resolves to `exapbxcld001` (PBX), not `exasbc`.

> **Correction (2026-07-26):** the `.253` row above used to be the bare `exafwlgla001` name.
> Robert, live: `host exafwlams001` returned `.253` (LAN) when Ansible's own inventory has meant
> the VRK/provisioning address (`192.168.139.{octet}`) under that exact bare hostname since
> 2026-07-16 — DNS and the `.ini` generator had silently diverged on what the bare name means.
> Fixed by making DNS match Ansible's convention: **bare `exafwl<site>001` is now the VRK/WAN
> address** (see the row below), and the old bare-meant-LAN record moved to its own `-lan`
> suffix, mirroring the existing `-wan` naming (kept, now redundant with bare but harmless). See
> `benarbejde/generate_inventory.py`'s own changelog for the full detail.

The forward zone also contains **firewall WAN addresses** — see [Section 9](#9-how-the-addressing-scheme-works) — and the provisioning ancillary hosts:

> **Correction (2026-07-10):** this table previously put every host below on `192.168.139.x` (vRACK). Only
> `EXADNSVRK001` actually lives there (the provisioning server does too, but has no formal hostname —
> see the 2026-07-21 correction below) — `EXAANSCLD001`, `EXASVRCLD002`, `EXARUDCLD001`,
> and `EXAPBXCLD001` are all on `192.168.69.x` (CLD LAN), per `benarbejde/begyndelse.json`. The old
> `exasvrcld003`/`exasvrcld004` names were also wrong — the real hostnames are `EXAANSCLD001` (Ansible) and
> `EXARUDCLD001` (Rudder).
>
> **Correction (2026-07-21):** `exaprvvrk001.jukebox.internal` (below) no longer exists as a DNS
> record at all — the provisioning server is a bootstrap-only helper, deliberately given no formal
> `EXA<ROLE><SITE><NNN>` hostname or DNS record any more. It's still real, still at `192.168.139.50`,
> just referenced by IP only now (see `benarbejde/begyndelse.json`'s `provisioning_edinburgh`).

| Name                               | IP               | Purpose                   |
|------------------------------------|------------------|---------------------------|
| `exadnsvrk001.jukebox.internal`    | `192.168.139.8`  | DNS/BIND server (this host), vRACK      |
| — (no DNS record — IP only)        | `192.168.139.50` | Provisioning / PXE server, vRACK, bootstrap-only |
| `exaanscld001.jukebox.internal`    | `192.168.69.9`   | Ansible control node, CLD LAN           |
| `exasvrcld002.jukebox.internal`    | `192.168.69.20`  | Windows Admin Centre, CLD LAN           |
| `exarudcld001.jukebox.internal`    | `192.168.69.12`  | Rudder configuration management (dormant — not in active use, kept as reference code only), CLD LAN |
| `exapbxcld001.jukebox.internal`    | `192.168.69.48`  | Central 3CX PBX, CLD LAN                |
| `exafwl{site}001.jukebox.internal` | `192.168.139.{octet}` | Each site's FWL WAN/provisioning face — canonical bare name since 2026-07-26, matches Ansible's own inventory; `exafwl{site}001-wan` also still resolves to the same address (kept for compatibility) |

### Reverse zone — provisioning network

File: `/etc/bind/db.192.168.139`
Zone: `139.168.192.in-addr.arpa`

This is a **dedicated, hand-built zone** — it is not produced by the per-site loop.
It contains:

- PTR records for the two ancillary hosts (`.8`, `.69`) — the provisioning server (`.50`) has no
  PTR record, bootstrap-only, IP-referenced only (2026-07-21)
- PTR records for every site firewall's WAN address on the provisioning network
  (`192.168.139.{octet}` → `exafwl{site}001.jukebox.internal.` — bare name since 2026-07-26)

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
sudo editzone
```

This opens `vim /etc/bind/db.jukebox.internal`, then on write/quit runs `named-checkzone` and `rndc reload` automatically. If the check fails, the reload does not happen. `editzone` writes to `/etc/bind/`, so it must be run with `sudo` — it's a real script at `/usr/local/bin/editzone`, not a shell alias, so (unlike an alias) `sudo editzone` actually works.

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
2. From the Ansible control node, regenerate zones the normal way:

   ```
   ansible-playbook -i configs/inventory playbooks/bind9/bind9-dns.yml --tags zones-full,reload
   ```

   (`zones-full`, not `zones` — that's the tag that actually reads `devices.csv`; see `bind9-dns.yml`'s
   own header comment.)

   **`regen-zone.sh` is *not* the same as the command above, despite living on the same box —
   don't use it as a shortcut.** It calls `bindme.sh --zone-only`, and `bindme.sh`'s zone
   generation is `sites.csv` + a hardcoded `SUFFIX_MAP` only — it never reads `devices.csv` at
   all. Concretely: `bindme.sh` still hardcodes the pre-2026-07-20 Rudder hostname
   `exardrcld001`, where the real canonical name (used everywhere else, including the Ancillary
   Hosts table below) is `exarudcld001`. Regenerating via `regen-zone.sh` produces the *same*
   result as the plain `zones` tag, not `zones-full` — it will silently drop any `devices.csv`
   exception and can reintroduce stale hostnames. Use it only as the break-glass fallback
   `bindme.sh` itself is for — when Ansible genuinely can't reach this box — not as a
   SSH-shortcut for a routine `zones-full` regen.
   
3. Confirm the new records are visible:

   ```
   dig @192.168.139.8 exafwl{SITE}001.jukebox.internal
   ```

Do **not** edit the generated sections of the zone file by hand — your changes will be overwritten on the next regeneration. Use the one-off section at the bottom for anything not covered by the standard SUFFIX_MAP (see Section 5).

---

## 5. Adding a One-Off Record

For hosts that are not in the SUFFIX_MAP (specialist devices, temporary VMs, extra management addresses, etc.) add records at the **bottom** of the zone file, below the generated block. The section is labelled clearly in the file.

```
sudo editzone
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

Then save, let `sudo editzone` check and reload, or run `checkbind` then `reloadbind`.

> **Important:** `bindme.sh` and `regen-zone.sh` overwrite the zone file completely. Back up your one-off records before re-running either script. The bottom of the file has a clearly marked one-off section — keep records there and note them somewhere safe (e.g. a comment in `sites.csv` or a brief note in this doc).

---

## 6. Commands Quick Reference

`reloadbind`/`checkbind`/`editzone` are real scripts at `/usr/local/bin/` (world-executable
except `editzone`, which is root-only) — **not** shell aliases, specifically so `sudo editzone`
actually works (shell aliases/functions are invisible to `sudo`, which execs a fresh,
non-interactive process rather than sourcing any shell rc file — found the hard way live on this
exact host, 2026-07-21). `bindstatus`/`bindlog` are still plain aliases, sourced from
`/etc/profile.d/bind-aliases.sh` and embedded in `.zshrc` for both `root` and `ansible` — they're
trivial one-liners with no root requirement, so the sudo problem never applied to them.

| Command       | What it does                                              | Needs `sudo`? |
|---------------|-------------------------------------------------------------|:---:|
| `reloadbind`  | `rndc reload jukebox.internal` — live zone reload         | No |
| `checkbind`   | `named-checkzone` — syntax check, no reload               | No |
| `editzone`    | `vim` + check + reload in one step                        | **Yes** |
| `bindstatus`  | `systemctl status named`                                  | No |
| `bindlog`     | `journalctl -u named -f` — follow the BIND log            | No |

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
sudo editzone
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
| CLD  | 192.168.69.0/24     | 192.168.69.253    | 192.168.139.69     |

**CLD is the one exception to the formula above.** Its firewall's WAN address is `192.168.139.69` — the real, fixed address of `EXAFWLVRK001`, not a derivation of CLD's own LAN octet (`69`). Those two numbers happen to match, which made this an easy mistake to make (and was, in fact, wrong in several places in this repo until 2026-07-08) — but the WAN address is looked up from devices.csv, never computed from CLD's own subnet the way every other site's is.
