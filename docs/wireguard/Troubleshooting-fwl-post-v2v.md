# TROUBLESHOOTING-FW-POST-V2V — Firewall Recovery After V2V Migration

**Document ref:** NET-FW-TROUBLESHOOT-001  
**Applies to:** Example Music Limited — all sites  
**Scope:** Linux firewall VMs (nftables + NetworkManager) migrated from VMware to Proxmox VE  
**Author:** Infrastructure Team  
**Status:** Live

---

## Version History

| Version | Date       | Author  | Change                                              |
|---------|------------|---------|-----------------------------------------------------|
| 1.0     | 2026-03-07 | Infra   | Initial document — NIC renaming, nmcli, nftables recovery  |
| 1.1     | 2026-03-07 | Infra   | Added conventions/placeholder table, session logging guide |
| 1.2     | 2026-03-07 | Infra   | Real-world validation against EXAFWLGLA001 — updated examples, added wg0 note, Wired connection gotcha, VMware naming clarification (ens32/ens33 not ens33/ens34) |
| 1.3     | 2026-03-07 | Infra   | Added WireGuard diagnosis and recovery (Steps 9-10) — wrong hub endpoint, wg-quick bounce, bidirectional nmap test; validated against EXAFWLGLA001↔EXAFWLFAL001 |
| 1.4     | 2026-03-07 | Infra   | Added Step 7b — dnsmasq interface name fix (sed + dnsmasq --test + verify); added dnsmasq rows to Quick Reference  |
| 1.5     | 2026-03-11 | Infra   | Added Step 0 — NetworkManager boot cycle fix (systemd ordering cycle introduced by virt-v2v; guestfs-firstboot disable). Validated against EXAFWLFAL001. Real terminal output included. Note: convert-v2v.py now automates these fixes via virt-customize — Step 0 is the manual fallback. |

---

## 1. Conventions Used in This Document

Before starting, substitute the placeholder values below with the real values for the VM you are working on. Every command in this document uses these placeholders consistently.

| Placeholder     | Meaning                                          | Example (FAL)        | Example (GLA)        |
|-----------------|--------------------------------------------------|----------------------|----------------------|
| `<VM_NAME>`     | EXA hostname of the firewall VM                  | `EXAFWLFAL001`       | `EXAFWLGLA001`       |
| `<WAN_IP>`      | Current WAN IP address of the VM                 | `192.168.139.51`     | `192.168.139.56`     |
| `<LAN_IP>`      | LAN gateway IP of the VM                         | `192.168.76.1`       | `192.168.141.253`    |
| `<SITE>`        | Three-letter site code                           | `FAL`                | `GLA`                |
| `<OLD_WAN_IF>`  | Interface name WAN was using in VMware           | `ens32`              | `ens32`              |
| `<OLD_LAN_IF>`  | Interface name LAN was using in VMware           | `ens33`              | `ens33`              |
| `<NEW_WAN_IF>`  | Interface name WAN has been assigned in Proxmox  | `ens18`              | `ens18`              |
| `<NEW_LAN_IF>`  | Interface name LAN has been assigned in Proxmox  | `ens19`              | `ens19`              |
| `<NM_WAN>`      | NetworkManager connection profile name for WAN   | `wan`                | `wan`                |
| `<NM_LAN>`      | NetworkManager connection profile name for LAN   | `lan`                | `lan`                |

> **Note:** VMware Workstation typically assigns `ens32` and `ens33` as the first two NIC names, not `ens33`/`ens34` as some documentation suggests. Proxmox consistently assigns `ens18`/`ens19`.Always verify with `nmcli connection show <profile> | grep connection.interface-name` rather
> than assuming.

Fill these in before you start — if you are sharing output with another engineer or raising a ticket, include your completed table so the context is unambiguous.

If the VM has a WireGuard interface (`wg0`), this is expected and does not need to be renamed — it is not a physical NIC and is unaffected by V2V migration.

---

## 2. Logging Your Session

