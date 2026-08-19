# Build Sheet — Salt Minion (All Windows Nodes)

**Document ID:** NET-BUILD-SALT-MINION-001
**Classification:** Internal — Network Operations
**Last Updated:** 2026-08-10 — ARM64 minion support added (custom build, see its own callout below; not an official Salt Project release; also a confirmed 3007.x vs the master's 3008.x pin, flagged not resolved)
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

`bootstrap/web/windows/` is organised into per-architecture subfolders (`amd64/`, `arm64/`,
restructured 2026-08-10 — matches `50-binaries.yml`'s own `files/{x86_64,arm64}/` convention,
though that one still genuinely uses `x86_64/` as its own subfolder name, a different namespace),
each holding the real vendor/build filename directly, **committed to this repo**:

| Arch | File | Version | Source |
|---|---|---|---|
| x86_64 | `bootstrap/web/windows/amd64/Salt-Minion-3008.0-Py3-AMD64.msi` | 3008.0 | Official Salt Project release. SHA256 verified against Broadcom's own `X-Checksum-Sha256` response header (`842a03fa627ad51c6fd95fd0801cf771df05281cd8ea0eedf823a2d4f9ca7704`) before being placed here. |
| arm64 | `bootstrap/web/windows/arm64/Salt-Minion-3008.0-Py3-ARM64.msi` | 3008.0 | Custom build, see the ARM64 callout below — **not** from Broadcom. |

This is a deliberate exception to the usual "large binaries aren't committed" convention (see
`docs/bootstrap/bootstrapping.md` §2.3) — same "genuinely open source / freely redistributable"
bar `windows_bootstrap/playbooks/files/README.md` already used to justify committing the
Sysinternals/jq/etc. binaries, Salt's installers are Apache-2.0. Both files are LFS-tracked
(`.gitattributes`), not plain git blobs — the arm64 build alone is ~70MB.

`82-salt-minion.yml` pushes the arch-matching committed MSI directly via `win_copy` (detects
`host_arch` via `tasks/arch_facts.yml`, then looks up the real filename via its own
`salt_minion_msi_filenames` map — vendor/build filenames aren't consistent across arches, so
this is an explicit map, not a single Jinja-templated pattern) — no HTTP fetch, no VRK
provisioning server involved for this specific step, since it's Ansible pushing a file it
already has, not the target machine pulling one over the network.

> **ARM64 — real, version-matched, but still not an official release.** Native Windows ARM64
> support for the Salt minion doesn't exist in any Broadcom-published build — checked directly
> against the real `packages.broadcom.com` directory listing. The arm64 MSI here is a custom
> build Robert compiled (2026-08-10) tracking three still-**open**, unmerged pull requests
> (confirmed live against the GitHub API, all three genuinely open, none merged as of
> 2026-08-10):
>
> - [salt#70003](https://github.com/saltstack/salt/pull/70003) — "Add native Windows arm64
>   minion MSI support"
> - [relenv#318](https://github.com/saltstack/relenv/pull/318) — "Windows arm64 support"
>   (relenv is Salt's own relocatable Python environment builder, a real dependency of the
>   minion build pipeline)
> - [pymssql#1013](https://github.com/pymssql/pymssql/pull/1013) — "Add native Windows arm64
>   wheel builds" (a Salt dependency, needed for the build to complete on ARM64 at all)
>
> An earlier build (3007.0, a dev version) had a genuine version mismatch against the master's
> 3008.x pin — resolved 2026-08-10 when this 3008.0 build was recompiled with the pymssql fix
> included, confirmed by Robert as good. Still treat it as experimental for other reasons:
> there's no vendor release to re-fetch if it needs updating (unlike the x86_64 build), no
> vendor-published checksum to verify it against, and the three PRs it depends on could still
> change materially, get abandoned, or land upstream in a different shape before merging.
> Rebuilding it means re-applying whatever those PRs have evolved into by hand, not re-running
> a fetch script. See the root `README.md`'s "Upstream Contributions" section for the same
> three links in context.

> **Version alignment — read before fetching a replacement.** `EXASLTCLD001` (the master,
> `ansible/playbooks/salt/playbooks/10-master.yml`) pins its Debian package install to
> `group_vars/salt_servers/main.yml`'s `salt_version_major` (currently `3008`). Both Windows
> installers here **must be from the same major line** as the master — master and minions on
> mismatched major versions is an unsupported combination upstream. If you bump one, bump
> all three (master, x86_64 minion, arm64 minion), in the same change.

To refresh the **x86_64** build when `salt_version_major` bumps:

```
1. Fetch the matching-major-line Windows installer from Salt Project's repository:
     https://packages.broadcom.com/artifactory/saltproject-generic/windows/<version>/
   (list the directory first to get exact filenames — verified 2026-07-20, packaging
    migrated to packages.broadcom.com after the Broadcom acquisition; repo.saltproject.io
    no longer serves current releases)
2. Verify the SHA256 against the download response's own X-Checksum-Sha256 header (or
   packages.broadcom.com's published checksum) before trusting the file
3. Place it under bootstrap/web/windows/amd64/ using its real, unmodified filename
   (e.g. Salt-Minion-3008.0-Py3-AMD64.msi) and update
   82-salt-minion.yml's salt_minion_msi_filenames map to match
4. Commit (LFS-tracked automatically via .gitattributes)
```

Refreshing the **arm64** build is not a fetch-and-verify process — see the ARM64 callout
above. It means re-applying the current state of the three referenced PRs (or their eventual
merged/superseded form) and rebuilding, then replacing
`bootstrap/web/windows/arm64/Salt-Minion-3008.0-Py3-ARM64.msi` by hand (renaming it to match
whatever version string the new build actually reports, and updating `82-salt-minion.yml`'s
`salt_minion_msi_filenames` map to match).

## Manual fallback — installing on an already-deployed endpoint

For machines that were never built via `windows_bootstrap` (existing fleet, hand-built boxes,
or a `TAB` row that turns out to be Windows after all and needs a one-off manual install
before `generate_inventory.py` is re-run to pick it up properly).

```powershell
# Run as Administrator. Fetch the MSI matching this machine's own architecture from wherever
# it's reachable -- e.g. a share, or copy it over directly -- there is no HTTP endpoint
# serving either (see above, this isn't fetched over the network by the automated path either).
# Use bootstrap/web/windows/amd64/Salt-Minion-3008.0-Py3-AMD64.msi or
# bootstrap/web/windows/arm64/Salt-Minion-3008.0-Py3-ARM64.msi as appropriate -- check
# $env:PROCESSOR_ARCHITECTURE if unsure which this machine actually is.

Start-Process msiexec.exe -ArgumentList `
  "/i", "C:\path\to\Salt-Minion-3008.0-Py3-AMD64.msi", `
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

`ansible/playbooks/salt/site.yml` is fully built (incl. gitfs/git_pillar and SaltGUI) — this
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
| `ansible/playbooks/salt/README.md` | Salt master build (`site.yml`'s numbered-stage chain), version-alignment details |
| `salt/README.md` | States/pillar layout, gitfs/git_pillar delivery mechanism, `screenprint` module |
| `benarbejde/role_codes.csv` (`SLT` row) | Salt master role code, standard `.22` slot, scope note |
| `benarbejde/generate_inventory.py` (`DEVICE_GROUP_MAP` comment) | Why `SUR`→`windows_laptop` and `TAB` is conditional on OS |
| Root `README.md`'s "Upstream Contributions" section | The three in-progress PRs (salt/relenv/pymssql) the ARM64 minion build depends on |

---

## Sign-Off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Build engineer | | | |
| Network lead | | | |
| Operations manager | | | |

---

*Internal Use Only — Network Engineering*
