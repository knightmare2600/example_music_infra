# Example Music Limited — WireGuard Inter-Hub Routing

> **Document ref:** NET-VPN-WG-001
> **Classification:** Internal — Infrastructure
> **Forest:** `jukebox.internal`
> **Last updated:** 2026-03-28

---

## Changelog

| Date       | Change |
|------------|--------|
| 2026-03-28 | Manual fix procedure updated with exact commands verified in production. |
|            | ODE CPH peer narrow AllowedIPs noted and fixed. CPH ListenPort added.   |
|            | BRK placeholder sections added (build planned). |
| 2026-03-28 | Initial document — hub topology, AllowedIPs rules, wg-quick route injection |

---

## Topology

```
                        ┌─────────────────────────────────────┐
                        │           PROVISIONING               │
                        │        192.168.139.0/24              │
                        │   (all hubs connect via WAN here)   │
                        └──────┬──────────────┬───────────────┘
                               │              │
                    ┌──────────┴───┐    ┌─────┴────────────┐
                    │     FAL      │    │       ODE         │
                    │ hub-primary  │    │  hub-regional     │
                    │10.0.76.0/24  │◄──►│ 10.0.126.0/24    │
                    │192.168.76.0  │    │ 192.168.126.0     │
                    └──────┬───────┘    └──────┬────────────┘
                           │                   │
            ┌──────────────┤           ┌───────┴────────────┐
            │              │           │                    │
     UK spokes          BRK hub    EU spokes             DK spokes
     (direct)        hub-regional   (direct)              (direct)
                    10.0.136.0/24
                    192.168.136.0
                           │
                  AMAPAC spokes (direct)
```

**Hub assignments:**

| Hub | Region | Direct spokes |
|-----|--------|---------------|
| FAL (Falkirk) | hub-primary | All UK sites: ABD BIR CLY COV DUN EDI GLA HAL HUL LIV LND MCR NEW PER SHE |
| ODE (Odense) | hub-regional | All EU sites: AMS BON CPH FAX GOT KGE KOR MIL MUN OSL VIE |
| BRK (Brockville) | hub-regional | All Americas + APAC: ATL CHI LAX MIA MTL NJC NYC TOR AKL MEL SYD |

**Inter-hub tunnels:**
- FAL ↔ ODE: direct tunnel
- FAL ↔ BRK: direct tunnel
- ODE ↔ CPH: (CPH is an ODE spoke, despite also being a historical hub site)
- ODE ↔ BRK: **no direct tunnel** — BRK traffic routes via FAL

---

## The `wg-quick` Route Injection Problem

WireGuard's `AllowedIPs` serve two purposes: they define which packets a peer
is allowed to send, and they are used by `wg-quick` to inject kernel routes at
startup. This is critical:

- `wg set` (live changes) updates the WireGuard peer table only — **no kernel routes added**
- `wg-quick up` / `systemctl restart wg-quick@wg0` injects kernel routes from `AllowedIPs` in the conf file
- If `AllowedIPs` in the conf is narrower than what `wg set` applied live, the routes are lost on reboot

**Consequence:** Every subnet a node needs to reach via a peer must be listed in
`AllowedIPs` in `/etc/wireguard/wg0.conf`. Not just the peer's own subnets — also
every subnet reachable *through* that peer.

---

## AllowedIPs Rules by Node Type

### Rule: each subnet appears in exactly ONE peer block per node

A subnet must never appear in two peer blocks on the same node — WireGuard will
reject the config if two peers claim the same subnet.

### Hub-primary (FAL)

| Peer | AllowedIPs must include |
|------|------------------------|
| ODE peer | ODE's own subnets + all EU spoke subnets (routed via ODE) |
| BRK peer | BRK's own subnets + all AMAPAC spoke subnets (routed via BRK) |
| Each UK spoke peer | That spoke's tunnel /32 + that spoke's LAN /24 only |

### Hub-regional (ODE)

| Peer | AllowedIPs must include |
|------|------------------------|
| FAL peer | FAL's own subnets + all UK spoke subnets (routed via FAL) |
| CPH peer | CPH's own subnets + FAL + all UK spoke subnets. CPH's DK spokes connect |
|          | directly to CPH, but ODE must accept FAL-bound return traffic arriving   |
|          | from CPH — so FAL+UK subnets must be in this peer block.                 |
| BRK peer | BRK's own subnets + all AMAPAC subnets (future — via FAL today) |
| Each EU spoke peer | That spoke's tunnel /32 + that spoke's LAN /24 only |

