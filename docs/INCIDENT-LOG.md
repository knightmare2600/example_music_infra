# Example Music Limited — Incident Log

**Doc ID:** OPS-INC-001  
**Scope:** Example Music Limited — Infrastructure  
**Applies to:** Operational incidents affecting the estate's infrastructure, tooling, or automation

---

## About this document

This is not a finger-pointing exercise. It is an honest, upfront record that something went wrong — a gap in a process, a mistake, an outcome nobody planned for — and what was done about it. Mistakes happen; that is not news to anyone who has run real infrastructure for any length of time. What matters is that they get caught, contained, fixed, and turned into something the estate is better protected against next time.

A few ground rules for every entry in this log:

- **No blame, no euphemisms.** We say what happened in plain language. We don't dress up a mistake in management-speak to soften it, and we don't need to soften it — but we also don't need to be crude or rude about it either, and we don't name-and-shame the people involved. Roles are used instead of names throughout.
- **Not everything is written down.** Some technical detail is deliberately left out where spelling it out in full serves no purpose beyond embarrassment — the difference between "an omission in the process left a required credential unavailable when it was needed" and the exact, unflattering specifics of how that happened. The engineering substance — cause, impact, fix — is always in here. Colour that adds nothing isn't.
- **The order of operations is always the same:** stop the problem from spreading, let the engineers actually fixing it work without someone stood over their shoulder, and only once things are stable and a safe hold period has passed does the paperwork — this document, any process or harness changes, any new procedure — get written up.
- **Every incident here made the estate better**, by definition — an incident is what happens when an error, omission, or mistake wasn't yet caught by something that now is (or, at minimum, is written down as a known, understood risk). Remove one contributing gap and, on the next attempt, that path to the accident is closed. That doesn't mean nothing will ever go wrong again — it means every entry here is a genuine, permanent improvement, and this log is the record of accumulating them.

## Index

Chronological, oldest incident first. Entries are added as they're formally written up, which is not necessarily the order they occurred — this log starts partway through the estate's history, and earlier incidents are backfilled retroactively as time allows, inserted in their correct chronological position rather than appended to the end.

