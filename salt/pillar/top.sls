# =============================================================================
# salt/pillar/top.sls
# Example Music Limited — Salt pillar top file
# =============================================================================
# IMPORTANT — this repo is public (github.com/knightmare2600/example_music_infra):
# nothing genuinely sensitive goes in this directory in plaintext, ever. If a
# real secret is ever needed here, GPG-encrypt it with Salt's own gpg renderer
# (#!yaml|gpg at the top of the file, individual values as PGP message blocks)
# — same posture as ansible/configs/inventory/group_vars/rudder_servers/
# vault.yml being ansible-vault-encrypted, not left in the clear, because it's
# committed to this same repo. Real credentials still belong in KeePass, not
# here, encrypted or not, unless a specific case makes that impractical.
#
# sites.sls is generated -- benarbejde/generate_inventory.py --emit-site-grains-pillar.
# Do not hand-edit; regenerate from sites.csv instead.
# =============================================================================

base:
  '*':
    - sites
