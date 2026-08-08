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

This is the thing you'll do most often. Full detail (including the exact PowerShell commands) lives in `ansible/playbooks/tacticalrmm/README.md`'s "Step 5" — this section is the short version, worth knowing without going and reading that file every time.

1. In the web UI: **Agents → + Add Agent**. Pick the target **Client** and **Site** (create them first under **Clients → + Add Client** / **+ Add Site** if they don't exist yet — nothing in this repo pre-creates Client/Site structure, it's purely web-UI-managed), and the agent type — `server` or `workstation`, matching the actual endpoint, don't default to `server` out of habit.
2. This generates a **signed, time-limited download URL** (expires within about an hour) and a matching one-time `--auth` deployment token. Copy both fresh, every time — neither is reusable, and neither belongs in a committed doc, a script, or a chat message that outlives the deployment.
3. On the endpoint, download and run the installer, then register the agent with the `--auth` token — see the README's Step 5 for the exact commands (they differ slightly by whether it's the first time an agent's been deployed to that endpoint or a reinstall).
4. `--insecure` is required on the registration step too — same self-signed certificate as the server itself. Omitting it fails the install outright, not silently.

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

If `TacticalRMM` genuinely isn't listed, create it directly with `AddDeviceGroup` rather than re-running the whole playbook — see the README's own Troubleshooting section for the exact command shape. Don't assume a clean exit code from any `meshctrl.js` command proves the action landed server-side — verify with a read-back command like `ListDeviceGroups` immediately after, the same lesson this exact bug taught during the original build.

---

## 7. Quick Reference

| I need to… | Go to |
|-----------|-------|
| Deploy an agent, full command detail | `ansible/playbooks/tacticalrmm/README.md` §"Step 5" |
| Understand how `EXARMMCLD001` was built | `ansible/playbooks/tacticalrmm/README.md`, `ansible/playbooks/tacticalrmm/PLAN-tacticalrmmme.md` |
| Learn the general TacticalRMM web UI (dashboards, alert policies, automated tasks) | `https://docs.tacticalrmm.com` — upstream, not this repo |
| Understand why standalone MeshCentral (`EXAMSHCLD001`) is gone | `ansible/playbooks/tacticalrmm/README.md`'s "EXAMSHCLD001 — RETIRED" section |
| Find a site's IP / subnet / naming convention | [ExampleMusic_Beginners_Guide.md](../ExampleMusic_Beginners_Guide.md) — the estate-wide guide this document is a companion to |
| Understand the full docs index | [INDEX.md](../INDEX.md) |

---

*Example Music Limited — Internal Infrastructure Documentation*
*Do not distribute outside the organisation*
*Credentials: See password manager — never store passwords in this document*
