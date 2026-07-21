## salt/states/wintools/init.sls
## Example Music Limited — Windows power-management registry keys + local
## break-glass admin account
##
## Ported 2026-07-20 from a dropped-in reference Salt state (since removed --
## see salt/README.md's workflow note). What did NOT make it here, and why:
##
##   - powercfg monitor-timeout-ac/dc and standby-timeout-ac/dc (all set to 0,
##     i.e. never sleep) -- conflicts with ansible/playbooks/windows_bootstrap/
##     tasks/screenlock.yml, which sets monitor-timeout-ac/dc to 60/30 for
##     security lock purposes. Ansible wins on this -- dropped here entirely,
##     not carried forward as an ongoing Salt assertion that would fight it.
##   - bginfo.exe/FileHash.exe/dosdev.exe/DelProf2.exe file.managed tasks --
##     fully merged into Ansible's windows_bootstrap (50-binaries.yml's new
##     binaries_flat, see group_vars/windows/vars.yml) instead. Not duplicated
##     here -- these are one-time file deployments, not the kind of ongoing
##     drift Salt needs to keep correcting, unlike the registry keys below.
##   - Two file.managed tasks for a bespoke third-party application's own
##     support tooling -- not reusable outside that specific app. Dropped
##     entirely.
##   - Commented-out C:\Drivers folder task and three custom-branded wallpaper
##     registry keys -- already inert in the source, AND pointed at the wrong
##     (unlocked, HKCU) registry keys anyway. See enforce_wallpaper below for
##     what this estate actually does instead.
##
## disable_disk_spindown below was added 2026-07-20 from a different dropped-in
## reference state -- included here despite the powercfg-conflict caution above
## because disk-timeout has no existing Ansible/Salt owner anywhere and no
## conflict, unlike monitor/standby.
##
## enforce_wallpaper also added 2026-07-20, Robert's own idea while reviewing
## a dropped-in wallpaper check: this estate's real wallpaper mechanism
## (ansible/playbooks/windows_bootstrap/playbooks/60-wallpaper.yml) already
## locks it via policy registry keys, not the plain user-changeable HKCU key
## the dropped-in check queried -- but "policy-locked" isn't "impossible to
## route around", so Salt re-asserts the same keys Ansible sets, same
## bootstrap-once/enforce-ongoing pattern as everything else here. No
## dedicated Salt "wallpaper" state module exists (checked, not assumed) --
## reg.present against the same keys is the real, correct mechanism.
##
## Every enforcement task below now has an onchanges-gated screenprint
## companion (matching audit/init.sls's existing colourised-output convention --
## same module, same messagetype palette). "onchanges" means these stay
## silent on a routine run where nothing had drifted -- a message only
## appears the moment this state actually corrects something, not on every
## run regardless of outcome.

## Set the hibernation registry key to the correct value
enablehibernation:
  reg.present:
    - name: 'HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Power'
    - vname: 'HibernateEnabled'
    - vdata: 0
    - vtype: 'REG_DWORD'

notify_enablehibernation:
  module.run:
    - name: screenprint.screen_print
    - message: "HibernateEnabled had drifted from 0 on {{ grains['id'] }} -- corrected."
    - messagetype: 'warning'
    - onchanges:
      - reg: enablehibernation

## Set the pagefile to be cleared at shutdown. Exact same registry key as
## ansible/playbooks/windows_bootstrap/tasks/power_pagefile.yml's own
## "Clear page file at shutdown" task -- deliberate duplication, not an
## oversight. Ansible sets this correctly at bootstrap time; Salt keeps
## re-asserting it afterward in case it ever drifts, same pattern as every
## other "bootstrap once, Salt enforces ongoing" case in this estate.
clearpagefile:
  reg.present:
    - name: 'HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management'
    - vname: 'ClearPageFileAtShutdown'
    - vdata: 1
    - vtype: 'REG_DWORD'

notify_clearpagefile:
  module.run:
    - name: screenprint.screen_print
    - message: "ClearPageFileAtShutdown had drifted from 1 on {{ grains['id'] }} -- corrected."
    - messagetype: 'warning'
    - onchanges:
      - reg: clearpagefile

## Disable hard disk spin-down. Same setting ansible/playbooks/windows_bootstrap/
## playbooks/70-hibernation.yml sets at bootstrap time (ported from the same
## dropped-in reference state) -- deliberate duplication, same
## "bootstrap once, Salt enforces ongoing" pattern as the registry keys above.
## Unlike monitor/standby-timeout (dropped, see this file's own header), nothing
## else in this estate touches disk-timeout, so there's no conflict to worry about.
## unless makes this idempotent -- cmd.run has no built-in way to know
## whether a command "changed" anything, so without this guard it would
## report changed=True (and fire notify_disable_disk_spindown below) on
## every single routine run, not just when the setting had actually
## drifted. Same query audit/init.sls's disk_spindown_status check already
## uses, so both sides agree on what "already disabled" looks like.
disable_disk_spindown:
  cmd.run:
    - name: 'powercfg /Change -disk-timeout-ac 0'
    - shell: powershell
    - unless: |
        if ((powercfg /Query SCHEME_CURRENT SUB_DISK DISKIDLE) -match 'AC Power Setting Index: 0x00000000') { exit 0 } else { exit 1 }

notify_disable_disk_spindown:
  module.run:
    - name: screenprint.screen_print
    - message: "Disk spin-down (AC) had drifted from 0 on {{ grains['id'] }} -- corrected."
    - messagetype: 'warning'
    - onchanges:
      - cmd: disable_disk_spindown