Always capture a full transcript when troubleshooting a firewall. This gives you an exact record of every command run and its output, which is invaluable if you need to hand off to another engineer, raise a ticket, or post-mortem what happened.

### Using `script`

`script` captures everything printed to your terminal — commands and output — to a file. It is available on every Linux system with no install required.

Start logging before you run any diagnostic commands:

```bash
script -a /tmp/<VM_NAME>-fw-recovery-$(date +%Y%m%d-%H%M%S).log
```

The `-a` flag appends if the file already exists (safe to use from the start). `date +%Y%m%d-%H%M%S` stamps the filename so you know when the session was.

You will see:
```
Script started, output log file is '/tmp/EXAFWLFAL001-fw-recovery-20260307-141523.log'
```

Everything from this point — including all commands and their output — is recorded. When you are done, exit the script session:

```bash
exit
```

You will see:
```
Script done, output log file is '/tmp/EXAFWLFAL001-fw-recovery-20260307-141523.log'
```

### Using `tee` for individual commands

If you only want to capture the output of specific commands rather than a full session, pipe through `tee`:

```bash
ip link show | tee -a /tmp/<VM_NAME>-diag.log
nmcli connection show | tee -a /tmp/<VM_NAME>-diag.log
nft list ruleset | tee -a /tmp/<VM_NAME>-diag.log
```

`tee -a` prints to screen and appends to the file simultaneously.

### Retrieving the log

Once networking is restored, copy the log off the VM:

```bash
# From another machine
scp ansible@<WAN_IP>:/tmp/<VM_NAME>-*.log ./
```

Or if you are still on the console, `cat` it so you can copy/paste:

```bash
cat /tmp/<VM_NAME>-fw-recovery-*.log
```

---

## 3. Prerequisites

- Proxmox console access to the affected VM (noVNC or SPICE)
- Root or sudo access on the VM
- The VM must be powered on
- The original VMX file or build sheet for the site (to cross-reference MAC addresses)
- Your completed placeholder table from Section 1

---

## 3a. Step 0 — NetworkManager Boot Cycle Fix (Do This First)

> **automation note:** `convert-v2v.py` applies both fixes below automatically via `virt-customize` before the disk is imported.
>
> If the conversion was run with an up-to-date version of the script and `virt-customize` succeeded, you can skip to Section 4.
> If you are recovering a VM that was converted before this automation existed (e.g. `EXAFWLFAL001`, `EXAFWLGLA001`), or if `virt-customize` reported a non-zero exit, apply these fixes manually before anything else.

This is the root cause of a class of failure where NetworkManager appears to be enabled and configured correctly but is completely dead on boot with **zero journal entries**. The usual symptoms that send engineers down the wrong path:

- `systemctl status NetworkManager` → `inactive (dead)`
- `nmcli` shows no IPs on any interface
- `journalctl -u NetworkManager -b 0` → **no entries at all**
- dnsmasq and cockpit both failed on boot
- nftables loaded fine (`active (exit)`)

The absence of journal entries is the key diagnostic indicator — NM didn't crash, it was never started.

### Why This Happens

virt-v2v leaves a systemd dependency cycle. NetworkManager is supposed to bring up `network.target`, but something in the migrated unit graph also makes it wait for `network.target` before starting. systemd detects the cycle and resolves it by silently deleting the NM start job. The journal confirms this:

```
Mar 11 20:38:50 EXAFWLFAL001 systemd[1]: network-online.target: Job network.target/start deleted to break ordering cycle starting with network-online.target/start
Mar 11 20:38:50 EXAFWLFAL001 systemd[1]: NetworkManager.service: Job dbus.service/start deleted to break ordering cycle starting with NetworkManager.service/start
```

The cascade from NM being dead:

```
Mar 11 20:38:56 EXAFWLFAL001 systemd[1]: cockpit.socket: Failed to receive listening socket (192.168.76.253:9090): Input/output error
Mar 11 20:40:20 EXAFWLFAL001 systemd[1]: Timed out waiting for device sys-subsystem-net-devices-ens34.device - /sys/subsystem/net/devices/ens34.
Mar 11 20:40:20 EXAFWLFAL001 dnsmasq[884]: unknown interface ens34
Mar 11 20:40:20 EXAFWLFAL001 dnsmasq[884]: FAILED to start up
```

Note the `ens34` reference above — that is a separate issue (stale interface name in dnsmasq config, covered in Step 7b). Fix the NM cycle first, then fix the interface names.

### Confirm the Cycle (Optional but Recommended)

```bash
# Should show two "deleted to break ordering cycle" lines
sudo journalctl -b 0 -p err --no-pager | head -20

# Confirm NM is enabled but dead with no journal entries
systemctl is-enabled NetworkManager   # should print: enabled
journalctl -u NetworkManager -b 0 --no-pager   # should print: -- No entries --

# Confirm it's not a block list issue (wpad and isatap only = normal)
dnscmd . /info /globalqueryblocklist 2>/dev/null || sudo cat /etc/NetworkManager/NetworkManager.conf
```

### Fix 1 — NetworkManager Ordering Drop-in

Write a drop-in that makes the dependency ordering explicit and breaks the cycle:

```bash
sudo mkdir -p /etc/systemd/system/NetworkManager.service.d

sudo tee /etc/systemd/system/NetworkManager.service.d/override.conf << 'EOF'
[Unit]
# Explicit ordering to fix cycle introduced by virt-v2v migration.
# NM brings up network.target — it must not also wait for it.
# Written manually — see NET-FW-TROUBLESHOOT-001 Step 0
After=network-pre.target
After=dbus.service
Before=network.target
EOF

sudo systemctl daemon-reload
```

Verify the file was written correctly:

```bash
cat /etc/systemd/system/NetworkManager.service.d/override.conf
```

### Fix 2 — Disable guestfs-firstboot

virt-v2v installs `guestfs-firstboot.service`, which runs one-shot scripts on first boot then deletes them. The service stays enabled after the scripts run and contributes to the ordering cycle on every subsequent boot.

Check whether it has pending scripts (it almost certainly does not on a VM that has already booted at least once):

```bash
ls /usr/lib/virt-sysprep/scripts/ 2>/dev/null && echo "has scripts" || echo "empty or absent"
```

If empty or absent, disable it:

```bash
sudo systemctl disable guestfs-firstboot.service
sudo systemctl daemon-reload
```

Expected output: `Removed /etc/systemd/system/multi-user.target.wants/guestfs-firstboot.service.`

Verify:

```bash
systemctl is-enabled guestfs-firstboot.service
# Expected: disabled
```

### Reboot and Confirm

```bash
sudo reboot
```

After the VM comes back up:

```bash
# NM must be active (running) — not dead
systemctl status NetworkManager

# Both interfaces must have IPs
nmcli device status
nmcli connection show

# No ordering cycle errors in boot journal
sudo journalctl -b 0 -p err --no-pager | grep -i "ordering cycle\|deleted to break"
# Expected: no output
```

A healthy result (EXAFWLFAL001, 2026-03-11):

```
● NetworkManager.service - Network Manager
     Loaded: loaded (/usr/lib/systemd/system/NetworkManager.service; enabled)
     Active: active (running)

DEVICE  TYPE      STATE      CONNECTION
ens18   ethernet  connected  wan
ens19   ethernet  connected  lan
wg0     wireguard connected  wg0
lo      loopback  connected  lo
```

Once NM is healthy, continue with Step 7b (dnsmasq interface names) if dnsmasq is still failing, then Step 9 (WireGuard) if the tunnel is down.

---

## 4. Background

When a Linux firewall VM is migrated from VMware Workstation to Proxmox VE using virt-v2v, the virtual NIC hardware changes. VMware Workstation typically presents NICs as `ens32`, `ens33` etc. Proxmox presents them as `ens18`, `ens19` etc. (or `enp0s18`/`enp0s19` — these are altnames for the same interface, both are valid).

