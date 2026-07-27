# playbooks/bootstrap_assets/

Fetches `bootstrap/web/`'s upstream-sourced boot assets (kernels, initrd,
loader binaries) instead of vendoring them into git — populates from
`bootstrap/asset_manifest.yml`, verifying every download by checksum.

See `docs/INDEX.md` for the wider documentation set this fits into.

## Files

| File | What it does |
|------|-------------|
| `fetch-assets.yml` | Reads `../../../bootstrap/asset_manifest.yml`, fetches whatever's missing from its real upstream (GitHub Releases for Robert's own `Spejder`/`klargoring` repos and third-party projects like `ipxe/wimboot`; direct URL + checksum file for official mirrors like Debian/OpenBSD; archive-extract for gparted's zip). Idempotent — only touches files that are actually missing. |

## Quick start

```bash
ansible-playbook ansible/playbooks/bootstrap_assets/fetch-assets.yml
```

Always runs against `hosts: localhost, connection: local` — this only ever
writes into this checkout's own `bootstrap/web/`, never a managed host. Not
run by the harness (`at_have_ryggen_fri/run.sh`) or by
`check_bootstrap_assets.py` — both stay read-only/offline by design; this
playbook is always a separate, explicit, human-triggered action. The check
tells you what's missing and whether the manifest covers it; this playbook
is what you run once you've decided to actually fetch it.

## Related documents

| Document | Where |
|----------|-------|
| `bootstrap/asset_manifest.yml` | The manifest this playbook consumes — one entry per fetchable asset, `source_type` selects the fetch strategy |
| `at_have_ryggen_fri/check_bootstrap_assets.py` | The offline harness check (25) that reports what's missing and whether this playbook can fetch it |
