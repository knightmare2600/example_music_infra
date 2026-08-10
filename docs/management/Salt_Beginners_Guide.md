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

## 6. SaltGUI — why states might not show up yet

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

---

## 7. Quick Reference

| I need to… | Go to |
|-----------|-------|
| Build `EXASLTCLD001` itself, or SaltGUI, from scratch | [ExampleMusic_Beginners_Guide.md](../ExampleMusic_Beginners_Guide.md) §7.4 |
| Understand the full states/pillar layout, gitfs mechanism | `salt/README.md` |
| Full minion buildsheet (checklist, sign-off) | `docs/buildsheets/buildsheet-salt-minion.md` |
| See what a specific state actually does | `salt/states/<name>/init.sls` — each has its own header comment |
| Understand the full docs index | [INDEX.md](../INDEX.md) |

---

*Example Music Limited — Internal Infrastructure Documentation*
*Do not distribute outside the organisation*
*Credentials: See password manager — never store passwords in this document*
