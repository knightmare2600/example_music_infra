# Build Sheet — Salt Minion (All Windows Nodes)

**Document ID:** NET-BUILD-SALT-MINION-001
**Classification:** Internal — Network Operations
**Last Updated:** 2026-07-20
**Signed off by:** ___________________________  Date: ___________

---

## Scope

Applies to every Windows node — client endpoints (`WKS`/`LAP`/`SUR` in
`benarbejde/role_codes.csv` terms), member servers (`SVR`), and domain controllers (`DCS`).
Does not apply to `PVE`/`FWL`/Linux hosts generally.

Scope revised twice on 2026-07-20 (was "client endpoints only" at the start of the day):
first widened to include member servers (Chocolatey-driven pull-based software management
benefits them too, same as client endpoints), then widened again to include domain
controllers — Robert's explicit call both times, after discussing whether the original
narrower scope actually held up.

`TAB` (Tablet) is **not** unconditionally in scope — most real `TAB` devices in `devices.csv`
are Android or iPadOS, not Windows. Only a `TAB` row whose `OS` column genuinely says Windows
folds into scope (via `windows_laptop`, see below) — `generate_inventory.py`'s
`DEVICE_GROUP_MAP` handles this per-row, not per-type.

`MAC`/`MBP` (macOS) are **future plans, not current scope** — Salt does support macOS
minions, this just isn't wired up yet. Don't assume they're covered by anything below.

Salt's job here is narrow on purpose: Chocolatey-driven software installs (routine packages
plus the occasional one-off like Bloomberg Terminal) and local-account housekeeping. Domain
join, sign-in, and everything else remain Ansible's (`windows_bootstrap`) and Active
Directory's job.

### Node Details (master)
```
Hostname : EXASLTCLD001
IP       : 192.168.69.22
Network  : CLD (192.168.69.0/24)
Role     : Salt master — all Windows nodes (client, server, DC)
```

## Primary path — automated, via windows_bootstrap

`ansible/playbooks/windows_bootstrap/playbooks/82-salt-minion.yml` installs the Salt minion
over SSH, near the end of the normal windows_bootstrap chain (after domain join), targeting
`windows_nodes` — the parent group that reaches every Windows role
(`generate_inventory.py`'s own `windows_dc → windows_server → windows → windows_nodes`
chain), so one group covers client endpoints, member servers, and domain controllers alike.
Points minions at `salt.jukebox.internal` (the CNAME, not a hardcoded IP) — derived from
`site_services.domain_fqdn` (`group_vars/all/site_services.yml`, loaded for every host
regardless of OS), so no separate Salt-specific IP var was needed once the DNS alias existed.

**This did not start out here.** The first version of this (same day, 2026-07-20) installed
the minion via `bootstrap/web/windows/unattend/headlessunattend.xml`'s `FirstLogonCommands`
instead — at Windows Setup time, before Ansible ever touches the box. That was wrong: the
unattend XML sets `ComputerName` to `*` (a random Setup-time name), and `FirstLogonCommands`
fires before any rename happens — so `MINION_ID` would have been baked in as that random
name, and `EXASLTCLD001` would have accumulated one dead/renamed key per build, needing
manual `salt-key` cleanup forever. Moving the install into `windows_bootstrap` (which only
runs *after* `00-preflight.yml`'s Phase G has already renamed the host to its real
`EXA<ROLE><SITE><NNN>` hostname) avoids the problem structurally — `MINION_ID` is always
correct, first time, no cleanup needed. The unattend XML no longer installs Salt at all.

Nothing to run by hand for a host built through the normal windows_bootstrap chain — this
buildsheet's manual fallback below is for everything else (existing fleet, hand-built boxes).

## Getting the installer onto the provisioning server / into the repo

`bootstrap/web/windows/Salt-Minion-Setup.msi` (AMD64, 3008.2) is fetched and **committed to
this repo** — SHA256 verified against Broadcom's own `X-Checksum-Sha256` response header
(`bcfdd77f35fe62b1402ce9d4920c087d1703c44f2f3d6cde6761c8ab127a17fa`) before being placed here,
same "don't guess a source, verify before trusting a binary" standard already applied to
Proxmox ISOs elsewhere in this repo. This is a deliberate exception to the usual "large
binaries aren't committed" convention (see `docs/bootstrap/bootstrapping.md` §2.3) — same
"genuinely open source / freely redistributable" bar `windows_bootstrap/playbooks/files/
README.md` already used to justify committing the Sysinternals/jq/etc. binaries, and Salt's
installers are Apache-2.0, an easier call than those.

`82-salt-minion.yml` pushes this committed MSI directly via `win_copy` (`{{ playbook_dir
}}/../../../../bootstrap/web/windows/Salt-Minion-Setup.msi`) — no HTTP fetch, no VRK
provisioning server involved for this specific step, since it's Ansible pushing a file it
already has, not the target machine pulling one over the network.

