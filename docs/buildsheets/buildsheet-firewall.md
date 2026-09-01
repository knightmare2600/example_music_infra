# Buildsheet — Firewall / Router (EXAFWL\*001)

**Doc ID:** NET-BUILD-FWL-001  
**Last Updated:** 2026-09-01  
**Applies to:** All site firewall/router VMs — CLD is the sole WireGuard hub; every other site, including FAL/ODE/BRK, is an ordinary spoke  
**Playbook (first-ever run, box still on its DHCP provisioning IP):** `ansible-playbook -i configs/inventory -e target=<host> -e ansible_host=<current-DHCP-IP> playbooks/firewallme/playbooks/90-firewall.yml --ask-vault-pass`  
**Playbook (subsequent runs, box already on its permanent static IP):** `ansible-playbook -i configs/inventory playbooks/firewallme/playbooks/90-firewall.yml -e target=<host> --ask-vault-pass`  
See Step 3a below for the full detail — proven live end-to-end against `EXAFWLATL001` on 2026-09-01, `failed=0`.  
**Break-glass script:** `firewallme.sh` — hosted on bootstrap server at `http://192.168.139.50/provision/firewallme.sh`. Kept for when Ansible genuinely can't reach the box (dead/replaced firewall, or the very first firewall at a brand-new site with no Ansible control node reachable at all). Steps 4 onward below document this path — see `ansible/playbooks/firewallme/` for the normal one.  
**Cross-reference:** `active-directory/ad-dc-wireguard-deployment.md` (NET-AD-DC-001, historical — see `ansible/playbooks/windows_dc/README.md` for the live procedure) · `buildsheet-pve.md` (NET-BUILD-PVE-001)

> ⚠️ **Build the hub before spokes.** CLD (`EXAFWLVRK001`/`EXAFWLCLD001`) must be fully live
> before any spoke can establish its WireGuard tunnel — every spoke connects directly to CLD,
> full stop, regional hubs (FAL/ODE/BRK) were retired 2026-07-17.  
> Order: **CLD → all spokes, any order** (FAL/ODE/BRK included — see the "WireGuard topology"
> section of `ansible/README.md` for the full detail and `docs/ansible/beginners_guide_to_ansible.md`'s
> "Bootstrapping the Base Nodes" for a worked walkthrough)

> **Fredericia Havn note:** `192.168.139.50` below is Edinburgh's bootstrap server. If you're
> building at Fredericia Havn instead, it's `172.16.124.1:8000` (gateway `172.16.124.2`) — see
> `docs/bootstrap/bootstrapping.md` §4.1a. `late_command.sh`/`firewallme.sh` detect this
> automatically; only matters if you're fetching something by hand (as below).

---

## Architecture Overview