### Hub-regional (BRK)

| Peer | AllowedIPs must include |
|------|------------------------|
| FAL peer | FAL's own subnets + all UK spoke subnets + ODE + all EU spoke subnets |
| Each AMAPAC spoke peer | That spoke's tunnel /32 + that spoke's LAN /24 only |

### Spoke (UK — connects to FAL)

| Peer | AllowedIPs must include |
|------|------------------------|
| FAL peer | FAL subnets + all UK spokes + ODE + all EU spokes + BRK + all AMAPAC spokes |

### Spoke (EU — connects to ODE)

| Peer | AllowedIPs must include |
|------|------------------------|
| ODE peer | ODE subnets + all EU spokes + FAL + all UK spokes + BRK + all AMAPAC spokes |

### Spoke (AMAPAC — connects to BRK)

| Peer | AllowedIPs must include |
|------|------------------------|
| BRK peer | BRK subnets + all AMAPAC spokes + FAL + all UK spokes + ODE + all EU spokes |

---

## What `firewallme.sh` Now Does

`firewallme.sh` is topology-aware. When writing a spoke's hub peer block, it
automatically includes all subnets reachable via that hub — not just the hub's
own subnets. It derives this from `sites.csv` and the hub topology map baked
into the script.

When building a new firewall:

1. Run `firewallme.sh` on the new node
2. Select site code and WireGuard role
3. The script generates a complete `wg0.conf` with correct full AllowedIPs
4. The script prints a peer stanza to paste into the hub's conf
5. On the hub, paste the stanza and apply live:
   ```bash
   sudo bash -c 'wg setconf wg0 <(wg-quick strip /etc/wireguard/wg0.conf)'
   ```
6. Restart `wg-quick` on the hub to inject kernel routes:
   ```bash
   sudo systemctl restart wg-quick@wg0
   ```

---

## Manual Fix Procedure (existing nodes built before topology-aware AllowedIPs)

Do not re-run `firewallme.sh` on existing nodes. Apply these fixes in place.

### Step 1 — Diagnose: check whether the route is going the wrong way

```bash
ip route get <destination-ip>
```

If the output shows `dev ens18` instead of `dev wg0`, the kernel has no wg0
route for that subnet — the `AllowedIPs` in `wg0.conf` is too narrow.

### Step 2 — Update `AllowedIPs` in `wg0.conf` using sed

Use the exact `sed` command for the node type. Verified in production 2026-03-28.

**EU spoke (e.g. AMS) — fix ODE pubkey mismatch after ODE rebuild:**
```bash
sudo sed -i 's|zp7+QwBZRxVi9c+tLbLKcozh7sqid/ize5PyesZkDTg=|gFK4oQNKN/a2UZvoil43OvOcjp2B6gT4YQ8IUqWrZ1o=|'   /etc/wireguard/wg0.conf
sudo systemctl restart wg-quick@wg0
```

**EU spoke — expand AllowedIPs to include all cross-hub subnets:**
```bash
sudo sed -i 's|AllowedIPs = 10.0.126.0/24, 192.168.126.0/24$|AllowedIPs = 10.0.126.0/24, 192.168.126.0/24, 10.0.76.0/24, 192.168.76.0/24, 10.0.224.0/24, 192.168.224.0/24, 10.0.121.0/24, 192.168.121.0/24, 10.0.41.0/24, 192.168.41.0/24, 10.0.247.0/24, 192.168.247.0/24, 10.0.138.0/24, 192.168.138.0/24, 10.0.131.0/24, 192.168.131.0/24, 10.0.141.0/24, 192.168.141.0/24, 10.0.142.0/24, 192.168.142.0/24, 10.0.148.0/24, 192.168.148.0/24, 10.0.151.0/24, 192.168.151.0/24, 10.0.20.0/24, 192.168.20.0/24, 10.0.161.0/24, 192.168.161.0/24, 10.0.191.0/24, 192.168.191.0/24, 10.0.173.0/24, 192.168.173.0/24, 10.0.114.0/24, 192.168.114.0/24|'   /etc/wireguard/wg0.conf
sudo systemctl restart wg-quick@wg0
```