> **ARM64 does not exist for Windows Salt minions.** Checked directly against the real
> `packages.broadcom.com` directory listing for 3008.2 (2026-07-20) — only four files are
> published: `Salt-Minion-3008.2-Py3-AMD64-Setup.exe`, `Salt-Minion-3008.2-Py3-AMD64.msi`,
> and 32-bit `x86` equivalents of both. No ARM64 build in any format. Salt's ARM64 packaging
> (confirmed via the Salt Project's own downloads page) is Linux-only; Windows minions are
> AMD64 (or 32-bit x86) only, regardless of the 3008.x line staying current.

> **Version alignment — read before fetching a replacement.** `EXASLTCLD001` (the master,
> `ansible/playbooks/salt/salt_master.yml`) pins its Debian package install to
> `group_vars/salt_servers/main.yml`'s `salt_version_major` (currently `3008`). The Windows
> installer here **must be from the same major line** — master and minions on mismatched
> major versions is an unsupported combination upstream. If you bump one, bump both, in the
> same change.

To refresh when `salt_version_major` bumps:

```
1. Fetch the matching-major-line Windows installer from Salt Project's repository:
     https://packages.broadcom.com/artifactory/saltproject-generic/windows/<version>/
   (list the directory first to get exact filenames — verified 2026-07-20, packaging
    migrated to packages.broadcom.com after the Broadcom acquisition; repo.saltproject.io
    no longer serves current releases)
2. Verify the SHA256 against the download response's own X-Checksum-Sha256 header (or
   packages.broadcom.com's published checksum) before trusting the file
3. Rename to Salt-Minion-Setup.msi (generic, version-free name — matches the fixed filename
   82-salt-minion.yml and the manual fallback below both reference, so this file can be
   refreshed in place without editing either)
4. Replace bootstrap/web/windows/Salt-Minion-Setup.msi and commit
```

## Manual fallback — installing on an already-deployed endpoint

For machines that were never built via `windows_bootstrap` (existing fleet, hand-built boxes,
or a `TAB` row that turns out to be Windows after all and needs a one-off manual install
before `generate_inventory.py` is re-run to pick it up properly).

```powershell
# Run as Administrator. Fetch the MSI from wherever it's reachable -- e.g. a share, or
# copy it over directly -- there is no HTTP endpoint serving it (see above, this isn't
# fetched over the network by the automated path either).

Start-Process msiexec.exe -ArgumentList `
  "/i", "C:\path\to\Salt-Minion-Setup.msi", `
  "MASTER=salt.jukebox.internal", "MINION_ID=$env:COMPUTERNAME" -Wait
```

`salt.jukebox.internal` is a CNAME to `exasltcld001.jukebox.internal` (`benarbejde/role_codes.csv`'s
`DNSAlias` column, added 2026-07-20 — see `ansible/playbooks/bind9/templates/
db.forward-zone.devices.j2`). If this endpoint has no working DNS yet (not domain-joined,
hand-built box before networking is sorted), use the raw IP instead:
`MASTER=192.168.69.22`.

MSI properties used above (confirmed against Salt's own install guide, not guessed):

| Property | Purpose | Default |
|----------|---------|---------|
| `MASTER` | Master hostname/IP (comma-separated list supported) | `salt` |
| `MINION_ID` | Minion identifier | Hostname or IP |
| `START_MINION` | Start the service after install | `1` (starts) |

`msiexec` runs with its normal UI by default from a manual PowerShell invocation like this —
add `/quiet /norestart` if a fully silent run is wanted.

## Verifying check-in

`ansible/playbooks/salt/salt_master.yml` is fully built (v1.0.0, incl. gitfs/git_pillar) — this
step assumes the physical/cloud host it targets, `EXASLTCLD001`, has actually been provisioned
and that playbook run against it. If it hasn't yet, do that first.

```bash
# On the Salt master
salt-key -L                    # new minion's key appears under "Unaccepted Keys"
salt-key -a <minion-name>      # accept it
salt '<minion-name>' test.ping # confirm check-in
```

## Ongoing state — every minion, every highstate

`salt/states/top.sls` applies `wintools` and `grains` to `'*'` — every minion, not just at
check-in time. Two things worth knowing before signing off a node:

- **`wintools/init.sls` creates/repairs a local `ansible` break-glass admin account with a
  hardcoded plaintext password (`Password1!`)** on every WKS/LAP/SUR/SVR/DCS node. This is a
  known, deliberate, documented weakness (see that file's own "KNOWN, DELIBERATE WEAKNESS"
  comment) — training-repo-only, not something to replicate in a real environment.
- `grains/init.sls` populates custom site/role/habitat grains from `pillar/sites.sls`
  (`benarbejde/sites.csv`, generated). `audit/init.sls` is a separate, on-demand-only diagnostic
  state (`salt '<minion>' state.apply audit`) — never applied automatically, not in `top.sls`.

See `salt/README.md` for the full states/pillar layout and the gitfs/git_pillar delivery
mechanism (wired up 2026-07-20) that serves all of this to minions.

## Firewall Rules Required
```
Inbound to EXASLTCLD001:
  4505/tcp  — Salt publish port (master -> minions)
  4506/tcp  — Salt request/reply port (minions -> master)

Outbound from every Windows node (client, server, DC):
  4505/tcp, 4506/tcp -> 192.168.69.22
```

---

## Build Checklist

| Hostname | Built via windows_bootstrap (82-salt-minion.yml) | Manual fallback used instead | Minion Key Accepted on EXASLTCLD001 | test.ping Confirmed | Notes |
|----------|----------------------------------------------------|-------------------------------|--------------------------------------|----------------------|------|
| | - [ ] | - [ ] | - [ ] | - [ ] | |

---

## Related Documents

| Document | Relevance |
|----------|-----------|
| `ansible/playbooks/windows_bootstrap/README.md` | Where `82-salt-minion.yml` sits in the overall chain |
| `ansible/playbooks/salt/README.md` | Salt master build (`salt_master.yml`), version-alignment details |
| `salt/README.md` | States/pillar layout, gitfs/git_pillar delivery mechanism, `screenprint` module |
| `benarbejde/role_codes.csv` (`SLT` row) | Salt master role code, standard `.22` slot, scope note |
| `benarbejde/generate_inventory.py` (`DEVICE_GROUP_MAP` comment) | Why `SUR`→`windows_laptop` and `TAB` is conditional on OS |

---

## Sign-Off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Build engineer | | | |
| Network lead | | | |
| Operations manager | | | |

---

*Internal Use Only — Network Engineering*