```mermaid
graph TD
    WAN["🌐 WAN / Provisioning<br/>192.168.139.0/24<br/> bootstrap: 192.168.139.50"]

    CLD["☁️ CLD — Cloud / Edinburgh<br/>sole WireGuard hub<br/>192.168.69.0/24 · wg: 10.0.69.1"]

    WAN --> CLD

    subgraph UK ["🇬🇧 United Kingdom"]
        direction TB
        FAL["FAL · Falkirk · .76"]
        EDI["EDI · Edinburgh · .131"]
        GLA["GLA · Glasgow · .141"]
        CLY["CLY · Clydebank · .41"]
        DUN["DUN · Dundee · .138"]
        PER["PER · Perth · .173"]
        ABD["ABD · Aberdeen · .224"]
        LND["LND · London · .20"]
        MCR["MCR · Manchester · .161"]
        BIR["BIR · Birmingham · .121"]
        LIV["LIV · Liverpool · .151"]
        NEW["NEW · Newcastle · .191"]
        SHE["SHE · Sheffield · .114"]
        HUL["HUL · Hull · .148"]
        COV["COV · Coventry · .247"]
        HAL["HAL · Halifax · .142"]
    end

    subgraph EU ["🇪🇺 Europe"]
        direction TB
        ODE["ODE · Odense · .126"]
        CPH["CPH · København · .231"]
        KGE["KGE · Køge · .65"]
        FAX["FAX · Faxe · .246"]
        KOR["KOR · Korsør · .238"]
        BON["BON · Bonn · .228"]
        BER["BER · Berlin · .113"]
        MUN["MUN · Munich · .189"]
        GOT["GOT · Gothenburg · .46"]
        OSL["OSL · Oslo · .47"]
        AMS["AMS · Amsterdam · .31"]
        MIL["MIL · Milan · .39"]
        VIE["VIE · Vienna · .78"]
    end

    subgraph NAAPAC ["🌎 Americas & APAC"]
        direction TB
        BRK["BRK · Brockville · .136"]
        TOR["TOR · Toronto · .146"]
        MTL["MTL · Montréal · .154"]
        NYC["NYC · New York · .212"]
        LAX["LAX · Los Angeles · .213"]
        MIA["MIA · Miami · .135 ⚠️"]
        NJC["NJC · New Jersey · .201"]
        CHI["CHI · Chicago · .214"]
        ATL["ATL · Atlanta · .33"]
        SYD["SYD · Sydney · .29"]
        MEL["MEL · Melbourne · .61"]
        AKL["AKL · Auckland · .93"]
    end

    CLD --> UK
    CLD --> EU
    CLD --> NAAPAC

    classDef hub fill:#0072B2,stroke:#000000,color:#ffffff
    classDef warn fill:#D55E00,stroke:#000000,color:#ffffff
    class WAN,CLD hub
    class MIA warn
    style UK fill:#56B4E9,stroke:#0072B2,color:#000000
    style EU fill:#F0E442,stroke:#E69F00,color:#000000
    style NAAPAC fill:#009E73,stroke:#000000,color:#ffffff
```

> Every site connects directly to CLD — including FAL/ODE/BRK, shown grouped by region above
> for readability only, not because they intermediate for anyone. There is no hub-to-hub mesh
> and no regional hub any more (retired 2026-07-17); FAL/ODE/BRK remain real **AD/DFS hubs**
> for their regions (see `docs/ExampleMusic_Beginners_Guide.md`), just not WireGuard ones.

---

## VM Specifications

| Parameter | Value |
|-----------|-------|
| vCPU | 1–2 |
| RAM | 512 MB |
| Disk | 5 GB (LVM, expandable) |
| NIC 1 (WAN) | Proxmox bridge connected to uplink / WAN vSwitch |
| NIC 2 (LAN) | Proxmox bridge connected to site LAN vSwitch |
| OS | Debian 13 (Trixie) — installed via iPXE/preseed |
| PVE node | Site PVE node (`.5` — or `.6`/`.7` at hub sites) |

> On VMware Fusion (ARM64 lab/test) use Host-Only for LAN, Bridged for WAN. Memory/CPU same.

---

## Step 1 — Create the VM on Proxmox

Use `create-vm.py` from DeployTools to provision the VM:

```bash
# From the PVE node or a machine with API access:
python3 create-vm.py --host 192.168.76.5 --user root@pam
```

Follow the interactive prompts. Suggested settings:

| Field | Value |
|-------|-------|
| VM name | `EXAFWL<SITE>001` (e.g. `EXAFWLEDI001`) |
| Memory | 512 MB |
| CPU | 1 socket, 2 cores |
| Disk | 5 GB, `zfs` or `local-lvm` |
| NIC 1 | `vmbr0` (WAN / uplink bridge) |
| NIC 2 | `vmbr1` (LAN bridge) |
| Boot order | CD-ROM first |

> If provisioning the **first VM at a new site** with no existing PVE node, boot the Debian ISO directly from the Proxmox web UI or attach via IPMI/RAC before WireGuard is up.

---

## Step 2 — Boot and Install Debian via iPXE

The Debian installer is served from the bootstrap server (`192.168.139.50`) using iPXE + preseed.

**2a. Boot the VM.** When the iPXE prompt appears:

```
dhcp net0
chain http://192.168.139.50/menu.ipxe
```

> If DHCP is already configured to serve the iPXE chain, this happens automatically.

**2b. The iPXE menu appears.** Select **Debian Install** (or equivalent entry in `menu.ipxe`).

