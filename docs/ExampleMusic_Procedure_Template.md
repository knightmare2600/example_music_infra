# Example Music Limited — [Procedure Title]

> **Classification:** Internal — Infrastructure  
> **Forest:** `jukebox.internal`  
> **Domains:** `example.net` · `example.org` · `example.com`  
> **Provisioning network:** `192.168.139.0/24`  
> **Credentials:** See password manager — do **not** store passwords in this document  

---

## Reference / Helpers

### Standard Site Subnets & Gateways

| Site | Subnet | `.1` Gateway | `.10` DC | `.253` FW |
|------|--------|-------------|----------|-----------|
| FAL | `192.168.76.0/24` | `192.168.76.1` | `192.168.76.10` | `192.168.76.253` |
| CPH | `192.168.231.0/24` | `192.168.231.1` | `192.168.231.10` | `192.168.231.253` |
| ODE | `192.168.126.0/24` | `192.168.126.1` | `192.168.126.10` | `192.168.126.253` |
| BRK | `192.168.136.0/24` | `192.168.136.1` | `192.168.136.10` | `192.168.136.253` |
| MCR | `192.168.161.0/24` | `192.168.161.1` | `192.168.161.10` | `192.168.161.253` |
| LIV | `192.168.151.0/24` | `192.168.151.1` | `192.168.151.10` | `192.168.151.253` |
| GLA | `192.168.141.0/24` | `192.168.141.1` | `192.168.141.10` | `192.168.141.253` |
| NEW | `192.168.191.0/24` | `192.168.191.1` | `192.168.191.10` | `192.168.191.253` |
| KGE | `192.168.65.0/24` | `192.168.65.1` | `192.168.65.10` | `192.168.65.253` |
| FAX | `192.168.246.0/24` | `192.168.246.1` | `192.168.246.10` | `192.168.246.253` |
| TOR | `192.168.146.0/24` | `192.168.146.1` | `192.168.146.10` | `192.168.146.253` |
| MTL | `192.168.154.0/24` | `192.168.154.1` | `192.168.154.10` | `192.168.154.253` |
| SYD | `192.168.29.0/24` | `192.168.29.1` | `192.168.29.10` | `192.168.29.253` |
| CLD | `192.168.139.0/24` | `192.168.139.1` | `192.168.139.10` | `192.168.139.253` |
| ATL | `192.168.33.0/24` | `192.168.33.1` | `192.168.33.10` | `192.168.33.253` |

> **Note:** All other sites can be found in the master CSV (`sites_extended.csv`).  

---

### Hostname / IP Suffix Conventions

| IP Suffix | Role | Hostname Template |
|-----------|------|-----------------|
| `.1`      | Primary Internet Gateway | `EXAFWL<SITE>001` / `EXARTR<SITE>001` |
| `.2`      | BMC pool slot 1 — DRAC/iLO | `EXARAC<SITE>001` |
| `.3`      | BMC pool slot 2 / RAC emulator (single-PVE) | `EXARAC<SITE>002` |
| `.4`      | BMC pool slot 3 / RAC emulator (two-PVE) | `EXARAC<SITE>003` |
| `.5`      | PVE node 1 | `EXAPVE<SITE>001` |
| `.6`      | PVE node 2 | `EXAPVE<SITE>002` |
| `.7`      | PVE node 3 | `EXAPVE<SITE>003` |
| `.10`     | Domain Controller — primary | `EXADCS<SITE>001` |
| `.11`     | Domain Controller — secondary | `EXADCS<SITE>002` |
| `.48`     | VOIP SBC / PBX (`CLD`) | `EXASBC<SITE>001` / `EXAPBX<CLD>001` |
| `.253`    | Secondary internet gateway / DNS | `EXAFWL<SITE>001` |

---

<details>
<summary>💻 Code Helpers (click to expand)</summary>

#### **Python**

```python
from site_ip import SiteIP, SiteHostnames
hosts = SiteHostnames("sites_extended.csv")
print(hosts.get_ip("ATL", "DC"))       # 192.168.33.10
print(hosts.get_hostname("CLD", ".48")) # EXAPBXCLD001
```

#### **Bash**

```
./site_ip.sh ATL DC      # returns 192.168.33.10
./site_ip.sh CLD .48     # returns EXAPBXCLD001
```

#### **PowerShell**

```
Get-SiteIP -Site ATL -Type DC       # 192.168.33.10
Get-SiteHostname -Site CLD -IPSuffix .48  # EXAPBXCLD001
```

------

### CSV Reference

**File:** `sites_extended.csv`

**Key columns:**

| Column             | Description                          |
| ------------------ | ------------------------------------ |
| `Site`             | Short site code                      |
| `Subnet`           | `/24` subnet                         |
| `Gateway`          | `.1` IP                              |
| `DC`               | `.10` IP                             |
| `FW`               | `.253` IP                            |
| `GatewayTemplate`  | `.1` host template                   |
| `BMC1Template`     | `.2` host template                   |
| `BMC2Template`     | `.3` host template                   |
| `BMC3Template`     | `.4` host template                   |
| `PVE1Template`     | `.5` host template                   |
| `PVE2Template`     | `.6` host template                   |
| `PVE3Template`     | `.7` host template                   |
| `DC1Template`      | `.10` host template                  |
| `DC2Template`      | `.11` host template                  |
| `SBC_PBX_Template` | `.48` host template (SBC or CLD PBX) |

