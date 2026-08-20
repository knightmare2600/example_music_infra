# TacticalRMM — Beginner's Guide

> **Classification:** Internal — Infrastructure
> **Server:** `EXARMMCLD001` (`192.168.69.14`)
> **Web UI:** `https://rmm.jukebox.internal`
> **Credentials:** See password manager — do **not** store passwords in this document

---

## Changelog

| Date       | Change                    |
|------------|---------------------------|
| 2026-08-08 | Initial version — companion to [ExampleMusic_Beginners_Guide.md](../ExampleMusic_Beginners_Guide.md), written the same way, for the same two people, after `EXAMSHCLD001` (standalone MeshCentral) was retired in favour of TacticalRMM's own bundled MeshCentral. |
| 2026-08-20 | Added §7, Tags — this estate's convention for grouping agents by role (`role:WKS`, `role:DCS`, etc., matching `benarbejde/role_codes.csv`) across Client/Site boundaries, and the bulk-script-by-tag workflow this makes possible (e.g. pushing a Chocolatey package to every workstation regardless of site). Renumbered the old §7 Quick Reference to §8. |

---

## 1. Introduction

This document is for Malcolm and Jamie. If you are neither Malcolm nor Jamie, you are welcome to read it, but it was written specifically for the two of you.

It assumes you have already read [ExampleMusic_Beginners_Guide.md](../ExampleMusic_Beginners_Guide.md) — the naming convention, IP addressing scheme, and "known source of truth" discipline described there apply here without repeating them.

This document covers **using** TacticalRMM day to day — logging in, deploying an agent, moving an agent between Client/Site, and the one real bug you're likely to hit. It does not cover how `EXARMMCLD001` was built — that's `ansible/playbooks/tacticalrmm/README.md` and `PLAN-tacticalrmmme.md`, and you shouldn't need either of those unless you're rebuilding the server itself.

It also does not attempt to teach you TacticalRMM's own web UI in general — dashboards, alert policies, automated tasks, scripting. TacticalRMM has its own upstream documentation for that (`https://docs.tacticalrmm.com`). What's here is specific to *this* estate's deployment: what's real, what's been live-tested, and what to do when the one known failure mode shows up.

---

## 2. What TacticalRMM Is (and Isn't)

TacticalRMM is this estate's endpoint inventory/monitoring/alerting/dashboards/reporting platform, and — via its own bundled MeshCentral instance — the remote-access platform: remote desktop, remote terminal, interactive PowerShell/CMD, Linux shell, file transfer.

It is explicitly **not** config management, and it is explicitly **not** software deployment. Those stay Salt's job (`EXASLTCLD001`) for Windows client endpoints, and Ansible's job for everything else. If you find yourself reaching for a TacticalRMM automated task to push a config change or install software, stop — that's the wrong tool for this estate, even though TacticalRMM is technically capable of it. This split is non-negotiable and repeated throughout this estate's own documentation for a reason: two systems fighting over the same job is worse than either system doing less.

TacticalRMM's own bundled MeshCentral instance is also this estate's **only** remote-access platform now. A standalone MeshCentral build (`EXAMSHCLD001`) existed briefly (2026-08-04 to 2026-08-08) but was retired once TacticalRMM's bundled instance was confirmed as a full, real-use replacement — see `ansible/playbooks/tacticalrmm/README.md`'s "EXAMSHCLD001 — RETIRED" section if you're wondering why an old runbook or diagram still mentions it.

---

## 3. Accessing TacticalRMM

