# Build Sheet — Windows Admin Node (Desktop Experience)

**Document ID:** NET-BUILD-WIN-001  
**Classification:** Internal — Network Operations  
**Last Updated:** 2026-09-01  
**Signed off by:** ___________________________  Date: ___________

**Deploy workflow:** unattend XML (`C:\DeployTools\unattend_xml\` — DeployTools share
`\\EXADCSCPH001\DeployTools`, same convention as `buildsheet-server.md`) → OpenSSH reachable →
`ansible/playbooks/windows_bootstrap/site.yml` — this is a `windows_server`-class node, built
via the same Ansible chain as any other server. Chocolatey packages, PS7 modules, RSAT tools,
and domain join below are all handled by that run; Windows Admin Centre install itself remains
a manual step (no Ansible automation for it yet).  
**First-ever run (box still on DHCP):** `ansible-playbook playbooks/windows_bootstrap/site.yml -i <dhcp-ip>, -e target_hosts=<dhcp-ip> --ask-vault-pass` — see `ansible/playbooks/windows_bootstrap/README.md`'s Usage section for the full detail and the named-inventory form used on every run after this one

---

## Standard Build Reference

### OS
Windows Server 2022 (Desktop Experience) — or Windows 11 Pro where noted.  
Primary use: Windows Admin Centre, RSAT, remote management of all site nodes.

### Hostname Convention
```
EXASVRCLD002   — Windows Admin Centre node (CLD network)
EXAWKS<SITE>001 — Site admin workstation (where applicable)
```

### IP
```
EXASVRCLD002 : 192.168.69.20  (CLD network)
Site nodes   : DHCP or static per site convention
```

### Chocolatey Packages (choco install)
```
7zip.install  notepadplusplus.install  hyper  putty.install  winscp.install  far  powershell-core
rustdesk.install  edit  sdelete  wget  busybox  vcredist-all  dotnetfx  windirstat
googlechrome  firefox  vlc  windows-terminal
```

`sysinternals` was removed from this list 2026-08-14 after a live SHA256 checksum-mismatch failure against `EXADCSLAX001` (upstream `download.sysinternals.com` zip updated in place without the Chocolatey package's checksum catching up). Individual Sysinternals tools (ProcExp, ADExplorer, etc.) are instead deployed as committed binaries under `ansible/playbooks/windows_bootstrap/playbooks/files/{x86_64,arm64}/`.

This is the same `choco_packages_common` + `choco_packages_gui` baseline every server/GUI-capable
host gets (`40-choco-packages.yml`) — there is no separate WAC-specific package list; role-based
extras were removed from that playbook entirely 2026-07-12. `vscode`/`git`/`wireshark` are **not**
automated by anything in this repo — install manually if wanted.

### PowerShell 7 Modules (Install-Module)
```
PSConsoleTools  PSWindowsUpdate  PSWriteColor  PSReadLine  Terminal-Icons  CompletionPredictor  NerdFonts
```

### Nerd Fonts

Not a Chocolatey package — `tasks/fonts.yml` fetches JetBrains Mono Nerd Font directly from its
upstream GitHub release zip (`exa_font_files`, `group_vars/all/vars.yml`).

### RSAT Tools (Install-WindowsFeature)

Server OS installs RSAT via Server Manager features, not `Add-WindowsCapability` (that mechanism
is for client/workstation OS):
```
RSAT-AD-PowerShell  RSAT-AD-AdminCenter  RSAT-ADDS-Tools  RSAT-DNS-Server  GPMC
```

### Windows Admin Centre
Download from https://aka.ms/WACDownload  
Install on `EXASVRCLD002` — configure gateway mode so all other
nodes can connect to it remotely without per-machine WAC installs.

### OpenSSH
```powershell
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.0.1
Set-Service -Name sshd -StartupType Automatic
Restart-Service sshd
```

---

## Build Checklist

## Build Checklist

| Hostname | Hostname Set | Static IP | RDP | OpenSSH | SSH on Boot | SSH Running | Chocolatey | Choco Packages Installed | PS7 Installed | PS7 Modules + Nerd Fonts | Domain Joined (JUKEBOX) | RSAT Tools Installed | WAC Install & Gateway Set | Admin Creds Stored in KeepassXC | Notes |
|----------|------------------------|----------------------|-------------|-------------------|-----------------------|-------------------------|---------------------|---------------------------|-----------------------|-------------------------------------|------------------------|---------------------|-----------------------------------------------|----------------------------------------------|------|
| **EXASVRCLD002** | - [ ] | - [ ] | - [ ] | - [ ] | - [ ] | - [ ] | - [ ] | - [ ] | - [ ] | - [ ] | - [ ] | - [ ] | - [ ] | - [ ] | WAC · 69.20 |

> Add rows for any additional site admin workstations as required.

## Sign-Off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Build engineer | | | |
| Network lead | | | |
| Operations manager | | | |

---

*Internal Use Only — Network Engineering*