`NetworkManager` connection profiles and `nftables` rules both reference interface names by string. After migration they will reference names that no longer exist, leaving the named connections (`wan`, `lan`) unbound and the firewall non-functional.

**Symptoms:**
- VM console has outbound connectivity (can ping/resolve DNS) but LAN is unreachable
- SSH on WAN IP may or may not work — depends on whether NM auto-created a "Wired connection" profile that grabbed the WAN interface before your `wan` profile could (see Step 3 note)
- LAN interface has no IP — no traffic passing to internal network
- `nmcli connection show` lists `wan` and `lan` connections as `--` (disconnected)
- `nmcli connection show` may show "Wired connection 1" or "Wired connection 2" bound
  to `ens18` or `ens19` — these are auto-generated profiles that stole the interface
- `ip link show` shows `ens18`/`ens19` state UP but with wrong or missing IPs

---


## 5. Diagnosis Procedure

Work through each step in order. Do not skip ahead to fixes until you understand the full picture — interface names, NM profiles, and nftables rules must all be consistent before the firewall will function correctly.

### Step 1 — Enumerate kernel interfaces

Find out what the kernel actually sees:

```bash
ip link show
```

Note the interface names and their MAC addresses. Also note any `altname` entries — these are alternative names for the same interface (e.g. `enp0s18`, `enxbc241197cfa1`) and can be used interchangeably with the primary name.

For a cleaner view of just names and MACs:

```bash
ip -br link show
```

Example output (EXAFWLGLA001):
```
lo               UNKNOWN        00:00:00:00:00:00 <LOOPBACK,UP,LOWER_UP>
ens18            UP             bc:24:11:97:cf:a1 <BROADCAST,MULTICAST,UP,LOWER_UP>
ens19            UP             bc:24:11:de:f1:a2 <BROADCAST,MULTICAST,UP,LOWER_UP>
wg0              UNKNOWN        <POINTOPOINT,NOARP,UP,LOWER_UP>
```

Note that `ens18` and `ens19` show `UP` here — this does not mean the correct NM profiles are bound to them. NM may have auto-created "Wired connection" profiles that grabbed the interfaces. The `wg0` interface is WireGuard and is unaffected by V2V migration.

**Record:** the new interface names and which MAC belongs to which.

---

### Step 2 — Identify WAN vs LAN by MAC

If you preserved MACs during V2V (recommended), the MACs will match the original VMware VM. Cross-reference against:

- The original VMX file (`ethernetN.generatedAddress`)
- The build sheet for the site
- The Proxmox VM hardware tab (Hardware → Network Device shows MAC per NIC)

If MACs were not preserved, identify WAN vs LAN by:

```bash
# Check which interface has a routable IP (will be WAN if DHCP came up)
ip addr show

# Or check ARP — WAN interface will have the gateway in its ARP table
arp -n
```

The interface with the gateway IP in its ARP cache is WAN.

---

### Step 3 — Check NetworkManager connection profiles

```bash
nmcli connection show
```

Example output (EXAFWLGLA001) showing the problem:
```
NAME                UUID                                  TYPE       DEVICE
Wired connection 1  f2fe5fa6-566c-3be5-95d9-c437ae7868f0  ethernet   ens18
lo                  7ec12820-e01f-4fa2-a731-48f579ff038c  loopback   lo
wg0                 68b5686e-af33-4900-b066-dc80fbce572f  wireguard  wg0
lan                 1f181f00-6a61-4457-b62d-ebcada01f1ed  ethernet   --
wan                 55db2cd9-015d-4e07-a83d-d5b539c224ce  ethernet   --
Wired connection 2  1b9b1ce3-3a77-33c4-9ac6-b0e180de92f6  ethernet   --
```