**CPH — expand AllowedIPs on the ODE peer + add ListenPort:**
```bash
sudo sed -i 's|AllowedIPs = 10.0.126.0/24, 192.168.126.0/24$|AllowedIPs = 10.0.126.0/24, 192.168.126.0/24, 10.0.76.0/24, 192.168.76.0/24, 10.0.224.0/24, 192.168.224.0/24, 10.0.121.0/24, 192.168.121.0/24, 10.0.41.0/24, 192.168.41.0/24, 10.0.247.0/24, 192.168.247.0/24, 10.0.138.0/24, 192.168.138.0/24, 10.0.131.0/24, 192.168.131.0/24, 10.0.141.0/24, 192.168.141.0/24, 10.0.142.0/24, 192.168.142.0/24, 10.0.148.0/24, 192.168.148.0/24, 10.0.151.0/24, 192.168.151.0/24, 10.0.20.0/24, 192.168.20.0/24, 10.0.161.0/24, 192.168.161.0/24, 10.0.191.0/24, 192.168.191.0/24, 10.0.173.0/24, 192.168.173.0/24, 10.0.114.0/24, 192.168.114.0/24|'   /etc/wireguard/wg0.conf
sudo sed -i '/^PrivateKey/a ListenPort = 51820' /etc/wireguard/wg0.conf
sudo systemctl restart wg-quick@wg0
```

> **Why `ListenPort` matters on CPH:** without it, CPH uses an ephemeral UDP
> source port that changes on every restart. ODE's `Endpoint` entry for CPH
> then becomes stale and the tunnel fails to re-establish until ODE sees
> incoming traffic from CPH's new port. Adding `ListenPort = 51820` makes
> the endpoint stable across reboots.

**ODE — expand CPH peer AllowedIPs (apply live, no restart needed):**
```bash
sudo sed -i '/## CPH/{n;n;s|AllowedIPs = 10.0.231.0/24, 192.168.231.0/24|AllowedIPs = 10.0.231.0/24, 192.168.231.0/24, 10.0.76.0/24, 192.168.76.0/24, 10.0.224.0/24, 192.168.224.0/24, 10.0.121.0/24, 192.168.121.0/24, 10.0.41.0/24, 192.168.41.0/24, 10.0.247.0/24, 192.168.247.0/24, 10.0.138.0/24, 192.168.138.0/24, 10.0.131.0/24, 192.168.131.0/24, 10.0.141.0/24, 192.168.141.0/24, 10.0.142.0/24, 192.168.142.0/24, 10.0.148.0/24, 192.168.148.0/24, 10.0.151.0/24, 192.168.151.0/24, 10.0.20.0/24, 192.168.20.0/24, 10.0.161.0/24, 192.168.161.0/24, 10.0.191.0/24, 192.168.191.0/24, 10.0.173.0/24, 192.168.173.0/24, 10.0.114.0/24, 192.168.114.0/24|}'   /etc/wireguard/wg0.conf
sudo bash -c 'wg setconf wg0 <(wg-quick strip /etc/wireguard/wg0.conf)'
```

> `wg setconf` applies live without dropping any tunnels. Use this on hub
> nodes where a restart would briefly disconnect all spokes. Use
> `systemctl restart wg-quick@wg0` on spoke nodes where a brief interruption
> is acceptable — it is the only way to inject new kernel routes.

### Step 3 — Verify routes were injected

```bash
ip route show | grep wg0
# Every subnet in AllowedIPs should have a corresponding wg0 route

# Spot-check a cross-hub destination
ip route get 192.168.231.253   # CPH via FAL→ODE
ip route get 192.168.76.253    # FAL via ODE→FAL (from CPH)
```

### Step 4 — Test end-to-end

```bash
# FAL → CPH (via ODE)
ping -c3 192.168.231.10

# CPH → FAL LAN
ping -c3 192.168.76.10
```

### Step 5 — Status of known fixes applied (2026-03-28)

| Node | Fix applied | Method | Verified |
|------|-------------|--------|---------|
| EXAFWLFAL001 | ODE peer AllowedIPs expanded | conf + reboot | ✓ |
| EXAFWLODE001 | FAL peer AllowedIPs expanded | conf + reboot | ✓ |
| EXAFWLODE001 | CPH peer AllowedIPs expanded | wg setconf (live) | ✓ |
| EXAFWLCPH001 | ODE peer AllowedIPs expanded | conf + restart | ✓ |
| EXAFWLCPH001 | ListenPort = 51820 added | conf + restart | `[PENDING]` |
| EXAFWLAMS001 | ODE pubkey corrected | sed + restart | ✓ |
| All other EU spokes | ODE pubkey — check needed | sed if required | `[TODO]` |

