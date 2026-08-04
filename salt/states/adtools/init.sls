## salt/states/adtools/init.sls
## Example Music Limited — PowerShell admin tool suite deployment (PS-easyIT +
## console-pwsh)
##
## Deploys a set of standalone PowerShell admin tools (github.com/PS-easyIT, NOT the
## easyDNS domain registrar -- see project notes; plus github.com/satorisage/
## console-pwsh) into C:\ADTools\<tool>\ on
## whichever Windows minion(s) this state is targeted at. Robert's own framing: not a
## replacement for Ansible/Salt driving these tasks directly -- these are ready-to-use
## GUI tools for when a junior admin isn't confident with raw PowerShell yet.
##
## Deliberately NOT wired into top.sls -- same "built, not auto-applied" pattern as
## bespoke_app_install/ (see that state's own header). Apply explicitly to whichever
## minions should get this:
##   salt 'EXADCS*' state.apply adtools
##   salt -G 'nodetype:DCS' state.apply adtools   (once/if an equivalent grain exists)
##
## Each tool is a single (or paired) script with no installer/package manager --
## confirmed 2026-08-04 by checking every repo's own README before writing this
## (easyDNS, easyADPW, easyADGroups, easyFolder, easyEXO,
## easyEXCH-ProxyMailAddresses -- all standalone .ps1 WPF GUI scripts; console-pwsh,
## added same day, is a pwsh 7+ menu/console tool instead -- "MSP Console",
## Exchange Online/Entra ID/Azure admin, github.com/satorisage/console-pwsh, entry
## point Start-MSPConsole.ps1, not WPF). Downloaded straight from GitHub's own
## archive zip (no local file_roots staging needed) via archive.extracted, same
## module bespoke_app_install/ already uses in this repo -- enforce_toplevel
## (default True) strips the repo-main/ wrapper folder GitHub zips always have, so
## each tool's real files land directly in C:\ADTools\<tool>\, not one level too deep.
##
## PowerShell_Certificate (PS-easyIT's own CERTUM code-signing cert, which easyEXO at
## least pulls in at startup) is deliberately EXCLUDED from this list -- Robert's call,
## 2026-08-04: "don't install their cert". If a signed script fails to run under the
## target's execution policy without it, that's a separate decision for Robert, not
## something this state works around silently.
##
## NinjaONE-Scripts is also deliberately excluded -- on hold while Robert checks
## whether NinjaOne has a free tier, not a permanent exclusion like the cert above.
##
## Confirmed working on Server Core, not just Desktop Experience/client Windows
## (Robert, 2026-08-04, contradicting my own initial assumption) -- no has_gui gate
## here, unlike 40-choco-packages.yml's GUI-Chocolatey-package logic, which is a
## genuinely different case (that's about installing full desktop applications, not
## dropping a few WPF .ps1 scripts in a folder for on-demand use).
##
## Each tool requires the AD PowerShell module (RSAT-AD-PowerShell) to actually do
## anything useful -- installed once here via win_servermanager, not per-tool.
##
## NOT YET LIVE-TESTED against a real Salt minion as of 2026-08-04 -- built and
## reasoned through (module choices match bespoke_app_install/'s own proven usage in
## this repo), but there's no Salt master/minion available to test against directly.
## Confirm a highstate/state.apply actually lands all six tools correctly on a real
## Windows minion before relying on this.

rsat_ad_powershell:
  win_servermanager.installed:
    - name: RSAT-AD-PowerShell

adtools_base_dir:
  file.directory:
    - name: 'C:\ADTools'
    - makedirs: True

{% set adtools = {
  'easyDNS':                       'https://github.com/PS-easyIT/easyDNS/archive/refs/heads/main.zip',
  'easyADPW':                      'https://github.com/PS-easyIT/easyADPW/archive/refs/heads/main.zip',
  'easyADGroups':                  'https://github.com/PS-easyIT/easyADGroups/archive/refs/heads/main.zip',
  'easyFolder':                    'https://github.com/PS-easyIT/easyFolder/archive/refs/heads/main.zip',
  'easyEXO':                       'https://github.com/PS-easyIT/easyEXO/archive/refs/heads/main.zip',
  'easyEXCH-ProxyMailAddresses':   'https://github.com/PS-easyIT/easyEXCH-ProxyMailAddresses/archive/refs/heads/main.zip',
  'console-pwsh':                  'https://github.com/satorisage/console-pwsh/archive/refs/heads/main.zip',
} %}
## All seven confirmed default_branch=main via the GitHub API 2026-08-04 (checked
## easyDNS/easyFolder/easyEXCH-ProxyMailAddresses/console-pwsh directly, assumed
## consistent org-wide for the rest of PS-easyIT -- if a future tool in this list
## ever uses a different default branch, this URL will 404 and the
## archive.extracted state below will fail loudly, not silently deploy nothing).

{%- for tool, url in adtools.items() %}
adtools_{{ tool }}:
  archive.extracted:
    - name: 'C:\ADTools\{{ tool }}'
    - source: {{ url }}
    - archive_format: zip
    - enforce_toplevel: True
    - require:
      - file: adtools_base_dir
{% endfor %}
notify_adtools_deployed:
  module.run:
    - name: screenprint.screen_print
    - message: "PS-easyIT AD tools deployed to C:\\ADTools\\ ({{ adtools.keys() | join(', ') }})"
    - messagetype: 'success'
    - require:
{%- for tool in adtools %}
      - archive: adtools_{{ tool }}
{%- endfor %}
