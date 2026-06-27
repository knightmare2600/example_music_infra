# Proxmox VE — Network Configuration

## Changelog

| Date | Change |
|---|---|
| 2026-03-01 | Initial document — VLAN-aware bridge, VMware terminology mapping, serial console, subscription nag removal |
| 2026-03-01 | Added ISO/template storage paths, custom BIOS/OVMF notes, SLIC activation |

## VMware ESXi Migration Reference & Site Bridge Setup

> **Applies to:** Proxmox VE 8.x
> **Audience:** Infrastructure technicians familiar with VMware ESXi/vSphere
> **References:**
> - [Proxmox VE Network Configuration](https://pve.proxmox.com/wiki/Network_Configuration)
> - [Proxmox VE Open vSwitch](https://pve.proxmox.com/wiki/Open_vSwitch)
> - [Proxmox Admin Guide §3.3 — Network](https://pve.proxmox.com/pve-docs/pve-admin-guide.html#sysadmin_network_configuration)

---

## VLAN Reference

> **The VLAN ID matches the third octet of the site subnet wherever possible.** This makes it easy to correlate at a glance — VLAN 76 is `192.168.76.0/24` is FAL.
>
> Linux has no concept of named VLANs — they are numbers only at the kernel level. Keep this table at the top of `/etc/network/interfaces` as a comment block (see Configuration section). It is also reproduced here for the docs.

| VLAN ID | Site Code | Location | Country | Subnet |
|---|---|---|---|---|
| 20 | LND | London | UK | `192.168.20.0/24` |
| 29 | SYD | Sydney | AU | `192.168.29.0/24` |
| 31 | AMS | Amsterdam | NL | `192.168.31.0/24` |
| 33 | GAA | Georgia, AL | US | `192.168.33.0/24` |
| 39 | MIL | Milan | IT | `192.168.39.0/24` |
| 41 | CLY | Clydebank | UK | `192.168.41.0/24` |
| 46 | GOT | Gothenburg | SE | `192.168.46.0/24` |
| 47 | OSL | Oslo | NO | `192.168.47.0/24` |
| 61 | MEL | Melbourne | AU | `192.168.61.0/24` |
| 65 | KGE | Køge | DK | `192.168.65.0/24` |
| 76 | FAL | Falkirk *(Head Office)* | UK | `192.168.76.0/24` |
| 78 | VIE | Vienna | AT | `192.168.78.0/24` |
| 93 | AKL | Auckland | NZ | `192.168.93.0/24` |
| 113 | BRD | West Berlin | DE | `192.168.113.0/24` |
| 114 | SHE | Sheffield | UK | `192.168.114.0/24` |
| 121 | BIR | Birmingham | UK | `192.168.121.0/24` |
| 126 | ODE | Odense | DK | `192.168.126.0/24` |
| 131 | EDI | Edinburgh | UK | `192.168.131.0/24` |
| 135 | MIA | Miami | US | `192.168.135.0/24` |
| 136 | BRK | Brockville | CA | `192.168.136.0/24` |
| 138 | DUN | Dundee | UK | `192.168.138.0/24` |
| 139 | PROV | Provisioning / Bootstrap | — | `192.168.139.0/24` |
| 141 | GLA | Glasgow | UK | `192.168.141.0/24` |
| 142 | HAL | Halifax | UK | `192.168.142.0/24` |
| 148 | HUL | Hull | UK | `192.168.148.0/24` |
| 151 | LIV | Liverpool | UK | `192.168.151.0/24` |
| 154 | MTL | Montreal | CA | `192.168.154.0/24` |
| 161 | MCR | Manchester | UK | `192.168.161.0/24` |
| 173 | PER | Perth | UK | `192.168.173.0/24` |
| 189 | MUN | Munich | DE | `192.168.189.0/24` |
| 191 | NEW | Newcastle | UK | `192.168.191.0/24` |
| 201 | NJC | New Jersey | US | `192.168.201.0/24` |
| 212 | NYC | New York | US | `192.168.212.0/24` |
| 213 | LAX | Los Angeles | US | `192.168.213.0/24` |
| 224 | ABD | Aberdeen | UK | `192.168.224.0/24` |
| 228 | BON | Bonn | DE | `192.168.228.0/24` |
| 231 | CPH | Copenhagen | DK | `192.168.231.0/24` |
| 238 | KOR | Korsør | DK | `192.168.238.0/24` |
| 246 | FAX | Faxe | DK | `192.168.246.0/24` |
| 247 | COV | Coventry | UK | `192.168.247.0/24` |

> **PROV (139)** is the bootstrap/provisioning network only. It is used during site bring-up and by the iPXE installer. The bootstrap server lives at `192.168.139.50`. No firewall handles DHCP on this VLAN — the bootstrap server does.

---

## VMware → Proxmox Terminology

If you're coming from ESXi/vSphere, the constructs map across but the terminology is different. The mental model is similar; the implementation is pure Linux.

| VMware ESXi | Proxmox VE | Notes |
|---|---|---|
| vSwitch | Linux Bridge (`vmbrX`) | The virtual switch itself |
| Port Group | VLAN tag on VM NIC | No separate "port group" object — the VLAN is set directly on the VM's NIC |
| Physical NIC uplink | Bridge port (`bridge-ports`) | The physical NIC(s) that back the bridge |
| NIC Teaming (active/passive) | Linux Bond | Create a bond, then attach the bond as the bridge port |
| NIC Teaming (LACP) | Linux Bond with `bond-mode 802.3ad` | Requires switch-side LACP configuration |
| VLAN Trunking | `bridge-vlan-aware yes` | Tick "VLAN aware" on the bridge |
| Distributed Switch (vDS) | Not directly equivalent | Proxmox SDN is the closest — available from PVE 8.1+, still beta for some configs |

The key difference to internalise: **in VMware you attach a VM to a port group which carries the VLAN. In Proxmox you attach a VM to a bridge and set the VLAN tag directly on the VM's virtual NIC.** The bridge itself is VLAN-agnostic if you enable VLAN awareness — it just passes tagged traffic through.

### A Note on Named VLANs

VMware lets you give port groups friendly names ("FAL-LAN", "MIA-DMZ" etc). **Proxmox and Linux have no equivalent** — VLANs are numbers at the kernel level, full stop. The SDN feature (Datacenter → SDN) introduces named VNets but is designed for overlay networking and is overkill for our setup.

The practical solution is to keep the VLAN reference table above as a comment block at the top of `/etc/network/interfaces` — it lives right alongside the config that uses it and any technician opening the file sees it immediately.

---

## Networking Concepts

### The Linux Bridge

A Linux bridge interface (commonly called `vmbrX`) is needed to connect guests to the underlying physical network. It can be thought of as a virtual switch which the guests and physical interfaces are connected to.

The most equivalent network construct out of the box with Proxmox is the default Proxmox Linux bridge. With the Linux Bridge in Proxmox, you establish the initial connectivity to your Proxmox host with a management IP address. The default Linux Bridge is backed by a physical network adapter.

### VLAN Awareness

Unlike the VMware default vSwitch0 and VM Network port group, the default Proxmox Linux Bridge is not VLAN-aware out of the box. You have to enable this. When you edit the default Linux Bridge, you will see the checkbox **VLAN aware** on the Linux Bridge properties.

Once VLAN awareness is enabled, you just create one bridge that every VLAN can use. Then you only need to set the VLAN tag for the VM you are creating — virtio will automatically filter packets by the given tag and tag untagged traffic.

### Port Groups — Where They Went

In the VMware world, a port group is used for connecting guests to a vSwitch. It is intended to be analogous to a switchport on a real world network switch. Proxmox approaches this differently — there are no port groups and the VLAN configuration is held by the guest's NIC. This is akin to if you could attach a VMware guest directly to a vSwitch and just specify the VLAN directly on the guest interface.

### Two Approaches to VLANs

There are two valid ways to do VLANs in Proxmox. Pick one and be consistent.

**Option A — Single VLAN-aware bridge (recommended — this is what we use)**

One bridge, VLAN awareness enabled. Each VM gets a VLAN tag on its NIC. Clean, simple, scales well. You create `vmbr1` once and never touch it again. Adding a new site is just a matter of assigning the right VLAN tag to the new VM's NIC.

**Option B — One bridge per VLAN (legacy/classic — not recommended)**

A separate `vmbrX` per VLAN, each backed by a VLAN sub-interface (`eno1.76` for VLAN 76 etc). Closer to the VMware mental model but creates a separate bridge and a separate VLAN interface for every single site — 40 sites means 80 extra interfaces. Makes `ip link show` and monitoring output extremely noisy. Not recommended for our scale.

---

## Our Setup — Site Bridges

Each site network maps to a VLAN ID (see VLAN Reference table above). All VMs for a given site are attached to the single VLAN-aware bridge `vmbr1` with their site's VLAN tag set on the NIC. The site firewall VM (e.g. `EXAFWLFAL001`) has two NICs — one on the site VLAN (LAN side) and one on VLAN 139 (provisioning/WAN side).

---

## Configuration

### Step 1 — Check Your Physical NICs

Before creating anything, check what NICs you have and what's already in use:

```bash
# Show all interfaces and their state
ip link show

# Show existing bridges and their ports
bridge link show

# Show bridges in the older brctl style (also valid)
brctl show
```

On a fresh Proxmox install you will typically see:

- `eno1` (or similar) — in use by `vmbr0`, the management bridge. **Leave this alone.**
- A second NIC (e.g. `enp1s0f1`) — free to use for `vmbr1`.

> If you only have one physical NIC, you can still create `vmbr1` with that NIC as the bridge port. VM traffic will share the uplink with management traffic. It works, but keep it in mind for troubleshooting.
>
> If the second NIC is not physically connected, `vmbr1` will still work for VM-to-VM traffic on the same host. VMs on the same node talking to each other never touch the physical NIC — it's all in-kernel switching. You only need the physical uplink connected if VMs need to reach the outside world.

### Step 2 — Create vmbr1 via the Web UI

Go to **Node → System → Network → Create → Linux Bridge** and fill in:

| Field | Value | Notes |
|---|---|---|
| **Name** | `vmbr1` | `vmbr0` already exists — leave it alone |
| **IPv4/CIDR** | *(leave blank)* | No IP on the VM bridge |
| **IPv4 Gateway** | *(leave blank)* | |
| **IPv6/CIDR** | *(leave blank)* | |
| **IPv6 Gateway** | *(leave blank)* | |
| **Autostart** | ✅ ticked | Must be up on boot |
| **VLAN aware** | ✅ ticked | The key setting — enables all site VLANs |
| **Bridge ports** | `enp1s0f1` | Your second NIC — verify name with `ip link show` |
| **Comment** | `VM bridge — all site VLANs` | Optional but helpful |

Click **Create**, then the orange **Apply Configuration** button at the top of the Network page.

### Step 2 (alternative) — Create vmbr1 via CLI

Proxmox's officially documented approach is to edit `/etc/network/interfaces` directly — the web UI is just a frontend that writes to the same file. Add the VLAN reference block and `vmbr1` stanza:

```
# ===========================================
# VLAN Reference — Example Music Limited
# ===========================================
# 20  = LND  London          192.168.20.0/24
# 29  = SYD  Sydney          192.168.29.0/24
# 31  = AMS  Amsterdam       192.168.31.0/24
# 33  = ATL  Georgia AL      192.168.33.0/24
# 39  = MIL  Milan           192.168.39.0/24
# 41  = CLY  Clydebank       192.168.41.0/24
# 46  = GOT  Gothenburg      192.168.46.0/24
# 47  = OSL  Oslo            192.168.47.0/24
# 61  = MEL  Melbourne       192.168.61.0/24
# 65  = KGE  Koge            192.168.65.0/24
# 76  = FAL  Falkirk (HQ)    192.168.76.0/24
# 78  = VIE  Vienna          192.168.78.0/24
# 93  = AKL  Auckland        192.168.93.0/24
# 113 = BER  West Berlin     192.168.113.0/24
# 114 = SHE  Sheffield       192.168.114.0/24
# 121 = BIR  Birmingham      192.168.121.0/24
# 126 = ODE  Odense (EU HQ)  192.168.126.0/24
# 131 = EDI  Edinburgh       192.168.131.0/24
# 135 = MIA  Miami           192.168.135.0/24
# 136 = BRK  Brockville      192.168.136.0/24
# 138 = DUN  Dundee          192.168.138.0/24
# 139 = PRV Provisioning     192.168.139.0/24
# 141 = GLA  Glasgow         192.168.141.0/24
# 142 = HAL  Halifax (UK)    192.168.142.0/24
# 148 = HUL  Hull            192.168.148.0/24
# 151 = LIV  Liverpool       192.168.151.0/24
# 154 = MTL  Montreal        192.168.154.0/24
# 161 = MCR  Manchester      192.168.161.0/24
# 173 = PER  Perth           192.168.173.0/24
# 189 = MUN  Munich          192.168.189.0/24
# 191 = NEW  Newcastle       192.168.191.0/24
# 201 = NJC  New Jersey      192.168.201.0/24
# 212 = NYC  New York        192.168.212.0/24
# 213 = LAX  Los Angeles     192.168.213.0/24
# 224 = ABD  Aberdeen        192.168.224.0/24
# 228 = BON  Bonn            192.168.228.0/24
# 231 = CPH  Copenhagen      192.168.231.0/24
# 238 = KOR  Korsor          192.168.238.0/24
# 246 = FAX  Faxe            192.168.246.0/24
# 247 = COV  Coventry        192.168.247.0/24
# ===========================================

# VM bridge — VLAN-aware, no IP
# All site VLANs pass through this bridge
auto vmbr1
iface vmbr1 inet manual
    bridge-ports enp1s0f1
    bridge-stp off
    bridge-fd 0
    bridge-vlan-aware yes
    bridge-vids 2-4094
```

Then apply without rebooting:

```bash
# Preview what will change before committing
ifreload -a --diff

# Apply
ifreload -a
```

> **Note:** `vmbr0` is your management interface — the IP the Proxmox web UI lives on. Leave this exactly as the installer created it. `vmbr1` is the VM bridge — no IP, VLAN-aware, all site traffic goes through here.

> **No DHCP on the bridge.** The bridge itself has no IP and requests no DHCP. Each site's firewall VM is responsible for DHCP on that site's VLAN. The bridge just passes frames.

### Step 3 — Assign VMs to Site VLANs

When creating or editing a VM, go to **Hardware → Network Device**. Set:

- **Bridge:** `vmbr1`
- **VLAN Tag:** the site VLAN ID (e.g. `76` for FAL, `135` for MIA)
- **Model:** `VirtIO (paravirtualized)` — best performance

The VM sees untagged traffic on its NIC. The bridge handles the tagging transparently. The VM does not need to know it's on a VLAN.

For firewall VMs that need to see multiple VLANs (e.g. the WAN-side NIC on VLAN 139), leave the VLAN Tag field empty — the VM will behave as if plugged into a trunk port.

---

## If You Have Two Physical NICs — Bonding for Redundancy

If the server has two NICs, bond them for redundancy before attaching to the bridge. This is the equivalent of NIC teaming in VMware.

### Active/Passive (no switch config required)

```
auto bond0
iface bond0 inet manual
    bond-slaves eno1 eno2
    bond-miimon 100
    bond-mode active-backup

auto vmbr1
iface vmbr1 inet manual
    bridge-ports bond0
    bridge-stp off
    bridge-fd 0
    bridge-vlan-aware yes
    bridge-vids 2-4094
```

### LACP / 802.3ad (requires switch-side configuration)

```
auto bond0
iface bond0 inet manual
    bond-slaves eno1 eno2
    bond-miimon 100
    bond-mode 802.3ad
    bond-xmit-hash-policy layer2+3

auto vmbr1
iface vmbr1 inet manual
    bridge-ports bond0
    bridge-stp off
    bridge-fd 0
    bridge-vlan-aware yes
    bridge-vids 2-4094
```

> LACP requires the upstream switch ports to be configured as a port-channel/LAG with LACP enabled. Active/passive requires no switch config and is fine for most sites.

---

## Firewall VM Network Layout

Each site firewall VM (FortiGate, OPNsense, pfSense etc) will typically have two or three virtual NICs:

| NIC | Bridge | VLAN Tag | Purpose |
|---|---|---|---|
| `net0` | `vmbr1` | `139` | WAN / provisioning side |
| `net1` | `vmbr1` | site octet (e.g. `76`) | LAN side — site subnet |
| `net2` | `vmbr1` | *(empty — trunk)* | Optional: if FW needs to route between sites |

The firewall VM handles DHCP for the site LAN. **Nothing on `vmbr1` itself has an IP address or requests DHCP** — the bridge is purely a frame-forwarding device.

---

## Checking Your Configuration

```bash
# Show all interfaces and their state — use this first
ip link show

# Show existing bridges and which NICs are their ports
bridge link show

# Show bridges in the older brctl style (also fine)
brctl show

# Show VLAN membership on all bridge ports
bridge vlan show

# Check a specific bridge has no IP (expected for vmbr1)
ip addr show vmbr1

# Show which VMs are attached to which bridge
grep -r "bridge=" /etc/pve/qemu-server/

# Preview pending network changes before applying
ifreload -a --diff
```

> `bridge show` on its own is not a valid command and will error. Use `bridge link show` or `brctl show`.

---

## Common Gotchas

**"My VM can't reach anything after I enabled VLAN awareness"**
The VM NIC needs a VLAN tag set. A VLAN-aware bridge with no tag on the NIC sends traffic as tagged VLAN 1, which is usually not what you want. Set the VLAN tag explicitly on every NIC attached to `vmbr1`.

**"I set VLAN awareness and now the Proxmox management interface is gone"**
This happens if `vmbr0` (the management bridge) and `vmbr1` (the VM bridge) share the same physical NIC. Keep them on separate NICs, or keep `vmbr0` as a non-VLAN-aware bridge and use `vmbr1` exclusively for VM traffic.

**"The web UI says 'pending changes' and won't apply"**
Proxmox stages changes to `/etc/network/interfaces.new`. If there's a conflict or syntax error it will refuse to apply. Check with `ifreload -a --diff` to see what it's trying to do.

**"I want the Proxmox host itself to have an IP on a site VLAN"**
You need a VLAN sub-interface on the bridge. For example, to give the host an IP on VLAN 76:

```
auto vmbr1.76
iface vmbr1.76 inet static
    address 192.168.76.5/24
```

This is how `EXAPVEFAL001` gets its management IP on the FAL LAN while still passing all other site VLANs through `vmbr1`.

---

## Full Example — `/etc/network/interfaces` for EXAPVEFAL001

```
auto lo
iface lo inet loopback

# Physical NICs
iface eno1 inet manual
iface enp1s0f1 inet manual

# Management bridge — Proxmox host management IP
# Leave this exactly as the installer created it
auto vmbr0
iface vmbr0 inet static
    address 192.168.76.5/24
    gateway 192.168.76.1
    bridge-ports eno1
    bridge-stp off
    bridge-fd 0
    # DNS is set via pvesh, not here

# =========================================
# VLAN Reference — Example Music Limited
# (truncated here for brevity — see full list above)
# 76  = FAL  Falkirk (HQ)    192.168.76.0/24
# 139 = PROV Provisioning    192.168.139.0/24
# ... etc
# =========================================

# VM bridge — VLAN-aware, no IP
# All site VLANs pass through here
auto vmbr1
iface vmbr1 inet manual
    bridge-ports enp1s0f1
    bridge-stp off
    bridge-fd 0
    bridge-vlan-aware yes
    bridge-vids 2-4094
```

VMs on this node are then configured as:

| VM | NIC | Bridge | VLAN | IP (inside VM) |
|---|---|---|---|---|
| `EXAFWLFAL001` (FortiGate — WAN NIC) | net0 | vmbr1 | 139 | `192.168.139.x` |
| `EXAFWLFAL001` (FortiGate — LAN NIC) | net1 | vmbr1 | 76 | `192.168.76.1` |
| `EXADCSFAL001` (Domain Controller) | net0 | vmbr1 | 76 | `192.168.76.10` |
| `EXADCSFAL002` (Domain Controller) | net0 | vmbr1 | 76 | `192.168.76.21` |

---

## ISO and Template Storage

ISOs and templates live in `/var/lib/vz/` as flat files regardless of whether the underlying storage is ZFS. VM disks are ZFS volumes, but ISOs are just files on the filesystem.

| Path | Web UI | Purpose |
|---|---|---|
| `/var/lib/vz/template/iso/` | local → ISO Images | ISO images |
| `/var/lib/vz/template/cache/` | local → CT Templates | LXC container templates |
| `/var/lib/vz/dump/` | local → Backups | VM/CT backups |
| `/var/lib/vz/images/` | local → Disk Images | Raw disk images — not used with ZFS, VM disks live in `rpool/data/` instead |

Upload ISOs with `scp` or `wget` directly — they appear in the web UI immediately with no rescan needed:

```bash
# scp from your workstation
scp myimage.iso root@192.168.139.50:/var/lib/vz/template/iso/

# wget direct on the node
wget -P /var/lib/vz/template/iso/ https://example.com/myimage.iso
```

---

## Custom BIOS / OVMF (and the bios440 Question)

In VMware you could drop a `bios440.rom` file into the VM directory to use a custom BIOS — a common trick for SLIC/OEM activation. Proxmox supports the equivalent, though the mechanism differs depending on whether you're using SeaBIOS or OVMF (UEFI).

### SeaBIOS — custom ROM

Proxmox uses SeaBIOS by default for legacy BIOS VMs. You can specify a custom SeaBIOS ROM per-VM by editing the VM config directly:

```bash
# /etc/pve/qemu-server/VMID.conf
bios: seabios
args: -bios /usr/share/seabios/bios-256k.bin
```

Replace the path with your own ROM file. The `args:` line passes raw QEMU arguments, so any ROM that QEMU's `-bios` flag accepts will work. Drop your custom ROM somewhere stable (e.g. `/usr/share/seabios/` or `/var/lib/vz/bios/`) and point to it.

For a Dell SLIC ROM specifically you would place the ROM file on the Proxmox host and reference it:

```bash
# Create a sensible home for custom ROMs
mkdir -p /var/lib/vz/bios

# Copy your ROM there
cp dell-slic.rom /var/lib/vz/bios/

# Then in the VM conf:
args: -bios /var/lib/vz/bios/dell-slic.rom
```

> **Note:** The `args:` line in a Proxmox VM config is a direct QEMU passthrough — it is powerful but unsupported by Proxmox itself. Changes made via `args:` will not be reflected in the web UI and will not be validated. Edit with care and always keep a note of what you've added.

### OVMF (UEFI) — custom firmware

If the VM uses OVMF (UEFI), the firmware file is specified differently. Proxmox ships OVMF in `/usr/share/OVMF/`. You can substitute a custom OVMF build by replacing or symlinking the firmware file, but this is host-wide and affects all OVMF VMs — not per-VM.

For per-VM UEFI firmware you would need to use `args:` similarly:

```
args: -drive if=pflash,format=raw,readonly=on,file=/var/lib/vz/bios/custom-ovmf.fd
```

### SLIC and OEM Activation — Practical Notes

SLIC tables are embedded in the BIOS ROM and are read by Windows during activation to match against an OEM certificate in the OS image. For this to work legally you need:

- A legitimate OEM ROM from a machine you own the licence for
- The matching OEM SLP key (embedded in the OEM Windows install media)
- The OEM certificate (`.xrm-ms` file) installed in Windows

Proxmox/QEMU will pass the SLIC table through to the guest if it's present in the ROM. The `-bios` approach above is the correct way to do this. Whether Windows picks it up depends on the guest having the matching OEM cert and key — the ROM alone is not sufficient.

If you are just after unattended activation for internal lab/infrastructure VMs, a KMS server (e.g. `vlmcsd` running as a container) is considerably less fiddly and fully legitimate with volume licence agreements.

---

## References

- Proxmox VE Network Configuration Wiki: https://pve.proxmox.com/wiki/Network_Configuration
- Proxmox Admin Guide — Network: https://pve.proxmox.com/pve-docs/pve-admin-guide.html#sysadmin_network_configuration
- Proxmox Open vSwitch Wiki: https://pve.proxmox.com/wiki/Open_vSwitch
- Proxmox Forum — VMware ESXi to Proxmox networking: https://forum.proxmox.com/threads/new-to-proxmox-networking-i-want-a-similar-setup-to-what-i-had-with-esxi.101872/
- Proxmox Networking for vSphere Admins: https://www.virtualizationhowto.com/2023/12/proxmox-networking-for-vmware-vsphere-admins/

---

*Example Music Limited — Internal Infrastructure Documentation*
*Do not distribute outside the organisation*
