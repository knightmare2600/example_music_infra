# Build Sheet — Windows Admin Node (Desktop Experience)

**Document ID:** NET-BUILD-WIN-001  
**Classification:** Internal — Network Operations  
**Last Updated:** 2026-07-15  
**Signed off by:** ___________________________  Date: ___________

**Deploy workflow:** unattend XML (`C:\DeployTools\unattend_xml\` — DeployTools share
`\\EXADCSCPH001\DeployTools`, same convention as `buildsheet-server.md`) → OpenSSH reachable →
`ansible/playbooks/windows_bootstrap/site.yml` — this is a `windows_server`-class node, built
via the same Ansible chain as any other server. Chocolatey packages, PS7 modules, RSAT tools,
and domain join below are all handled by that run; Windows Admin Centre install itself remains
a manual step (no Ansible automation for it yet).

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
7zip  notepadplusplus.install  hyper  putty  winscp  far  pwsh googlechrome  firefox  vscode  git  wireshark  sysinternals
```

### PowerShell 7 Modules (Install-Module)
```
PSWriteColor  ConsoleTools  PSReadLine  CompletionPredictor  Terminal-Icons
```

### Nerd Fonts
```
nerd-fonts-cascadiacode
```

### RSAT Tools (Add-WindowsCapability)
```
Rsat.ActiveDirectory.DS-LDS.Tools~~~~0.0.1.0
Rsat.DNS.Tools~~~~0.0.1.0
Rsat.GroupPolicy.Management.Tools~~~~0.0.1.0
Rsat.DFS.Tools~~~~0.0.1.0
Rsat.DFSR.Tools~~~~0.0.1.0
Rsat.DHCP.Tools~~~~0.0.1.0
Rsat.FailoverCluster.Management.Tools~~~~0.0.1.0
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
