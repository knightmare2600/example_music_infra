# Vendor MIBs for SNMP device monitoring

Deployed by `zabbix_server.yml`'s `snmp_devices` play to the Zabbix server's own
net-snmp MIB search path, so symbolic (not just numeric) OIDs resolve for the
`devices.csv` `ConnectionType=snmp` fleet (switches, printers, BMCs).

## Provenance

Extracted 2026-11-17 from source material Robert dropped in at the repo root
(`/mibs/`, gitignored, never committed — a full LibreNMS checkout, the
nagios.manubulon.com Cisco bundle, and a generic MIB tarball). Only the files
below were copied out; nothing else from those bundles is used or kept.

| Vendor | Files | Covers |
|---|---|---|
| `cisco/` | `CISCO-SMI`, `CISCO-TC`, `CISCO-PROCESS-MIB`, `CISCO-MEMORY-POOL-MIB`, `CISCO-ENVMON-MIB`, `CISCO-ENTITY-FRU-CONTROL-MIB`, `CISCO-ENTITY-SENSOR-MIB`, `CISCO-STACK-MIB` | Catalyst 9300/9200/2960X/2960 switches — CPU, memory, temp/fan/PSU, FRU sensors. `CISCO-SMI`/`CISCO-TC` are load-order dependencies for the rest. Interface stats use the standard `IF-MIB`, not Cisco-specific. |
| `tplink/` | `TPLINK-MIB`, `TPLINK-TC-MIB`, `TPLINK-PRODUCTS-MIB`, `TPLINK-SYSINFO-MIB`, `TPLINK-SYSMONITOR-MIB` | JetStream switches — system info + health monitoring. TP-Link's own LLDP/VLAN/static-route/PoE/DDM-optics MIBs exist in the source bundle but weren't copied — not needed for basic health monitoring, add later if a template needs them. |
| `dell/` | `IDRAC-MIB-SMIv2` | Dell iDRAC9 BMCs (FAL/CLY/SYD/MEL/AKL `RAC` rows). |
| `hp/` | `CPQSINFO-MIB`, `CPQHLTH-MIB`, `CPQHOST-MIB`, `CPQSTDEQ-MIB`, `CPQIDA-MIB` | HPE iLO5 BMCs (FAL/CLY `ILO` rows) — iLO's embedded SNMP agent still uses the legacy Compaq/HP Insight-Management MIB set. |
| `brother/` | `BROTHER-MIB` | Brother printer (SYD). |
| `printer/` | `Printer-MIB`, `IANA-PRINTER-MIB`, `HOST-RESOURCES-MIB`, `HOST-RESOURCES-TYPES` | Standard IETF printer/host MIBs — covers the HP/Xerox/Brother printer fleet's basic toner/tray/status generically. Kept here as our own authoritative copy rather than relying solely on Debian's `snmp-mibs-downloader`, which `zabbix_server.yml` already documents as best-effort (non-free component, "possibly not available on this image"). |

## Known gap

**Xerox has no vendor-specific MIB in any of the three source bundles** —
checked, not assumed (LibreNMS's full vendor tree, the nagios.manubulon.com
Cisco-focused bundle, and the generic 633-entry tarball all came up empty for
"xerox"/"xer"). The Xerox WorkCentre (LND) falls back to the standard
`Printer-MIB`/`HOST-RESOURCES-MIB` coverage above for basic status; anything
genuinely Xerox-proprietary stays numeric-OID-only unless a real Xerox MIB
turns up later.
