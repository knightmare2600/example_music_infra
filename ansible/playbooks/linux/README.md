# linux/ — Common Tools for Every Linux Host

Example Music Limited — `jukebox.internal` estate

## Overview

`tools.yml` is a single, `hosts: all` playbook meant to be run against every Linux host in the
fleet (Proxmox nodes, firewalls, Rudder servers, the Ansible control node itself) — it deploys
the common baseline every Linux box needs, regardless of role. Idempotent, safe to re-run
routinely as a sweep alongside role-specific plays.

| File | What it does |
|------|---------------|
| `tools.yml` | Common packages, zsh default shell, `/etc/example-music/` deploy (`sites.csv`, `devices.csv`, `address_policy.json`, `ad_forest.json`, `ad_groups.json`/`ad_users.json`/`ad_computers.json`), dotfiles (`.vimrc`, `.vim/`, `.zshrc`, `.gitconfig`, `.tmux.conf`) to every real user home directory, optional user creation, `nodeinfo.json` (best-effort, environment-aware) |

`files/` holds the dotfiles pushed by the tasks above — plain `win_copy`/`copy` sources, not
templated.

---

## Why `/etc/example-music/` is populated here

This is the one and only mechanism that deploys `benarbejde/`'s Ansible-consumed CSVs/JSON to
`/etc/example-music/` on every Ansible-managed Linux host — including the control node itself,
which needs it for `group_vars/all/vars.yml`'s `ad_forest_json_path`-based lookups (`exa_domain`,
etc.). See `docs/ansible/beginners_guide_to_ansible.md`'s "Two separate deploy mechanisms"
section for the full explanation of why this is distinct from `.githooks/pre-commit`'s sync to
`bootstrap/web/proxmox/` (a different mechanism, for a different audience — pre-Ansible/PXE
consumers, not Ansible itself).

**If a host's `/etc/example-music/` copy is missing or stale, this is the playbook to (re-)run
against it** — not a git hook, not a manual copy.

---

## Usage

Run from the `ansible/` root:

```bash
ansible-playbook playbooks/linux/tools.yml -i configs/inventory
```

Prompts for optional usernames to create (space-separated, blank to skip) if any are needed on
top of the standard `ansible`/role-specific accounts.

---

## Changelog

- 2026-07-15  Added this README — the module had no directory-level doc coverage (found during
  a docs-drift audit). See `tools.yml`'s own header changelog for the file's full history.
