# WireGuard VPN Troubleshooting Guide

---

**Document ID:** NET-VPN-WG-001  
**Classification:** Internal — Network Operations  
**Author:** Network Engineering  
**Last Updated:** 2026-03-04  
**Version:** 1.0  

---

## Table of Contents

1. [Introduction](#introduction)
2. [Prerequisites & Environment Details](#prerequisites--environment-details)
3. [Symptom: WireGuard Interface Not Coming Up After Reboot](#symptom-wireguard-interface-not-coming-up-after-reboot)
4. [Diagnosis: Checking Interface and Service Status](#diagnosis-checking-interface-and-service-status)
5. [Fix: Retrofitting systemd Unit Files](#fix-retrofitting-systemd-unit-files)
6. [Fix: Using `firewallme.sh` with systemd Integration](#fix-using-firewallmesh-with-systemd-integration)
7. [Fix: Using `sed` to Patch Broken Configs](#fix-using-sed-to-patch-broken-configs)
8. [Fix: Forcing Interface Bring-Up Manually](#fix-forcing-interface-bring-up-manually)
9. [Verification Steps](#verification-steps)
10. [Known Issues & Notes](#known-issues--notes)
11. [References](#references)

---

## Introduction

This document covers the procedure for diagnosing and resolving WireGuard VPN connectivity issues on Linux-based firewall/gateway devices, specifically in scenarios where:

- WireGuard interfaces fail to come up automatically after a reboot
- `systemd` unit files are missing, malformed, or not tied to the correct network interfaces
- The `firewallme.sh` hardening script needs to be extended to include systemd unit management for WireGuard
- Manual `sed`-based config patching is required to fix broken WireGuard configuration files

The procedures in this guide were developed and validated during a live troubleshooting session on the device and environment described below.

---

## Prerequisites & Environment Details

Before following any steps in this guide, confirm you have the following information to hand. The examples throughout this document use the values below — substitute your own where required.

### Device Under Repair

- **Hostname:** `EXAFWLEDI001`
- **Role:** Edge Firewall / WireGuard Gateway
- **OS:** Debian Server (systemd-based)
- **Primary LAN IP:** `192.168.139.x` *(confirm exact octet from device)*
- **Secondary / WireGuard-side IP:** `192.168.131.254/24`

### Network Interfaces

| Interface | Role | Notes |
|-----------|------|-------|
| `eth0` | WAN / Uplink | External-facing |
| `eth1` | LAN | Internal network |
| `wg0` | WireGuard VPN tunnel | Brought up by systemd / wg-quick |

> ***NB:** Interface names were explicitly provided during the session. If your device uses predictable names like `ens3`, `enp2s0`, etc., substitute accordingly throughout all commands and unit files below.*

### WireGuard Peer / Remote End

- **Remote Endpoint:** *(as configured in `/etc/wireguard/wg0.conf`)*
- **Remote Allowed IPs:** `192.168.131.0/24` *(or as applicable)*
- **Remote Public Key:** *(from peer's `wg0.conf` or `wg show`)*

### MAC Addresses

- `eth0` MAC: *(confirm with `ip link show eth0`)*
- `eth1` MAC: *(confirm with `ip link show eth1`)*

### Key Files

| File | Purpose |
|------|---------|
| `/etc/wireguard/wg0.conf` | WireGuard tunnel config |
| `/etc/systemd/system/wg-quick@wg0.service` | systemd unit (may need creating) |
| `/usr/local/bin/firewallme.sh` | Site firewall/hardening script |

---

## Symptom: WireGuard Interface Not Coming Up After Reboot

### What You See

After a reboot, the WireGuard interface `wg0` is absent:

```
$ ip link show wg0
Device "wg0" does not exist.
```

Or the interface exists but has no traffic / handshake:

```
$ wg show
interface: wg0
  public key: <key>
  private key: (hidden)
  listening port: 51820

peer: <peer-pubkey>
  endpoint: x.x.x.x:51820
  allowed ips: 192.168.131.0/24
  latest handshake: (never)
  transfer: 0 B received, 0 B sent
```

### Why This Happens

- The `wg-quick@wg0` systemd service was never enabled, so it doesn't start on boot
- The systemd unit file references an interface that doesn't exist at the time the unit fires
- `firewallme.sh` brings up firewall rules but doesn't start or enable WireGuard units
- A config file has a syntax error introduced manually or by a script, preventing `wg-quick` from parsing it

---

## Diagnosis: Checking Interface and Service Status

### Step 1 — Check if the service exists and its state

```bash
systemctl status wg-quick@wg0
```

**Broken output (service never enabled):**

```
● wg-quick@wg0.service - WireGuard via wg-quick(8) for wg0
     Loaded: loaded (/lib/systemd/system/wg-quick@.service; disabled; vendor preset: enabled)
     Active: inactive (dead)
```

Key indicator: `disabled` — the unit exists but is not set to start on boot.

**Broken output (unit file missing entirely):**

```
Unit wg-quick@wg0.service could not be found.
```

This means `wireguard-tools` is not installed, or the template unit is absent.

### Step 2 — Check WireGuard logs

```bash
journalctl -u wg-quick@wg0 -n 50 --no-pager
```

**Broken output (interface dependency issue):**

```
Mar 04 10:12:33 EXAFWLEDI001 wg-quick[1234]: [#] ip link add wg0 type wireguard
Mar 04 10:12:33 EXAFWLEDI001 wg-quick[1234]: [#] ip address add 192.168.131.254/24 dev wg0
Mar 04 10:12:33 EXAFWLEDI001 wg-quick[1234]: [#] ip link set mtu 1420 up dev wg0
Mar 04 10:12:34 EXAFWLEDI001 wg-quick[1234]: [#] wg setconf wg0 /dev/fd/63
Mar 04 10:12:34 EXAFWLEDI001 wg-quick[1234]: Warning: AllowedIP has nonzero host part
RTNETLINK answers: File exists
```

or a clean failure due to config parse error:

```
Mar 04 10:12:34 EXAFWLEDI001 wg-quick[1235]: /etc/wireguard/wg0.conf: line 9: invalid syntax
```

### Step 3 — Check the config file directly

```bash
cat /etc/wireguard/wg0.conf
```

Look for common corruption patterns: stray `=` signs, duplicate keys, missing `[Peer]` headers, or lines inadvertently joined by a script.

---

## Fix: Retrofitting systemd Unit Files

If `wg-quick@wg0` is disabled or missing, re-enable and start it:

### If the template unit exists (most common case)

```bash
# Enable so it starts on every boot
systemctl enable wg-quick@wg0

# Start it now without rebooting
systemctl start wg-quick@wg0

# Confirm it came up
systemctl status wg-quick@wg0
```

### If you need a custom override unit (e.g. to enforce interface ordering)

Create a drop-in override that waits for `eth0` and `eth1` to be up before starting:

```bash
mkdir -p /etc/systemd/system/wg-quick@wg0.service.d/
cat > /etc/systemd/system/wg-quick@wg0.service.d/override.conf << 'EOF'
[Unit]
After=network-online.target sys-subsystem-net-devices-eth0.device sys-subsystem-net-devices-eth1.device
Wants=network-online.target
BindsTo=sys-subsystem-net-devices-eth0.device

[Service]
Restart=on-failure
RestartSec=5s
EOF

systemctl daemon-reload
systemctl enable wg-quick@wg0
systemctl restart wg-quick@wg0
```

> **Why this matters:** Without `After=` constraints, `wg-quick` can fire before the physical NICs are registered, causing it to fail silently or leave the tunnel in a broken state after reboot. The device coming back up correctly *only after a manual restart* is a classic sign of this race condition.

---

## Fix: Using `firewallme.sh` with systemd Integration

`firewallme.sh` is the site hardening/firewall script. It should both apply iptables/nftables rules **and** ensure WireGuard is running. The systemd integration block should be added near the end of the script, after firewall rules are applied.

### What was added to `firewallme.sh`

```bash
# ─── WireGuard systemd integration ───────────────────────────────────────────
# Ensure wg-quick@wg0 is enabled and running after firewall rules are applied.
# Interface names: WAN=eth0, LAN=eth1, VPN=wg0

WG_IFACE="wg0"

echo "[*] Ensuring WireGuard systemd unit is enabled for ${WG_IFACE}..."

# Enable at boot if not already
if ! systemctl is-enabled --quiet "wg-quick@${WG_IFACE}"; then
    systemctl enable "wg-quick@${WG_IFACE}"
    echo "[+] Enabled wg-quick@${WG_IFACE}"
else
    echo "[=] wg-quick@${WG_IFACE} already enabled"
fi

# Start/restart if not active
if ! systemctl is-active --quiet "wg-quick@${WG_IFACE}"; then
    systemctl start "wg-quick@${WG_IFACE}"
    echo "[+] Started wg-quick@${WG_IFACE}"
else
    echo "[=] wg-quick@${WG_IFACE} already active"
fi
# ─────────────────────────────────────────────────────────────────────────────
```

This ensures that whenever `firewallme.sh` is run (at boot via rc.local, cron, or manually), WireGuard is also guaranteed to be up.

---

## Fix: Using `sed` to Patch Broken Configs

When a WireGuard config file has been corrupted — e.g. by a previous script run, manual editing, or copy-paste error — `sed` can be used to fix it in-place without opening an editor.

### Common corruption: duplicate `Address` line

**Broken `/etc/wireguard/wg0.conf` snippet:**

```
[Interface]
Address = 192.168.131.254/24
Address = 192.168.131.254/24     ← duplicate introduced by script re-run
PrivateKey = <key>
ListenPort = 51820
```

**Fix with `sed`:**

```bash
# Remove exact duplicate lines (keeps first occurrence)
awk '!seen[$0]++' /etc/wireguard/wg0.conf > /tmp/wg0.conf.fixed && mv /tmp/wg0.conf.fixed /etc/wireguard/wg0.conf
```

### Common corruption: stray characters injected into a key line

**Broken output:**

```
PrivateKey = ABC123==XYZ   ← trailing garbage after base64 key
```

**Fix with `sed` (strip everything after the valid base64 key):**

```bash
sed -i 's/^\(PrivateKey = [A-Za-z0-9+/=]*\).*/\1/' /etc/wireguard/wg0.conf
```

Same pattern applies to `PublicKey` and `PresharedKey`.

### Common corruption: missing newline before `[Peer]` block

**Broken output:**

```
ListenPort = 51820[Peer]    ← no newline between sections
PublicKey = <peer-key>
```

**Fix with `sed`:**

```bash
sed -i 's/\(51820\)\(\[Peer\]\)/\1\n\2/' /etc/wireguard/wg0.conf
```

### Common corruption: wrong AllowedIPs (non-zero host part warning)

**Broken output / warning:**

```
Warning: AllowedIP has nonzero host part: 192.168.131.254/24
```

This means the host IP was used instead of the network address.

**Fix:**

```bash
sed -i 's|AllowedIPs = 192\.168\.131\.254/24|AllowedIPs = 192.168.131.0/24|' /etc/wireguard/wg0.conf
```

Always verify the result after any `sed` patch:

```bash
cat /etc/wireguard/wg0.conf
wg-quick strip wg0   # dry-run parse, shows what wg would see
```

---

## Fix: Forcing Interface Bring-Up Manually

When you need to bring WireGuard up immediately without a full reboot:

```bash
# Bring down cleanly first if partially up
wg-quick down wg0 2>/dev/null || true

# Bring up
wg-quick up wg0

# Verify
wg show
ip addr show wg0
```

If `wg-quick up wg0` fails with a config parse error, always run the strip check first:

```bash
wg-quick strip wg0
```

This shows the parsed config without applying it — useful for spotting syntax issues before committing.

---

## Verification Steps

After any fix, confirm the following:

### 1. Interface is up with correct IP

```bash
ip addr show wg0
```

Expected:

```
4: wg0: <POINTOPOINT,NOARP,UP,LOWER_UP> mtu 1420 qdisc noqueue state UNKNOWN
    link/none
    inet 192.168.131.254/24 scope global wg0
```

### 2. Handshake established

```bash
wg show
```

Look for a recent `latest handshake` timestamp (within the last 2 minutes if traffic is flowing):

```
peer: <peer-pubkey>
  endpoint: x.x.x.x:51820
  allowed ips: 192.168.131.0/24
  latest handshake: 42 seconds ago
  transfer: 1.23 MiB received, 456 KiB sent
```

### 3. Routing is correct

```bash
ip route show | grep 192.168.131
```

### 4. systemd unit is enabled and active

```bash
systemctl is-enabled wg-quick@wg0   # should print: enabled
systemctl is-active wg-quick@wg0    # should print: active
```

### 5. Survives reboot

```bash
reboot
# After coming back up:
systemctl status wg-quick@wg0
wg show
```

---

## Known Issues & Notes

- **Race condition on boot:** On this device, WireGuard failed to come up automatically until a manual restart was performed. Root cause was the systemd unit firing before the physical NICs (`eth0`, `eth1`) were registered. Resolved by adding `After=` and `BindsTo=` directives in the drop-in override as described above.

- **`firewallme.sh` idempotency:** The `systemctl enable` call in `firewallme.sh` is safe to run multiple times — it is a no-op if already enabled.

- **Config file permissions:** `/etc/wireguard/wg0.conf` must be `chmod 600` and owned by `root`. If permissions are wrong, `wg-quick` will refuse to load it:

  ```bash
  chmod 600 /etc/wireguard/wg0.conf
  chown root:root /etc/wireguard/wg0.conf
  ```

- **After editing config, always restart the service — don't just reload:**

  ```bash
  systemctl restart wg-quick@wg0
  ```

  There is no live reload for WireGuard config via systemd; the interface must be torn down and re-created.

---

## References

- `wg(8)` man page — WireGuard control interface
- `wg-quick(8)` man page — WireGuard quick-start helper
- `systemd.unit(5)` — systemd unit file format
- `/usr/local/bin/firewallme.sh` — Site firewall hardening script (internal)
- WireGuard official docs: https://www.wireguard.com/

---

**Document End**  
*Internal Use Only — Network Engineering*  
*For questions or corrections, raise a ticket in the internal helpdesk.*

---