`wan` and `lan` show `--` — not bound. However note that "Wired connection 1" has auto-grabbed `ens18`. NetworkManager creates these generic profiles automatically when it sees an interface it doesn't recognise. They will have obtained a DHCP lease or similar, which is why the VM may appear partially reachable. These profiles should be left alone for now — once `wan` and `lan` are correctly bound in Step 6 they will be displaced.

Check what interface name each profile expects:

```bash
nmcli connection show wan | grep -E 'connection.interface|802-3-ethernet.mac'
nmcli connection show lan | grep -E 'connection.interface|802-3-ethernet.mac'
```

Example output:
```
connection.interface-name:              ens32
connection.interface-name:              ens33
```

This confirms the old VMware interface names. These are what need updating.

---

### Step 4 — Check nftables rules

```bash
grep -n 'ens\|eth\|enp' /etc/nftables.conf
```

Example output (EXAFWLGLA001):
```
7:    oifname "ens32" masquerade
14:    iifname "ens33" oifname "ens33" accept
15:    iifname "ens33" oifname "ens32" accept
16:    iifname "ens32" oifname "ens33" ct state related,established accept
26:    iifname "ens33" tcp dport 22 accept
27:    iifname "ens32" tcp dport 22 accept
28:    iifname "ens33" tcp dport 9090 accept
29:    iifname "ens33" udp dport 53 accept
30:    iifname "ens33" tcp dport 53 accept
31:    iifname "ens33" udp dport 67 accept
32:    iifname "ens33" udp dport 69 accept
33:    iifname "ens33" tcp dport 80 accept
```

Note which old names appear (`ens32` = WAN, `ens33` = LAN in this case) — you will need these in Step 7. Also check the running ruleset in case nftables failed to load at boot:

```bash
nft list ruleset | grep -E 'iif|oif|iifname|oifname'
```

If the running ruleset is empty or minimal when you expect complex rules, nftables failed to start because the interface names didn't exist at boot — meaning the
firewall is currently running with no rules (wide open or no NAT). Confirm:

```bash
nft list ruleset
```

---

### Step 5 — Map old names to new names

At this point you should have a clear picture. Example (EXAFWLGLA001):

| Role | Old name (VMware) | New name (Proxmox) | MAC                 |
| ---- | ----------------- | ------------------ | ------------------- |
| WAN  | `ens32`           | `ens18`            | `bc:24:11:97:cf:a1` |
| LAN  | `ens33`           | `ens19`            | `bc:24:11:de:f1:a2` |

Do not proceed until this table is complete and you are confident in the mapping. Getting WAN and LAN reversed will lock you out entirely.

---

## 6. Fix Procedure

### Step 6 — Update NetworkManager profiles

Rebind each connection profile to the correct new interface name:

```bash
sudo nmcli connection modify wan ifname ens18
sudo nmcli connection modify lan ifname ens19
```

If the profiles also have a MAC address binding that needs clearing (visible in Step 3):

```bash
sudo nmcli connection modify wan ethernet.mac-address ""
sudo nmcli connection modify lan ethernet.mac-address ""
```

Optionally, set a static WAN IP if the ISP has given one:
```bash
nmcli connection modify wan ipv4.addresses 192.168.139.9/24 ipv4.gateway 192.168.139.254 ipv4.dns "1.1.1.1 8.8.8.8" ipv4.method manual
```

Bring the connections up:

```bash
sudo nmcli connection up wan
sudo nmcli connection up lan
```

Verify:

```bash
sudo nmcli connection show
ip addr show
```

Example of a healthy result (EXAFWLGLA001):
```
NAME                UUID                                  TYPE       DEVICE
wan                 55db2cd9-015d-4e07-a83d-d5b539c224ce  ethernet   ens18
lan                 1f181f00-6a61-4457-b62d-ebcada01f1ed  ethernet   ens19
lo                  7ec12820-e01f-4fa2-a731-48f579ff038c  loopback   lo
wg0                 68b5686e-af33-4900-b066-dc80fbce572f  wireguard  wg0
Wired connection 1  f2fe5fa6-566c-3be5-95d9-c437ae7868f0  ethernet   --
Wired connection 2  1b9b1ce3-3a77-33c4-9ac6-b0e180de92f6  ethernet   --
```

