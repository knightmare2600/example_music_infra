# windows_bootstrap/playbooks/files/

Local assets pushed directly to Windows hosts via `win_copy`, replacing the old
pre-Ansible pattern of fetching everything over HTTP from the provisioning
server (`exa_asset_base`/`exa_wallpaper_url`). That pattern only existed
because there was no other way to get a file onto a box before Ansible
existed in this estate — now that it does, these are just playbook files.

Nothing in this directory is checked into git except this README — the
files below are either licensed third-party binaries or a company logo,
neither of which belong in a public-style repo. Drop the real files in
before running `50-binaries.yml` / `60-wallpaper.yml`.

## files/ (top level)

- `ExampleMusicWallpaper.png` — the corporate wallpaper image, used by
  `60-wallpaper.yml` and `05-bootstrap.yml` (Stage 9). Platform-agnostic
  (same PNG regardless of CPU architecture), so it lives at the top level,
  not under an arch subfolder.

## x86_64/ and arm64/

Officially supported architectures: AMD64 and ARM64. One subfolder per
architecture (`x86_64` is the AMD64 build — matching `arch_facts.yml`'s
`host_arch` detection and the existing `detect_cpu.ps1`/`detect_cpu.cmd`
folder convention, not a different name for the same thing), each
containing the arch-specific build of every binary listed in
`binaries_extra` (see `group_vars/windows_server`, `windows_desktop`,
`windows_laptop`):

- `ADExplorer64.exe` / `ADExplorer64a.exe` — Sysinternals AD Explorer
- `procexp64.exe` / `Procmon64a.exe` — Sysinternals Process Explorer
- `jq-windows-amd64.exe` / `jq-windows-arm64.exe` — jq
- `ScreenRes-x64.exe` / `ScreenRes-arm64.exe` — ScreenRes
- `WinDirStat.exe` / `WinDirStat_arm64.exe` — WinDirStat (desktop/laptop only)

`binaries_common` (`group_vars/windows/vars.yml`) is currently empty — if it
ever gets populated again, add those files at the top level of both
`x86_64/` and `arm64/` too (50-binaries.yml's "Deploy common binaries" task
already looks in `{{ host_arch }}/` for them).
