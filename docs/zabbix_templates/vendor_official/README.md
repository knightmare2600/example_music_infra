# Official Zabbix 7.0 templates — unmodified vendor originals

These 5 files are **verbatim copies** of Zabbix's own official templates, pulled
2026-11-19 from `github.com/zabbix/zabbix`, branch `release/7.0` (the actual
7.0-bundled template revision — the public `zabbix.com/integrations/*` website
defaults to showing the newest Zabbix version's docs, which can misleadingly
suggest a higher version requirement than what's really needed here; the
versioned source tree is the authoritative copy). Nothing in them has been
edited — not a byte — so a straight `Import` in the Zabbix UI reproduces
exactly what upstream ships.

They're kept separate from this directory's other `zabbix_template_*.json`
files because those are estate-custom templates built for this repo; these
are unmodified third-party originals, kept here purely so Robert can import
them from a local checkout without a second fetch from GitHub.

| File | Official template name | Fits |
|---|---|---|
| `template_net_cisco_snmp.yaml` | **Cisco IOS by SNMP** | Catalyst switches (any model) |
| `template_net_tplink_snmp.yaml` | **TP-LINK by SNMP** | TP-Link JetStream switches |
| `template_server_dell_r740_snmp.yaml` | **DELL PowerEdge R740 by SNMP** | Dell iDRAC9 BMCs |
| `template_server_hp_dl380_snmp.yaml` | **HPE ProLiant DL380 by SNMP** | HPE iLO5 BMCs |
| `template_os_linux_snmp_snmp.yaml` | **Linux by SNMP** | `EXAUFCCLD001` (Debian/UniFi controller) |

## To import

Zabbix web UI on `EXAZABCLD001` → **Data collection → Templates → Import**
→ pick the file → Import. Each is a complete, self-contained
`zabbix_export` document — import them one at a time, in any order; none
of the 5 depend on each other.

Vendor MIB dependencies for each (already deployed to the Zabbix server's
net-snmp MIB path by `zabbix_server.yml`'s `snmp_devices` play) are listed
in `../../../ansible/playbooks/zabbix/files/mibs/README.md`, cross-checked
against each of these templates' own `MIBs used:` footer.

No official Zabbix 7.0 template exists for printers — see that same MIBs
README for the current state of that gap (community template vs. custom
build, Robert's call, still open).

Once imported, `ansible/tasks/zabbix_snmp_device_register.yml`'s
`template.get` lookup will find them by name and link the right one
automatically on the next `snmp_devices`-tagged run — it never calls
`template.create` itself.
