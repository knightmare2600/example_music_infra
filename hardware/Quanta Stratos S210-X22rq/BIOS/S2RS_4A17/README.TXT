================================================================================
QUANTA Computer Inc. BIOS RELEASE NOTES for S2RS/Q/G Ivy Bridge(16MB BIOS)
================================================================================
Project Name      : S2RS/Q/G
BIOS Version      : S2RS4A17
Build Date        : 2015/06/25
Update BootBlock  : YES
Clear NVRAM       : YES
8MB ROM Checksum  : 62126F17 
16MB BIN Checksum : CBB71901
ROM MD5(8MB)      : 9a0c91f51005a3d1cb73ad09a8d7a1aa   
BIN MD5(16MB)     : 1c47545894425c9ed9595f47f025617e 
================================================================================
                        HARDWARE REQUIREMENTS/REVISIONS
================================================================================
System hardware revision supported: S2RS/Q/G PVT board. 

================================================================================
                        INTEL PROCESSOR MICORCODE REVISIONS
================================================================================

----------------------+------------------------------------+-----------------
Filename              | Description                        | Stepping(s)     
----------------------+------------------------------------+-----------------
M0F206D2_8000020C.PDB | Protein Data Bank format, Revision 8000020C | B-0 (Sandy Bridge-EP) 
M0F206D3_80000304.PDB | Protein Data Bank format, Revision 80000304 | B-1 (Sandy Bridge-EP) 
M6D206D5_00000513.PDB | Protein Data Bank format, Revision 00000513 | C-0 (Sandy Bridge-EP) 
M6D206D6_80000619.PDB | Protein Data Bank format, Revision 00000619 | C-1,M-0 (Sandy Bridge-EP)
M6D206D7_0000070D.PDB | Protein Data Bank format, Revision 0000070D | C-2,M-1 (Sandy Bridge-EP)
MED306E2_0000020D.PDB | Protein Data Bank format, Revision 0000020D | B-1, B-2, L-1, L-2, R-0, and R-1
MED306E3_00000308.PDB | Protein Data Bank format, Revision 00000308 | B-3 (Ivy Bridge-EP)
MED306E4_00000417.PDB | Protein Data Bank format, Revision 00000417 | C-0, C-1, S-0, S-1, M-0, M-1 (Ivy Bridge-EP)

================================================================================
                        SYSTEM FIRMWARE REQUIREMENTS/REVISIONS
================================================================================
Patsburg SATA RAID         : v3.5.0.1005
Patsburg SCU               : v3.5.0.1005
Intel(R) I350 (Powerville) : IBA GE v1.3.81
Intel(R) X540 (Twinville)  : IBA XE v2.2.05
iSCSI                      : iSCSI Remote Boot v2.7.97
Intel(R) SPS F/W (ME)      : SPS_02.01.07.225.0
Intel(R) QPI and MRC       : 2.00.00.02
ACM                        : PW 2.4
SINIT                      : PW 2.4
================================================================================
                        IMPORTANT INSTALLATION NOTES
================================================================================
WARNING:  
(1) It is very important to follow the flash option provided in the batch file (BIOS_dos.bat/
   ME_dos.bat for DOS, BIOS_win64.cmd/ME_win64.cmd for Windows, BIOS_lnx64.sh/ME_lnx64.sh for Linux). 
   Using incorrect flash option to flash BIOS may cause damage to your system

1. Burn xxxx.BIN via fixture or,

2. For DOS environment, follow below steps to update both BIOS and ME FW:
   (1) Unzip the release package to the same folder in a HDD or USB Flash Drive with bootable DOS.
   (2) Insert the USB Flash Drive or HDD mentioned in step (1).
   (3) Power on the system and boot into this USB Flash Drive or HDD.
   (4) Execute batch file BIOS_dos.bat to update BIOS.
   (5) Execute batch file ME_dos.bat to update ME FW.
   (6) After the update finished, perform an DC cycle, the new BIOS/ME FW runs.
   (7) Then, please enter setup, press <F9> to load default and save before any test run.
 
3. For x64 Windows environment, follow below steps to update both BIOS and ME FW:
   (1) Power on the system and boot into Windows OS.
   (2) Unzip the release package to the same folder in the HDD.
   (3) Open Command Prompt, change to the folder with release package located.
   (4) Execute batch file BIOS_win64.cmd to update BIOS.
   (5) Execute batch file ME_win64.cmd to update ME FW.
   (6) After the update finished, perform an DC cycle, the new BIOS/ME FW runs.
   (7) Then, please enter setup, press <F9> to load default and save before any test run.
   
