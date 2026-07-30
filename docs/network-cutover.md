# Example Music Limited — Network Cutover Reference

> **Classification:** Internal — Infrastructure  
> **Doc ID:** NET-DIAG-002  
> **Generated:** 2026-07-13 — derived by comparing every site's Old Network and New Network boxes in [network-diagram.md](network-diagram.md) against each other  
> **Purpose:** Every place where the legacy diagrams and the current `benarbejde/sites.csv`/`devices.csv` source of truth genuinely disagree about what lives at a given IP octet or hostname. This is what techs on site MUST know before touching cabling or config during a cutover, so a network doesn't go down because someone trusted the wrong document.

---

## How this list was built

`network-diagram.md`'s Old Network box (hand-maintained, historical) and New Network box (generated fresh from `sites.csv`/`devices.csv`/`address_policy.json`) were compared per site, per IP octet. Every octet where **both** boxes have an entry but disagree on which hostname belongs there is listed below. This is a mechanical, repeatable comparison — see `at_have_ryggen_fri/README.md`'s Backlog section for the harness check that will keep this current automatically (Phase 4, not yet wired as of this writing).

**Not everything that differs between Old and New is a cutover conflict.** The New Network box is deliberately more complete than the Old one (that's the whole point of this diagram work) — a device only in New because Old never documented it is not a conflict, it's just Old being sparse. Only genuine same-octet-different-identity disagreements are listed here.

---

## 1. RTR/FWL octet swap — the big one

**18 of 47 sites' Old Network diagrams have the router and firewall's octets backwards** relative to the current, correct convention in `benarbejde/address_policy.csv` (`RTR` = `.1`, `FWL` = `.253`/`.254`). The old diagrams show the router at `.254` and the firewall at `.1` — the opposite way round.

**Affected sites:** ABD, AKL, BER, BIR, BON, BRK, CLY, COV, CPH, DUN, EDI, FAL, FAX, LAX, LND, MEL, ODE, SYD

**What to do on site:** Before touching anything, confirm which physical box is actually the router and which is the firewall — don't trust the old diagram's `.1`/`.254` labelling at any of the 18 sites above. Cross-check against `network-inventory.md`/`sites.csv`'s `Gateway`/`FW` columns (the router's IP is the site's Gateway; the firewall is the WAN-facing box at `.253`/`.254`) before recabling or reconfiguring anything. This exact confusion was already caught and fixed in the shared legend tables (`network-inventory.md`, `site-inventory.md`, `docs/inventory/network-inventory-merged.md` — see `at_have_ryggen_fri/facts.yml`'s `fwl_octet_role`/`rtr_octet_role`) — this is the same bug surfacing in the per-site diagrams, which the legend fix never touched.

**Sites confirmed clean** (Old and New already agree on RTR/FWL octets): AAR, AMS, ATL, BRT, CHI, CLD, DRS, DUS, FRE, GOT, HAL, HUL, KGE, KOR, MIA, MIL, MTL, MUN, NJC, NYC, OSL, PER, SHE, TOR, VIE.

---

## 2. Site-specific collisions

### EDI — Edinburgh, `.12`

- **Old Network:** `EXARRYEDI001` — Rudder Relay
- **New Network:** `EXADCSEDI002` — secondary Domain Controller (a `devices.csv` exception row explicitly assigns `.12` here: *"DC secondary needs rebuild corrected to .12"*)

**What to do on site:** Don't assume `.12` is still the Rudder Relay. Confirm what's physically there before cabling — if it's genuinely the DC rebuild, the Rudder Relay needs a new home; if it's still the Rudder Relay, `devices.csv` needs correcting, not the diagram.

### LAX — Los Angeles, `.73`

- **Old Network:** `EXATTYLAX001` — labelled "Atari ST · MIDI" (hostnamed as if it were a VT320 serial terminal — `TTY` prefix)
- **New Network:** `EXAASTLAX001` — the same device, correctly hostnamed under the `AST` (Atari ST) type per `devices.csv`

**What to do on site:** This is the same physical device under two different hostnames — not two devices fighting over one octet. `EXAASTLAX001` is the correct name per the current source of truth; `EXATTYLAX001` is a legacy misnaming (`TTY` is genuinely used elsewhere for real serial terminals — see FAL — so don't assume every `TTY`-prefixed host in old documentation is one). Correct any DNS/monitoring/inventory reference still using the old name.

---

## 3. Explicitly NOT a cutover conflict — DCR → DCS domain controller rename

**6 sites** (BIR, GLA, LIV, LND, MCR, NEW) show a difference between Old (`EXADCR<SITE>001`) and New (`EXADCS<SITE>001`) at the same octet. **This is intentional, not a conflict** — confirmed with Robert 2026-07-13. `EXADCR*` is the documented legacy domain-controller naming, `EXADCS*` is the rebuild target; the mapping is already tracked in `buildsheets/buildsheet-domainControllers.md` Appendix A. The Old Network box deliberately keeps the legacy `DCR` name so the two boxes stay visually distinguishable — no action needed at cutover beyond following the existing DC rebuild procedure.

---

## Keeping this current

This doc is a snapshot from the 2026-07-13 comparison. If `sites.csv`/`devices.csv` changes, or `network-diagram.md`'s Old Network boxes are edited, re-run the comparison rather than trusting this list is still accurate — see `at_have_ryggen_fri/README.md`'s Backlog section.
