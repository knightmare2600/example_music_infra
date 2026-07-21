# =============================================================================
# salt/states/top.sls
# Example Music Limited — Salt state top file
# =============================================================================
# '*' is fine for now -- every Salt minion in this estate is Windows-only by
# scope (see ansible/playbooks/salt/README.md), so there's no non-Windows
# target to accidentally catch yet. Revisit with a proper grain-based match
# (e.g. G@os_family:Windows) if that ever changes.
# =============================================================================

base:
  '*':
    - wintools
    - grains