## Re-assert the corporate wallpaper policy keys -- same registry keys/values
## ansible/playbooks/windows_bootstrap/playbooks/60-wallpaper.yml sets at
## bootstrap time. Keep the path below in sync BY HAND with that file's
## exa_wallpaper_dest (group_vars/all/vars.yml) if it ever changes -- Ansible
## and Salt are separate systems with no shared var scope, same as
## salt_version_major elsewhere in this estate.
enforce_wallpaper_image_path:
  reg.present:
    - name: 'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\PersonalizationCSP'
    - vname: 'DesktopImagePath'
    - vdata: 'C:\Windows\Web\Wallpaper\ExampleMusic\corporate.png'
    - vtype: 'REG_SZ'

enforce_wallpaper_image_url:
  reg.present:
    - name: 'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\PersonalizationCSP'
    - vname: 'DesktopImageUrl'
    - vdata: 'C:\Windows\Web\Wallpaper\ExampleMusic\corporate.png'
    - vtype: 'REG_SZ'

enforce_wallpaper_image_status:
  reg.present:
    - name: 'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\PersonalizationCSP'
    - vname: 'DesktopImageStatus'
    - vdata: 1
    - vtype: 'REG_DWORD'

enforce_wallpaper_policy:
  reg.present:
    - name: 'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System'
    - vname: 'Wallpaper'
    - vdata: 'C:\Windows\Web\Wallpaper\ExampleMusic\corporate.png'
    - vtype: 'REG_SZ'

enforce_wallpaper_style:
  reg.present:
    - name: 'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System'
    - vname: 'WallpaperStyle'
    - vdata: '10'
    - vtype: 'REG_SZ'

enforce_no_themes_tab:
  reg.present:
    - name: 'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\Explorer'
    - vname: 'NoThemesTab'
    - vdata: 1
    - vtype: 'REG_DWORD'

## Queue SetWallpaper.exe (see files/README.md, windows_bootstrap) for next
## interactive logon -- same RunOnce mechanism 60-wallpaper.yml uses
## Ansible-side, added here 2026-07-21 so Salt's ongoing enforcement also
## forces a visible refresh, not just corrects the registry keys underneath.
## Path below kept in sync BY HAND with exa_wallpaper_dest_bmp
## (group_vars/all/vars.yml) -- no shared var scope between Ansible and Salt,
## same as enforce_wallpaper_image_path above. Only queued when the
## wallpaper enforcement actually found and fixed drift (onchanges on the
## same six keys as notify_enforce_wallpaper below), not on every routine run.
queue_setwallpaper_runonce:
  reg.present:
    - name: 'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce'
    - vname: 'ExaSetWallpaper'
    - vdata: 'C:\Windows\SetWallpaper.exe /D:S C:\Windows\Web\Wallpaper\ExampleMusic\corporate.bmp'
    - vtype: 'REG_SZ'
    - onchanges:
      - reg: enforce_wallpaper_image_path
      - reg: enforce_wallpaper_image_url
      - reg: enforce_wallpaper_image_status
      - reg: enforce_wallpaper_policy
      - reg: enforce_wallpaper_style
      - reg: enforce_no_themes_tab

## One combined message for all six wallpaper keys rather than six separate
## ones -- they're a single logical action (re-assert the corporate
## wallpaper policy), and a user who changed the wallpaper will typically
## have knocked out more than one of them at once via the Settings app.
notify_enforce_wallpaper:
  module.run:
    - name: screenprint.screen_print
    - message: "Corporate wallpaper policy had drifted on {{ grains['id'] }} -- corrected."
    - messagetype: 'warning'
    - onchanges:
      - reg: enforce_wallpaper_image_path
      - reg: enforce_wallpaper_image_url
      - reg: enforce_wallpaper_image_status
      - reg: enforce_wallpaper_policy
      - reg: enforce_wallpaper_style
      - reg: enforce_no_themes_tab

## Local break-glass admin account, for when the normal SSH-key-based Ansible
## access is broken (e.g. "someone changed/forgot the ansible password").
## Membership in Administrators means this account already gets SSH access
## automatically via the shared C:\ProgramData\ssh\administrators_authorized_keys
## file windows_bootstrap already populates (00-preflight.yml/75-openssh.yml) --
## no separate per-user key deployment needed.
##
## KNOWN, DELIBERATE WEAKNESS: this password is a hardcoded plaintext literal.
## Windows genuinely has no mechanism to set a local account password from a
## pre-computed hash (confirmed against Salt's own docs -- password_hash in
## salt.states.user is Linux/BSD/Solaris only; the Windows account-management
## API only ever accepts plaintext, which it then hashes internally). The
## correct fix would be a GPG-encrypted Salt pillar value plus a real random
## password pushed to KeePass -- deliberately NOT done here. This is a
## training/practice estate, not a real one -- do not do this in a real
## environment.
create_ansible_user:
  user.present:
    - name: ansible
    - fullname: ansible
    - password: 'Password1!'
    - win_description: Ansible User (break-glass local admin -- see comment above)
    - groups:
      - Administrators

notify_create_ansible_user:
  module.run:
    - name: screenprint.screen_print
    - message: "Break-glass 'ansible' account was missing, not in Administrators, or had a non-standard password on {{ grains['id'] }} -- corrected."
    - messagetype: 'warning'
    - onchanges:
      - user: create_ansible_user