`wan` now shows `ens18`, `lan` shows `ens19`. The "Wired connection" profiles have been displaced to `--` as expected. WAN should have its IP address and SSH should now be reachable.

---

### Step 7 — Update nftables rules

Replace the old interface names throughout the nftables config:

```bash
sudo sed -i 's/ens32/ens18/g; s/ens33/ens19/g' /etc/nftables.conf
```

Adjust the old and new names to match your Step 5 mapping table. If you have more than two interfaces, chain multiple substitutions:

```bash
sudo sed -i 's/ens32/ens18/g; s/ens33/ens19/g; s/ens34/ens20/g' /etc/nftables.conf
```

Verify the result — there should be no remaining references to old names:

```bash
grep -n 'ens32\|ens33' /etc/nftables.conf
```

An empty result is correct. Reload nftables:

```bash
sudo systemctl reload nftables
```

If reload is not supported by the unit file:

```bash
sudo systemctl restart nftables
```

Confirm the ruleset loaded correctly. Example of a healthy result (EXAFWLGLA001):

```
table ip nat {
    chain POSTROUTING {
        type nat hook postrouting priority srcnat; policy accept;
        oifname "ens18" masquerade
    }
}
table ip filter {
    chain FORWARD {
        type filter hook forward priority filter; policy drop;
        iifname "ens19" oifname "ens19" accept
        iifname "ens19" oifname "ens18" accept
        iifname "ens18" oifname "ens19" ct state established,related accept
        iifname "wg0" accept
        oifname "wg0" accept
    }
    chain INPUT {
        type filter hook input priority filter; policy drop;
        ct state established,related accept
        iifname "lo" accept
        ip protocol icmp accept
        iifname "ens19" tcp dport 22 accept
        iifname "ens18" tcp dport 22 accept
        ...
    }
}
```

Also check the service status:

```bash
sudo systemctl status nftables
```

Look for `ExecReload` with `status=0/SUCCESS` and a recent timestamp confirming the reload applied your updated config.

---

### Step 7b — Update dnsmasq configuration

dnsmasq, if running on the firewall for DHCP and DNS, also binds to interface names by string. It will fail silently or refuse to start if its config still references the old names.

Check for interface references:

```bash
grep -rn 'ens\|eth\|enp' /etc/dnsmasq.conf /etc/dnsmasq.d/ 2>/dev/null
```

If any old interface names appear (e.g. `interface=ens33`, `listen-address` bound to an IP on a now-renamed interface, or `bind-interfaces` directives), replace them:

```bash
sudo sed -i 's/ens32/ens18/g; s/ens33/ens19/g' /etc/dnsmasq.conf
## Also check drop-in files:
sudo sed -i 's/ens32/ens18/g; s/ens33/ens19/g' /etc/dnsmasq.d/*.conf 2>/dev/null
```

Adjust old/new names to your Step 5 mapping table.

Verify the config parses cleanly before restarting:

```bash
sudo dnsmasq --test
```

Expected output: `dnsmasq: syntax check OK.`

Then restart the service:

```bash
sudo systemctl restart dnsmasq
sudo systemctl status dnsmasq
```

Check it is listening on the correct interface:

```bash
ss -ulnp | grep 53
# Expected: udp  UNCONN  0  0  <LAN_IP>:53  0.0.0.0:*  users:(("dnsmasq",...))
```

If dnsmasq was not previously running on this firewall, skip this step.

---


#### Networking and firewall

From the VM console:

```bash
# WAN connectivity
ping -c 3 8.8.8.8
dig google.com

# LAN interface is up with correct IP
ip addr show ens19
# Expected: inet 192.168.141.253/24 (GLA) or appropriate site subnet
```

From a machine on the LAN:

```bash
# Can reach LAN gateway IP
ping -c 3 <LAN_IP>

# Can reach internet through firewall (confirms NAT/masquerade is working)
curl -s https://ifconfig.me
```

