# Network Diagram Icon Legend

> **Classification:** Internal — Infrastructure  
> **Applies to:** [`../network-diagram.md`](../network-diagram.md) — every node in every Old
> Network and New Network box  
> **Source of truth:** `benarbejde/role_codes.csv`'s `Code`/`Emoji` columns (also what
> `generate_network_diagrams.py`'s `TYPE_SYMBOLS` loads directly, 2026-07-20 — no more hardcoded
> Python dict to drift from this doc) — this file is the human-readable legend; keep both in
> sync if either changes. `at_have_ryggen_fri` check 20 (`check_role_codes.py`) verifies they
> agree, every run.

**These are "feel," not "official."** Robert's framing, 2026-07-13: nobody is trying to draw
precise device iconography here, just something evocative enough to scan a 50-node diagram
quickly. If a symbol doesn't feel right, that's a legitimate reason to change it — there's no
"correct" answer being approximated.

**Real Unicode characters only.** No FontAwesome/iconify syntax, no actual vendor logos — see
`../network-diagram.md`'s Visual Standard section for why (tested live, both fail to render
reliably through the kroki.io pipeline this repo relies on, and vendor logos are trademarked
regardless). A few of the things asked for don't exist as Unicode characters at all — noted below,
not silently swapped without explanation.

**Suggesting a replacement?** Browse the full official list at
**[unicode.org/emoji/charts/full-emoji-list.html](https://unicode.org/emoji/charts/full-emoji-list.html)**
— every emoji, its code point, and how it renders across major platforms, one page. Pick a
character, hand over the type code and the new symbol; each one gets a quick kroki.io round-trip
before it's committed (see `at_have_ryggen_fri/check_mermaid.py`), same as every other
diagram change in this repo.

## Curveball / novelty devices

| Type | Symbol | Device | Notes |
|---|---|---|---|
| PAY | ☎️ | Payphone | No AT&T logo or British red-phonebox glyph exists in Unicode — telephone receiver instead |
| MUS | 💿 | Jukebox | No jukebox glyph exists in Unicode either — confirmed via web search, not assumed — optical disc instead |
| VND | 🍫 | Vending machine | |
| DON | 🍩 | Doughnut vending | |
| COF | 🍵 | Coffee machine | Teacup-without-handle — reads more like a coffee mug than ☕ did, per Robert. Was ☕, changed 2026-07-13 |
| TEA | 🫖 | Tea/coffee machine | |
| BUS | 🚌 | Tour bus | |
| CAR | 🚗 | Car | |
| TRK | 🚚 | Truck | |
| JET | ✈️ | Jet | The generic airport-signage aeroplane, as asked |
| PMP | ⛽ | Petrol pump | |
| CLK | ⏰ | Embedded NTP clock | Deliberately not 🕰️ — that's the Old Network box's own symbol |
| MIC | 🎤 | Microphone | |
| RAD | 📻 | Radio | |
| MOO | 🎹 | Moog synth | Same symbol as FCL — both "a keyboard," per Robert |
| FCL | 🎹 | Fairlight CMI | Same symbol as MOO |
| SYN | 🎹 | Synthesizer (e.g. Moog, Korg, Yamaha) | Added 2026-07-26 — generic synth code, distinct from MOO (Moog specifically) and FCL (Fairlight CMI specifically). Same symbol as both — all three "a keyboard" |
| AST | 🕹️ | Atari ST | No Atari logo in Unicode — joystick as a non-trademarked stand-in for the same retro-computing era |
| LIN | 🥁 | Drum machine | |
| MID | 🎚️ | MIDI sequencer / workstation | Added 2026-07-26 — distinct from NIX ("MIDI archive (*nix-adjacent)"), an archival Unix-like device, not a sequencer |
| OBS | 🎬 | Outside broadcast station | Added 2026-07-26 |
| TTY | ⌨️ | VT320 serial terminal | |

## Network infrastructure

| Type | Symbol | Device | Notes |
|---|---|---|---|
| RTR | 📡 | Router | |
| FWL | 🧱 | Firewall | Brick — a firewall as a wall. Was 🔥 (the "firewall" pun); changed 2026-07-13 per Robert |
| SWI | 🔀 | Switch | |
| BMC | 🔧 | BMC / iDRAC / iLO / Redfish | Standard `.2`-`.4` slots — same symbol as RAC (its legacy devices.csv-row equivalent) |
| ILO | 🔧 | Integrated Lights-Out (HP iLO) | Added 2026-07-26 — kept as its own code, distinct from BMC's generic iDRAC/iLO/Redfish consolidation above. Same symbol as BMC/RAC |

## Servers / compute / management

| Type | Symbol | Device | Notes |
|---|---|---|---|
| DCS | 🗝️ | Domain controller (current naming) | |
| DCR | 🗝️ | Domain controller (legacy naming) | Same symbol as DCS — same role |
| SVR | 🗄️ | Generic server | |
| SRV | 🗄️ | Generic server | Same symbol as SVR |
| PVE | 🗂️ | Proxmox hypervisor node | Layered/stacked feel, deliberately distinct from a generic server |
| ESX | 💾 | VMware ESXi hypervisor (legacy) | Added 2026-07-31 for old-network diagram restyling — found live at FAL (single HP ML310e host), not `PVE` as the original hand-written box wrongly assumed. No VMware logo usable (trademarked, same rule as Cisco/AT&T/Atari elsewhere in this legend) — generic floppy disk, Robert's call, deliberately distinct from `PVE`'s 🗂️ |
| RUD | ⚙️ | Rudder (config mgmt) | Standard `.12` slot, CLD only. Was `RDR` until 2026-07-20 — split apart because `devices.csv` reused the same three letters for badge readers too (see RDR under Endpoints below) |
| RRY | 🔁 | Rudder Relay | |
| SLT | 🧂 | Salt master (config mgmt — all Windows nodes) | CLD only (`EXASLTCLD001`, `.22`). Manages `WKS`/`LAP`/`SUR`/`SVR`/`DCS` — `TAB` only if genuinely Windows, `MAC`/`MBP` future plans. `FWL`/`PVE` stay Ansible-only, no Syndic tier at current scale |
| ANS | 🤖 | Ansible control node | |
| PBX | 🔌 | Phone exchange (3CX PBX) | |
| DNS | 🧭 | DNS server | |
| TMP | 📦 | Temporary/bootstrap-only provisioning server | VRK/FRD only — IP-referenced, no formal `EXA<ROLE><SITE><NNN>` hostname or DNS record |
| NAS | 🗃️ | Network storage | |
| SBC | 🛡️ | Session Border Controller | "Border controller" — a boundary/edge device |
| UFC | 🎛️ | UniFi Network Controller (WiFi mgmt) | |
| RAC | 🔧 | BMC / iDRAC / iLO | |
| TAR | 💽 | Tape archive | |

## Wireless

| Type | Symbol | Device |
|---|---|---|
| WAP | 📶 | Wireless access point |

## Endpoints

| Type | Symbol | Device | Notes |
|---|---|---|---|
| WKS | 🖥️ | Workstation | |
| RDR | 🔐 | Reader — badge reader | Standard `.21` slot (added 2026-07-20). Was conflated with Rudder under the same `RDR` code — see RUD under Servers/compute/management above |
| LAP | 💻 | Laptop | |
| MBP | 💻 | MacBook Pro | Same symbol as LAP |
| TAB | 📱 | Tablet | |
| SUR | 🖊️ | Microsoft Surface | Stylus — Surface devices are known for pen input |
| PHN | 📞 | Office/desk phone | Distinct from PAY's ☎️ (payphone) and PBX's 🔌 (exchange) |
| PRN | 🖨️ | Printer | |
| CAM | 🎥 | CCTV camera | |
| LCD | 🖼️ | Digital signage / display | |
| TVS | 📺 | TV display | |
| MAC | 🍎 | Apple/iMac | Generic red-apple emoji, not Apple Inc.'s trademarked logo |
| BPS | 🪪 | Badge programming station | |
| NIX | 🐧 | MIDI archive (\*nix-adjacent) | |
| VCU | 🎧 | Video conferencing unit | |
| IOT | 📟 | IoT / miscellaneous embedded device | Added 2026-07-26 — catch-all for embedded devices that don't fit an existing code |

## Not yet decided

| Type | Symbol | Device | Status |
|---|---|---|---|
| — | ❓ | *(none currently)* | Placeholder used only when a genuinely new device type appears with no agreed symbol yet — see `at_have_ryggen_fri/README.md`'s Backlog section if one shows up |
