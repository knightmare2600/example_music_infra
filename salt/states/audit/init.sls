## salt/states/audit/init.sls
## Example Music Limited — "on the spot check what is missing" audit
##
## Ported 2026-07-20 from a dropped-in reference Salt state (~739 lines, since
## removed -- see salt/README.md's workflow note). Robert's own description:
## written as a quick on-the-spot check of what's missing/wrong on a node --
## diagnostic only, no config.management.state (every task here is module.run
## against screenprint.screen_print, not a real resource state -- nothing here
## is idempotent or "manages" anything, it only reports).
##
## Only the genuinely reusable checks made it here -- everything specific to a
## handful of bespoke/third-party applications, a remote-access tool, and two
## log-shipping agents was dropped entirely (no equivalent stack in this
## estate).
##
## Real bug fixed while porting: the original disk-space check computed the
## FREE percentage ($_.free/($_.used+$_.free)) but warned "80% or more USED"
## when that FREE figure exceeded 80 -- backwards. This version computes the
## USED percentage directly and warns when USED exceeds 80, matching what the
## message actually says.
##
## Salt minion version check references salt_version_major (3008) directly --
## keep this in sync BY HAND with group_vars/salt_servers/main.yml's own
## salt_version_major if that ever bumps. Ansible (the master's bootstrap) and
## Salt (this minion-side check) are separate systems with no shared var scope,
## so this is one deliberate, documented duplication point, not an oversight.
##
## Deliberately NOT in salt/states/top.sls -- on-demand only, matching its
## original "quick on-the-spot check" purpose. Run it explicitly:
##   salt <target> state.apply audit

print_header_info_message:
  module.run:
    - name: screenprint.screen_print
    - message: 'Performing deployment checks on {{ grains["id"] }}'
    - messagetype: 'banner'

##----------------------------------------{ Windows OS Checks }----------------------------------------
print_windows_os_checks_info_message:
  module.run:
    - name: screenprint.screen_print
    - message: 'Performing Windows OS checks...'
    - messagetype: 'header'

## Check the corporate wallpaper policy key (wintools/init.sls's enforce_wallpaper_policy task).
## Real, correct key this time -- HKLM Policies\System\Wallpaper, not the plain user-changeable
## HKCU key a dropped-in reference check used to check instead.
{% set wallpaper = salt['reg.read_value']('HKLM', 'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System', 'Wallpaper').vdata %}

wallpaper_status:
{% if wallpaper|string == 'C:\\Windows\\Web\\Wallpaper\\ExampleMusic\\corporate.png' %}
  module.run:
    - name: screenprint.screen_print
    - message: 'Corporate wallpaper policy key is set to the expected value.'
    - messagetype: 'success'
{% else %}
  module.run:
    - name: screenprint.screen_print
    - message: 'Corporate wallpaper policy key is NOT set to the expected value. Current value: {{ wallpaper }}. Apply the wintools salt state.'
    - messagetype: 'warning'
{% endif %}

## Check if the page file is set to be cleared at shutdown. Returns 0 or 1. Expected "good" value is 1.
## Same registry key salt/states/wintools/init.sls's clearpagefile task sets -- this is the audit
## companion confirming it actually took, not a duplicate of the same logic.
{% set clearpagefilestatus = salt['reg.read_value']('HKLM', 'SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Memory Management', 'ClearPageFileAtShutdown').vdata %}

clear_page_file_at_shutdown_status:
{% if clearpagefilestatus is not none %}
  {% if clearpagefilestatus|string == '1' %}
    module.run:
      - name: screenprint.screen_print
      - message: 'ClearPageFileAtShutdown registry key is set to the expected value: {{ clearpagefilestatus }}'
      - messagetype: 'success'
  {% else %}
    module.run:
      - name: screenprint.screen_print
      - message: 'ClearPageFileAtShutdown registry key is NOT set to the expected value 1. Current value is: {{ clearpagefilestatus }}. Apply the wintools salt state.'
      - messagetype: 'error'
  {% endif %}
{% else %}
  module.run:
    - name: screenprint.screen_print
    - message: 'ClearPageFileAtShutdown registry key does not exist or cannot be read.'
    - messagetype: 'error'
{% endif %}

## Check hibernation is disabled. Returns 0 or 1. Expected "good" value is 0.
## Same key wintools/init.sls's enablehibernation task sets.
{% set hibernationstatus = salt['reg.read_value']('HKLM', 'SYSTEM\\CurrentControlSet\\Control\\Power', 'HibernateEnabled').vdata %}

