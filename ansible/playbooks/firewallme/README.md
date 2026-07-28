# firewallme

Configures Linux firewall appliances (EXAFWL*). Ansible port of firewallme.sh.

## Dependencies
Install galaxy collections first:
```
ansible-galaxy collection install -r requirements.yml
```
(`ansible.posix` ships bundled with the full `ansible` package, already installed by this repo's
own `bootstrap/setup-workstation-*` scripts -- normally already present, declared here for
completeness on a control node set up a different way.)

## Usage

Run from the `ansible/` root:

```
ansible-playbook -i configs/inventory playbooks/firewallme/playbooks/90-firewall.yml \
  -e target=EXAFWLKGE001 --ask-vault-pass
```

## Files

| File | What it does |
|------|---------------|
| `playbooks/90-firewall.yml` | Full firewall build/reconfigure — the Ansible port of `firewallme.sh` (see below) |
| `playbooks/add-wg-spoke.yml` | Registers a new WireGuard spoke peer on a hub — SSH-fetches the spoke's live PublicKey/PSK, writes the `[Peer]` block via `blockinfile` (idempotent, per-site marker), live-applies with `wg set`. Run from the hub side: `ansible-playbook -i configs/inventory playbooks/firewallme/playbooks/add-wg-spoke.yml -e "target=<hub-host> spoke_site=<CODE> spoke_host=<spoke-host>"` |

## Tags
`firewall`, `preflight`, `interfaces`, `wan`, `wireguard`, `confirm`,
`packages`, `network`, `nftables`, `dnsmasq`, `ssh`, `cockpit`, `finish`

## SSH key preflight (2026-07-26)

`90-firewall.yml` imports `../../ssh_preflight_with_fallback.yml` first, before its own
`gather_facts: true` ever attempts a real connection. Real live failure that prompted this
(`EXAFWLAMS001`): the Ansible SSH key was rejected outright, and the play just died
`UNREACHABLE` with no recovery path. Now: tests the current key, and if it's rejected,
prompts for a fallback password (only useful if the account's password was already
manually unlocked out-of-band for recovery — every node's `ansible` account has a locked
password and passwordless sudo by design). A working answer lets the main play connect via
password instead; a blank answer skips that host cleanly (`hosts: ...:!ssh_preflight_skip`)
rather than failing the whole run. Once connected, `pre_tasks` pushes the real key back and
re-verifies it works, so the next run won't need the fallback again. Shared with
`linux/tools.yml`, which had the identical mechanism built in 2026-07-16 — extracted into
`ansible/playbooks/ssh_preflight_with_fallback.yml` / `ansible/tasks/refresh_ansible_ssh_key.yml`
this same day rather than duplicated a second time.

## Safety model (2026-07-09 hardening pass)

Running Ansible tasks *over SSH on the box being reconfigured* has a failure mode
firewallme.sh itself never has: a task can trigger a service restart that kills the very
SSH connection Ansible is using, aborting the play mid-way with the firewall
half-configured. This role was audited and hardened against that:

- **NetworkManager**: connection profiles are written directly as
  `/etc/NetworkManager/system-connections/{wan,lan}.nmconnection` keyfiles
  (`roles/firewall/templates/*.nmconnection.j2`) instead of shelled-out `nmcli con add`/
  `delete` calls. This is genuinely idempotent — an unchanged re-run writes nothing and
  notifies nothing. When something *does* change, NetworkManager is told via
  `nmcli connection reload` (re-reads connection files, does not tear down active
  connections) — never `systemctl restart NetworkManager`, which would drop every
  NM-managed connection on the box, including Ansible's own if it's connected over WAN or
  LAN.
- **nftables**: before applying a changed ruleset live, the play checks which interface
  the current session's default route is on (mirrors firewallme.sh's own `CURRENT_IFACE`
  check exactly). If that's the WAN interface and WAN SSH isn't enabled, the ruleset is
  written to disk but the live reload is deferred with a printed message — applying it
  would otherwise cut the connection Ansible is running the play over.
- **dnsmasq / WireGuard**: starting these services is gated behind `fw_wan_activate`,
  same as WAN interface activation already was — nothing that could plausibly affect a
  live session starts until the operator has explicitly said it's safe to.
- **DNS**: `fw_cld_dns` is set from `ansible/configs/inventory/group_vars/all/site_services.yml` (generated
  from `devices.csv`, same source firewallme.sh itself reads via `begyndelse.json`) rather
  than hardcoded — the two can't drift out of sync. Fallback DNS is `9.9.9.9` (Quad9),
  matching firewallme.sh's own choice (survives a CLD/VRK outage), not `1.1.1.1`.
- **Prompts**: every confirmation (interfaces, WAN mode, WAN SSH policy, WireGuard role,
  and now the reboot question too) happens before `00_preflight_5_confirm.yml`'s "type yes"
  gate — nothing is written to disk until the operator has seen the full plan and
  confirmed it. The reboot question used to be asked at the very end, after everything
  was already applied; it's now asked up front and just acted on at the end.

**CONFIRMED DONE, 2026-07-14**: live end-to-end test against a real firewall (`EXAFWLBRT001`,
failed=0) — the `.nmconnection` keyfile format, `nmcli connection reload` behaviour, and the
full safety model above all verified working, not just theoretically sound. Three real bugs
were found and fixed during that test (dash/bash `[[ ]]` incompatibility, nftables syntax, CLD
hub-IP resolution) — see `project_firewallme_hardening` in project memory for the full
writeup if picking this up again.
