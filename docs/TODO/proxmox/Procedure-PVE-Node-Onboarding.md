# Procedure: Proxmox VE Node Onboarding
**Reference:** `pve_onboard.yml`
**Scope:** Example Music Limited — Infrastructure
**Applies to:** Any new Proxmox VE node added to the estate

---

## Overview

New PVE nodes arrive in a known state from our PXE/iPXE first-boot installer: Debian Trixie, `ansible` user created, SSH accessible as root. This procedure verifies that state and completes Ansible management setup using `pve_onboard.yml`.

The playbook is idempotent and safe to re-run. It does not rebuild the node — it only ensures the minimum management surface is in place.

---

## Prerequisites

| Requirement | Detail |
|---|---|
| Ansible management node | `EXAANSCLD001` (or site equivalent), bootstrapped via `ansibleme.sh` |
| Network reachability | Ansible node can reach the target PVE node on port 22 |
| Root SSH access | Password-based root login must be available on the new PVE node |
| Inventory updated | PVE node IP/hostname must be in `[pvenodes]` in `configs/inventory` |
| Enterprise repo resolved | PVE no-subscription repo must be in place (handled at PXE install time) |

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
ansible-playbook playbooks/proxmox/pve_onboard.yml -i configs/inventory --user=root -k --limit <node-ip-or-hostname>
```

`-k` prompts for the root SSH password. `--limit` scopes the run to the specific node if you do not want to run against all `[pvenodes]` at once.

You will be prompted:

```bash
SSH password:
```

Enter the root password set during PXE install.

### Expected output

```bash
PLAY [pvenodes] ****************************************************************

TASK [Gathering Facts] *********************************************************
ok: [192.168.20.x]

TASK [Install management packages] *********************************************
changed: [192.168.20.x]

TASK [Verify ansible user exists (created by PXE installer; created here if missing)]
ok: [192.168.20.x]       ← "ok" means PXE did its job; "changed" means it was created now

TASK [Ensure ansible SSH public key is authorised]
changed: [192.168.20.x]

TASK [Deploy sudoers drop-in (validate before placing)]
changed: [192.168.20.x]

TASK [Ensure ansible is in kvm group]
changed: [192.168.20.x]

PLAY RECAP *********************************************************************
192.168.20.x : ok=6  changed=4  unreachable=0  failed=0
```

A `failed=0` result means onboarding succeeded.

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

---

## 7. All subsequent playbooks

After onboarding, all playbooks targeting this node run as the `ansible` user with key-based auth and passwordless sudo — no `-k` flag required:

```bash
# Deploy management tools
ansible-playbook playbooks/linux/tools.yml -i configs/inventory --limit <node-ip>

# Build cloud-init templates (Ubuntu Noble + Debian Trixie)
ansible-playbook playbooks/proxmox/cloud_templates.yml -i configs/inventory --limit <node-ip>
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

### ansible user missing after PXE install

If `id ansible` fails on the new node, the first-boot script did not run or failed silently. The playbook will create the user anyway. Investigate the PXE firstboot log at `/var/log/firstboot.log` (if present) to understand why.

---

## Reference

| File | Purpose |
|---|---|
| `configs/inventory` | Host groups — add new PVE nodes to `[pvenodes]` |
| `configs/ansible-id_rsa.pub` | Public key distributed to managed hosts |
| `files/sudoer_ansible` | Sudoers drop-in deployed to each node |
| `playbooks/proxmox/pve_onboard.yml` | This procedure's playbook |
| `group_vars/pvenodes/main.yml` | Package list and template VMIDs |