4. For x64 Linux environment, follow below steps to update both BIOS and ME FW:
   (1) Power on the system and boot into Linux OS.
   (2) Unzip the release package to the same folder in the HDD.
   (3) Open Terminal, change to the folder with release package located.
   (4) Execute batch file BIOS_lnx64.sh to update BIOS.
   (5) Execute batch file ME_lnx64.sh to update ME FW.
   (6) After the update finished, perform an DC cycle, the new BIOS/ME FW runs.
   (7) Then, please enter setup, press <F9> to load default and save before any test run.


Note: Update BIOS via AFUDOS utility with BIOS ROM file will NOT update SPS 
      firmware (ME firmware) and ME configuration.
- Because flash parameter "/n" has been removed from flash batch file.
  Please make sure the onboard BIOS version is 4A12 or later befoer using this batch to update BIOS.

================================================================================
                        KNOWN ISSUES/WORKAROUNDS
================================================================================
================================================================================
S2RS_4A14:
- Load all Brocade option rom first to avoid BDA 40:13 system memory is destroyed.

S2RS_4A05:
- Always configure S2RS CPU1 root port 2 as x8 x8 (Can't support GPU SKU).


================================================================================
                        FEATURES ADDED/MODIFY
================================================================================
S2RS_4A17:
- N/A.

S2RS_4A16:
-Update 4.6.51_SECBOOT_WIN8_023 module from 4.6.5.1_SECBOOT_WIN8_015 (related to #155714).
-Update 4.6.5.x_CRYPTOAPI_021 module from 4.6.5.x_CRYPTOAPI_015.(related to #155714)
-Update 4.6.3_SHELL_r61_00" module from 4.6.3_SHELL_20100528_01.(related to #155714)
-Add module "Lsi Sas Config" for LSI UEFI Driver(related to #150753,150754,151933,154378,158067).
-Update IntelLTSX_15 (BIOSACM:PW2.4 and SINITACM:PW2.2) to IntelLTSX_18 (BIOSACM:PW2.4 and SINITACM:PW2.4).
-Dynamic disable S2RS unused PCIe root port device if no PCIe Device.

S2RS_4A15:
- Update 82599 PXE Oprom to 2.3.27.
- New option "Disabled" can be selected to disable boot device.

S2RS_4A14:
- Support QDCM.

S2RS_4A13:
- Update ACM to version 2.4 from 2.2. 
- Update 4.6.4_SNB_Romley_40b.

S2RS_4A12:
- Update Intel 10Gbe EFI driver to v4.2.23 from v2.9.01.
- Follow SI spec to modify RedHat and CentOS boot name.
- Modify the correct length of DIMM module part number in SMBIOS type 17.

S2RS_4A11:
- N/A.

S2RS_4A10:
- Update Intel Nehalem Microcode module to 4.6.0_INTEL_MICROCODE_63 from 4.6.0_INTEL_MICROCODE_55.
- Change below BIOS default.
Hardware Prefetch - Disabled.
Adjacent Cache Prefetch - Disabled.
DCU Streamer Prefetcher - Disabled.
VT-D - Disabled.

S2RS_4A09:
- Update "EFI OS BootOptionNames" module to 4.6.4.1_EfiOsBootOptionNames_05 from 4.6.4.1_EfiOsBootOptionNames_03.
- Update "NetBootHotKey" module to 4.6.3_NetBootHotKey_07 from 4.6.3_NetBootHotKey_05.

S2RS_4A08:
- Enable SATA hot plug function.

S2RS_4A07:
- Update Intel Nehalem Microcode module to 4.6.0_INTEL_MICROCODE_55 from 4.6.0_INTEL_MICROCODE_53.
- Update "Intel Sandy Bridge Power Management" module to 4.6.3_INTEL_SB_PPM_18 from 4.6.3_INTEL_SB_PPM_17.
- Update module SandyBridge - Romley to 4.6.4_SNB_Romley_32a from 4.6.4_SNB_Romley_31
- Update 4.6.3_IntelLTSX_15 from 4.6.3_IntelLTSX_14.
- Support MRC error status log to BMC.

S2RS_4A06:
- Support UEFI ISCSI BOOT.
- Update Intel Nehalem Microcode module to 4.6.0_INTEL_MICROCODE_53 from 4.6.0_INTEL_MICROCODE_52.
- Update "Runtime ErrorLog" to 4.6.4.1_RtErrorLog_04 from 4.6.4.1_RtErrorLog_03.
- Update "Intel Sandy Bridge Power Management" module to 4.6.3_INTEL_SB_PPM_17 from 4.6.3_INTEL_SB_PPM_16.
- Set "Enforce Short PDG" to "Enabled" support 1866MHZ DIMM.

S2RS_4A05:
- Update ME package to VIP:52784 SPS_02.01.07.225
- Update module Intel Sandy Bridge Power Management to 4.6.3_INTEL_SANDY_BRIDGE_PPM_16 
- Update Romley Refresh CPU Specific Code module to 4.6.4.0_IVYBRIDGEEP_05 from 4.6.4.0_IVYBRIDGEEP_04.
- Update module Intel ME Subsystem to 4.6.4_Intel_ME_SB_26 from 4.6.4_Intel_ME_SB_25.
- Update module Intel Patsburg to 4.6.4_Intel_Patsburg_24 from 4.6.4_Intel_Patsburg_23a.
- Update module SandyBridge - Romley to 4.6.4_SNB_Romley_30 from 4.6.4_SNB_Romley_29.
- Update "Runtime ErrorLog" to 4.6.4.1_RtErrorLog_03 from 4.6.4.1_RtErrorLog_02.

S2RS_4A04:
- Update module IScsi to 4.6.5.1_iSCSI_04 from 4.6.5.1_iSCSI_03.
- Update module Intel Nehalem to 4.6.3_INTEL_Nehalem_51 from 4.6.3_INTEL_Nehalem_50.
- Update CryptoPkg;4.6.5.x_CRYPTOAPI_015 from CryptoPkg;4.6.5.x_CRYPTOAPI_014.
- Update USB module to 4.6.3_USB_08.10.27 from 4.6.3_USB_08.10.24.
- Update "SandyBridge - Romley" module to 4.6.4_SNB_Romley_29 from 4.6.4_SNB_Romley_28b.
- Update 4.6.5.1_SECBOOT_WIN8_ 018 from 4.6.5.1_SECBOOT_WIN8_ 017.
- Update 4.6.4_UEFI_NETWORK_STACK_II_08 from 4.6.4_UEFI_NETWORK_STACK_II_05.
- Update CSM module to 4.6.5.3_CSM.7.71_80 from 4.6.3.1_CSM.7.70_79.
- Update module Intel Patsburg to 4.6.4_Intel_Patsburg_23a from 4.6.4_Intel_Patsburg_22a.
- Show "Launch Storage OpROM policy" and "Launch PXE OpROM policy" in BIOS setup menu.
- Function implementation : MEZZ ISCSI/PXE is controlled by setup menu option.


S2RS_4A03:
- Show options "Patrol Scrub" and "Demand Scrub" base on SI Spec and gray out if access level is administrator.
- Update module Intel VT-d to 4.6.4_Intel_VTd_08 from 4.6.4_Intel_VTd_07.
- Update 4.6.4_SNB_Romley_26a from 4.6.4_SNB_Romley_26.
- Update 4.6.5.1_FixedBootOrder_14 from 4.6.5.1_FixedBootOrder_13.
- Update Runtime ErrorLog module to 4.6.4.1_RtErrorLog_01 from (BETA)4.6.4.1_RtErrorLog_01.
- Update AHCI module to 4.6.3_AhciSrc_022 from 4.6.3_AhciSrc_021.
- Update 4.6.4_Intel_Patsburg_22a from 4.6.4_Intel_Patsburg_21a.
- Update Intel ME Subsystem module to 4.6.4_Intel_ME_SB_24 from 4.6.4_Intel_ME_SB_23.
- Increase SATA OPROM delay time to 6 seconds.

S2RS_4A02:
- Enable UEFI IPv6 PXE support.
- Set "PCI Error Status Logging Support" default is enabled.
- Modify "Memory Corr. Error Threshold" only support four settings "1,5,10,20".
- Update 4.6.4_SNB_Romley_25 from (BETA)4.6.4_SNB_Romley_25.


S2RS_4A01:
- - Support Ivy bridge CPU and change code base to AMI 4.6.5.4.

================================================================================
                        FEATURES REMOVED
================================================================================
S2RS_4A17:
- N/A.

S2RS_4A16:
- N/A.

S2RS_4A15:
- N/A.

S2RS_4A14:
- N/A.

S2RS_4A13:
- N/A.

S2RS_4A12:
- N/A.

S2RS_4A11:
- N/A.

S2RS_4A10:
- N/A.

S2RS_4A09:
- N/A.

S2RS_4A08:
- N/A.

S2RS_4A07:
- N/A.

S2RS_4A06:
- N/A.

S2RS_4A05:
- N/A.

S2RS_4A04:
- N/A.

S2RS_4A03:
- N/A.

S2RS_4A02:
- N/A.

S2RS_4A01:
- N/A.

================================================================================
                        ISSUES FIXED
================================================================================
S2RS_4A17:
- 157056 : The WOL function(S5 status) under W2012R2 is not workable (Linux is pass) on QN 10GbE 57810.
- Memory speed of the SMBIOS (Offset 15h ) should be displayed the MAX speed, not the current speed.
- Fix send wrong mac address to BMC if onboardLan1 is enabled and onboardLan2 is disabled.
 
S2RS_4A16:
- Fix #150461 : There are two ubuntu option on boot order after install ubuntu14.04. 
- Fix #155714: Customer shell USB key is recognized as illegal key after install customer db/PK/KEK key.
However, the shell USB key should be legal key for boot.
- Fix #150753: LSI critical boot issue and Safestor function will let UEFI BIOS can't show RAID card OptionROM under Advanced.
- Fix #150754: Setting LSI Safestore will let BIOS didn't show RAID card device under boot loader.
- Fix #151933: Watchdog timeout still work when user in LSI UEFI webBIOS. So SUT will auto reboot when user setting in the LSI UEFI webBIOS.
- Fix #154378: All the LSI Raid Card function will be disappeared under BIOS when user modified the CSM to ''UEFI olny'' and unplug the HDD.
- Fix #158067: BIOS setting quit boot (enable) but in post will auto change to diagnostics screen after RAID card post.
- Fix ME SCI handler method L24 can't find PRAD table when (Notify(\_SB.PRAD, 0x80)).

S2RS_4A15:
- Hidden "DIMM Voltage Select" and "DIMM Voltage SVID setting".
- DIMM Co initialization failed but BIOS post still shows DIMM C1.

S2RS_4A14:
- N/A.

S2RS_4A13:
- N/A.

S2RS_4A12:
- 141819: The IPv6 invalid IP shouldn't be saved successfully under BIOS.
- 144341: Press F12 during the POST under legacy boot mode would abnormally invoke UEFI PXE option rom

S2RS_4A11:
- Fix HII Font Protocol Test Error with SCT 2.3.1C.
- 141819: The IPv6 invalid IP shouldn't be saved successfully under BIOS.
- 140951: Onboard 10G LAN performance is too low when run iperf with both LOMs at the same time.
- 140291: SUT will NOT prompt warning message when setting reserved IPv6 [2001::/32] as IP and gateway address under BIOS setup/Server Mgmt.

S2RS_4A10:
- N/A.

S2RS_4A09:
- Modify SMBIOS Type 4 CPU socket to "LGA 2011"
- 138189 : After installing UEFI RHEL 6.4 x64 with LSI 2208 Mezz Card, it will have two boot device in BIOS Setup.
- 138438 : "Bootup NumLock State" default setting is not correct.
- 138545 : BIOS Version showed as ''S2RS4A08'' in BIOS Setup. but showed as ''S2RQ4A08'' in SMBIOS Type 0.

S2RS_4A08:
- Follow SI-standard BIOS Setup SPEC-V1.04, change Boot mode "LEGACY" to "Legacy".

S2RS_4A07:
- Fixed use Rastool 3.6.2 to inject PCIE Un-Correctable and Correctable Error system will be hang.
- Grayout UEFI iSCSI configuration page if access level is USER.
- Fix USB key will be detected as HDD if file path is \efi\boot\bootx64.efi and boot mode is UEFI.
- Fix FRB2 timer is still count when user enter LSI Raid card.
- Fix issue:There is no BMC fail error message during post when user disable BMC.
- Add "Setup Prompt Timeout" attribute "Flag" to fix there is no any popup warning message if user change the item then boot to any devcie.
- Fix Password clear event will be log twice if press F12 enter bios setup.
- Fix there are duplicated UEFI devices under BIOS override menu if install UEFI SUSE.
- Fix "When SEL is Full" is set to  "Erase Immediately", the function will not work normally.

S2RS_4A06:
- By EE request, CPU0 root port 2A is always configured as x8 x8(slot6 can't support GPU SKU).

S2RS_4A05:
- Hide S2RS debug options.

S2RS_4A04:
- Fix system will not boot to BIOS setup menu without any boot device if boot mode is legacy
- Add module "EfiOsBootOptionNames" to fix system can't boot to UEFI ESX5.1.
- The order of SMBIOS UUID should be the same order with BMC raw data.

S2RS_4A03:
- Update AST2300 device SSID.
- Fix SMBIOS type0 BIOS version and build date are all empty.
- Fix issues - PCIE error log is malfunction.
- Change Console redirection baudrate default is 115200.
- Fix FRB2 is not be disabled when enter LSI config utility.

S2RS_4A02:
- Fix BMC network configuration is malfunction.
- Gray out the boot items of setup menu when access level is user.
- Fix sent wrong Ivy bridge type to BMC.
- Remove string "EVALUATION COPY" during POST.
- Modified USB floppy group string.

S2RS_4A01:
- N/A.

[END OF RELEASE NOTES]