**2c. The installer runs unattended using `lvm-bios.seed`/`lvm-efi.seed`** (picked automatically by architecture — see `menu.ipxe` §4.1a in `docs/bootstrap/bootstrapping.md`). You will be prompted for:

| Prompt | Value |
|--------|-------|
| Hostname | `EXAFWL<SITE>001` — e.g. `EXAFWLEDI001` |
| Ansible user password | See password manager — **change immediately after first boot** |

The installer will then proceed automatically. Watch the bootstrap server console — you will see HTTP requests for `lvm.seed`, `late_command.sh`, and `ansible_sshkey.pub` as the install progresses.

**What `lvm.seed` configures automatically:**
- GB locale and keyboard
- Debian mirror: `ftp.uk.debian.org`
- LVM partitioning: `/boot` (ext3, 384MB) + swap (512MB LV) + `/` (ext4, 5GB LV, expandable)
- VG name = hostname
- Packages: `vim tmux openssh-server net-tools tofrodos tree sudo zsh zsh-autosuggestions zsh-syntax-highlighting`
- Unattended security updates enabled
- Calls `late_command.sh` at the end

**What `late_command.sh` does:**
- Forces LVM modules into initramfs (ensures LVM is accessible at boot)
- Adds `ansible` user to `sudo`
- Installs `openssh-server`, `sudo`, `net-tools`, `bash-completion`
- Fetches `begyndelse.json` (well-known service addresses) to `/etc/example-music/` — the one file no Ansible playbook ever deploys, so this is its only source before Ansible manages the box. `sites.csv`/`devices.csv` are **not** fetched here as of v1.6 — `ansible/playbooks/linux/tools.yml` deploys both once the node is under Ansible management, and the break-glass scripts' own documented path is a manual wget anyway
- Fetches `ansible_sshkey.pub` from `http://192.168.139.50/` and places it in `/home/ansible/.ssh/authorized_keys`
- Sets up `.vimrc` (ruler, dark background, syntax hilighting)
- Configures password-less sudo for the `ansible` user via `/etc/sudoers.d/ansible`

**2d. On first reboot:** the VM comes up with Debian installed, `ansible` user present, SSH key auth ready.

---

## Step 3 — Change the Ansible User Password

```bash
ssh ansible@<VM-IP>
passwd
```

> ⚠️ The default password set during preseed install **must be changed immediately**. See password manager for the current default and the required new credential pattern.

---

## Step 3a — Run the Ansible Playbook (normal path — preferred over Step 4)

This is the normal onboarding path — use it unless Ansible genuinely can't reach the box (see
Step 4 for that break-glass case instead). Proven live end-to-end against a genuinely fresh
`EXAFWLATL001` on 2026-09-01 (`ok=195 changed=60 skipped=78 failed=0`).

**The box is still on its DHCP provisioning IP at this point** — same DHCP-first-then-static
pattern every fresh node in this estate follows (see `docs/bootstrap/bootstrapping.md`'s Proxmox
worked example for the equivalent walkthrough). Its hostname is already set correctly by preseed
(`EXAFWL<SITE>001`), but the inventory's `ansible_host` for that host is its future **static**
IP, which isn't live yet — connecting needs an explicit override to the box's *current* DHCP
address for this one run only:

```bash
ansible-playbook -i configs/inventory \
  -e target=EXAFWL<SITE>001 \
  -e ansible_host=<current-DHCP-IP> \
  playbooks/firewallme/playbooks/90-firewall.yml \
  --ask-vault-pass
```

`-e ansible_host=` always wins over the inventory file's own `ansible_host=` for that one run,
without needing to edit the inventory just to reach a temporary address.

**Before running this against a genuinely fresh box for the first time ever**, make sure the
control node's own `/etc/example-music/*` is current — an early preflight play checks this
automatically (before any interactive prompts) and fails with the exact fix command if it's
stale, but if you already know it needs a refresh, run this first:

```bash
ansible-playbook ansible/playbooks/linux/tools.yml --limit EXAANSCLD001
```