**Web UI:** `https://rmm.jukebox.internal` — self-signed certificate (`--insecure`, same reasoning as every other strictly-internal/WireGuard-only box in this estate; your browser will warn you once, that's expected).

**Credentials:** KeePassXC, under `Infrastructure/CLD` — three separate entries, not one:

| Entry | What it's for |
|-------|----------------|
| `EXARMMCLD001-django-admin` | Your actual login — username + password |
| `EXARMMCLD001-django-totp-setup-key` | The TOTP base32 secret — **not** a login password, this seeds your authenticator app (or `keepassxc-cli`'s own TOTP support) the first time you set up 2FA. Login MFA is bound the moment the server-side account was created, not deferred to first browser login — if your authenticator ever needs re-seeding, this is the value, ask before assuming it's stale |
| `EXARMMCLD001-meshcentral-admin` | Separate credentials for the bundled MeshCentral instance directly (`https://mesh.jukebox.internal`) — you won't normally need this; TacticalRMM's own UI reaches MeshCentral sessions for you |

If none of these three entries exist yet in your own KeePassXC vault, that's a sync issue, not a "they were never set" issue — ask Malcolm/Robert rather than assuming the server has no credentials.

---

## 4. Deploying an Agent to an Endpoint

This is the thing you'll do most often.

1. In the web UI: **Agents → + Add Agent**. Pick the target **Client** and **Site** (create them first under **Clients → + Add Client** / **+ Add Site** if they don't exist yet — nothing in this repo pre-creates Client/Site structure, it's purely web-UI-managed), and the agent type — `server` or `workstation`, matching the actual endpoint, don't default to `server` out of habit.
2. This generates a **signed, time-limited download URL** (expires within about an hour) and a matching one-time `--auth` deployment token. Copy both fresh, every time — neither is reusable, and neither belongs in a committed doc, a script, or a chat message that outlives the deployment.

On the Windows endpoint, in `pwsh.exe` (not `powershell.exe`):

```powershell
# 1. Download the installer -- <signed-url> and the version/arch in the
#    filename both come straight from the web UI dialog above, copy exactly
iwr '<signed-download-url-from-web-ui>' -OutFile tacticalagent-v<version>-windows-<arch>.exe

# 2. Silent install of the installer itself
tacticalagent-v<version>-windows-<arch>.exe /VERYSILENT /SUPPRESSMSGBOXES

# 3. Brief pause -- lets the installer settle before the next step registers
#    the agent with the backend
ping 127.0.0.1 -n 7

# 4. Register the agent with EXARMMCLD001
"C:\Program Files\TacticalAgent\tacticalrmm.exe" -m install `
  --api https://api.jukebox.internal `
  --client-id <client-id> --site-id <site-id> `
  --agent-type server `
  --auth <auth-token-from-step-1> `
  --rdp --ping --insecure
```

`--insecure` is **required** on the registration step too — same self-signed certificate as the server itself; omitting it fails the install outright, not silently. `--rdp`/`--ping` are optional per-endpoint feature toggles (enable RDP, respond to ICMP), not required for a successful install. `--client-id`/`--site-id` are the numeric IDs from the web UI's Add Agent dialog, not the Client/Site names themselves.

**If the install fails with "Unable to download the mesh agent from the RMM"** — see §6 below before assuming the whole build is broken. This is a known, understood failure mode with a specific fix, not a sign the server needs rebuilding.

---

## 5. Moving an Agent to a Different Client/Site

Sometimes an agent gets deployed under the wrong Client/Site — commonly the default `TacticalRMM` Client/Site during initial testing, needing to move to a real one afterward.

Confirmed against the real backend source, not guessed: an `Agent` only has a `site` field (no separate `client` field at all — a Site belongs to a Client, so moving the Site moves the Client too).

1. In the dashboard tree, right-click the agent (or double-click, depending on your dashboard's own configured default double-click action) → **Edit Agent**.
2. Pick the target Site (under the target Client) in the Site dropdown, save.

There is **no bulk "move to site" action** — the bulk-actions endpoint only covers running commands/scripts across many agents at once, not reassigning Site/Client. For a single agent, the per-agent Edit dialog above is the only path regardless of how many agents you're moving one at a time.

---

## 6. Troubleshooting — "Unable to download the mesh agent from the RMM"

A real bug, hit live during this estate's own TacticalRMM build (2026-08-07), root-caused and fixed in `tacticalrmm_server.yml` — but the same *symptom* can still show up if MeshCentral's device group ever gets deleted or renamed by hand, so it's worth knowing how to diagnose rather than assuming it can never recur.

Diagnose directly rather than guessing or re-running the whole build:

```bash
sudo -u tacticalrmm bash -c "cd /rmm/api/tacticalrmm && /rmm/api/env/bin/python manage.py check_mesh"
```

This walks the exact same code path the agent installer hits, and reports exactly which stage fails. If it stops at `"Error: you are using a custom mesh device group name..."`, the `TacticalRMM` device group in MeshCentral doesn't exist (or doesn't match TacticalRMM's own Global Settings). Check what device groups actually exist:

```bash
# credentials from KeePassXC, EXARMMCLD001-meshcentral-admin
node node_modules/meshcentral/meshctrl.js --url wss://mesh.jukebox.internal:443 \
  --loginuser <user> --loginpass <pass> ListDeviceGroups
```

If `TacticalRMM` genuinely isn't listed, create it directly rather than re-running the whole playbook, as the `tacticalrmm` service user, from `/meshcentral`:

```bash
sudo -u tacticalrmm bash -c '
  cd /meshcentral
  node node_modules/meshcentral/meshctrl.js \
    --url wss://mesh.jukebox.internal:443 \
    --loginuser <user> --loginpass <pass> \
    AddDeviceGroup --name TacticalRMM
'
```

(credentials from KeePassXC, `EXARMMCLD001-meshcentral-admin`)

**Don't stop there and assume it worked.** A clean exit code from `meshctrl.js` is not proof the group actually landed server-side — that's exactly the class of bug this whole failure mode traces back to (the original build's own `AddDeviceGroup` call also exited 0 without the group actually existing, due to a readiness-check race). Always verify with a read-back immediately after:

```bash
sudo -u tacticalrmm bash -c "cd /meshcentral && node node_modules/meshcentral/meshctrl.js --url wss://mesh.jukebox.internal:443 --loginuser <user> --loginpass <pass> ListDeviceGroups"
```

Confirm `TacticalRMM` genuinely appears in the output before considering this fixed.

---

## 7. Tags — Grouping Agents Across Client/Site by Role

Client/Site is TacticalRMM's primary hierarchy, but it's a *location* axis, not a *role* one — every workstation across every site doesn't share a Site, so there's no way to target "all workstations, wherever they are" through Client/Site alone. Tags are TacticalRMM's own answer to this: a label on an agent, independent of Client/Site, usable to filter the Agents table and to scope bulk actions (including bulk script runs) across the whole estate at once.

**This estate's convention: tag by role code, not ad-hoc names.** Use the same codes already defined in `benarbejde/role_codes.csv` — `role:WKS` for workstations, `role:DCS` for domain controllers, `role:SVR` for generic servers, `role:LAP` for laptops, `role:SUR` for Surface devices, and so on for whatever role codes actually get an RMM agent. Don't invent parallel names like "servercore" that don't map to anything else in the estate — the whole point of `role_codes.csv` being the single source of truth for role naming is that it stays the one place this vocabulary lives; a second, TacticalRMM-only naming scheme for the same concept is exactly the kind of duplicated-logic problem this estate avoids elsewhere.

### Creating and assigning a tag

1. Tags are managed under **Settings** in the web UI. Create the tag once (e.g. `role:WKS`) — exact menu wording may have moved since this was written, TacticalRMM upstream evolves independently of this doc; if it's not where you expect, check `https://docs.tacticalrmm.com` rather than assuming the feature's gone.
2. **Per-agent**: open the agent's **Edit Agent** dialog (same one used to move Client/Site in §5) — there's a Tags field there to add one or more tags to that single agent.
3. **In bulk**: from the Agents table, filter/search by hostname (e.g. `EXAWKS` to catch every workstation regardless of site — see §4's naming convention), multi-select the results, and use the bulk "Add Tag" action rather than tagging one at a time.

### Using a tag for a bulk action (worked example: push a Chocolatey package to every workstation)

1. Tag every `EXAWKS*` agent `role:WKS` (once, per the bulk step above — new agents get tagged individually going forward, or the next time you sweep the Agents table by hostname).
2. Add the script once (Settings → Scripts → *Add Script*, PowerShell):
   ```powershell
   choco install winscp -y
   ```
   (Chocolatey itself doesn't need separate installing on estate-built workstations — it's already part of the standard Windows build, Stage 11 of `Join-DomainAndBootstrap.ps1`.)
3. Agents table → filter by tag `role:WKS` → multi-select the results → bulk action → *Run Script* → pick the Chocolatey script → *Run Now*.
4. Check the per-agent script-run history for exit code `0` before considering it done — same as any other bulk script run, don't assume success from the action just having fired.

**Not yet confirmed, flagged rather than assumed**: whether a tag can be the *targeting* criterion for a recurring Automated Task inside a Policy — i.e. whether a brand-new `EXAWKS*` agent, tagged `role:WKS` the moment it's registered, would automatically inherit a standing "install winscp" task without anyone re-running the bulk action above. Policies in TacticalRMM fundamentally apply via Client/Site (and the built-in Server/Workstation agent-type split), and this estate's install tracks upstream `master`/`main` rather than a pinned release, so exact tag-scoped Automation Manager behaviour hasn't been checked against what's actually running on `EXARMMCLD001`. Until that's confirmed live, treat tags as reliable for **search, filtering, and bulk ad-hoc actions** (fully confirmed, used above) — not yet as a substitute for a real recurring Policy assignment.

---

## 8. Quick Reference

| I need to… | Go to |
|-----------|-------|
| Deploy or move an agent, troubleshoot the mesh-agent bug | §4/§5/§6 above — this document is now the complete, self-contained reference for all of it |
| Tag agents by role, or push something to every agent matching a role/tag | §7 above |
| Understand how `EXARMMCLD001` was built, or rebuild it | `ansible/playbooks/tacticalrmm/README.md`, `ansible/playbooks/tacticalrmm/PLAN-tacticalrmmme.md` |
| Learn the general TacticalRMM web UI (dashboards, alert policies, automated tasks) | `https://docs.tacticalrmm.com` — upstream, not this repo |
| Understand why standalone MeshCentral (`EXAMSHCLD001`) is gone | `ansible/playbooks/tacticalrmm/README.md`'s "EXAMSHCLD001 — RETIRED" section |
| Find a site's IP / subnet / naming convention | [ExampleMusic_Beginners_Guide.md](../ExampleMusic_Beginners_Guide.md) — the estate-wide guide this document is a companion to |
| Understand the full docs index | [INDEX.md](../INDEX.md) |

---

*Example Music Limited — Internal Infrastructure Documentation*
*Do not distribute outside the organisation*
*Credentials: See password manager — never store passwords in this document*
