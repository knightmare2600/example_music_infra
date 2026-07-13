# Procedure: Proxmox VE Node Onboarding

**Reference:** `playbooks/proxmox/site.yml`  
**Scope:** Example Music Limited — Infrastructure  
**Applies to:** Any new Proxmox VE node added to the estate

---

## Overview

New PVE nodes arrive in a known state from our PXE/iPXE first-boot installer: Debian Trixie, `ansible` user created, SSH accessible as root. This procedure verifies that state and completes Ansible management setup using `site.yml`.

> **If this node was built via `playbooks/proxmox/bootstrap-new-node.yml`** (the normal path for a brand-new node still on its DHCP IP), all of this already happened automatically — as of 2026-07-12 that playbook chains straight into this entire `site.yml` stage table in the same run, then reboots once at the end. You don't need to run anything from this procedure separately afterward. This procedure is for running/re-running `site.yml` on its own — a node built some other way, or a deliberate standalone refresh (see the "Forcing a full re-onboard" section below).

`site.yml` chains eight numbered stages:

| Stage | Purpose | Runs on a refresh of an already-onboarded node? |
|---|---|---|
| `00-preflight.yml` | Site lookup (`sites.csv`) + detect whether this node is already onboarded | Always |
| `10-packages.yml` | Management packages (`apt`) | Always |
| `20-ansible-access.yml` | ansible user, SSH key, sudoers, kvm group | **Only on first onboard**, or with `-e pve_force_full_onboard=true` |
| `30-example-music.yml` | `/etc/example-music/{sites,devices}.csv` + `nodeinfo.json` | Always |
| `40-scripts.yml` | Maintenance scripts, apt config, NIC-guard credentials dir | Always |
| `45-virt-tools.yml` | V2V/VirtIO prerequisites, optional proxmoxbmc/BIOS ROM files (file placement only) | Always |
| `46-proxmorph.yml` | proxmorph PVE web UI themes + optional hardware sensor monitoring | Always |
| `50-systemd-units.yml` | systemd units, timers, Zabbix agent (restarts it) | **Only on first onboard**, or with `-e pve_force_full_onboard=true` |

The playbook is idempotent and safe to re-run. It does not rebuild the node — it only ensures the minimum management surface is in place, and by default a re-run against an already-onboarded node **skips anything that touches access or live service state** (stages 20 and 50) so routine refreshes can't disrupt a running hypervisor. Pass `-e pve_force_full_onboard=true` if you deliberately want those stages to run again (e.g. the SSH key was rotated, or a unit file changed and you want it reloaded).

---

## Prerequisites

| Requirement | Detail |
|---|---|
| Ansible management node | `EXAANSCLD001` (or site equivalent), bootstrapped via `ansibleme.sh` |
| Network reachability | Ansible node can reach the target PVE node on port 22 |
| Root SSH access | Password-based root login must be available on the new PVE node |
| Inventory updated | PVE node IP/hostname must be in `[pvenodes]` in `configs/inventory` |
| Enterprise repo resolved | PVE no-subscription repo must be in place (handled at PXE install time) |
| Hostname follows convention | `EXAPVE<SITE><NNN>` (e.g. `EXAPVEFAL001`) — `00-preflight.yml` parses the site code from this to look up `sites.csv` |

> **Note:** If the node was provisioned by our PXE installer, the `ansible` user already exists. The playbook will verify this and skip creation if present.