> **Tip:** Update `sites_extended.csv` to add new sites, subnets, or host templates. All helper scripts reference this CSV dynamically.

------

## Changelog

| Date       | Change           |
| ---------- | ---------------- |
| YYYY-MM-DD | Initial document |

------

## Standard IP Convention

Every site follows this addressing scheme within its `/24` subnet.
 Exceptions are noted in individual site entries.

| Address       | Role                                                         | Hostname pattern                      |
| ------------- | ------------------------------------------------------------ | ------------------------------------- |
| `.1`          | Primary internet gateway                                     | `EXAFWL<SITE>001` / `EXARTR<SITE>001` |
| `.2`          | BMC pool slot 1 — DRAC / iLO                                 | `EXARAC<SITE>001`                     |
| `.3`          | BMC pool slot 2 — or RAC emulator VM on single-PVE-node sites | `EXARAC<SITE>002`                     |
| `.4`          | BMC pool slot 3 — or RAC emulator VM on two-PVE-node sites   | `EXARAC<SITE>003`                     |
| `.5`          | PVE node 1                                                   | `EXAPVE<SITE>001`                     |
| `.6`          | PVE node 2                                                   | `EXAPVE<SITE>002`                     |
| `.7`          | PVE node 3                                                   | `EXAPVE<SITE>003`                     |
| `.10`         | Domain Controller — primary                                  | `EXADCS<SITE>001`                     |
| `.11`         | Domain Controller — secondary                                | `EXADCS<SITE>002`                     |
| `.48`         | VOIP SBC — trunks to `EXACLDPBX001`                          | `EXASBC<SITE>001`                     |
| `.100`–`.249` | DHCP pool                                                    | —                                     |
| `.250`–`.252` | RT switches                                                  | `EXASWI<SITE>001`–`003`               |
| `.253`        | Secondary internet gateway                                   | —                                     |

> **BMC pool:** `.2`/`.3`/`.4` are shared between physical DRAC/iLO interfaces and the RAC emulator VM. Physical PVE node BMCs consume from `.2` upward; the RAC VM (`EXARAC<SITE>00N`) takes the next free slot.
>  ***NB: On three-PVE-node sites the pool is fully consumed by physical BMCs.***

------

## Naming Convention Reference

| Prefix              | Role                                          | Example        |
| ------------------- | --------------------------------------------- | -------------- |
| `EXAFWL`            | Firewall                                      | `EXAFWLFAL001` |
| `EXARTR`            | Router                                        | `EXARTRFAL001` |
| `EXASWI`            | Switch                                        | `EXASWIFAL001` |
| `EXADCS` / `EXADCR` | Domain Controller (site/regional)             | `EXADCSFAL001` |
| `EXAPVE`            | Proxmox VE node                               | `EXAPVEFAL001` |
| `EXASRV`            | Server                                        | `EXASVRCLD001` |
| `EXARAC`            | Remote Access Console (DRAC/iLO/RAC emulator) | `EXARACFAL001` |
| `EXANAS`            | NAS                                           | `EXANASFAL001` |
| `EXASBC`            | VOIP SBC — trunks to `EXACLDPBX001`           | `EXASBCFAL001` |
| `EXAPBX`            | PBX                                           | `EXACLDPBX001` |
| `EXAPRV`            | Provisioning / bootstrap server               | `EXAPRVFAL001` |
| `EXAWAP`            | WiFi Access Point                             | `EXAWAPFAL001` |
| `EXAWKS`            | Workstation                                   | `EXAWKSFAL001` |
| `EXALAP`            | Laptop                                        | `EXALAPFAL001` |
| `EXAMBP`            | MacBook Pro                                   | `EXAMBPFAL001` |
| `EXAMAC`            | iMac                                          | `EXAMACFAL001` |
| `EXASUR`            | Surface                                       | `EXASURFAL001` |
| `EXATAB`            | Tablet                                        | `EXATABFAL001` |
| `EXAPHN`            | Phone                                         | `EXAPHNFAL001` |
| `EXACAM`            | Camera                                        | `EXACAMFAL001` |
| `EXAVND` / `EXADON` | Vending machine                               | `EXAVNDFAL001` |
| `EXAMUS`            | Jukebox / instrument                          | `EXAMUSFAL001` |
| `EXAPAY`            | Payphone                                      | `EXAPAYFAL001` |
| `EXANIX`            | Unix / legacy system                          | `EXANIXPER001` |

------

*Example Music Limited — Internal Infrastructure Documentation*
 *Do not distribute outside the organisation*
 *Credentials: See password manager — never store passwords in this document*
