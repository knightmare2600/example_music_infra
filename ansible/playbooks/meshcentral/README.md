# playbooks/meshcentral/

Bootstraps `EXAMSHCLD001` (or any MeshCentral server) from a fresh Debian
Trixie install to a running MeshCentral remote management server. Remote
management platform, phase 1/2 — see `ansible/README.md`'s `## meshcentral`
section and project notes for the full brief.

Does **not** replace SaltStack (config management stays Salt's job) or
Chocolatey (Windows package management stays Chocolatey's job) — MeshCentral
is a pure remote-access platform: remote desktop, remote terminal, interactive
PowerShell/CMD, Linux shell, file transfer.

TLS is self-signed (MeshCentral's own zero-config default), not Let's
Encrypt — this box is strictly internal/WireGuard-only (confirmed with
Robert, 2026-08-04), and ACME validation needs public DNS + inbound 80/443
from the internet, neither of which apply here.

## Files

| File | What it does |
|------|-------------|
| `meshcentral_server.yml` | Entry point — hostname, static IP, base packages, UFW, Node.js, MeshCentral install, config, systemd, MOTD, nodeinfo |
| `templates/mesh-static.nmconnection.j2` | NetworkManager static-IP profile, session-safe templated-keyfile pattern (same as `rudder/templates/rudder-static.nmconnection.j2`) |

## Quick start

**Step 1 — Inventory is already in `configs/inventory/meshcentral.ini`.**

**Step 2 — host_vars are pre-filled** (`host_vars/EXAMSHCLD001/main.yml`) —
static IP `192.168.69.13`, CLD LAN.

**Step 3 — First run (root login, before ansible user exists)**

```bash
ansible-playbook playbooks/meshcentral/meshcentral_server.yml \
  --limit meshcentral_servers \
  --user root -k
```

**Step 4 — Subsequent runs**

```bash
ansible-playbook playbooks/meshcentral/meshcentral_server.yml \
  --limit meshcentral_servers
```

**Step 5 — First login**: browse to `https://192.168.69.13/` and create the
initial admin account through MeshCentral's own web UI (no scripted admin
bootstrap yet — see "Not yet built" below).

## Not yet built

- **Scripted initial-admin-account creation.** First login currently has to
  go through MeshCentral's own web UI setup flow manually.
- **Live-tested against real hardware.** Sections 1-4 (hostname/network/
  packages/firewall) are a direct, proven adaptation of `rudder_server.yml`'s
  own live-tested pattern — only variable names changed. Sections 5-10 (the
  actual Node.js/MeshCentral install, config, systemd) are new, built from
  MeshCentral's own public documentation, and have not been run against a
  real Debian Trixie box. Test before relying on this unattended.
- **TacticalRMM, reverse proxy, monitoring, logging, backups, hardening,
  disaster recovery** — later phases of the remote management platform
  brief, not started.
