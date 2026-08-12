# Salt — Beginner's Guide

> **Classification:** Internal — Infrastructure
> **Server:** `EXASLTCLD001` (`192.168.69.22`)
> **SaltGUI:** `http://192.168.69.22:8080`
> **Credentials:** See password manager — do **not** store passwords in this document

---

## Changelog

| Date       | Change                    |
|------------|---------------------------|
| 2026-08-10 | §3.2 corrected — ARM64 Windows Salt minions are now real, via a custom build Robert added (`Salt-Minion-3008.0-Py3-ARM64.msi`) tracking 3 still-open upstream PRs. Previous "ARM64 does not exist" claim was accurate for the *official* release at the time, but the section didn't leave room for a self-built alternative — now covers both paths explicitly. |
| 2026-08-10 | §3.2 updated again, same day — `bootstrap/web/windows/` restructured into per-arch subfolders (`{x86_64,arm64}/`), both MSIs now real vendor/build filenames, and the earlier 3007.x-vs-3008.x version mismatch is resolved (both `3008.0`, arm64 recompiled with the pymssql fix, confirmed good by Robert). |
| 2026-08-10 | New §6 "Automatic Highstate" and §7 "Querying and Confirming Custom Grains" added — `82-salt-minion.yml` now drops a `minion.d/` schedule config so `top.sls`'s `wintools`+`grains` states actually apply on their own (previously nothing triggered `state.apply` at all, ever, without a human running it by hand). Old §6/§7 renumbered to §8/§9. |
| 2026-08-11 | New §3.3 — running `82-salt-minion.yml` against a single existing host via `--limit` (not `-e target=`, which this playbook's static `hosts: windows_nodes` doesn't respond to). Confirmed with Robert: Salt scope is every Windows node, no DCS/SVR exclusion — `cld.ini`'s `EXASLTCLD001` comment claiming otherwise was itself wrong, fixed same day. |
| 2026-08-11 | New §9–§13 added: real command-line `state.apply` examples, verifying gitfs/git_pillar delivery is healthy, forcing a refresh, recovering from a full disk, and recovering a `salt-master` that won't start — all written up after `EXADCSCLD001`'s first real end-to-end `state.apply` succeeded the same day, following a full disk-full/delivery-failure saga (see `docs/INCIDENT-LOG.md`'s `INC-2026-08-11-SALT-DISK-FULL`). Old §9 (Quick Reference) renumbered to §14, updated with links to all five new sections. |
| 2026-08-12 | §7 and its quick-reference command updated — two new custom grains added, `country_code` and `office_name`, and `street` renamed to `street_address`. `office_name` is deliberately blank for most sites (only set where a site genuinely has a distinct venue/building name, not just a street address) — `sites.csv` gained a new `OfficeName` column, split by hand per-site (not a mechanical comma-split) from 14 sites whose `Street` column used to mix a venue name in with the actual address. |
| 2026-08-12 | New §8.1 — running `state.apply`/`test.ping` from SaltGUI's own browser Command-box, sourced from SaltGUI's official docs (not yet independently confirmed against a live login here — flagged explicitly as such). Quick Reference updated with a link. |
| 2026-08-08 | Initial version — companion to [ExampleMusic_Beginners_Guide.md](../ExampleMusic_Beginners_Guide.md) and [TacticalRMM_Beginners_Guide.md](TacticalRMM_Beginners_Guide.md), written after `EXASLTCLD001` and SaltGUI were both confirmed live end to end. |

---

## 1. Introduction

This document is for Malcolm and Jamie. If you are neither Malcolm nor Jamie, you are welcome to read it, but it was written specifically for the two of you.

It assumes you have already read [ExampleMusic_Beginners_Guide.md](../ExampleMusic_Beginners_Guide.md) — the naming convention and IP addressing scheme described there apply here without repeating them. It also assumes `EXASLTCLD001` itself is already built (that's `ansible/playbooks/salt/README.md` and `ExampleMusic_Beginners_Guide.md` §7.4's job, not this one).

This document covers **adding a Windows node to Salt** — the day-to-day operation you'll actually do repeatedly — plus enough of "what Salt is doing and where" to troubleshoot when a minion doesn't check in the way you expect.

---

## 2. What Salt Is (and Isn't) in This Estate

Salt's job here is deliberately narrow: **Chocolatey-driven software installs** (routine packages, plus the occasional one-off) and **local-account housekeeping**, for Windows nodes only.

In scope: client endpoints (`WKS`/`LAP`/`SUR`), member servers (`SVR`), and domain controllers (`DCS`) — per `benarbejde/role_codes.csv`'s `SLT` row. A `TAB` row only counts if `devices.csv`'s `OS` column genuinely says Windows (most real `TAB` rows are Android/iPadOS).

**Not in scope, on purpose:**
- **Domain join, sign-in, anything Active Directory** — that stays `windows_bootstrap`/AD's job entirely.
- **`FWL`/`PVE`/Linux hosts generally** — Ansible's job. Salt never touches these.
- **`MAC`/`MBP` (macOS)** — future plans, not built yet. Salt does support macOS minions in general; this estate hasn't wired it up.

If you find yourself wanting Salt to do something that sounds like "manage a config file" or "join a domain," that's almost certainly Ansible's job instead — this split is deliberate, matches how TacticalRMM/Salt/Ansible responsibilities are kept apart throughout this whole estate.

---

## 3. Adding a Minion

Two paths, depending on how the node was built.

### 3.1 A brand-new node — nothing to do

Any Windows box built through the normal `windows_bootstrap` chain gets its Salt minion installed automatically, near the end of that chain (`82-salt-minion.yml`, after domain join) — `MINION_ID` is set correctly first time because the host's already been renamed to its real `EXA<ROLE><SITE><NNN>` hostname by that point. Nothing to run by hand. Skip to §5 (accepting the key).

### 3.2 An existing node (e.g. `EXADCSCLD001`) — manual install

A node built *before* Salt existed as an option, or built outside the `windows_bootstrap` chain, needs the minion installed by hand. This is the case worth knowing well, since it's the one you'll actually run yourself.

**If the target is x86_64** — the common case — get the official Salt Project installer. Run as Administrator, in `pwsh.exe` (not `powershell.exe`):

```powershell
iwr 'https://packages.broadcom.com/artifactory/saltproject-generic/windows/3008.2/Salt-Minion-3008.2-Py3-AMD64.msi' -OutFile Salt-Minion-Setup-x86_64.msi
```

**Verify it before trusting it** — never skip this for a binary you're about to run as Administrator:

```powershell
Get-FileHash Salt-Minion-Setup-x86_64.msi -Algorithm SHA256
```

Compare the output against `bcfdd77f35fe62b1402ce9d4920c087d1703c44f2f3d6cde6761c8ab127a17fa` (Broadcom's own published checksum for this exact build, confirmed live against their real `X-Checksum-Sha256` response header before this doc was written — don't trust it just because it's written down here, re-verify against Broadcom's own header if it's been a while). If they don't match, delete the file and start over — don't proceed.

> **If the target is ARM64** — genuinely different, read this rather than trying the `iwr` above. Native Windows ARM64 Salt minion builds don't exist upstream at all yet (nothing published on Broadcom's site — checked directly). What exists instead is a **custom build already committed to this repo**, `bootstrap/web/windows/arm64/Salt-Minion-3008.0-Py3-ARM64.msi`, assembled by tracking three still-open, unmerged upstream PRs ([salt#70003](https://github.com/saltstack/salt/pull/70003), [relenv#318](https://github.com/saltstack/relenv/pull/318), [pymssql#1013](https://github.com/pymssql/pymssql/pull/1013)). There's nothing to `iwr` from a vendor and no vendor checksum to verify against — copy the file itself from the repo/provisioning share instead. Treat it as experimental for that reason alone — see `docs/buildsheets/buildsheet-salt-minion.md`'s own ARM64 callout for the full caveat before relying on it for anything production-critical.
>
> **Version alignment matters, for both architectures.** `EXASLTCLD001` (the master) is pinned to major version `3008` (`group_vars/salt_servers/main.yml`'s `salt_version_major`). Whichever minion you're installing **must** be from the same major line — mismatched major versions between master and minions is unsupported upstream. Both committed MSIs are currently `3008.0`, matching the pin. If that pin ever changes, get the matching minion version, not just whatever's newest.

**Install it** (adjust the filename for your target's actual architecture — note the real committed files live under per-arch subfolders, `bootstrap/web/windows/{x86_64,arm64}/`, not flat in `windows/` itself):

```powershell
Start-Process msiexec.exe -ArgumentList `
  "/i", "Salt-Minion-Setup-x86_64.msi", `
  "MASTER=salt.jukebox.internal", "MINION_ID=$env:COMPUTERNAME" -Wait
```

`salt.jukebox.internal` is a CNAME to `EXASLTCLD001` — use it, not a hardcoded IP, so this keeps working if the master's own address ever changes. If this endpoint genuinely has no working DNS yet, use `MASTER=192.168.69.22` instead.

`MINION_ID=$env:COMPUTERNAME` is important — it's what makes the minion identify itself with the box's real hostname (e.g. `EXADCSCLD001`) rather than Salt's own default. Confirm `$env:COMPUTERNAME` is actually correct *before* running this — if the box hasn't been renamed yet, fix that first, don't install Salt against a wrong name you'll have to clean up later with `salt-key -d`.

### 3.3 Or: run `82-salt-minion.yml` against just this one host via Ansible

The actually-recommended way to onboard a single existing node, rather than the raw `msiexec` above — same install, but also gets the `minion.d/` automatic-highstate config (§6) and the already-installed/version-mismatch checks (v1.4.0) that the manual path above doesn't:

```bash
ansible-playbook -i configs/inventory playbooks/windows_bootstrap/playbooks/82-salt-minion.yml --limit EXADCSCLD001
```

**Use `--limit`, not `-e target=`.** Unlike `80-domainjoin.yml` (`hosts: "{{ target | default('all') }}"`), this playbook's `hosts:` is the static group `windows_nodes` — `-e target=<host>` has no effect on it at all and would run against every Windows node in inventory instead of just the one you meant. `--limit` is the standard Ansible mechanism that works regardless of what `hosts:` says.

Scope is deliberately every Windows node — WKS/LAP/SUR/SVR/DCS alike, no exclusions (Robert's confirmed call, 2026-08-11; an older inventory comment on `EXASLTCLD001` in `cld.ini` claiming DCS/SVR stay Ansible-only was itself wrong/stale and has been corrected).

---

## 4. Where Minion State Actually Lives

Once installed, Salt on Windows keeps everything under `C:\ProgramData\Salt Project\Salt\conf\` — worth knowing for troubleshooting, since this is where you'd look if something isn't behaving as expected:

| Path | What's there |
|------|--------------|
| `C:\ProgramData\Salt Project\Salt\conf\minion` | The minion's own config — which master it points at, its ID |
| `C:\ProgramData\Salt Project\Salt\conf\grains` | Custom grains this estate's own `grains` state writes (site/role/habitat data, from `salt/pillar/sites.sls`) |
| `C:\ProgramData\Salt Project\Salt\conf\pki\minion\` | The minion's own keypair — what the master needs to accept before it'll talk to it |

If a minion never checks in, this is where to look first — confirm `conf\minion` actually points at the right master, and that a keypair genuinely exists under `pki\minion\`.

---

## 5. Accepting the Key and First Check-In

On the **master** (`EXASLTCLD001`):

```bash
salt-key -L                    # new minion's key appears under "Unaccepted Keys"
salt-key -a <minion-name>      # accept it -- e.g. salt-key -a EXADCSCLD001
salt '<minion-name>' test.ping # confirm it actually checks in
```

`auto_accept` is deliberately `false` in this estate's master config — every new key needs a manual accept, on purpose, not something to change for convenience.

**First real state run**, once the key's accepted:

```bash
salt '<minion-name>' state.apply
```

`salt/states/top.sls` applies two states to every minion this way, not just at check-in: `wintools` and `grains`. Worth knowing before you run this for the first time — `wintools/init.sls` creates/repairs a local `ansible` break-glass admin account with a **hardcoded plaintext password** (`Password1!`) on every node it touches. This is a known, deliberate, documented weakness (see that state's own header) — training-repo-only, never something to replicate for real. `grains/init.sls` populates the custom site/role/habitat grains mentioned in §4 above. A third state, `audit`, exists but is never applied automatically — run it on demand only: `salt '<minion-name>' state.apply audit`.

---

## 6. Automatic Highstate — grains/wintools apply on their own now

Until 2026-08-10, `salt/states/top.sls` declared `wintools`+`grains` for every minion, but **nothing actually triggered `state.apply`** — no scheduler on the master, no `startup_states` on the minion, no reactor/orchestration. Those states only ever landed on a node if someone ran `salt '<minion-name>' state.apply` by hand from the master (§5 above). A node could sit fully checked-in, keys accepted, for months without its grains file ever being written.

Fixed in `82-salt-minion.yml`, which now drops a `minion.d/` config include (Salt's own convention — `default_include: minion.d/*.conf` is the out-of-the-box minion default, merges alongside the base `conf\minion` file the MSI's own `MASTER`/`MINION_ID` properties write) at:

```
C:\ProgramData\Salt Project\Salt\conf\minion.d\example-music-schedule.conf
```

containing:

```yaml
startup_states: highstate

schedule:
  example_music_periodic_highstate:
    function: state.apply
    minutes: 60
    splay: 300
```

`startup_states: highstate` applies `top.sls` once whenever the minion service starts — covers the very first check-in right after onboarding, and every reboot after that. The `schedule:` block re-applies on top, every 60 minutes by default (splayed over 5 minutes so a fleet-wide reboot doesn't have every minion hit the master in the same instant) — so a grains file gone stale after a later rename/site move, or drifted `wintools` state, self-heals without anyone needing to remember to trigger it. The interval is `salt_minion_highstate_interval_minutes` in `82-salt-minion.yml`'s own `vars:` block if it ever needs adjusting.

**Practical implication:** any node onboarded via `82-salt-minion.yml` from 2026-08-10 onward gets this automatically. A node onboarded *before* that date won't have the `minion.d/` drop-in — re-run `82-salt-minion.yml` against it once to pick it up (it's idempotent; the MSI copy/install steps will no-op, only the new config/restart tasks will actually do anything).

---

## 7. Querying and Confirming Custom Grains

The rendered grains file lives at `C:\ProgramData\Salt Project\Salt\conf\grains` (§4's table above) — `nodetype`/`city`/`country`/`country_code`/`entity`/`office_name`/`street_address`/`postal_code`/`habitat`, sourced from a real `sites.csv` lookup (`salt/pillar/sites.sls`, generated by `generate_inventory.py --emit-site-grains-pillar`). See `salt/states/grains/init.sls`'s own header for exactly what each field is and where it comes from. `office_name` is blank for most sites — only set where a site genuinely has a venue/building name distinct from its street address (e.g. FAL's `office_name: "Brockville Stadium"`, `street_address: "1876 Hope Street"`) — a blank `office_name` is normal, not stale data.

**From the master**, read them without touching the minion directly:

```bash
salt '<minion-name>' grains.items          # everything, including these custom ones
salt '<minion-name>' grains.get nodetype   # a single grain
salt '<minion-name>' grains.get city
```

**Confirm the file itself is present and not stale/blank** (e.g. after a rename or site move):

```bash
salt '<minion-name>' state.apply audit     # salt/states/audit/init.sls -- flags a missing/blank
                                            # grain, a minion-id/hostname mismatch, wintools
                                            # drift, wrong Salt version line, etc. in one pass
```

**Force a refresh right now**, without waiting for §6's schedule:

```bash
salt '<minion-name>' state.apply           # re-applies top.sls (wintools + grains) immediately
```

**Confirm the automatic-highstate schedule (§6) is actually configured**, useful right after onboarding a node to check the `minion.d/` drop-in took:

```bash
salt '<minion-name>' schedule.list
```

**Known limitation, not yet resolved**: a changed grains file needs the minion to restart before Salt itself picks it up (`grains/init.sls`'s own header) — `state.apply` triggers that restart automatically (`onchanges`-gated, backgrounded), but it means `grains.items` run *immediately* after a `state.apply` that actually changed the file can still show the **old** value for a few seconds until the restart completes. If a value looks stale right after a change, wait ~10 seconds and re-run `grains.get`.

---

## 8. SaltGUI — why states might not show up yet, and how to run jobs from it

If you've logged into SaltGUI and don't see `salt/states/`'s content anywhere, there are two genuinely different, unrelated reasons, worth telling apart:

**1. The states genuinely haven't synced from git yet.** States/pillar are served to the master via `gitfs`/`git_pillar`, pulling directly from this repo's own public GitHub remote (`10-master.yml`'s Section 6 — confirmed correctly configured: `gitfs_remotes` points at the real repo URL, `root: salt/states`). This sync happens automatically in the background on Salt's own schedule, but a master that's only just been (re)started may not have completed its first sync yet. Force it directly rather than waiting:

```bash
# On the master
salt-run fileserver.update
salt-run fileserver.file_list   # ground truth -- what the master's fileserver actually has right now
```

If `fileserver.file_list` shows the real contents of `salt/states/` (e.g. `top.sls`, `wintools/init.sls`), the sync genuinely worked — regardless of what SaltGUI itself is showing.

**2. SaltGUI has no minions to show anything against yet.** Most of SaltGUI's own panels (Minions, Grains, Jobs) are inherently sparse or empty until at least one minion has actually checked in — which, if you're reading this section before completing §5, hasn't happened yet. This isn't a states-sync problem at all; it's the expected look of a SaltGUI dashboard with zero accepted minions. Accept a key and run a real `test.ping`/`state.apply` first, then check SaltGUI again.

I haven't personally driven SaltGUI's UI live to confirm exactly which panel browses raw file-server content (it may not have a dedicated "browse states" view at all — its own scope is more job/minion/key management than a file browser) — if `fileserver.file_list` above confirms the sync is genuinely fine, treat that as the authoritative answer over whatever SaltGUI's UI does or doesn't show.

### 8.1 Running `state.apply`/`test.ping` from SaltGUI (the §9 equivalent, in the browser)

**Source: SaltGUI's own official documentation ([erwindon.github.io/SaltGUI](https://erwindon.github.io/SaltGUI/), [github.com/erwindon/SaltGUI](https://github.com/erwindon/SaltGUI)), not yet independently confirmed by actually clicking through a live login here** — if anything below doesn't match what you actually see, that's the real answer; fix this section to match, don't trust this over your own screen.

**The Command-box** is the general way to run anything — click the **`>_`** icon, top-right corner, from any page. It opens an overlay with a target field and a command field:

- **Target**: a single minion name (`EXADCSCLD001`), a glob (`EXADCS*`), a compound expression, or a nodegroup. Typing `##connected` auto-fills every currently-connected minion — the GUI equivalent of `salt '*'`.
- **Command**: a plain module.function for a minion-targeted call (`test.ping`, `state.apply`) — same as the CLI. Master-side runner/wheel calls need their own prefix: `runners.fileserver.update` (the §11 "force a refresh" equivalent), `wheel.key.finger`.
- Selecting row(s) in a table first (e.g. ticking a minion's checkbox on the **Minions** page) and *then* opening the command-box pre-fills the target field with that selection, rather than typing the name by hand.
- Two run modes: normal (waits, shows the result once the job completes — same as the CLI's default blocking behaviour) or asynchronous (returns immediately with a progress indicator, check the **Jobs** page for the result once it lands — the GUI equivalent of `--async` + `salt-run jobs.lookup_jid`).
- Output appears directly in the command-box overlay once the job completes.

**Other relevant pages**, per the official docs: **Minions** (status, checkboxes for multi-select, right-click/dropdown menus on rows for common actions without opening the command-box by hand), **Jobs** (last 7 on the main dashboard, up to 50 on the dedicated Jobs page, filterable), **Highstate** (an overview of every minion's current state/highstate status — likely the most direct place to confirm `state.apply` actually landed cleanly across the fleet, faster than checking minions one at a time), **Grains**/**Pillars** (per-minion values — pillar data is hidden by default, has to be deliberately shown).

---

## 9. Applying State From the Command Line — Real Commands

Everything here is exactly what actually worked, live, against a real minion (`EXADCSCLD001`, 2026-08-11) — not theoretical syntax. Run all of these **on the master** (`EXASLTCLD001`), as `sudo`.

```bash
# 1. Confirm the minion is actually reachable before anything else
sudo salt EXADCSCLD001 test.ping

# 2. Apply top.sls (wintools + grains) right now, don't wait for the hourly schedule (§6)
sudo salt EXADCSCLD001 state.apply

# 3. Read back what actually landed
sudo salt EXADCSCLD001 grains.items                                          # everything
sudo salt EXADCSCLD001 grains.item nodetype city country country_code entity office_name street_address postal_code habitat   # just the custom ones, no noise
```

`state.apply`'s output is long — for each state ID it shows `Result`, `Comment`, and (if anything actually changed) a `diff`. The line that matters most is the summary at the very end:

```
Summary for EXADCSCLD001
-------------
Succeeded: 19 (changed=3)
Failed:     0
-------------
```

`Failed: 0` is what you're checking for. `changed=3` just means 3 of the 19 states genuinely did something (e.g. wrote a new grains file) — a routine re-run against an already-correct minion will show `changed=0` and that's equally healthy, not a problem.

Targeting more than one minion works the normal Salt way — a glob, or a grain match:

```bash
sudo salt 'EXADCS*' state.apply           # every DC
sudo salt -G 'nodetype:DCS' state.apply   # same thing, by grain (nodetype is populated by the grains state itself)
```

SaltGUI's own equivalent — the browser Command-box, same targeting options — is documented in §8.1.

---

## 10. Verifying the Master's Git-Backed Delivery Is Healthy

States and pillar are served from this repo via `gitfs`/`git_pillar` — both maintain their own local clone under `/var/cache/salt/master/{gitfs,git_pillar}`, refreshed from GitHub. This section is the direct, evidence-based way to check that mechanism is actually working, not just assume it because the master is running.

**The most direct check — from the minion's own perspective, live, no assumptions:**

```powershell
# On the minion itself (as Administrator)
& "C:\Program Files\Salt Project\Salt\salt-call.exe" cp.envs        # should show: local: [base]
& "C:\Program Files\Salt Project\Salt\salt-call.exe" cp.list_master # should list top.sls, wintools/init.sls, grains/init.sls, etc.
& "C:\Program Files\Salt Project\Salt\salt-call.exe" cp.get_file salt://top.sls C:\Windows\Temp\test-top.sls
Get-Content C:\Windows\Temp\test-top.sls   # should show real YAML content, not an empty/missing file
```

**Listing and fetching are genuinely different operations in Salt, and can disagree** — this is exactly what happened on 2026-08-11 (see `docs/INCIDENT-LOG.md`'s `INC-2026-08-11-SALT-DISK-FULL`): `cp.list_master` correctly listed `top.sls`, while `cp.get_file` for that exact same file returned nothing. If you only check listing, you can be fooled into thinking delivery is healthy when it isn't — always confirm with an actual `cp.get_file` fetch, not just a listing.

**From the master itself:**

```bash
sudo salt-run fileserver.envs           # should show: - base
sudo salt-run fileserver.file_list base # should list the same content as cp.list_master above
```

**If `state.apply` fails with `"No Top file or master_tops data matches found"`** but the checks above look fine — the master-dispatched `-l debug` output won't help (state compilation happens client-side on the minion, the master only ever sees the minion's one-line final answer). Get the minion's own debug trace instead:

```powershell
& "C:\Program Files\Salt Project\Salt\salt-call.exe" state.apply -l debug 2>&1 | Select-Object -Last 150
```

Look for a line like `Could not find file 'salt://top.sls' in saltenv 'base'` and, just above it, `the 'file_roots' configuration is: {'base': []}`. If you see that alongside a working `cp.list_master`, this is the exact same class of problem found and fixed on 2026-08-11 — see §10.1 below for the two confirmed real causes, in the order to check them.

### 10.1 Known real causes of "listing works, fetching doesn't" (check in this order)

**1. Missing `git-lfs` filter registration.** This repo's `.gitattributes` defines real `filter=lfs` rules (large binaries elsewhere in the repo, unrelated to `salt/states`/`salt/pillar` themselves) — if `git-lfs` isn't installed and registered, git's handling of the *whole* repository checkout can misbehave, not just the specific LFS-tracked files. Check:

```bash
which git-lfs
sudo git config --system --get filter.lfs.clean
```

Both should return real output. If either is missing, `10-master.yml`'s Section 5 already installs `git-lfs` and runs `git lfs install --system --skip-smudge` (the `--skip-smudge` keeps LFS-tracked files as small pointers rather than downloading their real content — don't drop that flag, it's what keeps this master's disk footprint from ballooning further). Re-running `10-master.yml` fixes this on its own if it's ever missing:

```bash
ansible-playbook -i configs/inventory playbooks/salt/playbooks/10-master.yml \
  --ask-vault-pass --start-at-task="5 | Install git-lfs"
```

**2. `gitfs_base`/`env: base` not set.** Check `/etc/salt/master` for these two lines:

```bash
grep -A1 'gitfs_base\|env: base' /etc/salt/master
```

`gitfs`'s own default `gitfs_base` is a branch literally named `master` — this repo only has `main`, so without `gitfs_base: main` explicitly set, `gitfs` has nothing mapped to the `base` saltenv at all. `git_pillar`'s per-remote branch name maps to a pillarenv of the *same* name unless explicitly overridden with `env: base` — same problem, same fix, different config block. Both are already set in `10-master.yml`'s Section 6 as of 2026-08-11 — if they're ever missing (e.g. hand-edited away, or a much older master rebuilt from an outdated checkout), re-run:

```bash
ansible-playbook -i configs/inventory playbooks/salt/playbooks/10-master.yml \
  --ask-vault-pass --start-at-task="6 | Write /etc/salt/master"
```

**3. `gitfs_provider`/`git_pillar_provider: gitcli`, and shallow clone.** Do **not** use these together — `gitcli` has a confirmed real bug (2026-08-11) where its bare clone never points `HEAD` at the branch it actually fetched, leaving it dangling at a branch this repo doesn't have. This makes listing operations work (they resolve via explicit branch config) while individual file fetches silently fail (they rely on `HEAD` implicitly). `10-master.yml` pins `gitfs_provider`/`git_pillar_provider: gitpython` specifically to avoid this — if you ever see `gitcli` in `/etc/salt/master`, that's a regression, not a valid alternative. Neither `gitpython` nor `pygit2` support shallow clones (`gitfs_depth`/`git_pillar_depth`) at all — that's `gitcli`-only, and `gitcli` isn't safe to use here until this is fixed upstream.

---

## 11. Forcing a Refresh ("re-pulling")

Both `gitfs` and `git_pillar` sync automatically on their own schedule — but if you've just pushed a change to `salt/states/` or `salt/pillar/` and don't want to wait:

```bash
sudo salt-run fileserver.update    # gitfs -- states
```

There's no separate one-line runner for forcing a `git_pillar` refresh outside its own schedule — it updates on the same background cycle as `gitfs`. If you need pillar data refreshed on a *minion* after a master-side pillar change (the master already has the new data, but the minion is holding a stale copy from its last check-in):

```bash
sudo salt EXADCSCLD001 saltutil.refresh_pillar
```

**This does NOT do a fresh git clone — it's a real incremental update, confirmed not just assumed** (2026-08-11): running `fileserver.update` twice in a row with nothing changed upstream left both the total cache size and an existing file's exact modification time completely unchanged between runs. It behaves like an ordinary `git pull`, not a rebuild-from-scratch — routine use of this command will not grow the cache over time. It will only grow if genuinely new large content lands in the repo (expected, not a leak).

---

## 12. If the Master's Disk Fills Up

See `docs/INCIDENT-LOG.md`'s `INC-2026-08-11-SALT-DISK-FULL` for the full story of why this happened once already. Quick diagnosis and recovery:

```bash
# Check what's actually using the space
sudo du -h --max-depth=1 /var/cache/salt/master

# gitfs/git_pillar are both PURE CACHES -- safe to delete entirely, Salt regenerates
# them from GitHub on next use. Not authoritative data, nothing is lost.
sudo systemctl stop salt-master
sudo rm -rf /var/cache/salt/master/gitfs /var/cache/salt/master/git_pillar
sudo systemctl start salt-master
sudo salt-run fileserver.update
```

**Current expected size, as of 2026-08-11, both fully rebuilt from scratch**: `gitfs` ~575MB, `git_pillar` ~5.6GB (`git_pillar` checks out the *entire* repository rather than just `salt/pillar/`, a known, accepted inefficiency — see the incident log's own Root Cause section for why this isn't being chased further right now). Total, ~6.2GB. If you see numbers wildly larger than this after a clean rebuild, something new has regressed — don't assume it's normal, investigate with §10's diagnostic commands.

**If this happens again and you can't even log in**: the disk-full lockout blocks new sessions but the root account can usually still get in via the reserved-blocks margin ext4 keeps for root — try `ssh` as `ansible` first, and if that's rejected too, console/out-of-band access is the fallback (see `docs/linux-recovery-runbook.md` for the general pattern, not specific to Salt).

**Root filesystem headroom**: extended by +10GB on 2026-08-11 as an independent safety margin (`lvextend -L+10240M /dev/mapper/EXASLTCLD001`, followed by a filesystem grow to match). Check current headroom any time with `df -h /`.

---

## 13. If `salt-master` Won't Start At All

Real example, 2026-08-11: switching `gitfs_provider` to a provider that turned out to be invisible to Salt's own bundled Python took `salt-master` down completely, crash-looping on every restart attempt. First move, always:

```bash
sudo systemctl status salt-master
sudo journalctl -u salt-master -n 30 --no-pager
```

Look for a `[CRITICAL]` line near the bottom — Salt's own pre-flight checks are usually explicit about what failed (e.g. `Master failed pre flight checks, exiting`, with the real reason logged just above it). Common real causes seen so far:

- **`No suitable gitfs provider module is installed`** — `gitfs_provider`/`git_pillar_provider` is set to something not actually available to Salt's own runtime. **Important**: Salt ships its own bundled, self-contained Python (relenv), completely separate from the system's `/usr/bin/python3` — `apt install python3-<whatever>` does **nothing** for Salt's own provider modules. Check what Salt itself says is available (the crash log names it directly, e.g. `GitPython is installed, you may wish to set gitfs_provider to 'gitpython'`) rather than guessing or installing system packages.
- **A syntax error in `/etc/salt/master`** — `salt-master` will refuse to start and usually say so plainly. `10-master.yml`'s Section 6 always keeps a `.bak` backup (`backup: true` on the `copy` task) if you need to compare against the last-known-good version by hand: `ls -la /etc/salt/master.*`.

**Recovery**: fix the actual cause (usually a provider/config value), then re-apply via Ansible rather than hand-editing the live file — keeps the repo as the source of truth, not a one-off manual patch that drifts:

```bash
ansible-playbook -i configs/inventory playbooks/salt/playbooks/10-master.yml \
  --ask-vault-pass --start-at-task="6 | Write /etc/salt/master"
sudo systemctl status salt-master   # confirm it's genuinely staying up, not just restarting once
```

Watch it for a minute after — a master that starts cleanly once but crashes again on its own internal retry logic will show that in `journalctl -u salt-master -f`, not just in the immediate `systemctl status` output.

---

## 14. Quick Reference

| I need to… | Go to |
|-----------|-------|
| Build `EXASLTCLD001` itself, or SaltGUI, from scratch | [ExampleMusic_Beginners_Guide.md](../ExampleMusic_Beginners_Guide.md) §7.4 |
| Understand the full states/pillar layout, gitfs mechanism | `salt/README.md` |
| Full minion buildsheet (checklist, sign-off) | `docs/buildsheets/buildsheet-salt-minion.md` |
| See what a specific state actually does | `salt/states/<name>/init.sls` — each has its own header comment |
| Query or confirm a minion's custom grains | §7 above |
| Check/adjust the automatic highstate schedule | §6 above |
| Apply state from the command line, real examples | §9 above |
| Run `state.apply`/`test.ping` from SaltGUI's browser UI | §8.1 above |
| Check gitfs/git_pillar are actually delivering content | §10 above |
| Force a refresh without waiting for the schedule | §11 above |
| The master's disk filled up | §12 above |
| `salt-master` won't start at all | §13 above |
| Full incident write-up for the 2026-08-11 disk-full/delivery saga | `docs/INCIDENT-LOG.md`'s `INC-2026-08-11-SALT-DISK-FULL` |
| Understand the full docs index | [INDEX.md](../INDEX.md) |

---

*Example Music Limited — Internal Infrastructure Documentation*
*Do not distribute outside the organisation*
*Credentials: See password manager — never store passwords in this document*
