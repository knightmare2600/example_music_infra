Example Music Limited -- WinPE deployment files
================================================

The WinPE .wim files (x86_64/boot_x64.wim, arm64/boot_arm64.wim) that
menu.ipxe's WinPE entries expect are NOT included in this repository, and
never will be -- not an oversight, not a TODO.

Why: a WinPE .wim is built from Microsoft's own Windows ADK (Assessment
and Deployment Kit). Redistributing a built .wim falls under Microsoft's
ADK licensing terms, which this repo cannot satisfy -- so it is never
committed here, via git-lfs or otherwise.

What IS included: wimboot (x86_64/wimboot, x86_64/wimboot.i386,
arm64/wimboot.arm64) -- the loader that streams a .wim over HTTP at boot
time. wimboot itself is GPL2 (github.com/ipxe/wimboot), contains no
Microsoft code, and is unaffected by the above.

If you need a working WinPE entry, build the .wim yourself from a
legitimately-licensed local ADK install using Build-WinPE.ps1 (see
docs/bootstrap/WinPE_DaRT_Build_Guide.md), then place the result at
x86_64/boot_x64.wim or arm64/boot_arm64.wim on your own copy of this
server. Do not ask for one to be shared, and do not add one to this repo.

See docs/bootstrap/bootstrapping.md for the full asset-status table.