hibernation_status:
{% if hibernationstatus is not none %}
  {% if hibernationstatus|string == '0' %}
    module.run:
      - name: screenprint.screen_print
      - message: 'HibernateEnabled registry key is set to expected value: {{ hibernationstatus }}'
      - messagetype: 'success'
  {% else %}
    module.run:
      - name: screenprint.screen_print
      - message: 'HibernateEnabled registry key is NOT set to expected value 0, current value is: {{ hibernationstatus }}. Apply the wintools salt state.'
      - messagetype: 'error'
  {% endif %}
{% else %}
  module.run:
    - name: screenprint.screen_print
    - message: 'HibernateEnabled registry key does not exist or cannot be read.'
    - messagetype: 'error'
{% endif %}

## Check for the binaries wintools actually deploys (see ansible/playbooks/windows_bootstrap/
## group_vars/windows/vars.yml's binaries_flat) -- at C:\Windows\, NOT C:\Windows\System32\ like
## the original checked. That path was specific to wherever the original came from; ours go to
## C:\Windows\ (files/README.md's own documented convention, confirmed, not guessed).
{% for winbin in ['bginfo.exe', 'FileHash.exe', 'dosdev.exe', 'DelProf2.exe'] %}
check_winbin_installed_{{ winbin }}:
{% if not salt['file.file_exists']('C:\\Windows\\' + winbin) %}
  module.run:
    - name: screenprint.screen_print
    - message: 'Binary C:\Windows\{{ winbin }} not installed. Re-run windows_bootstrap''s 50-binaries.yml.'
    - messagetype: 'warning'
{% else %}
  module.run:
    - name: screenprint.screen_print
    - message: 'Binary C:\Windows\{{ winbin }} is installed.'
    - messagetype: 'success'
{% endif %}
{% endfor %}

## Disk space check for C: drive -- computes USED percentage directly (the original computed
## FREE and warned backwards, see this file's own header comment).
{%- set used_pct = salt['cmd.run']('powershell -Command "(Get-PSDrive C | % { $_.used/($_.used + $_.free) } | % tostring p)"') %}
{%- set used_pct = used_pct[:-1] %}

drive_free:
{% if used_pct|float > 80 %}
  module.run:
    - name: screenprint.screen_print
    - message: 'Disk space is 80% or more used: {{ used_pct }}%'
    - messagetype: 'warning'
{% else %}
  module.run:
    - name: screenprint.screen_print
    - message: 'Disk space is less than 80% used: {{ used_pct }}%'
    - messagetype: 'success'
{% endif %}

## Verify disk spin-down is disabled (wintools/init.sls's disable_disk_spindown task).
## UNVERIFIED against a real Windows box -- powercfg /Query's exact output format for a
## disabled (0x00000000) AC setting index hasn't been confirmed live, only against
## documented format. If this check misfires, verify the grep pattern against real
## `powercfg /Query SCHEME_CURRENT SUB_DISK DISKIDLE` output before trusting it further.
{% set diskidle_query = salt['cmd.run']('powercfg /Query SCHEME_CURRENT SUB_DISK DISKIDLE') %}

disk_spindown_status:
{% if 'AC Power Setting Index: 0x00000000' in diskidle_query %}
  module.run:
    - name: screenprint.screen_print
    - message: 'Disk spin-down (AC) is disabled as expected.'
    - messagetype: 'success'
{% else %}
  module.run:
    - name: screenprint.screen_print
    - message: 'Disk spin-down (AC) does NOT appear disabled. Apply the wintools salt state.'
    - messagetype: 'warning'
{% endif %}

##----------------------------------------{ Break-glass Account Checks }----------------------------------------
print_account_checks_info_message:
  module.run:
    - name: screenprint.screen_print
    - message: 'Performing break-glass account checks...'
    - messagetype: 'header'

## Verify the local ansible break-glass account (wintools/init.sls's create_ansible_user task)
## exists and is still a member of Administrators -- if either is false, the "someone changed/
## forgot the ansible password" fallback this account exists for wouldn't actually work.
{% set ansible_user_info = salt['user.info']('ansible') %}

check_ansible_account_exists:
{% if ansible_user_info %}
  module.run:
    - name: screenprint.screen_print
    - message: 'Local ansible account exists.'
    - messagetype: 'success'
{% else %}
  module.run:
    - name: screenprint.screen_print
    - message: 'Local ansible account is MISSING. Apply the wintools salt state.'
    - messagetype: 'error'
{% endif %}

check_ansible_account_is_admin:
{% if ansible_user_info and 'Administrators' in ansible_user_info.get('groups', []) %}
  module.run:
    - name: screenprint.screen_print
    - message: 'Local ansible account is a member of Administrators.'
    - messagetype: 'success'
{% elif ansible_user_info %}
  module.run:
    - name: screenprint.screen_print
    - message: 'Local ansible account exists but is NOT a member of Administrators. Apply the wintools salt state.'
    - messagetype: 'error'
{% endif %}

##----------------------------------------{ Salt Minion Checks }----------------------------------------
print_salt_checks_info_message:
  module.run:
    - name: screenprint.screen_print
    - message: 'Performing Salt Minion checks...'
    - messagetype: 'header'