**What to expect interactively:** site code, environment, WAN/LAN interface, WAN mode
(`(d)hcp`/`(s)tatic`, single letter), WAN SSH, WireGuard role, and a final confirm-before-apply
summary — same prompts `firewallme.sh` asks (see Step 4's table below), just as Ansible
`pause` prompts instead of a bash script. Answer `spoke` for WireGuard role at any site other
than CLD (CLD is forced to hub automatically). **Say no to WAN activation** if you're connected
over the WAN interface yourself right now — the play writes every config regardless and defers
bringing WAN up live to avoid dropping your own session; bring it up afterwards with
`nmcli con up wan`, or just reboot (recommended anyway — the final prompt offers this).

**Once the box is on its permanent static IP** (after that reboot), every later run against the
same host drops the `ansible_host=` override entirely and just uses the inventory as normal:

```bash
ansible-playbook -i configs/inventory playbooks/firewallme/playbooks/90-firewall.yml -e target=EXAFWL<SITE>001 --ask-vault-pass
```

---

## Step 4 — Run `firewallme.sh` (break-glass path)

> This step and the ones after it are the **break-glass** path — use them when Ansible can't
> reach the box yet. In the normal case, skip straight to running the Ansible playbook (see the
> header above) instead of any of this.

`firewallme.sh` configures NAT, DHCP/DNS, WireGuard, Cockpit, SSH banner, and dynamic MOTD.

```bash
wget http://192.168.139.50/provision/firewallme.sh
tofrodos firewallme.sh
chmod 755 firewallme.sh
sudo ./firewallme.sh
```

The script is interactive. It will prompt for the following — answers for each site are in the network inventory (`network-inventory.md`):

| Prompt | Notes |
|--------|-------|
| WAN interface | Auto-detected from `192.168.139.x` DHCP lease — confirm or override |
| LAN interface | Remaining interface — confirm |
| Site code | e.g. `EDI`, `CPH`, `BRK` — auto-fills subnet, city, entity |
| LAN IP suffix | `1` (primary gateway) or `253` (secondary) — see network inventory |
| Ansible/PXE last octet | `15` (standard) |
| Internal DNS IP | Last octet of DC primary — e.g. `10` → `192.168.x.10` — leave blank if DC not yet built |
| WAN SSH | `N` unless remote access required — if yes, restrict to source IP |
| WireGuard role | `hub-primary` · `hub-regional` · `spoke` · `none` — see the warning below |

> ⚠️ **This break-glass script itself still offers all four role choices unrestricted — it
> hasn't been touched since the regional hubs were retired.** The Ansible role
> (`90-firewall.yml`) *has* been restricted: it only offers `spoke`/`none` for any site except
> CLD, which is forced to the hub role automatically. Answering `hub-primary`/`hub-regional`
> here for anything other than CLD will build a real, functioning hub that nothing else in the
> estate expects or talks to — always answer `spoke` unless you are genuinely building CLD's
> own firewall from this break-glass path.

**WireGuard role-specific prompts:**

*Hub-primary / hub-regional:*
- Tunnel IP (default: `10.0.<octet>.1`)
- Listen port (default: `51820`)
- For hub-regional: FAL endpoint and public key (fetched automatically via SSH, or paste manually)
- Add spoke peers interactively, or skip and edit `/etc/wireguard/wg0.conf` later

*Spoke:*
- Tunnel IP (default: `10.0.<octet>.1`)
- Hub site code (e.g. `FAL`, `ODE`, `BRK`) — endpoint and public key auto-fetched or pasted
- Optional backup hub peers

> **Hub key auto-fetch:** The script will attempt `ssh ansible@<hub-ip> 'cat /etc/wireguard/public.key'` automatically. If SSH fails (hub not yet reachable or key not accepted), it falls back to manual paste. The hub's public key is always saved at `/etc/wireguard/public.key`.

**What `firewallme.sh` configures:**
- Installs all required packages (NM, nftables, dnsmasq, WireGuard, Cockpit, grc, tmux, zsh, etc.)
- Cockpit Navigator file manager plugin
- Strips unused locales, generates lean initramfs (blacklists audio/GPU/WiFi/BT modules)
- Sets up zsh + prompt for `ansible` and `root`
- Pins interface names by MAC via systemd `.link` files (survives reboots and PCI bus shuffles)
- Creates NetworkManager WAN (DHCP) and LAN (static) profiles
- Enables IP forwarding
- Configures nftables: NAT/masquerade, FORWARD, INPUT (SSH, Cockpit, DNS, DHCP, TFTP, HTTP on LAN; WireGuard on WAN for hubs)
- Configures dnsmasq: DHCP range `.150`–`.250`, upstream DNS, iPXE vendor class tagging, local DNS records (`ansible.jukebox.internal` + CNAMEs)
- Binds Cockpit socket to LAN IP only
- Generates and starts WireGuard (`wg-quick@wg0`)
- Configures SSH login banner (entity, site, hostname)
- Configures dynamic MOTD (ASCII art, WireGuard peer status, system stats)
- Writes sentinel file `/etc/.i_am_a_firewall` (prevents re-runs)
- Prompts to reboot

---

## Step 5 — Reboot

The script prompts to reboot. **Say yes.** This ensures:
- systemd `.link` files take effect (interface name pinning)
- NM profiles load cleanly
- WireGuard starts via `wg-quick@wg0.service`
- Cockpit socket binds to LAN correctly

---

## Step 6 — Add This Site as a Peer on the Hub (Spokes Only)

After the spoke reboots, the script will have printed a peer stanza. Copy it to the hub:

```
# <SITE>
[Peer]
PublicKey = <spoke-public-key>
Endpoint = <spoke-WAN-IP>:51820
AllowedIPs = 10.0.<octet>.0/24, 192.168.<octet>.0/24
PersistentKeepalive = 25
```

On the hub, append this to `/etc/wireguard/wg0.conf` and apply live:

```bash
sudo bash -c 'wg setconf wg0 <(wg-quick strip /etc/wireguard/wg0.conf)'
sudo wg show
```

The spoke's public key is always retrievable at:
```bash
sudo cat /etc/wireguard/public.key
# or derive from private key:
sudo cat /etc/wireguard/private.key | wg pubkey
```

---

## Step 7 — Verify

```bash
# On the spoke — check tunnel is up and hub handshake received
sudo wg show

# Ping the hub tunnel IP — CLD is the only hub, every spoke pings the same address
ping -c 3 10.0.69.1        # CLD

# Ping hub LAN
ping -c 3 192.168.69.10    # CLD's own DC (EXADCSCLD001)

# Check dnsmasq is serving DHCP/DNS
dig ansible.jukebox.internal @192.168.<site-octet>.1

# Check Cockpit
curl -k https://192.168.<site-octet>.<1 or 253>:9090

# Useful diagnostics
sudo tcpdump -i <WAN-iface> udp port 51820 -n   # WireGuard traffic
sudo nft list ruleset                             # firewall rules
sudo journalctl -u wg-quick@wg0 -n 50           # WG service log
sudo journalctl -u dnsmasq -n 50                 # DHCP/DNS log
```

**Fix subnet if AllowedIPs was set to /32 instead of /24:**
```bash
sudo sed -i 's/AllowedIPs = 10.0.<octet>.0\/32/AllowedIPs = 10.0.<octet>.0\/24/' /etc/wireguard/wg0.conf
sudo bash -c 'wg setconf wg0 <(wg-quick strip /etc/wireguard/wg0.conf)'
```

---

## Step 8 — Add to Ansible Inventory

Once the firewall is up and reachable, add it to the Ansible inventory on `EXAANSCLD001` (the Ansible control node, `192.168.69.9`). `EXASVRCLD002` is the Windows Admin Centre node, not the Ansible control node — see `benarbejde/begyndelse.json`.

---

## Useful Post-Build Commands

```bash
# Live WireGuard reload without reboot
sudo bash -c 'wg setconf wg0 <(wg-quick strip /etc/wireguard/wg0.conf)'

# View WireGuard status (peers, handshakes, traffic)
sudo wg show

# Verify traffic on WAN
sudo tcpdump -i <WAN-iface> udp port 51820 -n

# View nftables ruleset
sudo nft list ruleset

# Reload nftables rules
sudo nft -f /etc/nftables.conf

# dnsmasq status
sudo systemctl status dnsmasq
sudo journalctl -u dnsmasq -f

# Cockpit
https://192.168.<octet>.<1 or 253>:9090

# Sentinel file (shows build config)
cat /etc/.i_am_a_firewall
```

---

## Build Checklist

> One row per site. Tick left to right.  
>
> **Columns:**
> `VM` 	`VM created on PVE`
> `OS`	`Debian installed via iPXE`
> `PW`	`ansible password changed`
> `FW`	`firewallme.sh run`
> `RB`	`rebooted`
> `WG`	`WireGuard tunnel up`
> `PR`	`Peer stanza added to hub`
> `VF`	`verified (ping + DNS + Cockpit)`
> `AN`	`added to Ansible inventory`
> `OK`	`engineer sign-off`



### Cloud / Provisioning (build these first)

| Site | Hostname     | IP              | Role        | VM   | OS   | PW   | FW   | RB   | WG   | PR   | VF   | AN   | OK   | Notes                         |
| ---- | ------------ | --------------- | ----------- | ---- | ---- | ---- | ---- | ---- | ---- | ---- | ---- | ---- | ---- | ----------------------------- |
| CLD  | EXAFWLVRK001 | 192.168.69.253 (CLD LAN) / 192.168.139.69 (vRACK) | Cloud Infra | X    | X    | X    | X    | X    | X    | N/A  | X    |      |      | Hosted at OVH. Two internal interfaces, not one — see bootstrapping.md §1.2 |
| PRV  | EXAFWLPRV001 | 192.168.139.253 | Cloud twin  | X    | X    | X    | X    | X    | X    | X    | X    |      |      | Legal fiction. Does not exist |

### Scotland

> **FAL** (Falkirk) is included here now, not in a separate "Hubs" section — it's an ordinary
> CLD spoke since regional hubs were retired 2026-07-17. Still the UK AD/DFS hub, just not a
> WireGuard one. Its `WG`/`PR`/`VF` columns are cleared rather than carrying over pre-migration
> ticks: a firewall already live before the retirement was **not** automatically re-pointed at
> CLD (that's a real, live per-node operation, not a data-file edit — see
> `group_vars/firewalls/main.yml`'s own changelog) — verify/redo these live before ticking them.

| Site | Hostname | IP | VM | OS | PW | FW | RB | WG | PR | VF | AN | OK | Notes |
|------|----------|----|----|----|----|----|----|----|----|----|----|----|----|
| ABD | EXAFWLABD001 | 192.168.224.253 |      |      |      |      |      |      |      |      |      |      | |
| CLY | EXAFWLCLY001 | 192.168.41.253 |      |      |      |      |      |      |      |      |      |      | |
| DUN | EXAFWLDUN001 | 192.168.138.253 |      |      |      |      |      |      |      |      |      |      | |
| EDI | EXAFWLEDI001 | 192.168.131.253 |      |      |      |      |      |      |      |      |      |      | |
| FAL | EXAFWLFAL001 | 192.168.76.253 | X | X | X | X | X | ⚠️ | ⚠️ | ⚠️ |      |      | Head Office — formerly UK regional hub, now an ordinary CLD spoke; see note above |
| GLA | EXAFWLGLA001 | 192.168.141.253 |      |      |      |      |      |      |      |      |      |      | |
| PER | EXAFWLPER001 | 192.168.173.253 |      |      |      |      |      |      |      |      |      |      | |

### England

| Site | Hostname | IP | VM | OS | PW | FW | RB | WG | PR | VF | AN | OK | Notes |
|------|----------|----|----|----|----|----|----|----|----|----|----|----|----|
| BIR | EXAFWLBIR001 | 192.168.121.253 |      |      |      |      |      |      |      |      |      |      | |
| COV | EXAFWLCOV001 | 192.168.247.253 |      |      |      |      |      |      |      |      |      |      | |
| HUL | EXAFWLHUL001 | 192.168.148.253 |      |      |      |      |      |      |      |      |      |      | |
| HAL | EXAFWLHAL001 | 192.168.142.253 |      |      |      |      |      |      |      |      |      |      | |
| LIV | EXAFWLLIV001 | 192.168.151.253 |      |      |      |      |      |      |      |      |      |      | |
| LND | EXAFWLLND001 | 192.168.20.253 |      |      |      |      |      |      |      |      |      |      | |
| MCR | EXAFWLMCR001 | 192.168.161.253 |      |      |      |      |      |      |      |      |      |      | |
| NEW | EXAFWLNEW001 | 192.168.191.253 |      |      |      |      |      |      |      |      |      |      | |
| SHE | EXAFWLSHE001 | 192.168.114.253 |      |      |      |      |      |      |      |      |      |      | |

### Danmark

| Site | Hostname | IP | VM | OS | PW | FW | RB | WG | PR | VF | AN | OK | Notes |
|------|----------|----|----|----|----|----|----|----|----|----|----|----|----|
| CPH | EXAFWLCPH001 | 192.168.231.253 |      |      |      |      |      |      |      |      |      |      | DeployTools host site |
| FAX | EXAFWLFAX001 | 192.168.246.253 |      |      |      |      |      |      |      |      |      |      | |
| KGE | EXAFWLKGE001 | 192.168.65.253 |      |      |      |      |      |      |      |      |      |      | |
| KOR | EXAFWLKOR001 | 192.168.238.253 |      |      |      |      |      |      |      |      |      |      | |
| ODE | EXAFWLODE001 | 192.168.126.253 | X | X | X | X | X | ⚠️ | ⚠️ | ⚠️ |      |      | EU Head Office — formerly EU regional hub, now an ordinary CLD spoke; see Scotland section's note on FAL for why `WG`/`PR`/`VF` are cleared, not carried over |

### Deutschland

| Site | Hostname | IP | VM | OS | PW | FW | RB | WG | PR | VF | AN | OK | Notes |
|------|----------|----|----|----|----|----|----|----|----|----|----|----|----|
| BER | EXAFWLBER001 | 192.168.113.253 |      |      |      |      |      |      |      |      |      |      | |
| BON | EXAFWLBON001 | 192.168.228.253 |      |      |      |      |      |      |      |      |      |      | |
| MUN | EXAFWLMUN001 | 192.168.189.253 |      |      |      |      |      |      |      |      |      |      | |

### Sverige / Norge / Nederland / Italia / Österreich

| Site | Hostname | IP | VM | OS | PW | FW | RB | WG | PR | VF | AN | OK | Notes |
|------|----------|----|----|----|----|----|----|----|----|----|----|----|----|
| AMS | EXAFWLAMS001 | 192.168.31.253 |      |      |      |      |      |      |      |      |      |      | Amsterdam |
| GOT | EXAFWLGOT001 | 192.168.46.253 |      |      |      |      |      |      |      |      |      |      | Gothenburg |
| MIL | EXAFWLMIL001 | 192.168.39.253 |      |      |      |      |      |      |      |      |      |      | Milan |
| OSL | EXAFWLOSL001 | 192.168.47.253 |      |      |      |      |      |      |      |      |      |      | Oslo |
| VIE | EXAFWLVIE001 | 192.168.78.253 |      |      |      |      |      |      |      |      |      |      | Vienna |

### Canada

| Site | Hostname | IP | VM | OS | PW | FW | RB | WG | PR | VF | AN | OK | Notes |
|------|----------|----|----|----|----|----|----|----|----|----|----|----|----|
| BRK | EXAFWLBRK001 | 192.168.136.253 |      |      |      |      |      |      |      |      |      |      | NA/APAC Head Office — formerly NA/APAC regional hub, retired 2026-07-17, never actually built (no ticks in the old Hubs table either) — build as an ordinary CLD spoke |
| MTL | EXAFWLMTL001 | 192.168.154.253 |      |      |      |      |      |      |      |      |      |      | Montréal |
| TOR | EXAFWLTOR001 | 192.168.146.253 |      |      |      |      |      |      |      |      |      |      | Toronto |

### USA

| Site | Hostname | IP | VM | OS | PW | FW | RB | WG | PR | VF | AN | OK | Notes |
|------|----------|----|----|----|----|----|----|----|----|----|----|----|----|
| ATL | EXAFWLATL001 | 192.168.33.253 |      |      |      |      |      |      |      |      |      |      | Atlanta |
| CHI | EXAFWLCHI001 | 192.168.214.253 |      |      |      |      |      |      |      |      |      |      | Chicago |
| LAX | EXAFWLLAX001 | 192.168.213.253 |      |      |      |      |      |      |      |      |      |      | Los Angeles |
| MIA | EXAFWLMIA001 | 192.168.135.253 |      |      |      |      |      |      |      |      |      |      | Miami — PENDING BUILD |
| NJC | EXAFWLNJC001 | 192.168.201.253 |      |      |      |      |      |      |      |      |      |      | New Jersey |
| NYC | EXAFWLNYC001 | 192.168.212.253 |      |      |      |      |      |      |      |      |      |      | New York |

### Australia / New Zealand

| Site | Hostname | IP | VM | OS | PW | FW | RB | WG | PR | VF | AN | OK | Notes |
|------|----------|----|----|----|----|----|----|----|----|----|----|----|----|
| AKL | EXAFWLAKL001 | 192.168.93.253 |      |      |      |      |      |      |      |      |      |      | Auckland |
| MEL | EXAFWLMEL001 | 192.168.61.253 |      |      |      |      |      |      |      |      |      |      | Melbourne |
| SYD | EXAFWLSYD001 | 192.168.29.253 |      |      |      |      |      |      |      |      |      |      | Sydney |

---

## Sign-Off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Build engineer | | | |
| Network lead | | | |
| Operations manager | | | |

---

## Appendix — Bootstrap Server Contents Reference

> **Corrected 2026-07-11** — this table previously described a `phoenixpe/` directory and other
> files that don't exist anywhere in the real `bootstrap/web/` tree (the same fictional layout
> already found and corrected in `docs/bootstrap/bootstrapping.md` §2.3). Replaced with the real,
> current top-level layout.

The bootstrap server at `192.168.139.50` (Edinburgh — or `172.16.124.1:8000` at Fredericia Havn,
see `docs/bootstrap/bootstrapping.md` §4.1a) serves:

| File / directory | Purpose |
|------|---------|
| `bootstrap.ipxe` | Embedded iPXE boot script (compiled into the iPXE binary) |
| `menu.ipxe` | Full iPXE boot menu — OS install + rescue options, gateway-based datacentre detection |
| `boot.ipxe`, `lvm.seed` | **Stale/superseded** — pre-rename leftovers, not part of the real boot chain (see each file's own 2026-07-11 note). Don't chain to `boot.ipxe`; use `menu.ipxe`. |
| `debian/lvm-bios.seed`, `debian/lvm-efi.seed` | Debian preseed (arch-specific) — partitioning, locale, packages, late_command |
| `debian/late_command.sh` | Post-install chroot script — ansible user, SSH key, sudoers |
| `ansible_sshkey.pub` | Ansible SSH public key — deployed to all nodes at install |
| `provision/firewallme.sh` | Firewall/router setup script — run manually on first boot |
| `debian/` | Debian netboot files |
| `proxmox/` | Proxmox VE answer files, `first-boot.sh`, provisioning scripts |
| `windows/` | Windows unattend/PostOOBE bootstrap files |

> `firewallme.sh` lives at `bootstrap/web/provision/firewallme.sh` in this repo. The script
> contains reference WAN IPs and WireGuard public keys for **all four** hub-era sites — `CLD`,
> `FAL`, `ODE`, `BRK` — in its `HUB_KNOWN_PUBKEY` and `HUB_WAN_IP` tables, update the relevant
> entry if any of them is rebuilt. Only `CLD`'s is actually load-bearing today (the sole real
> hub) — the other three are kept as reference data only, same reasoning as
> `group_vars/firewalls/main.yml`'s own `wg_hub_known_pubkeys`/`wg_hub_wan_ips`.

---

*Example Music Limited — Internal Infrastructure Documentation*  
*Do not distribute outside the organisation*  
*Credentials: See password manager — never store passwords in this document*
