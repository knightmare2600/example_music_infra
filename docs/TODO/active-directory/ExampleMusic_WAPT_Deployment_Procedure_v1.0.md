# Example Music Limited — WAPT Server & Agent Deployment

> **Classification:** Internal — Infrastructure
> **Forest:** `jukebox.internal`
> **Domains:** `example.net` · `example.org` · `example.com`
> **Provisioning network:** `192.168.139.0/24`
> **Credentials:** See password manager — do **not** store passwords in this document

---

## Changelog

| Date       | Version | Change           | Author              |
|------------|---------|------------------|---------------------|
| 2025-04-26 | 1.0     | Initial document | Infrastructure Team |

---

## Overview

WAPT (Windows Agent Packaging Tool) is an agent-based software deployment platform developed by Tranquil IT. A central WAPT server hosts packages and manages agents installed on Windows endpoints. Agents communicate with the server over HTTPS and receive deployment instructions via the WAPT console.

This procedure covers server installation, SSL certificate handling, agent deployment via GPO, and validation.

> ℹ️ **NOTE:** WAPT uses its own PKI for package signing — this is separate from the SSL certificate used for HTTPS communication between agents and the server. This procedure covers the HTTPS certificate only.

---

## Prerequisites

| Requirement      | Detail                                                              |
|------------------|---------------------------------------------------------------------|
| WAPT Server OS   | Debian 11/12 (recommended) or compatible Linux                      |
| Windows domain   | Active Directory with Group Policy Management Console (GPMC)        |
| DNS              | WAPT server must be reachable by FQDN from all endpoints            |
| Firewall         | TCP 443 open from endpoints to WAPT server                          |
| OS access        | SSH to WAPT server as root or sudo user                             |
| Domain access    | Domain Admin account for GPO creation and certificate deployment     |
| Credentials      | See password manager                                                |

> ⚠️ **WARNING:** WAPT agents register using the server FQDN, not its IP address. If DNS resolution fails on an endpoint, the agent will not register. Confirm forward DNS resolution for the WAPT server FQDN from a representative workstation before proceeding.

---

## Step 1 — Install the WAPT Server

### 1.1 — Add the Tranquil IT repository

```bash
wget -O - https://wapt.tranquil.it/apt/tranquil-it.gpg | sudo gpg --dearmor -o /usr/share/keyrings/tranquil-it.gpg
echo "deb [signed-by=/usr/share/keyrings/tranquil-it.gpg] https://wapt.tranquil.it/apt/debian/ stable main" | sudo tee /etc/apt/sources.list.d/wapt.list
sudo apt update
sudo apt install waptserver -y
```

### 1.2 — Run the setup wizard

```bash
sudo waptserver-setup
```

The wizard will prompt for the server FQDN, admin password, and certificate options. Key points:

- Enter the server **FQDN** when prompted — do not enter an IP address. Agents embed this value at install time and cannot easily be changed after.
- The wizard generates a self-signed SSL certificate by default. If you have a CA-signed certificate, the wizard provides an option to supply it. CA-signed certificates are strongly preferred in production as they avoid the GPO certificate distribution step.
- Note the admin password entered — store it in the password manager immediately.

**Expected result:** The wizard completes without error. The WAPT web interface is accessible at `https://<fqdn>/` and returns the WAPT console login page.

---

## Step 2 — Export the WAPT Server SSL Certificate

This step is only required if a self-signed certificate was generated during setup. If a CA-signed certificate was used and Windows endpoints already trust the issuing CA, skip to Step 4.

On the WAPT server:

```bash
cp /opt/wapt/waptserver/ssl/server.crt /root/wapt-server.crt
```

Copy the certificate file to a location accessible from the domain controller — for example, the SYSVOL share or a temporary network path. The file is not sensitive (it is a public certificate), but restrict write access to the share.

> ℹ️ **NOTE:** The certificate at `/opt/wapt/waptserver/ssl/server.crt` is the server's public SSL certificate. It does not contain a private key. It is safe to distribute to endpoints — that is its purpose.

---

## Step 3 — Deploy the Certificate to Windows Endpoints via GPO

Windows does not trust self-signed certificates by default. Without distributing the WAPT server certificate to endpoints, agents will fail to register with TLS errors and the console will show no nodes.

Two options are provided. Use Option A in all environments. Option B is for isolated testing only.

---

### Option A — GPO Deployment (Required for Production)

#### 3.1 — Open Group Policy Management

On the domain controller, open **Group Policy Management** (`gpmc.msc`).

#### 3.2 — Create a new GPO

Right-click the domain or the target OU and select **Create a GPO in this domain, and Link it here**. Name it:

```
Deploy WAPT Root Certificate
```

#### 3.3 — Edit the GPO and import the certificate

Right-click the new GPO and select **Edit**. Navigate to:

```
Computer Configuration
  └── Policies
        └── Windows Settings
              └── Security Settings
                    └── Public Key Policies
                          └── Trusted Root Certification Authorities
```

Right-click **Trusted Root Certification Authorities** → **Import** → select `wapt-server.crt`.

#### 3.4 — Link the GPO to the correct OUs

Link the GPO to the OUs containing the machines that will run the WAPT agent. Typically:

- Workstations OU
- Servers OU (if agents are deployed to servers)

Do not link to the Domain Controllers OU unless WAPT agents are being deployed to DCs, which is uncommon.

