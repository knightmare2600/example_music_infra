# Procedure: Proxmox VE Node Onboarding
**Reference:** `playbooks/proxmox/site.yml`
**Scope:** Example Music Limited — Infrastructure
**Applies to:** Any new Proxmox VE node added to the estate

---

## Overview

New PVE nodes arrive in a known state from our PXE/iPXE first-boot installer: Debian Trixie, `ansible` user created, SSH accessible as root. This procedure verifies that state and completes Ansible management setup using `site.yml`.

`site.yml` chains six numbered stages:

| Stage | Purpose | Runs on a refresh of an already-onboarded node? |
|---|---|---|
| `00-preflight.yml` | Site lookup (`sites.csv`) + detect whether this node is already onboarded | Always |
| `10-packages.yml` | Management packages (`apt`) | Always |
| `20-ansible-access.yml` | ansible user, SSH key, sudoers, kvm group | **Only on first onboard**, or with `-e pve_force_full_onboard=true` |
| `30-example-music.yml` | `/etc/example-music/{sites,devices}.csv` + `nodeinfo.json` | Always |
| `40-scripts.yml` | Maintenance scripts, apt config, NIC-guard credentials dir | Always |
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

---

## 1. Verify the node is in the inventory

On `EXAANSCLD001`, as the `ansible` user:

```bash
cat ~/ansible/configs/inventory
```

The target node should appear under `[pvenodes]`. If it is missing, add it:

```ini
[pvenodes]
192.168.139.5   # EXAPVECLD001
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

### FAILED — apt 401 Unauthorized

The Proxmox enterprise repo is active and no subscription key is present. Fix on the node:

```bash
echo "deb http://download.proxmox.com/debian/pve bookworm pve-no-subscription" > /etc/apt/sources.list.d/pve-community.list
rm -f /etc/apt/sources.list.d/pve-enterprise.list
apt-get update
```

Then re-run the playbook.

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
| `playbooks/proxmox/site.yml` | This procedure's entry point — chains the six stages below |
| `playbooks/proxmox/playbooks/00-preflight.yml` | Site lookup + onboarding-state detection |
| `playbooks/proxmox/playbooks/10-packages.yml` | Management packages |
| `playbooks/proxmox/playbooks/20-ansible-access.yml` | User/SSH key/sudoers/kvm group (gated) |
| `playbooks/proxmox/playbooks/30-example-music.yml` | `/etc/example-music/` — sites.csv, devices.csv, nodeinfo.json |
| `playbooks/proxmox/playbooks/40-scripts.yml` | Maintenance scripts, apt config, NIC-guard credentials dir |
| `playbooks/proxmox/playbooks/50-systemd-units.yml` | systemd units + Zabbix agent (gated) |
| `group_vars/pvenodes/main.yml` | Package list and template VMIDs |