From outside (WAN side):

```bash
# SSH now reachable
ssh ansible@<WAN_IP>
```

---

### Step 9 — Verify WireGuard

WireGuard is managed by `wg-quick`, not NetworkManager. Even after `NetworkManager` and `nftables` are fixed, the WireGuard tunnel may still be down for one of two reasons:

- The spoke's `wg0.conf` has the wrong hub endpoint IP (common if hub was also recently migrated and its WAN IP changed)
- The `wg0` interface is down and needs bouncing after the `nftables` fix

#### Check WireGuard status

```bash
sudo wg show
```

A healthy spoke looks like:
```
interface: wg0
  public key: vgTrFPKBgIo6xFfe4rcqOjYxtrQTluTuGXJ8pm8lzB0=
  private key: (hidden)
  listening port: 57052
peer: yxYnCsZwxDmv6WrduGTC7pnW3sUxob1GGYpttPfGbmk=
  endpoint: 192.168.139.51:51820
  allowed ips: 10.0.76.0/24, 192.168.76.0/24
  latest handshake: 2 seconds ago
  transfer: 92 B received, 180 B sent
  persistent keepalive: every 25 seconds
```

If `latest handshake` shows `never` and transfer shows `0 B received`, the tunnel has not established. If `wg show` returns empty output, the interface is down entirely.

#### Check the hub endpoint IP is correct

```bash
sudo cat /etc/wireguard/wg0.conf
```

Verify the `Endpoint` line points to the hub's current WAN IP. If the hub was recently migrated its WAN IP may have changed. Cross-reference against the CLD
subnet DHCP assignments or the hub's `ip addr show`.

If the endpoint is wrong, update it permanently and apply live:

```bash
# Update the config file
sudo sed -i 's/<OLD_HUB_IP>/<NEW_HUB_IP>/' /etc/wireguard/wg0.conf

# Bounce the interface to pick up the change
sudo wg-quick down wg0 && sudo wg-quick up wg0
```

> **Note:** `wg set` can update the endpoint live without a restart, but if the interface is already down it will have no effect. `wg-quick down/up` is safer.

#### Bounce wg0 if the interface is down

```bash
sudo wg-quick down wg0 && sudo wg-quick up wg0
sudo wg show
```

Wait up to 25 seconds (one keepalive interval) for the handshake to appear.

#### NM and wg0

`wg0` appears in `nmcli connection show` as type `wireguard` — NM is observing it but does not control it. Do not attempt to bring it up via `nmcli`. Use `wg-quick`
or `systemctl start wg-quick@wg0` only.

---

### Step 10 — Bidirectional connectivity test

Once WireGuard is up, confirm the tunnel is routing correctly in both directions using nmap. This verifies routing, firewall FORWARD rules, and the tunnel itself.

**From the spoke, test the hub's LAN:**

```bash
nmap -p22,9090 <HUB_LAN_IP> -oG -
```

Example (GLA → FAL):
```
Host: 192.168.76.253 ()  Ports: 22/open/tcp//ssh///, 9090/open/tcp//zeus-admin///
```

| Port | Expected | Reason |
|------|----------|--------|
| 22   | open     | SSH permitted on LAN interface (`ens19`) |
| 9090 | open     | Cockpit permitted on LAN interface (`ens19`) |

**From the hub, test the spoke's LAN:**

```bash
nmap -p22,9090 <SPOKE_LAN_IP> -oG -
```

Example (FAL → GLA):
```
Host: 192.168.141.253 ()  Ports: 22/open/tcp//ssh///, 9090/closed/tcp//zeus-admin///
```

| Port | Expected | Reason                                                       |
| ---- | -------- | ------------------------------------------------------------ |
| 22   | open     | SSH permitted on `wg0` in spoke INPUT chain                  |
| 9090 | closed   | Cockpit permitted on `ens19` (LAN) only — traffic from hub arrives on `wg0`, which is not permitted for `TCP/9090`. This is correct and expected — do not chase it. |