#### 3.5 — Force a policy update on a test machine

On a representative workstation, run:

```powershell
gpupdate /force
```

#### 3.6 — Verify the certificate is present

```powershell
certlm.msc
```

Navigate to **Trusted Root Certification Authorities → Certificates** and confirm the WAPT server certificate is listed. The certificate subject will match the FQDN entered during WAPT server setup.

**Expected result:** The WAPT certificate appears in the Trusted Root Certification Authorities store on the test machine.

---

### Option B — Manual Import (Isolated Testing Only)

> ⚠️ **WARNING:** Do not use this method in production. It requires manual intervention on every endpoint and does not scale. Use Option A.

On the target machine, with the certificate copied to `C:\temp\wapt-server.crt`:

```powershell
Import-Certificate -FilePath "C:\temp\wapt-server.crt" -CertStoreLocation Cert:\LocalMachine\Root
```

---

> ⚠️ **WARNING — verify_cert = 0:** The WAPT agent configuration supports a `verify_cert = 0` option which disables TLS certificate verification entirely. This must never be used in production. It exposes endpoints to man-in-the-middle attacks and removes all transport security. If you are seeing TLS errors, fix the certificate trust chain — do not disable verification.

---

## Step 4 — Build a Custom WAPT Agent

Rather than deploying the generic agent installer, WAPT generates a customised agent binary pre-configured with the server address and certificate. This avoids needing to pass arguments at install time and is the correct method for GPO deployment.

On the WAPT server:

```bash
wapt-get make-agent
```

Output:

```
waptagent-custom.exe
```

Copy `waptagent-custom.exe` to the SYSVOL scripts share so it is accessible from all domain-joined machines:

```
\\<domain>\SYSVOL\<domain>\scripts\wapt\waptagent-custom.exe
```

---

## Step 5 — Deploy the Agent via GPO Startup Script

#### 5.1 — Create or edit a GPO for agent deployment

In GPMC, create a new GPO named:

```
Deploy WAPT Agent
```

Link it to the same OUs as the certificate GPO from Step 3.

#### 5.2 — Add a Computer Startup Script

Navigate to:

```
Computer Configuration
  └── Policies
        └── Windows Settings
              └── Scripts (Startup/Shutdown)
                    └── Startup
```

Add a PowerShell startup script with the following content:

```powershell
$AgentPath = "\\<domain>\SYSVOL\<domain>\scripts\wapt\waptagent-custom.exe"
$Service = Get-Service -Name WAPTService -ErrorAction SilentlyContinue

if (-not $Service) {
  Start-Process -FilePath $AgentPath -ArgumentList "/S" -Wait
}
```

> ℹ️ **NOTE:** The `if (-not $Service)` check prevents the installer from running on every startup once the agent is already installed. Without this guard the agent reinstalls on every reboot.

#### 5.3 — Confirm the script runs on next boot

Restart a test machine. After login, allow a few minutes for the startup script to complete, then check:

```powershell
Get-Service WAPTService
```

**Expected result:** `Status` shows `Running`.

---

## Step 6 — Validate

### 6.1 — Confirm the agent service is running on the endpoint

```powershell
Get-Service WAPTService
```

Expected output:

```
Status   Name               DisplayName
------   ----               -----------
Running  WAPTService        WAPT Service
```

### 6.2 — Confirm the node appears in the WAPT console

Open the WAPT console at `https://<fqdn>/` and log in. The endpoint should appear under **Hosts** within a few minutes of the agent service starting.

### 6.3 — Confirm no TLS errors

On the endpoint, check the WAPT agent log:

```
C:\Program Files (x86)\wapt\wapt.log
```

There should be no entries containing `SSL`, `certificate`, or `TLS` errors. If errors are present, the certificate trust chain is not correctly established — revisit Step 3.

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Agent fails to register, TLS errors in log | Certificate not trusted on endpoint | Complete Step 3 — confirm cert in `certlm.msc` |
| Agent registers but shows wrong server address | IP used instead of FQDN during setup | Rebuild agent with `wapt-get make-agent` after correcting FQDN in WAPT config |
| Node does not appear in console after install | DNS resolution failure | Confirm endpoint can resolve WAPT server FQDN — `Resolve-DnsName <fqdn>` from endpoint |
| WAPTService not present after startup script | Script did not run, or path to installer unreachable | Check SYSVOL path is accessible from endpoint — `Test-Path \\<domain>\SYSVOL\...` |
| `gpupdate /force` does not deliver certificate | GPO not linked to correct OU | Confirm GPO link in GPMC and run `gpresult /r` on endpoint to check applied GPOs |
| Agent reinstalls on every reboot | Startup script missing `Get-Service` guard | Update startup script per Step 5.2 |

---

## Completion Checklist

- [ ] WAPT server accessible via HTTPS at `https://<fqdn>/`
- [ ] SSL certificate trusted on all target endpoints (confirmed via `certlm.msc`)
- [ ] Custom agent built with `wapt-get make-agent` and copied to SYSVOL
- [ ] Agent GPO created, linked, and confirmed via `gpresult /r`
- [ ] `WAPTService` running on at least one test endpoint
- [ ] Test node visible in WAPT console under Hosts
- [ ] WAPT agent log contains no TLS or certificate errors

---

*Example Music Limited — Internal Infrastructure Documentation*
*Do not distribute outside the organisation*
*Credentials: See password manager — never store passwords in this document*
