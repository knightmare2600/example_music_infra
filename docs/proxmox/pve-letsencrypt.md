# Proxmox VE — Let's Encrypt Wildcard Certificate

## Changelog

| Date | Change |
|---|---|
| 2026-03-01 | Initial document — DNS-01 wildcard certificates, supported providers, web UI/CLI setup, renewal, multi-node, CNAME delegation |

## Automatic ACME via DNS-01 Challenge

> **Applies to:** Proxmox VE 8.x
> **Audience:** Infrastructure technicians
> **References:**
> - [Proxmox VE Certificate Management](https://pve.proxmox.com/wiki/Certificate_Management)
> - [Proxmox Admin Guide — ACME](https://pve.proxmox.com/pve-docs/pve-admin-guide.html#sysadmin_certificate_management)
> - [Let's Encrypt DNS Challenge](https://letsencrypt.org/docs/challenge-types/#dns-01-challenge)

---

## Why DNS-01 and Not HTTP-01

Let's Encrypt offers two main challenge types. For a wildcard certificate (`*.yourdomain.com`) **DNS-01 is mandatory** — HTTP-01 cannot validate wildcards because there is no single host to serve a challenge file from.

DNS-01 works by having the ACME client place a temporary TXT record at `_acme-challenge.yourdomain.com`. Let's Encrypt queries that record publicly to confirm you control the domain, then issues the certificate. The Proxmox node itself never needs to be publicly reachable — only the DNS TXT record does.

This also means your Proxmox nodes can be entirely internal/private as long as your DNS zone has a public presence for validation purposes.

---

## Prerequisites

Before starting, confirm:

- You have a real public domain (e.g. `yourdomain.com`) — Let's Encrypt cannot validate a purely private zone with no public DNS presence
- Your DNS provider has an API and is supported by a Proxmox ACME plugin (see list below)
- You have API credentials for your DNS provider ready
- The Proxmox node has outbound internet access (to reach Let's Encrypt and your DNS provider's API) — even if the node itself is not publicly reachable inbound

### Supported DNS Providers (selection)

Proxmox ships with plugins for a large number of providers. A non-exhaustive list:

| Provider | Plugin Name |
|---|---|
| Cloudflare | `cloudflare` |
| Amazon Route 53 | `route53` |
| Azure DNS | `azure` |
| Gandi | `gandi` |
| OVH | `ovh` |
| Hetzner DNS | `hetzner` |
| DigitalOcean | `dgon` |
| Namecheap | `namecheap` |
| GoDaddy | `godaddy` |
| Linode/Akamai | `linode` |
| Porkbun | `porkbun` |

Full list: `Datacenter → ACME → DNS Plugins → Add` — the dropdown contains every supported provider.

---

## Setup — Web UI

### Step 1 — Register an ACME Account

Go to **Datacenter → ACME → Accounts → Add**

| Field | Value |
|---|---|
| **Account Name** | `letsencrypt` (or any name you like) |
| **Email** | your admin email — Let's Encrypt will send expiry warnings here |
| **ACME Directory** | `Let's Encrypt V2` for production, or `Let's Encrypt V2 Staging` to test first |
| **ToS** | Accept |

> **Do a staging run first.** Let's Encrypt production has rate limits (5 failed validations per domain per hour, 50 certs per domain per week). Staging has much higher limits and will catch config errors without burning your quota. Staging certs are not trusted by browsers but are structurally identical for testing purposes.

Click **Register**.

---

### Step 2 — Add a DNS Plugin

Go to **Datacenter → ACME → DNS Plugins → Add**

| Field | Value |
|---|---|
| **Plugin ID** | A name for this config, e.g. `cloudflare-yourdomain` |
| **DNS API** | Select your provider from the dropdown |
| **API Data** | Provider-specific credentials — see below |

**Cloudflare example:**
```
CF_Token=your-cloudflare-api-token
```
Use a scoped API token (Zone → DNS → Edit for the specific zone) rather than your global API key.

**Route53 example:**
```
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

**Hetzner example:**
```
HETZNER_Token=your-hetzner-dns-api-token
```

The credentials are stored in `/etc/pve/priv/acme/` which is only readable by root.

Click **Add**.

---

### Step 3 — Configure the Certificate on the Node

Go to **Node → Certificates → ACME → Add**

| Field | Value |
|---|---|
| **Domain** | `*.yourdomain.com` |
| **Challenge Type** | `DNS` |
| **Plugin** | Select the plugin you just created |
| **Alias** | Leave blank unless using CNAME delegation (see Advanced section) |
| **Digest** | Leave blank |

Optionally add a second domain entry for the bare domain if you want it covered too:

| Field | Value |
|---|---|
| **Domain** | `yourdomain.com` |
| **Challenge Type** | `DNS` |
| **Plugin** | Same plugin |

> A single Let's Encrypt cert can cover both `*.yourdomain.com` and `yourdomain.com` — the wildcard alone does not cover the apex.

---

### Step 4 — Order the Certificate

Still under **Node → Certificates**, click **Order Certificates Now**.

Proxmox will:
1. Contact Let's Encrypt and begin the ACME order
2. Use the DNS plugin to create the required `_acme-challenge.yourdomain.com` TXT record via your provider's API
3. Wait for Let's Encrypt to validate the record
4. Retrieve the signed certificate
5. Install it and restart `pveproxy` automatically

The whole process typically takes 30–90 seconds. The TXT record is cleaned up automatically afterwards.

Once complete, the web UI will be serving the new certificate. Hard refresh your browser (`Ctrl+Shift+R`) to pick it up.

---

## Setup — CLI

If you prefer the command line, everything above can be done with `pvenode` and `pvesh`.

```bash
# Register ACME account
pvenode acme account register letsencrypt admin@yourdomain.com --directory https://acme-v02.api.letsencrypt.org/directory

# For staging (test first):
pvenode acme account register letsencrypt-staging admin@yourdomain.com --directory https://acme-staging-v02.api.letsencrypt.org/directory

# Add DNS plugin (Cloudflare example)
pvesh create /cluster/acme/plugins --id cloudflare-yourdomain --type dns --api cloudflare --data "CF_Token=your-token-here"

# Add domains to the node
pvenode config set --acme account=letsencrypt --acmedomain0 "domain=*.yourdomain.com,plugin=cloudflare-yourdomain" --acmedomain1 "domain=yourdomain.com,plugin=cloudflare-yourdomain"

# Order the certificate
pvenode acme cert order

# Renewal (normally automatic -- run manually if needed)
pvenode acme cert renew
```

---

## Renewal

Proxmox handles renewal automatically via a systemd timer. No cron job needed, no certbot, no external scripts.

```bash
# Check the renewal timer
systemctl status pveproxy-acme.timer

# Check when it last ran / next run
systemctl list-timers pveproxy-acme.timer

# Force a manual renewal
pvenode acme cert renew
```

Let's Encrypt certificates are valid for 90 days. Proxmox will attempt renewal at 30 days before expiry by default.

---

## Deploying the Same Cert to Multiple Nodes

Each Proxmox node gets its own certificate — the wildcard covers all of them (`node1.yourdomain.com`, `node2.yourdomain.com` etc) but each node runs its own ACME renewal independently. Repeat Steps 3 and 4 on each node. The DNS plugin config only needs to be set up once at the Datacenter level and is shared across all nodes in the cluster.

---

## Advanced — CNAME Delegation

If your primary DNS zone is managed by a provider with a poor or no API, you can delegate just the ACME challenge subdomain to a different provider that does have a good API.

Create a CNAME in your primary DNS:
```
_acme-challenge.yourdomain.com  CNAME  _acme-challenge.yourdomain.net-acme-dns.io
```

Then configure the plugin to use the delegated zone. This lets you use a static/manual DNS provider for your main zone while still automating certificate renewal.

---

## Where the Cert Lives

Once issued, the certificate files are at:

```
/etc/pve/nodes/<nodename>/pveproxy-ssl.pem   # Certificate + chain
/etc/pve/nodes/<nodename>/pveproxy-ssl.key   # Private key
```

These are managed by Proxmox — do not replace them manually or they will be overwritten on the next renewal.

The ACME account and plugin configuration lives at:
```
/etc/pve/priv/acme/          # ACME account credentials
/etc/pve/priv/acme-plugins/  # DNS plugin API credentials (root-only)
```

---

## Troubleshooting

**"Timeout during connect"**
The node cannot reach Let's Encrypt (`acme-v02.api.letsencrypt.org`) or your DNS provider's API. Check outbound internet access from the node — even internal nodes need outbound HTTPS for this to work.

**"DNS record not found" / validation fails**
The DNS plugin created the TXT record but Let's Encrypt couldn't see it yet — DNS propagation lag. Some providers are faster than others. If this happens consistently, check whether your DNS provider has a propagation delay setting in the plugin config (`DNSSLEEP` in some plugins).

**"Too many certificates already issued"**
You've hit Let's Encrypt's rate limit for the domain. Use staging to test, switch to production only when you're confident the config is correct.

**"pveproxy-ssl.pem: permission denied"**
The cert files are owned by root and the `www-data` group. If you've manually touched them check permissions:
```bash
chmod 640 /etc/pve/nodes/$(hostname)/pveproxy-ssl.pem
chmod 640 /etc/pve/nodes/$(hostname)/pveproxy-ssl.key
```

---

## Adding to first-boot.sh

The DNS credentials are environment-specific and should be configured consciously rather than baked into the provisioning script. The recommended approach is to add a post-provisioning reminder to `first-boot.sh` output rather than automating the ACME setup:

```bash
info "Post-provisioning: configure Let's Encrypt wildcard cert"
info "  Datacenter → ACME → Accounts → Add (letsencrypt)"
info "  Datacenter → ACME → DNS Plugins → Add (your provider)"
info "  Node → Certificates → ACME → Add (*.yourdomain.com)"
info "  Node → Certificates → Order Certificates Now"
info "  See docs/pve-letsencrypt.md for full procedure"
```

---

*Example Music Limited — Internal Infrastructure Documentation*
*Do not distribute outside the organisation*