SSH open in both directions confirms full bidirectional tunnel operation. The 9090 asymmetry is by design. If Cockpit access via tunnel is required, add the following to the spoke's nftables INPUT chain and reload:

```bash
# In /etc/nftables.conf INPUT chain
iifname "wg0" tcp dport 9090 accept
```



## 7. Permanent Fix — Traditional NIC Naming

The `sed` fixes above will need to be repeated every time this VM is migrated or the kernel is updated in a way that changes NIC enumeration. The permanent solution is to force traditional `ethN` naming via GRUB boot parameters, so NIC names are stable across hypervisors and kernel versions.

**Add to GRUB:**

```bash
sudo sed -i 's/GRUB_CMDLINE_LINUX="/GRUB_CMDLINE_LINUX="net.ifnames=0 biosdevname=0 /' /etc/default/grub
update-grub
```

Then update the NM profiles and nftables config one final time to use `eth0`/`eth1`, and they will never need changing again after a future migration.

> **Note:** This should be actioned on the source VM *before* V2V migration. It is on the pre-migration checklist (NET-VIRT-V2V-001 Appendix B).

---

## 8. Quick Reference — Diagnostic Commands

| What you want to know | Command |
|-----------------------|---------|
| What interfaces does the kernel see? | `ip -br link show` |
| What IPs are assigned? | `ip addr show` |
| Which interface has the default route? | `ip route show default` |
| What's in the ARP cache? | `arp -n` |
| Are NM profiles bound to interfaces? | `nmcli connection show` |
| What interface/MAC does a profile expect? | `nmcli connection show <name> \| grep -E 'interface\|mac'` |
| What interface names are in nftables.conf? | `grep -n 'ens\|eth\|enp' /etc/nftables.conf` |
| What rules are currently loaded? | `nft list ruleset` |
| Did nftables load successfully at boot? | `systemctl status nftables` |
| Does dnsmasq have old interface names? | `grep -rn 'ens\|eth\|enp' /etc/dnsmasq.conf /etc/dnsmasq.d/` |
| Does dnsmasq config parse cleanly? | `dnsmasq --test` |
| Is dnsmasq listening on the right interface? | `ss -ulnp \| grep 53` |
| Is SSH listening? | `ss -tlnp \| grep 22` |
| What's blocking SSH? | `nft list ruleset \| grep -A5 ssh` |
| Is WireGuard up and are peers connected? | `sudo wg show` |
| What endpoint is the spoke pointing at? | `sudo cat /etc/wireguard/wg0.conf` |
| Bounce WireGuard interface | `sudo wg-quick down wg0 && sudo wg-quick up wg0` |
| Is WireGuard service healthy? | `systemctl status wg-quick@wg0` |
| Test tunnel routing (SSH + Cockpit) | `nmap -p22,9090 <REMOTE_LAN_IP> -oG -` |
| Is NM enabled but dead with no journal entries? | `systemctl is-enabled NetworkManager && journalctl -u NetworkManager -b 0 --no-pager` |
| Did systemd delete NM job to break ordering cycle? | `journalctl -b 0 -p err --no-pager \| grep "ordering cycle"` |
| Is the NM ordering drop-in present? | `cat /etc/systemd/system/NetworkManager.service.d/override.conf` |
| Is guestfs-firstboot still enabled? | `systemctl is-enabled guestfs-firstboot.service` |
| Does guestfs-firstboot have pending scripts? | `ls /usr/lib/virt-sysprep/scripts/` |

---

## 9. Related Documents

- `NET-VIRT-V2V-001` — VMware to Proxmox V2V Migration Procedure
- `NET-VPN-WG-001` — WireGuard Provisioning and Re-keying
- `bootstrapping.d` — Proxmox Node First-Boot Provisioning

---

*Example Music Limited — Internal Infrastructure Documentation*   *Classification: Internal — Infrastructure Team*