## Catches a machine renamed without its Salt minion config being re-keyed to match --
## ported 2026-07-20 from audit/salt/init.sls (see salt/cleanup/), fixed two bugs while
## porting: the original's if/else branches had their state IDs swapped (mismatch case
## was labelled minion-name-match and vice versa -- messages were correct, just the IDs
## weren't), and its regex (^id) wasn't anchored to the colon, risking a false match
## against some other id*-prefixed config key.
{% set disk_id_line = salt['cmd.run']('powershell -Command "(Select-String -Path \'C:\\ProgramData\\Salt Project\\Salt\\conf\\minion\' -Pattern ^id:).Line"') %}
{% set disk_id = disk_id_line[3:].strip() %}
{% set running_id = grains['id'] %}

minion_name_status:
{% if disk_id != running_id %}
  module.run:
    - name: screenprint.screen_print
    - message: 'Salt minion id mismatch. On disk: {{ disk_id }} vs running: {{ running_id }}. Re-run 82-salt-minion.yml.'
    - messagetype: 'error'
{% else %}
  module.run:
    - name: screenprint.screen_print
    - message: 'Salt minion name on disk ({{ disk_id }}) matches running id ({{ running_id }}).'
    - messagetype: 'success'
{% endif %}

## Keep "3008" in sync by hand with group_vars/salt_servers/main.yml's salt_version_major --
## see this file's own header comment for why there's no shared var between Ansible and Salt.
{% if not grains['saltversion'].startswith('3008') %}
salt_minion_build_check:
  module.run:
    - name: screenprint.screen_print
    - message: 'Salt minion version {{ grains["saltversion"] }} is not on the expected 3008.x line. See docs/buildsheets/buildsheet-salt-minion.md.'
    - messagetype: 'error'
{% else %}
salt_minion_build_check:
  module.run:
    - name: screenprint.screen_print
    - message: 'Salt minion version {{ grains["saltversion"] }} is on the expected 3008.x line.'
    - messagetype: 'success'
{% endif %}

## Verify the custom grains file (salt/states/grains/init.sls's render_custom_grains target) exists.
{% if not salt['file.file_exists']('C:\\ProgramData\\Salt Project\\Salt\\conf\\grains') %}
check_custom_grains_file_exists:
  module.run:
    - name: screenprint.screen_print
    - message: 'Custom grains file is missing. Apply the grains salt state.'
    - messagetype: 'error'
{% else %}
check_custom_grains_file_exists:
  module.run:
    - name: screenprint.screen_print
    - message: 'Custom grains file exists.'
    - messagetype: 'success'
{% endif %}

## Check if any of our real custom grains (see salt/states/grains/init.sls) are blank --
## happens if the grains file exists but is stale/wasn't refreshed after a site/role change.
{% for grain in ['nodetype', 'city', 'country', 'entity', 'habitat'] %}
{% set grain_value = salt['grains.get'](grain, '') %}
{% if grain_value == '' %}
check_grain_{{ grain }}_not_blank:
  module.run:
    - name: screenprint.screen_print
    - message: 'Custom grain {{ grain }} is blank.'
    - messagetype: 'warning'
{% endif %}
{% endfor %}

## Warn if habitat is not production -- same intent as the original, but references our own
## grains/pillar mechanism (salt/pillar/habitat.sls, not yet built) instead of the original's
## own differently-named per-node pillar dict.
{% if grains.get('habitat', '') != 'production' %}
warn_habitat_not_production:
  module.run:
    - name: screenprint.screen_print
    - message: 'Habitat is NOT set to production (current: {{ grains.get("habitat", "unset") }}). If unintentional, check pillar/habitat.sls for a per-minion override.'
    - messagetype: 'warning'
{% endif %}

## Check salt-minion service is set to automatically start
{% set salt_minion_startuptype = salt['cmd.run']('powershell -Command "(Get-Service salt-minion -ErrorAction SilentlyContinue).StartType"') %}

print_salt_minion_startup_status:
{% if salt_minion_startuptype|string == 'Automatic' %}
  module.run:
    - name: screenprint.screen_print
    - message: 'Salt Minion service is set to startup type: {{ salt_minion_startuptype }}'
    - messagetype: 'success'
{% else %}
  module.run:
    - name: screenprint.screen_print
    - message: 'Salt Minion service is set to startup type: {{ salt_minion_startuptype }} (expected Automatic).'
    - messagetype: 'error'
{% endif %}

## Bookends the banner at the top of this file -- ported 2026-07-20 from audit/footer/init.sls
## (see salt/cleanup/salt/audit/), same pattern as the intro, dropped apptype (no equivalent here).
print_footer_info_message:
  module.run:
    - name: screenprint.screen_print
    - message: 'Deployment checks on {{ grains["id"] }} completed'
    - messagetype: 'footer'
