# Build Sheet — Windows Admin Node (Desktop Experience)

**Document ID:** NET-BUILD-WIN-001  
**Classification:** Internal — Network Operations  
**Last Updated:** 2026-03-05  
**Signed off by:** ___________________________  Date: ___________

> ⚠️ **TODO:** autounattend.xml files exist but location not yet confirmed.
> Check with build engineer before starting a manual build — the XML may automate a significant portion of this checklist. Update this sheet once the XML files are located and tested.

---

## Standard Build Reference

### OS
Windows Server 2022 (Desktop Experience) — or Windows 11 Pro where noted.  
Primary use: Windows Admin Centre, RSAT, remote management of all site nodes.

### Hostname Convention
```
EXASVRCLD001   — Windows Admin Centre node (CLD network)
EXAWKS<SITE>001 — Site admin workstation (where applicable)
```

### IP
```
EXASVRCLD001 : 192.168.139.20  (CLD network)
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
Install on `EXASVRCLD001` — configure gateway mode so all other
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
| **EXASVRCLD001** | - [ ] | - [ ] | - [ ] | - [ ] | - [ ] | - [ ] | - [ ] | - [ ] | - [ ] | - [ ] | - [ ] | - [ ] | - [ ] | - [ ] | WAC · 139.20 |

> Add rows for any additional site admin workstations as required.

## Sign-Off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Build engineer | | | |
| Network lead | | | |
| Operations manager | | | |

---

*Internal Use Only — Network Engineering*
