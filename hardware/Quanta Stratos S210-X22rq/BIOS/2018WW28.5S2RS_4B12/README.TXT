================================================================================
QUANTA Computer Inc. BIOS RELEASE NOTES for S2RS/Q/G Ivy Bridge (16MB Customized BIOS)
================================================================================
Project Name     : S2RS/Q/G
BIOS Version     : S2RS4B12
Build Date       : 2018/07/13
Update BootBlock : YES
Clear NVRAM      : YES
ROM MD5(8MB)      : ed2035c92c2d2a336ffbd43e6d1e2372
BIN MD5(16MB)     : 1878211575d00cc90a951be7e93f138e
ROM Checksum(8MB) : 61C720A5
BIN Checksum(16MB): CB6BCB1E
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
M6D206D6_8000061D.PDB | Protein Data Bank format, Revision 0000061D | C-1,M-0 (Sandy Bridge-EP)
M6D206D7_00000714.PDB | Protein Data Bank format, Revision 00000714 | C-2,M-1 (Sandy Bridge-EP)
MED306E2_0000020D.PDB | Protein Data Bank format, Revision 0000020D | B-1, B-2, L-1, L-2, R-0, and R-1 (Ivy Bridge-EP)
MED306E3_00000308.PDB | Protein Data Bank format, Revision 00000308 | B-3 (Ivy Bridge-EP)
MED306E4_0000042D.PDB | Protein Data Bank format, Revision 0000042D | C-0, C-1, S-0, S-1, M-0, M-1 (Ivy Bridge-EP)

================================================================================
                        SYSTEM FIRMWARE REQUIREMENTS/REVISIONS
================================================================================
VGA (embedded in AST2300)  : 0.96
Patsburg SATA RAID         : v3.5.0.1005
Patsburg SCU               : v3.5.0.1005
Intel(R) I350 (Powerville) : IBA GE v1.3.81
Intel(R) X540 (Twinville)  : IBA XE v2.2.05
iSCSI                      : iSCSI Remote Boot v2.7.97
Intel(R) SPS F/W (ME)      : SPS_02.01.07.225.0
Intel(R) QPI and MRC       : 2.00.00.02
TXT ACM                    : PW 2.2
TXT SINIT                  : PW 2.2 
================================================================================
                        IMPORTANT INSTALLATION NOTES
================================================================================
WARNING:  
(1) It is very important to follow the flash option provided in the batch
    file (UPDATE.BAT / UP_ALL.BAT) to update BIOS under DOS environment. 
    Using incorrect flash option to flash BIOS may cause damage to your system.

1. Burn S2RSxxxx.BIN via fixture, or
2. Follow below steps to update whole image include ME firmware:
   (1) Copy AFUDOS.EXE, BIOS ROM (xxxx.ROM/xxxx.BIN) and UPDATE.BAT/UP_ALL.BAT batch file to 
       a HDD or USB Flash Drive with bootable DOS.
   (2) AC power off the system.
   (3) Insert the USB Flash Drive or HDD mentioned in step 1.
   (5) Power on the system and boot into the USB Flash Drive or HDD.
   (6) Execute UPDATE.BAT/UP_ALL.BAT.
   (7) After the update finished, AC power off the system.
   (9) Power on the system, the new BIOS runs.
   (10)First PO after BIOS update, please enter setup, press <F9> to load default and save before any test run.

Note: Update BIOS via AFUDOS utility with BIOS ROM file will NOT update SPS 
      firmware (ME firmware) and ME configuration.

================================================================================
                        KNOWN ISSUES/WORKAROUNDS
================================================================================
================================================================================
S2RS_4A05:
- Always configure S2RS CPU1 root port 2 as x8 x8 (Can't support GPU SKU).


================================================================================
                        FEATURES ADDED/MODIFY
================================================================================
S2RS_4B12:
- Base on Intel SRV_P_251 to update microcode.

S2RS_4B11:
- Base on Intel SRV_P_234 to update microcode.

S2RS_4B09:
- Remove AMI default key of secure boot function.

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
S2RS_4B12:
- N/A.

S2RS_4B11:
- N/A.

S2RS_4B09:
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
S2RS_4B12:
- N/A.

S2RS_4B11:
- N/A.

S2RS_4B09:
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