> **Circular-dependency warning — read this before using this procedure for a brand-new site's very first PVE node:**
> This procedure runs `site.yml` *from* an Ansible control node against the target PVE node. That means it presupposes
> a working Ansible control node already exists — which itself normally runs as a VM *on* a PVE node. For the very
> first PVE node at a new site (the one that will eventually host that site's own `EXAANS<SITE>001`, if it has one,
> or that leans on the estate's existing `EXAANSCLD001`), this is not circular in practice, because `EXAANSCLD001`
> already exists and can onboard any new PVE node anywhere, including a brand-new site's first one. It only becomes
> genuinely circular if you are trying to bootstrap `EXAANSCLD001` itself, or any Ansible control node, from scratch
> with no other Ansible control node reachable — in that specific case, `bootstrap/web/provision/ansibleme.sh` is the
> break-glass path (it clones this repo and configures itself directly on the target box over SSH, without needing
> an existing Ansible control node to drive it), not this procedure. Run `ansibleme.sh` first in that case, then come
> back here for every PVE node after that.

---

## 1. Verify the node is in the inventory

On `EXAANSCLD001`, as the `ansible` user:

```bash
cat ~/ansible/configs/inventory
```

The target node should appear under `[pvenodes]`. If it is missing, add it:

```ini
[pvenodes]
192.168.69.5    # EXAPVECLD001
192.168.20.x    # EXAPVELND001  ← add new node here
```

---

## 2. Confirm network reachability

```bash
ssh root@<node-ip>
```

You should get a root prompt. Exit once confirmed. If this fails, check:

- The node has completed first-boot (check Proxmox console)
- The firewall/WireGuard route between sites is up
- The node IP matches what is in the inventory

---

## 3. (Optional) Pre-flight check — verify ansible user exists

If you want to confirm the PXE installer did its job before running the playbook:

```bash
ssh root@<node-ip> "id ansible && cat /home/ansible/.ssh/authorized_keys 2>/dev/null | head -1 || echo 'no key yet'"
```

Expected output:

```
uid=1001(ansible) gid=1001(ansible) groups=1001(ansible)
no key yet
```

The user exists but has no key yet — that is the correct pre-onboarding state. If `id ansible` fails entirely, the PXE install did not complete correctly. The playbook will still create the user, but investigate why the first-boot did not run.

---

## 4. Run the onboarding playbook

From `~/ansible/` on the Ansible node, run as the `ansible` user:

```bash
ansible-playbook playbooks/proxmox/site.yml -i configs/inventory --user=root -k --limit <node-ip-or-hostname>
```

`-k` prompts for the root SSH password. `--limit` scopes the run to the specific node if you do not want to run against all `[pvenodes]` at once.

You will be prompted:

```bash
SSH password:
```

Enter the root password set during PXE install.

### Expected output (first-ever onboard — every stage runs)

Six plays run in sequence, one per stage. Abbreviated:

```bash
PLAY [Proxmox VE — Preflight (site lookup, onboarding-state detection)] ********
TASK [Gathering Facts] **********************************************************
TASK [Include hostname facts] ***************************************************
TASK [Load sites.csv] ************************************************************
TASK [Show preflight summary] ****************************************************
ok: [192.168.20.x] => {
    "msg": [
        "Host          : 192.168.20.x (site=LND)",
        "Site data     : city=London country=United Kingdom entity=Example Music Limited",
        "Already onboarded : False",
        "Full onboard run  : True ",
        ""
    ]
}

PLAY [Proxmox VE — Management packages] ******************************************
TASK [Install management packages] ***********************************************
changed: [192.168.20.x]

PLAY [Proxmox VE — Ansible user and access setup] ********************************
TASK [Verify ansible user exists (created by PXE installer; created here if missing)]
ok: [192.168.20.x]       ← "ok" means PXE did its job; "changed" means it was created now
TASK [Ensure ansible SSH public key is authorised] *******************************
changed: [192.168.20.x]
TASK [Deploy sudoers drop-in (validate before placing)] **************************
changed: [192.168.20.x]
TASK [Ensure ansible is in kvm group (needed for virt-customize)] ****************
changed: [192.168.20.x]

PLAY [Proxmox VE — /etc/example-music deployment] ********************************
TASK [Deploy sites.csv to /etc/example-music] ************************************
changed: [192.168.20.x]
TASK [Deploy devices.csv to /etc/example-music] **********************************
changed: [192.168.20.x]
TASK [Write /etc/example-music/nodeinfo.json] ************************************
changed: [192.168.20.x]

PLAY [Proxmox VE — Maintenance scripts] ******************************************
TASK [Deploy PVE scripts to /usr/local/bin] **************************************
changed: [192.168.20.x]

PLAY [Proxmox VE — Systemd units and Zabbix agent] *******************************
TASK [Deploy PVE maintenance systemd units] **************************************
changed: [192.168.20.x]
TASK [Enable and start PVE maintenance timers] ***********************************
changed: [192.168.20.x]

PLAY RECAP ************************************************************************
192.168.20.x : ok=NN  changed=NN  unreachable=0  failed=0
```

A `failed=0` result on every play means onboarding succeeded.

### Expected output (refresh of an already-onboarded node)

```bash
TASK [Show preflight summary] ****************************************************
ok: [192.168.20.x] => {
    "msg": [
        ...
        "Already onboarded : True",
        "Full onboard run  : False ",
        "Access-setup and systemd-units stages will be SKIPPED this run — pass -e pve_force_full_onboard=true to force them."
    ]
}
...
PLAY [Proxmox VE — Ansible user and access setup] ********************************
TASK [Skip — already onboarded, access setup not requested] *********************
ok: [192.168.20.x] => {"msg": "192.168.20.x is already onboarded — skipping access setup..."}
...
PLAY [Proxmox VE — Systemd units and Zabbix agent] *******************************
TASK [Skip — already onboarded, systemd units not requested] ********************
ok: [192.168.20.x] => {"msg": "192.168.20.x is already onboarded — skipping systemd units..."}
```

Packages, `/etc/example-music/`, and scripts still refresh normally — only access setup and systemd/Zabbix are skipped.

### Forcing a full re-onboard of an already-onboarded node

```bash
ansible-playbook playbooks/proxmox/site.yml -i configs/inventory -e target=<node-ip-or-hostname> -e pve_force_full_onboard=true
```

Use this when the SSH key was rotated, sudoers content changed, or a systemd unit file changed and you want it reloaded/restarted on a live node. Since this restarts `zabbix-agent` and reloads systemd, prefer running it outside of any active maintenance/backup window.

---

## 5. Verify key-based access

Once the playbook completes, confirm that the `ansible` user can now log in without a password:

```bash
ssh -i ~/ansible/configs/ansible-id_rsa ansible@<node-ip> "hostname && id"
```

Expected:

```
EXAPVELND001
uid=1001(ansible) gid=1001(ansible) groups=1001(ansible),5(kvm)
```

If this succeeds, the node is fully onboarded.

---

## 6. Smoke-test via Ansible

```bash
ansible pvenodes -i configs/inventory -m ping --limit <node-ip>
```

Expected:

```yaml
192.168.20.x | SUCCESS => {
    "changed": false,
    "ping": "pong"
}
```

Also worth checking that `/etc/example-music/nodeinfo.json` looks right:

```bash
ansible pvenodes -i configs/inventory --limit <node-ip> -m ansible.builtin.slurp -a "src=/etc/example-music/nodeinfo.json" \
  | python3 -c "import json,sys,base64; d=json.load(sys.stdin); print(base64.b64decode(d['content']).decode())"
```

Expected fields: `role: "proxmox"`, `site`, `city`, `country`, `entity` (from `sites.csv`), `ansible_managed: true`, `bootstrapped_by: "proxmox/site.yml"`.

---

## 7. All subsequent playbooks

After onboarding, all playbooks targeting this node run as the `ansible` user with key-based auth and passwordless sudo — no `-k` flag required:

```bash
# Deploy management tools
ansible-playbook playbooks/linux/tools.yml -i configs/inventory --limit <node-ip>

# Build cloud-init templates (Ubuntu Noble + Debian Trixie)
ansible-playbook playbooks/proxmox/cloud_templates.yml -i configs/inventory --limit <node-ip>

# Routine refresh (packages/example-music/scripts only — safe, no override needed)
ansible-playbook playbooks/proxmox/site.yml -i configs/inventory --limit <node-ip>
```

---

## Troubleshooting

### UNREACHABLE — port 22 connection refused

The node may still be in first-boot. Wait 2–3 minutes and retry. Check the Proxmox console for the boot status.

### UNREACHABLE despite port 22 being open — SSH keypair preflight failure

Found the hard way, 2026-07-12: `bootstrap-new-node.yml` failed `UNREACHABLE` against a real node even though `nmap` confirmed port 22 was open. The real cause — the control node's own `ansible-id_rsa` private key had gone missing — was hidden behind `exa_pretty`'s terse `other=1` summary; only `-vvv` or a plain manual `ssh` invocation showed it.

`bootstrap-new-node.yml` and `00-preflight.yml` (and therefore `site.yml`) now each run a leading, separate SSH keypair preflight play first (`ansible/tasks/ssh_key_preflight.yml`) — a real `ssh` connectivity test using the exact key `ansible.cfg`'s `private_key_file` points at, run **before** Ansible's own connection attempt gets a chance to fail obscurely. This is a **showstopper, not a warning**: if the key is missing, or present but the connection test still fails, the play fails immediately with the real `ssh` stderr shown in full, and nothing further runs against that host.

If you hit this:

1. Run `ansible/at_have_ryggen_fri/run.sh --strict` (check 11, `check_ssh_keys.py`) — on the real control node this checks whether the configured private key is actually present, and if not, scans `~/.ssh/` for a plausible existing candidate (any `.pub` whose comment contains "exa").
2. If a genuine, matching keypair turns up: **never** move or copy the private half into this repo, anywhere, full stop. Only the public half is ever committed/served, and only in these three places (keep all three in sync if the key is ever rotated):
   - `ansible/configs/ansible-id_rsa.pub` (gitignored locally, but read by `ansible.cfg`'s connection)
   - `bootstrap/web/ansible_sshkey.pub` (the one committed, HTTP-servable copy)
   - `bootstrap/web/proxmox/VRK-answer.toml` / `FRD-answer.toml`'s `root-ssh-keys`
3. If no matching keypair can be found, the private key is genuinely, not just apparently, lost — regenerate on the control node directly (matches `bootstrap/web/provision/ansibleme.sh`'s own `ssh-keygen` invocation), then re-distribute the new public half to the three locations above and to any already-onboarded node's `~ansible/.ssh/authorized_keys`.

The preflight play can be overridden with `-e ssh_key_preflight_skip=true` for a genuine edge case (e.g. a node only reachable by password, before any key exists at all) — this is an explicit, auditable override, not a default. `00-preflight.yml` also auto-skips this check for the documented `--user=root -k` password-authenticated first-ever-onboard run below, since a broken key is irrelevant when that run isn't using one.

### FAILED — apt 401 Unauthorized

The Proxmox enterprise repo is active and no subscription key is present. Fix on the node:

```bash
echo "deb http://download.proxmox.com/debian/pve trixie pve-no-subscription" > /etc/apt/sources.list.d/pve-community.list
rm -f /etc/apt/sources.list.d/pve-enterprise.list
apt-get update
```

Then re-run the playbook. Note `10-packages.yml` already does this repo-fix automatically as its first step on every run (moved there 2026-07-10, see `first-boot.sh`) — this manual command is a fallback for the rare case where apt itself fails before Ansible can even connect.

### FAILED — sudoers validation error

The `files/sudoer_ansible` file on the Ansible node has been modified and no longer passes `visudo -c`. Verify its contents:

```bash
cat ~/ansible/files/sudoer_ansible
# Should contain exactly:
# ansible ALL=(ALL) NOPASSWD: ALL
```

This only matters if `20-ansible-access.yml` actually ran (first onboard, or `-e pve_force_full_onboard=true`) — it's skipped on a routine refresh.

### ansible user missing after PXE install

If `id ansible` fails on the new node, the first-boot script did not run or failed silently. The playbook will create the user anyway (as long as it's not skipped — see above). Investigate the PXE firstboot log at `/var/log/firstboot.log` (if present) to understand why.

### WARN — site code not found in sites.csv

`00-preflight.yml` couldn't match the node's parsed site code against any row in `sites.csv`. `nodeinfo.json`'s `city`/`country`/`entity` fields will be blank. Check the hostname follows the `EXAPVE<SITE><NNN>` convention and that `<SITE>` has a row in `benarbejde/sites.csv`.

---

## Reference

| File | Purpose |
|---|---|
| `configs/inventory` | Host groups — add new PVE nodes to `[pvenodes]` |
| `configs/ansible-id_rsa.pub` | Public key distributed to managed hosts |
| `files/sudoer_ansible` | Sudoers drop-in deployed to each node |
| `benarbejde/sites.csv`, `benarbejde/devices.csv` | Authoritative site/device registries, deployed to every node's `/etc/example-music/` |
| `playbooks/proxmox/site.yml` | This procedure's entry point — chains the eight stages below |
| `ansible/tasks/ssh_key_preflight.yml` | Real SSH connectivity preflight (showstopper) — used by both `bootstrap-new-node.yml` and `00-preflight.yml` |
| `playbooks/proxmox/playbooks/00-preflight.yml` | SSH keypair check, then site lookup + onboarding-state detection |
| `playbooks/proxmox/playbooks/10-packages.yml` | Management packages, apt repo fix, subscription nag removal |
| `playbooks/proxmox/playbooks/20-ansible-access.yml` | User/SSH key/sudoers/kvm group (gated) |
| `playbooks/proxmox/playbooks/30-example-music.yml` | `/etc/example-music/` — sites.csv, devices.csv, nodeinfo.json |
| `playbooks/proxmox/playbooks/40-scripts.yml` | Maintenance scripts, apt config, NIC-guard credentials dir, dynamic MOTD |
| `playbooks/proxmox/playbooks/45-virt-tools.yml` | V2V/VirtIO prerequisites, optional proxmoxbmc/BIOS ROM files |
| `playbooks/proxmox/playbooks/46-proxmorph.yml` | proxmorph PVE web UI themes + sensor monitoring |
| `playbooks/proxmox/playbooks/50-systemd-units.yml` | systemd units + Zabbix agent (gated) |
| `group_vars/pvenodes/main.yml` | Package list and template VMIDs |
