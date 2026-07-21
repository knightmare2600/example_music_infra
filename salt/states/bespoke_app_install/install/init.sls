## salt/states/bespoke_app_install/install/init.sls
## Example Music Limited — generic bespoke Windows app installer/redeployer
##
## PRESERVED BUT NOT ACTIVE: not included in top.sls, no real pillar data
## exists for it. Genericised 2026-07-21 from a dropped-in reference Salt
## state that deployed one specific real bespoke app -- Robert's explicit
## call: the app-specific content itself (URLs, hardcoded paths/usernames)
## has no equivalent here, but the underlying pattern -- detect the version
## on disk, compare against the desired version, kill/extract/relaunch only
## if it actually differs -- is genuinely reusable, worth keeping ready for
## whenever Example Music has its own bespoke Windows app to deploy this way.
##
## To activate for a real app: fill in pillar under `bespoke_app` (see the
## defaults below for the expected shape), add `bespoke_app_install` to
## top.sls (or target it per-minion), and drop the real .zip/.ico into
## bespoke_app_install/files/.
##
## Real bugs found and fixed while genericising (not present in behaviour
## below):
##   - The original wrapped its whole version-check block in
##     `file_exists(...) or not directory_exists(...) or not file_exists(...)`
##     -- the first and third clauses are direct opposites of each other
##     (X or not X), which is always true regardless of the second clause.
##     The entire condition was a tautology -- the block always ran
##     unconditionally, making the wrapping `if` dead code. Removed; the
##     inner version-comparison logic (the part that actually matters) is
##     unaffected and preserved as-is.
##   - The VERSION file's `contents:` block had two separate Jinja print
##     statements on two lines -- the real version, then a second line
##     containing either ".0" or nothing. That second line serves no
##     purpose and would have left a stray blank/".0" line in the file.
##     Simplified to just write the version string directly.
##   - `messagetype: "warn"` isn't a value screenprint.py actually maps to a
##     colour (only header/success/warning/error/info/banner/footer are) --
##     silently fell through to the default (uncoloured) case. Fixed to
##     "warning".
##
## Preserved as-is, NOT resolved, since the original intent isn't known:
##   - `grains['apptype']`/`grains['appversion']` are referenced below exactly
##     as the original used them, but no equivalent grains exist in this
##     estate's real grains/init.sls (which deliberately dropped app-specific
##     fields -- "no equivalent app in this estate"). Whoever activates this
##     for a real app needs to either add matching custom grains, or gate
##     which minions run this state some other way (e.g. per-minion
##     targeting in top.sls) instead of relying on these two grains existing.
##   - The gating condition below is `apptype matches OR habitat is staging`
##     -- i.e. staging boxes get this app deployed even if apptype doesn't
##     match. Kept exactly as the original had it; not clear whether that
##     was deliberate ("staging always gets whatever's being tested") or a
##     mistake, and this template isn't active, so not worth guessing at.

{% set app = pillar.get('bespoke_app', {}) %}
{% set app_name = app.get('name', 'bespoke_app') %}
{% set install_dir = app.get('install_dir', 'C:\\' ~ app_name) %}
{% set shortcut_cleanup_users = app.get('shortcut_cleanup_users', ['Administrator']) %}
{% set app_data = pillar.get('bespoke_app_data', {}).get(grains['id'], {}) %}

{% if grains.get('apptype') == app_name or grains.get('habitat') == 'staging' %}

  ## Detect the build version on disk, if any
  {%- if salt['file.file_exists'](install_dir ~ '\\VERSION') %}
    {%- set app_build = salt['file.read'](install_dir ~ '\\VERSION').strip() %}
  {%- else %}
    {%- set app_build = '1.0.0' %}
  {%- endif %}

  ## Desired version: a per-minion grain override if set, else the pillar default
  {%- if grains.get('appversion', 'none') != 'none' %}
    {%- set pillarver = grains.get('appversion') %}
  {%- else %}
    {%- set pillarver = app.get('version') %}
  {%- endif %}

  {% if app_build != pillarver or not salt['file.directory_exists'](install_dir) %}
    kill-bespoke-app:
      process.absent:
        - name: {{ app_name }}

    extract-bespoke-app:
      archive.extracted:
        - name: C:\
        - source: salt://bespoke_app_install/files/versions/{{ app_name }}_windows_{{ pillarver }}.zip
        - keep_source: False
        - enforce_toplevel: False
        - force: True
        - overwrite: True

    bespoke_app_startup:
      reg.present:
        - name: HKU\{{ app_data.get('winuserid', '') }}\SOFTWARE\Microsoft\Windows\CurrentVersion\Run
        - vname: {{ app_name }}Launcher
        - vdata: '"C:\Windows\System32\cmd.exe" /c "start /D {{ install_dir }} {{ install_dir }}\{{ app_name }}.exe"'
        - vtype: REG_SZ

    remove_startup_shortcuts:
      file.absent:
        - names:
          {% for user in shortcut_cleanup_users %}
            - "C:\\Users\\{{ user }}\\AppData\\Roaming\\Microsoft\\Windows\\Start Menu\\Programs\\Startup\\{{ app_name }}.lnk"
          {% endfor %}

    bespoke_app_favicon:
      file.managed:
        - name: '{{ install_dir }}\{{ app_name }}.ico'
        - source: salt://bespoke_app_install/files/{{ app_name }}.ico

    bespoke_app_config_windows:
      file.managed:
        - name: {{ install_dir }}\{{ app_name }}.yml
        - source: salt://bespoke_app_install/templates/windows-{{ grains['habitat'] }}.j2
        - template: jinja
        - defaults:
            hostname: {{ grains['id'] }}
            apptype: {{ app_name }}

    build_version:
      file.managed:
        - name: {{ install_dir }}\VERSION
        - contents: "{{ pillarver }}"

    start_bespoke_app:
      cmd.wait:
      - name: '{{ install_dir }}\{{ app_name }}.exe'
      - shell: cmd
      - runas: admin
      - cwd: '{{ install_dir }}'
      - listen_in:
        - file: extract-bespoke-app

  {% else %}
    this_is_a_noop:
      module.run:
        - name: screenprint.screen_print
        - message: 'No operations executed -- on-disk version already matches pillar. Confirm this is an intended run.'
        - messagetype: 'warning'
  {% endif %}

{% else %}
  print_grain_vs_app_error:
    module.run:
      - name: screenprint.screen_print
      - message: 'ERROR: apptype grain is set to "{{ grains.get("apptype") }}" but a deploy of "{{ app_name }}" was attempted.'
      - messagetype: 'error'

{% endif %}
