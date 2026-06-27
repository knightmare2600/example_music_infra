# Build Sheet — Domain Controllers (EXADCS\*001)

**Document ID:** NET-BUILD-DCS-001  
**Classification:** Internal — Network Operations  
**Domain:** `jukebox.internal` (NetBIOS: `JUKEBOX`)  
**Last Updated:** 2026-03-06  
**Signed off by:** ___________________________  Date: ___________

---

## Standard Build Reference

### Unattend XML
Use `autounattend2022.xml` or `autounattend_2022gui.xml` from `C:\DeployTools\unattend_xml\`  
DeployTools share: `\\EXADCSCPH001\DeployTools` (Z: drive — mapped by `PostOOBE.cmd` as `JUKEBOX\Administrator`)

### Windows Optional Features
```powershell
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.0.1
```

### Chocolatey Packages (choco install)
```
7zip  notepadplusplus.install  hyper  putty  winscp  far  powershell-core  rustdesk
```

> **RustDesk** is also pre-staged in `C:\DeployTools\utils\` on the WinPE image.  
> Acknowledge at build time that RustDesk is installed and reachable before signing off.

### PowerShell 7 Modules (Install-Module)
```
PSWriteColor  PSConsoleTools  PSReadLine  CompletionPredictor  Terminal-Icons
```

### Nerd Fonts
```
nerd-fonts-cascadiacode  (or preferred variant — via choco or oh-my-posh)
```

### RSAT / AD Management Tools (Add-WindowsCapability)
```
Rsat.ActiveDirectory.DS-LDS.Tools~~~~0.0.1.0
Rsat.DNS.Tools~~~~0.0.1.0
Rsat.GroupPolicy.Management.Tools~~~~0.0.1.0
Rsat.DFS.Tools~~~~0.0.1.0
Rsat.DFSR.Tools~~~~0.0.1.0
```

### OpenSSH Boot Commands
```powershell
Set-Service -Name sshd -StartupType Automatic
Restart-Service sshd
```

### IP Convention
```
Primary DC   : 192.168.<site-octet>.10
Secondary DC : 192.168.<site-octet>.11  (if applicable)
```

---

## Promotion Status

DC promotion is a multi-step process covered in **NET-AD-DC-001**.  
The `DC` checkbox below confirms the full promotion procedure  
in that document has been completed and signed off on the DC Promotion Sheet.

---

## Build Checklist

> **Columns:** HN = Hostname set correctly · RDP = RDP enabled · SF = OpenSSH feature installed · SB = SSH start on boot · SR = SSH started/restarted · CH = Chocolatey installed · CP = Choco packages installed · P7 = PowerShell 7 installed · PM = PS7 modules installed · DJ = Domain joined (JUKEBOX) · RS = RSAT / AD tools installed · DC = DC promoted (see NET-AD-DC-001) · IP = Static IP set · RD = RustDesk acknowledged

### Scotland

| Hostname | RDP | SF | SB | SR | CH | CP | P7 | PM | DJ | RS | DC | IP | RD | Notes |
|----------|-----|----|----|----|----|----|----|----|----|----|----|----|----|----|
| EXADCSFAL001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | HEAD OFFICE / PDC EMULATOR / FSMO |
| EXADCSEDI001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | ⚠️ See Appendix A — legacy EXADCREDI001 to be decommissioned |
| EXADCSGLA001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | ⚠️ See Appendix A — legacy EXADCRGLA001 to be decommissioned |
| EXADCSABD001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| EXADCSCLY001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| EXADCSDUN001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| EXADCSPER001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |

### England

| Hostname | RDP | SF | SB | SR | CH | CP | P7 | PM | DJ | RS | DC | IP | RD | Notes |
|----------|-----|----|----|----|----|----|----|----|----|----|----|----|----|----|
| EXADCSLND001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | ⚠️ See Appendix A — legacy EXADCRLND001 to be decommissioned |
| EXADCSBIR001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | ⚠️ See Appendix A — legacy EXADCRBIR001 to be decommissioned |
| EXADCSMCR001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | ⚠️ See Appendix A — legacy EXADCRMCR001 to be decommissioned |
| EXADCSLIV001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | ⚠️ See Appendix A — legacy EXADCRLIV001 to be decommissioned |
| EXADCSNEW001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | ⚠️ See Appendix A — legacy EXADCRNEW001 to be decommissioned |
| EXADCSSHE001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| EXADCSHUL001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| EXADCSCOV001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| EXADCSHAL001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |

### Danmark

| Hostname | RDP | SF | SB | SR | CH | CP | P7 | PM | DJ | RS | DC | IP | RD | Notes |
|----------|-----|----|----|----|----|----|----|----|----|----|----|----|----|----|
| EXADCSCPH001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | ORIG DC → SITE DC · DeployTools host |
| EXADCSKGE001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | ⚠️ WS2016 EOL — rebuild priority |
| EXADCSFAX001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| EXADCSKOR001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |
| EXADCSODE001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | EU HUB |

### Deutschland

| Hostname | RDP | SF | SB | SR | CH | CP | P7 | PM | DJ | RS | DC | IP | RD | Notes |
|----------|-----|----|----|----|----|----|----|----|----|----|----|----|----|----|
| EXADCSBON001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | SCHEMA MASTER / DOMAIN NAMING MASTER |
| EXADCSBERG001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | ⚠️ See Appendix A — legacy EXADCSBRD001 in inventory |
| EXADCSMUN001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | |

### Sverige / Norge / Nederland / Italia / Österreich

| Hostname | RDP | SF | SB | SR | CH | CP | P7 | PM | DJ | RS | DC | IP | RD | Notes |
|----------|-----|----|----|----|----|----|----|----|----|----|----|----|----|----|
| EXADCSGOT001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | Gothenburg |
| EXADCSOSL001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | Oslo |
| EXADCSAMS001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | Amsterdam |
| EXADCSMIL001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | Milan |
| EXADCSVIE001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | Vienna |

### Canada

| Hostname | RDP | SF | SB | SR | CH | CP | P7 | PM | DJ | RS | DC | IP | RD | Notes |
|----------|-----|----|----|----|----|----|----|----|----|----|----|----|----|----|
| EXADCSBRK001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | NA / APAC HUB |
| EXADCSTOR001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | Toronto |
| EXADCSMTL001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | Montréal |

### USA

| Hostname | RDP | SF | SB | SR | CH | CP | P7 | PM | DJ | RS | DC | IP | RD | Notes |
|----------|-----|----|----|----|----|----|----|----|----|----|----|----|----|----|
| EXADCSNYC001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | New York |
| EXADCSLAX001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | Los Angeles |
| EXADCSMIA001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | Miami — PENDING BUILD |
| EXADCSNJC001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | New Jersey |
| EXADCSCHI001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | Chicago |
| EXADCSATL001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | Athens GA |

### Australia / New Zealand

| Hostname | RDP | SF | SB | SR | CH | CP | P7 | PM | DJ | RS | DC | IP | RD | Notes |
|----------|-----|----|----|----|----|----|----|----|----|----|----|----|----|----|
| EXADCSSYD001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | Sydney |
| EXADCSMEL001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | Melbourne |
| EXADCSAKL001 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | Auckland |

---

## DC Promotion Sheet

Attach or staple the DC Promotion Sheet (NET-AD-DC-001 completion record)
for each node once promoted. The `DC` checkbox above is not ticked until
that sheet is complete and signed off.

---

## Sign-Off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Build engineer | | | |
| Network lead | | | |
| Operations manager | | | |

---

## Appendix A — Legacy Hostnames & Known Naming Inconsistencies

> **Action for build engineer:** When you encounter any of the hostnames or naming patterns below,  
> update the relevant record to use the canonical convention and note it in the build log.  
> Do not propagate legacy names into new DNS records, AD objects, or documentation.

### DCR → DCS (Legacy Regional DCs — Rebuild in Progress)

The following DCs exist under the legacy `EXADCR*` naming scheme. They are functional but  
will be replaced by new `EXADCS*` builds as part of this rollout. Until decommissioned,  
the legacy nodes should remain in service. Do **not** demote them until the new DCS node  
for that site is promoted, replicated, and signed off.

| Legacy Hostname | Site | Canonical Replacement | Status |
|----------------|------|-----------------------|--------|
| `EXADCRGLA001` | GLA | `EXADCSGLA001` | Pending rebuild |
| `EXADCREDI001` | EDI | `EXADCSEDI001` | Pending rebuild |
| `EXADCRLND001` | LND | `EXADCSLND001` | Pending rebuild |
| `EXADCRMCR001` | MCR | `EXADCSMCR001` | Pending rebuild |
| `EXADCRLIV001` | LIV | `EXADCSLIV001` | Pending rebuild |
| `EXADCRNEW001` | NEW | `EXADCSNEW001` | Pending rebuild |
| `EXADCRBIR001` | BIR | `EXADCSBIR001` | Pending rebuild |

### BRD → BER (West Berlin Site Code Correction)

The network inventory currently records the West Berlin site as `BRD` in some places.  
`BER` is canonical. The inventory will be updated as part of the next full review.

| Legacy / Incorrect | Canonical | Affected hostnames |
|--------------------|-----------|-------------------|
| `EXADCSBRD001` | `EXADCSBERG001` | Update DNS, AD site object, inventory |
| `BRD` site code | `BER` | Update any references in site-inventory.md, network-inventory.md |

### SVR → SRV (Server Role Prefix)

If you encounter any hostnames using `EXASVR*`, the canonical prefix is `EXASRV*`.  
Update DNS and AD computer object names when rebuilding.

| Legacy pattern | Canonical pattern | Example |
|---------------|-------------------|---------|
| `EXASVR<SITE><N>` | `EXASRV<SITE><N>` | `EXASVRCLD001` → `EXASRVCLD001` |

> Note: `EXASVRCLD001`, `EXASVRCLD002`, `EXASVRCLD003` in the network inventory  
> are already using the legacy pattern and should be corrected on next rebuild.

---

*Internal Use Only — Network Engineering*
