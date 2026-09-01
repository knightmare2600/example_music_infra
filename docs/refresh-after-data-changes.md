# Refreshing deployed data after a `benarbejde/` change

**Classification:** Internal — Infrastructure
**Doc ID:** OPS-REFRESH-001

Editing `benarbejde/sites.csv`/`devices.csv`/`role_codes.csv`/`address_policy.csv`
and regenerating the repo's own derived files (see
[adding-a-new-device.md](adding-a-new-device.md)) only fixes what's committed to
git. Several hosts keep their **own separate deployed copy** of that data on
disk, and nothing refreshes those automatically — Robert, 2026-08-06, after a
live DNS/PVE mix-up this week that traced back to exactly this: "it needs a
small doc... where it says 'the following playbooks need run on the following
hosts.'"

## What's already protected automatically

The Ansible **control node's own** `/etc/example-music/*` copy is gated —
`ansible/tasks/example_music_freshness_gate.yml`, included as the first
`pre_tasks` entry in every one of the following playbooks, fails the whole
play loudly and immediately if the control node's own copy is stale, rather
than crashing cryptically deep inside `generate_inventory.py` the way the
original 2026-07-26 incident did:

- `ansible/playbooks/bind9/bind9-dns.yml`
- `ansible/playbooks/rudder/rudder_server.yml`
- `ansible/playbooks/meshcentral/meshcentral_server.yml`
- `ansible/playbooks/tacticalrmm/tacticalrmm_server.yml`
- `ansible/playbooks/firewallme/playbooks/90-firewall.yml`
- `ansible/playbooks/firewallme/playbooks/add-wg-spoke.yml`
- `ansible/playbooks/linux/rename-host.yml`
- `ansible/playbooks/salt/playbooks/10-master.yml`
- `ansible/playbooks/windows_adschema/playbooks/10-ad-schema.yml`
- `ansible/playbooks/windows_adschema/playbooks/20-ad-groups.yml`
- `ansible/playbooks/windows_adschema/playbooks/30-ad-users.yml`
- `ansible/playbooks/windows_adschema/playbooks/40-ad-computers.yml`
- `ansible/playbooks/windows_bootstrap/playbooks/00-preflight.yml`
- `ansible/playbooks/windows_dc/playbooks/00-dc-preflight.yml`

`check_data_refresh_doc_coverage.py` (check 35) keeps this list honest —
it fails if a future playbook starts including the gate without this list
being updated to match. **If your playbook run goes through the control
node, you're covered — you'll get told, not silently served stale data.**

## What isn't protected — the actual gap

Any host with its **own** locally-deployed `/etc/example-music/*` copy, read
by something running **directly on that host** rather than via an
Ansible-mediated `delegate_to`/`lookup`, has no equivalent gate.
`bootstrap/web/proxmox/create-vm.py` on a Proxmox node is the confirmed real
case (2026-08-05/06: printed "Unknown role code" for a genuinely valid role,
because that PVE node's own `/etc/example-music/role_codes.csv` predated the
role being added — the repo and the control node were both already correct,
only that one node's own copy was stale).

`ansible/playbooks/linux/tools.yml` is **the only playbook that deploys
`benarbejde/*` to `/etc/example-music/*`** anywhere (control node included —
the gate above only checks freshness, it doesn't deploy). It targets
`groups['all']` (every managed host, PVE nodes included) minus
`groups['ssh_preflight_skip']`.

## Recommended — weekly control-node refresh

Run this against the Ansible control node itself, on a regular schedule (weekly is a reasonable
default), rather than only when the gate above actually catches a stale copy:

```
ansible-playbook playbooks/linux/tools.yml --limit EXAANSCLD001
```

The gate is a reactive backstop — it stops a run before it does anything wrong on stale data, but
it only fires at the moment you happen to run one of the 14 gated playbooks. A live incident
2026-09-01 (`EXAFWLATL001` firewall onboarding test) hit exactly this: the control node's own
`sites.csv` had drifted stale from earlier `benarbejde/` edits made days before, and the gate
correctly caught it — but only after the operator had already started the firewall run. Refreshing
proactively on a routine cadence means the gate rarely has anything to catch in the first place,
rather than being the thing that tells you mid-run.

## The checklist

After any edit to `benarbejde/sites.csv`/`devices.csv`/`role_codes.csv`/
`address_policy.csv` (and the regeneration steps in
[adding-a-new-device.md](adding-a-new-device.md)):

| If you're about to... | Re-run this first |
|---|---|
| Run `create-vm.py`, or anything else that reads `/etc/example-music/*` **directly on a Proxmox node** | `ansible-playbook playbooks/linux/tools.yml --limit <that PVE node>` |
| Run any of the 14 gated playbooks listed above | Nothing extra — the gate catches a stale control-node copy for you |
| Expect a new/changed device to resolve in DNS | `ansible-playbook playbooks/bind9/bind9-dns.yml --tags zones-full,reload` against `EXADNSVRK001` |
| Run anything else, on any other host, that reads `/etc/example-music/*` directly (not via the control node) | `ansible-playbook playbooks/linux/tools.yml --limit <that host>` |

When in doubt: `linux/tools.yml` is cheap and idempotent to re-run against a
specific host with `--limit` — if you're not sure whether a host's copy is
current, just re-run it.

## Why this isn't (and can't be) a harness check

`at_have_ryggen_fri` is deliberately clone-safe — every check runs against
files in this git checkout, never a live host (see
`at_have_ryggen_fri/README.md`). Whether a specific remote host's
`/etc/example-music/*` is stale is live-host state the harness has no way to
observe from a bare clone. `check_control_node_freshness.py` (check 24) is
the one narrow exception — it only checks host-local state when run *on* a
host that happens to have `/etc/example-music/` present (e.g. run directly on
the control node itself), and skips cleanly everywhere else. This doc is the
substitute for a check that structurally can't exist: a static reminder of
which playbook fixes which gap, not an automated detector of which host is
currently out of date.