| Incident ID | Date | Summary |
|---|---|---|
| [INC-2026-04-03-BMC-CREDS](#inc-2026-04-03-bmc-creds--mismatched-bmc-credentials-on-a-newly-delivered-fal-server) | 2026-04-03 | Vendor delivered the wrong physical chassis under otherwise-correct paperwork — documented BMC credentials didn't work on arrival at FAL |
| [INC-2026-07-12-SSH-KEY](#inc-2026-07-12-ssh-key--lost-ssh-keypair-delayed-pve-node-deployment-in-scandinavia) | 2026-07-12 | Lost/forgotten SSH keypair delayed PVE node deployment in Scandinavia |

---

## INC-2026-04-03-BMC-CREDS — Mismatched BMC credentials on a newly-delivered FAL server

### Incident Background

**Date:** 3 April 2026  
**Scope:** Commissioning of a newly-delivered physical server at FAL (Falkirk)  
**Cause (summary):** The vendor shipped a different physical chassis than the one described on its own accompanying asset tags and paperwork — identically specced, but not the same unit — so the documented BMC administrator credentials did not work on the hardware actually received.

A new server arrived at FAL and was racked as normal. The asset tags and delivery paperwork listed BMC administrator credentials for remote out-of-band management. Those credentials did not authenticate against the delivered unit. It was later established that the vendor had shipped a different, identically-specced chassis than the one the paperwork actually described — a fulfilment mix-up on their end, not a data-entry error on ours. The hardware itself was fine for purpose; only the credentials on file were wrong for the box in front of the technician.

### Root Cause & Mitigation

With the documented BMC credentials unusable, remote out-of-band access to the server was not available at all — there was no way to reach it except locally. The technician connected a crash cart (monitor, keyboard, a small power bar) directly to the server. A mild inconvenience at FAL, with a technician already on site; the same problem at a site without easy physical presence, such as LAX or SYD, would have cost considerably more time.

With local console access, the technician PXE-booted the server using the estate's own iPXE menu to boot into GParted Live (already an existing boot option, not something built for this), then installed `ipmitool` on that live environment.

From there, `ipmitool user set password 2 <new password>` reset the BMC's administrator account directly, in-band, from the host's own IPMI device — bypassing the broken remote credential path entirely (method per [Exxact's own "Resetting the BMC Using ipmitool on Linux" guide](https://support.exxactcorp.com/hc/en-us/articles/31728599437847-Resetting-the-BMC-Using-ipmitool-on-Linux)). The technician confirmed the new password actually worked and enabled Serial-over-LAN before rebooting out of GParted — not assumed, tested, before moving on.

Once rebooted, the technician independently confirmed BMC connectivity a second way — using [`fyrtaarn`](https://github.com/knightmare2600/fyrtaarn) and a separate `ipmitool` check from a different machine entirely (a MacBook) — before trusting the new credentials for anything further. Only then did the technician log into the BMC properly and use virtual media to install Proxmox VE, as any normal build would.

Licensing and asset records were updated to reflect the chassis actually received, rather than the one originally described on paperwork — the hardware itself needed no remedial work.

### Lessons Learned

- Asset tags and delivery paperwork describing BMC credentials cannot be assumed to match the physical hardware actually received — a vendor fulfilment error can substitute a different, even identically-specced, unit without it being obvious until credentials are tried.
- Recovery from unusable/mismatched BMC credentials does not require vendor involvement or a warranty RMA cycle — local console access plus a standard, documented `ipmitool` procedure was enough, provided someone can physically reach the box.
- Physical proximity matters specifically for this failure mode: the same problem at a harder-to-reach site turns a same-visit fix into a real delay.

### Improvements Made

- Documentation was updated to reflect the credential-reset procedure actually used, so the next occurrence of this specific problem is a known, rehearsed step rather than a live investigation.
- The senior technician was informed, and the vendor was formally emailed to raise a compliance record over the chassis mismatch — the appropriate escalation channel for a vendor-side fulfilment error, separate from the technical recovery itself.
- **Cross-check, every time.** The reset password was tested and SOL was confirmed working before the technician moved on — not assumed correct. Then it was verified again, independently, a second way (`fyrtaarn` plus a separate `ipmitool` check from an entirely different machine) before being trusted for the actual build. The same standing rule as every other entry in this log: a second, independent pass before relying on something operationally, because the cost of skipping it is paid later, at the worst possible time.

### Executive Summary

A vendor fulfilment error — the wrong physical chassis delivered under otherwise-correct paperwork — meant a new FAL server's documented BMC credentials didn't work on arrival. Nothing was actually broken: the hardware was fit for purpose, and the credentials were recoverable on site, the same visit, using a standard local procedure rather than a vendor RMA cycle. Every step of the recovery was verified before being trusted for the next one. A compliance record was raised with the vendor as the appropriate formal follow-up. This is how these incidents work: something exposes a gap nobody had reason to look for yet, it gets handled, and the fix becomes a permanent part of how the estate protects itself going forward.

---

## INC-2026-07-12-SSH-KEY — Lost SSH keypair delayed PVE node deployment in Scandinavia

### Incident Background

**Date:** 12 July 2026  
**Scope:** Deployment of a new Proxmox VE node in Gothenburg, Sweden (Scandinavia region)  
**Cause (summary):** An omission in the estate's SSH keypair process left the private half of a required key unavailable when a live deployment needed it, delaying that node's onboarding.

During a live deployment of a new Proxmox VE node in Gothenburg, the automation responsible for giving the node its real identity (hostname, static networking) failed to connect. Nothing about the failure pointed at why — the node was reachable on the network — but the connection itself would not complete.

### Root Cause & Mitigation

Investigation traced the failure to the SSH keypair the estate's automation uses to reach Proxmox nodes: the private half of that key — required on the Ansible control node, per the configured path automation relies on — could not be found there. Only the public half — routinely distributed to new nodes during provisioning — was present. An omission in the process that carries a keypair from wherever it's generated to where it's actually needed had gone unnoticed until this deployment hit it for the first time on real hardware.

To keep the affected build moving, the engineer generated a fresh keypair directly on the control node and manually added the new public key to the Gothenburg node — using a combination of direct SSH (where already reachable) and out-of-band BMC/console access (where it wasn't) — restoring managed access without needing to rebuild the node. Username/password authentication remained available throughout as an existing, already-accepted fallback for Proxmox nodes specifically: if key-based access is ever unavailable, password auth is the documented alternative for these nodes, not a new decision made in response to this incident.

### Lessons Learned

- There was a check that a *public* key existed somewhere in the repository, but nothing that confirmed the *private* half was actually present and working before automation depended on it.
- The failure gave no indication it was a key/authentication problem — it looked identical to a generic network issue, and the real cause only became clear after testing the connection by hand.
- There was no written recovery procedure for this exact situation. It was worked out live, under time pressure, rather than being a known, rehearsed step.

### Improvements Made

- The verification harness run before any change is trusted now includes a dedicated SSH keypair check — it confirms the public key is consistent everywhere it's committed, and, on the real control node, that the private half is genuinely present.
- The node-onboarding automation now performs a real connection test using the actual configured key before doing anything else, and stops outright with a clear explanation if that test fails, instead of proceeding and failing confusingly later.
- The recovery steps used here — generate fresh, redistribute the public half, verify — are now written down as a documented procedure.
- **Cross-check, every time.** The fix for this exact problem was tested end-to-end against a real connection before being trusted — not just read over and assumed correct. That's the standing rule for anything touching access to live infrastructure: a second, independent pass — another engineer, or a genuine live test — before it's relied on operationally. The same reason airline cabin crews call out "cross-check" to one another before a door is armed applies here: the cost of skipping it is paid later, at the worst possible time.

### Executive Summary

A gap in how SSH keypairs move from creation to actual use let a key go missing without anyone knowing, until a live deployment in Scandinavia needed it and lost time as a result. Nothing was lost that couldn't be regenerated, and the affected node was recovered the same day using existing, documented fallback access. The automation and its safety checks have both been updated so this specific failure mode is now caught immediately, with a clear explanation, instead of surfacing as an unexplained delay. This is how these incidents work: something exposes a gap nobody had reason to look for yet, it gets fixed, and the fix becomes a permanent part of how the estate protects itself going forward.
