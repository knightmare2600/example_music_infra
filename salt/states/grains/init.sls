## salt/states/grains/init.sls
## Example Music Limited — custom grains (site + role + environment)
##
## Ported 2026-07-20 from a dropped-in Salt state (salt/testcustomgrains.sls, see
## top-level salt/cleanup/ for the original). What changed and why:
##
##   - Original parsed city/country/brand/group-style fields out of a hyphen-
##     encoded minion ID (a multi-field naming scheme with no equivalent in our
##     hostname scheme). We use EXA<ROLE><SITE><NNN> instead -- role code and site
##     code are parsed directly from fixed positions in the hostname, and
##     city/country/entity come from a real sites.csv lookup (pillar/sites.sls,
##     generated -- benarbejde/generate_inventory.py --emit-site-grains-pillar),
##     matching how every other role in this estate already gets this data.
##   - Original's `defaults:` block passed several of those same fields (plus
##     a node-number and hostname) all set to the same unparsed grains['id']
##     string -- the template it called never actually used any of them (it
##     re-parsed grains['id'] itself instead). That whole redundant/broken
##     pattern is gone.
##   - Several fields describing a specific bespoke application (its own
##     type/location/version, plus a Windows user SID) dropped entirely -- no
##     equivalent app in this estate.
##   - habitat (deliberately not named "environment" -- Salt's own saltenv concept
##     already owns that word) still defaults to production, same as Ansible's own
##     nodeinfo_environment default. No per-minion pillar override exists yet;
##     add one under pillar/habitat.sls if/when a specific minion genuinely needs
##     to differ from production.
##   - Restart is now conditional (onchanges) on the grains file actually
##     changing, not unconditional on every state.apply run like the original.
##   - Fixed salt-call.exe's path: original used C:\salt\salt-call.exe (a
##     custom INSTALLDIR override specific to wherever it came from); our MSI
##     install uses the real default INSTALLDIR, C:\Program Files\Salt Project\Salt.
##   - Restart still backgrounded (bg: True) + last (order: last) -- known,
##     deliberate catch-22 (new grains aren't visible until the minion restarts,
##     but a restart mid-job kills the job that triggered it); whether a
##     lighter-weight refresh (no restart) actually reloads a STATIC grains file
##     is still unverified (see 2026-07-20 discussion) -- do not assume one of
##     the saltutil refresh/sync functions solves this without testing live.
##   - notify_render_custom_grains added 2026-07-20: onchanges-gated screenprint
##     call, same convention as wintools/init.sls and audit/init.sls -- silent
##     on a routine run where the rendered grains file already matched, only
##     speaks up the moment it actually had to (re)write the file.

{% set minion_id = grains['id'] %}
{% set role_code = minion_id[3:6] %}
{% set site_code = minion_id[6:9] %}
{% set site = pillar.get('sites', {}).get(site_code, {}) %}
{% set habitat = pillar.get('habitat', {}).get(minion_id, 'production') %}

render_custom_grains:
  file.managed:
    - name: 'C:\ProgramData\Salt Project\Salt\conf\grains'
    - source: salt://grains/templates/grains.j2
    - template: jinja
    - defaults:
        nodetype: {{ role_code }}
        city: "{{ site.get('city', '') }}"
        country: "{{ site.get('country', '') }}"
        entity: "{{ site.get('entity', '') }}"
        habitat: {{ habitat }}

notify_render_custom_grains:
  module.run:
    - name: screenprint.screen_print
    - message: "Custom grains file on {{ minion_id }} was missing or out of date -- rewritten, salt-minion restarting to pick it up."
    - messagetype: 'warning'
    - onchanges:
      - file: render_custom_grains

restart_salt_minion:
  cmd.run:
    - name: 'C:\Program Files\Salt Project\Salt\salt-call.exe service.restart salt-minion'
    - bg: True
    - order: last
    - onchanges:
      - file: render_custom_grains
