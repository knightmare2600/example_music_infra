# windows_bootstrap/playbooks/files/

Local assets pushed directly to Windows hosts via `win_copy`, replacing the old
pre-Ansible pattern of fetching everything over HTTP from the provisioning
server (`exa_asset_base`/`exa_wallpaper_url`). That pattern only existed
because there was no other way to get a file onto a box before Ansible
existed in this estate — now that it does, these are just playbook files.

**2026-07-12:** the 10 binaries below are now committed to git — Robert's
explicit call, overriding this file's previous "these don't belong in a
public-style repo" stance. Worth noting the actual split when that
judgement comes up again: jq/ScreenRes/dua-cli are genuinely open source
(redistribution is fine); the three Sysinternals tools (AD Explorer,
Process Explorer, Process Monitor) are free-to-download but not open
source — proprietary Microsoft freeware. Robert's decision was to commit
all of them anyway, publicly-downloadable-and-free being the bar that
mattered to him, not open-source-licence purism.

## files/ (top level)

- `ExampleMusicWallpaper.png` — the corporate wallpaper image, used by
  `60-wallpaper.yml`. Platform-agnostic (same PNG regardless of CPU
  architecture), so it lives at the top level, not under an arch subfolder.

## x86_64/ and arm64/

Officially supported architectures: AMD64 and ARM64. One subfolder per
architecture (`x86_64` is the AMD64 build — matching `arch_facts.yml`'s
`host_arch` detection and the existing `detect_cpu.ps1`/`detect_cpu.cmd`
folder convention, not a different name for the same thing), each
containing the arch-specific build of every binary listed in
`binaries_extra` (see `group_vars/windows_server`, `windows_desktop`,
`windows_laptop`):

- `ADExplorer64.exe` / `ADExplorer64a.exe` — Sysinternals AD Explorer
  (https://live.sysinternals.com/tools/ADExplorer64.exe /
  https://live.sysinternals.com/tools/ARM64/ADExplorer64a.exe) — **server only**
- `procexp64.exe` / `procexp64a.exe` — Sysinternals Process Explorer
  (https://live.sysinternals.com/tools/procexp64.exe /
  https://live.sysinternals.com/tools/ARM64/procexp64a.exe) — **server only**
- `Procmon64.exe` / `Procmon64a.exe` — Sysinternals Process Monitor, a
  different tool from Process Explorer above despite the similar name
  (https://live.sysinternals.com/tools/Procmon64.exe /
  https://live.sysinternals.com/tools/ARM64/Procmon64a.exe) — **server only**
- `jq-windows-amd64.exe` / `jq-windows-arm64.exe` — jq
  (https://github.com/jqlang/jq/releases) — server, desktop, laptop
- `screenres-amd64.exe` / `screenres-arm64.exe` — ScreenRes (lowercase,
  `-amd64` not `-x64` — matches the real release asset names)
  (https://github.com/knightmare2600/ScreenRes/releases) — server, desktop, laptop

WinDirStat is **not** dropped here — it's in `choco_packages_common`
(`playbooks/40-choco-packages.yml`), installed via Chocolatey on every host
including servers (confirmed working on Server Core, which has just enough
GUI to run it). A `binaries_extra` copy existed on desktop/laptop until
2026-07-12 — removed as a dead duplicate.

dua-cli is **not** dropped here either — `tasks/dua_cli.yml` downloads it
directly from its upstream GitHub release at run time (arch-aware), since
it ships as a per-platform zip rather than a bare exe. Nothing to place in
this directory for it.

**2026-07-12 correction:** Process Explorer's ARM64 entry previously
pointed at `Procmon64a.exe` (Process Monitor's ARM64 binary) instead of its
own `procexp64a.exe` — a different Sysinternals tool was silently deployed
under Process Explorer's name. Also, ScreenRes's real release asset names
are lowercase `screenres-amd64.exe`/`screenres-arm64.exe`, not
`ScreenRes-x64.exe`/`ScreenRes-arm64.exe` as previously listed here — if
you already have files under the old names, rename them to match.

All of the above deploy to `C:\Windows\` (not `C:\Windows\System32\`) —
still systemwide-on-PATH either way, since `C:\Windows` is itself a default
PATH entry; `50-binaries.yml` has never used `System32` for any entry, so
none of the new/fixed ones are an exception to that.

`binaries_common` (`group_vars/windows/vars.yml`) is currently empty — if it
ever gets populated again, add those files at the top level of both
`x86_64/` and `arm64/` too (50-binaries.yml's "Deploy common binaries" task
already looks in `{{ host_arch }}/` for them).