---

## Adding a New Spoke — Checklist

When `firewallme.sh` runs on a new spoke it prints a peer stanza. After
completing the new firewall setup:

- [ ] Paste the peer stanza into the hub's `/etc/wireguard/wg0.conf`
- [ ] Apply live on hub: `sudo bash -c 'wg setconf wg0 <(wg-quick strip /etc/wireguard/wg0.conf)'`
- [ ] Restart hub wg-quick to inject kernel routes: `sudo systemctl restart wg-quick@wg0`
- [ ] Verify handshake: `sudo wg show wg0` — new peer should show a recent handshake
- [ ] Test connectivity from new spoke to hub LAN
- [ ] Test connectivity from new spoke to a cross-hub site (e.g. UK→CPH, EU→FAL)
- [ ] Update `hosts.txt` and `inventory.txt` via `site-inventory-audit.py --generate-hosts --generate-inventory`

---

## BRK — Build Checklist (planned, week of 2026-04-07)

> **[PLACEHOLDER]** BRK (Brockville, Canada) is the AMAPAC hub. Build is
> planned for the week of 2026-04-07. Complete this section once built.

### Pre-build: what FAL needs when BRK comes online

When `firewallme.sh` runs on BRK and selects `hub-regional`, it will print a
peer stanza to add to FAL. Paste it into FAL's `wg0.conf` under the BRK peer
comment block that is already there:

```ini
## BRK
[Peer]
PublicKey = <BRK-public-key>
Endpoint = 192.168.139.136:51820
AllowedIPs = 10.0.136.0/24, 192.168.136.0/24, 10.0.33.0/24, 192.168.33.0/24,
             10.0.214.0/24, 192.168.214.0/24, 10.0.213.0/24, 192.168.213.0/24,
             10.0.135.0/24, 192.168.135.0/24, 10.0.154.0/24, 192.168.154.0/24,
             10.0.201.0/24, 192.168.201.0/24, 10.0.212.0/24, 192.168.212.0/24,
             10.0.146.0/24, 192.168.146.0/24, 10.0.93.0/24, 192.168.93.0/24,
             10.0.61.0/24, 192.168.61.0/24, 10.0.29.0/24, 192.168.29.0/24
PersistentKeepalive = 25
```

Apply on FAL without restarting:
```bash
sudo bash -c 'wg setconf wg0 <(wg-quick strip /etc/wireguard/wg0.conf)'
```

### Post-build: what ODE needs

ODE has no direct tunnel to BRK — AMAPAC traffic routes via FAL. ODE does
not need a BRK peer block. AMAPAC subnets will be reachable from ODE spokes
via ODE→FAL→BRK automatically once FAL's BRK peer is live.

### Post-build: BRK build checklist

- [ ] `firewallme.sh` run, role: `hub-regional`, site: `BRK`
- [ ] BRK public key recorded in password manager
- [ ] BRK peer stanza pasted into FAL `wg0.conf` and applied live
- [ ] FAL→BRK tunnel handshake confirmed: `sudo wg show wg0`
- [ ] FAL→BRK LAN ping: `ping -c3 192.168.136.253`
- [ ] Update `HUB_KNOWN_PUBKEY[BRK]` in `firewallme.sh` with verified pubkey
- [ ] AMAPAC spokes built using `firewallme.sh` — select hub: `BRK`
- [ ] Cross-hub test: UK spoke → ATL (via FAL→BRK→ATL)
- [ ] Cross-hub test: EU spoke → SYD (via ODE→FAL→BRK→SYD)
- [ ] `site-inventory-audit.py --generate-hosts --generate-inventory` re-run

---

## Known Hub Endpoints (provisioning network)

| Hub | WAN IP (provisioning) | WG Listen Port | Tunnel IP |
|-----|----------------------|----------------|-----------|
| FAL | 192.168.139.76 | 51820 | 10.0.76.1 |
| ODE | 192.168.139.126 | 51820 | 10.0.126.1 |
| BRK | 192.168.139.136 | 51820 | 10.0.136.1 (planned) |

> Public keys are stored on each hub at `/etc/wireguard/public.key`.
> `firewallme.sh` fetches them live via SSH during spoke setup.
> Do not store private keys in this document.

---

*Example Music Limited — Internal Infrastructure Documentation*
*Do not distribute outside the organisation*
*Credentials: See password manager — never store passwords in this document*
