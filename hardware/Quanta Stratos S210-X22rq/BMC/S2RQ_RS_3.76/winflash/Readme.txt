; ASPEED iRMP Windows SOC Flash Utility ReadME
;===============================================================================
1.Platform Requirement:
- Windows Environment
- M/B with PCI Slots
- Support ASPEED Chips
  >> AST1000/2000 A1 and after
  >> AST1100/2050/2100/2150/2200
  >> AST2300/1300/1050
  >> AST2400/1400
  >> AST2400/1400 + AST1070
  >> AST1010    
- Support O.S.
  >> Windows 2000
  >> Windows XP x86/x64
  >> Windows Server 2003 x86/x64
  >> Windows Server 2008 x86/x64
  >> Windows Server 2008 R2
  >> Windows Vista x86/x64
  >> Windows 7 x86/x64
  >> Windows 8 customer preview x86/x64
2.Release Package:
- The release package include the following stuffs:
  >> socflash: the execution file in command prompt
  >> x86/astio.sys: the x86 WDM driver  
  >> x64/astio.sys: the x64 WDM driver for Vista/Windows2008
  >> x64r2/astio.sys: the x64 WDM driver for Windows7/Server2008R2
- Please make sure the directories of x86 ,x64, x64r2 are the sub-directory of socflash    
3.Execute Flash Utility:
- Suggest to use the batch file the package provide (socflash.bat)
  >> Description: The batch file will check the O.S. to decide to launch 32/64bits program
  >> Usage: socflash.bat [command line options]
     ++ see item 4 & 5 to get detail
4.Flash Utility Usage (New Interface):
- Run in Command Prompt
- Format:
  >> socflash [operand]
     ++ operand list
     +++ if=the update file
     +++ of=the backup file
     +++ cs=chip select
     ++++ AST1000/2000: 0/1 (default: 0)
     ++++ AST1100/2050/2100: 0/1/2
     +++++ default: get from SCU trapping
     ++++++ if Boot Trapping is disabled, then set to 0 for AST2100, and 2 for others     
     +++ flashtype=flash chip type
     ++++ 0/1/2/3: NOR/NAND/SPI/SYS SPI
     +++++ SYS SPI: AST2400/1400/2300/1300/1050 only
     +++ width= NOR flash bus width
     ++++ 8/16: AST2400/1400/2300/1300/1050
     ++++ 8   : AST2100/2200
     ++++ 16  : AST2000
     +++ skip=the skip size in bytes at the start of input file (default=0)
     +++ offset=the offset in bytes at the start of the flash (default=0)
     +++ count=the size in bytes copy to the flash (default=the size of the flash)
     +++ backupcount=the size in bytes backup from the flash (default=the size of the flash)          
     +++ writeclk/readclk/eraseclk: SPI Write CLK/Read CLK/EraseCLK
     ++++ writeclk=50	; The Max. SPI Write CLK is 50MHz     
     +++ gpio_b/gpio_f=set gpio before/after flash update program execute
     ++++ support chips: AST1100/2050/2100/2150/2200/1300/2300/1400/2400
     ++++ limitation: max. gpio set: 10     
     ++++ format:[port+pin+data ....]
     ++++ example: gpio_b=c41a71 means set GPIO C4 to 1, A7 to 1 before program execute
     ++++ example: gpio_f=c40a70 means set GPIO C4 to 0, A7 to 0 after program execute
     +++ reginit_b/reginit_f=Reg. Table File
     ++++ set ARM interface reg. before/after flash update
     ++++ command example: reginit_b=reginit.inf
     ++++ reg. file format: [addr] [mask] [data]
     +++++ ex: 0x1e6e2000 0x00000000 0x1688a8a8	; write 0x1688a8a8 to 0x1e6e2000     
     +++++ notes: skip the command if add ";" at the first of the line               
     +++ option=f|c|2|r|d|x|l|i|m
     ++++ f: skip the comparision of flash data and force to update
     ++++ c: use chip erase instead of sector erase 
     ++++ r: reset scratch  
     ++++ d: disable ARM after update flash        
     ++++ 2: two flash update support
     +++++ AST1100/2050/2100: two SPI solution: 1st SPI is on CS2; 2nd SPI is on CS0 
     +++++ AST2000: two NOR Flash Solution: 1st Flash is on CS0; 2nd Flash is on CS1
     ++++ x: low speed mode (SPI only)
     +++++ use this option if can' find SPI flash or update properly in normal mode     
     ++++ l: Update firmware through LPC path 
     +++++ AST2400/1400/2300/1300/1050 only     
     ++++ i: Update Firmware Image to Flash only if Image and Flash Size are the same
     ++++ m: Update firmware through co-processor 
     +++++ AST2400/1400 + AST1070 only                                     
  >> example:
     ++ socflash if=new.bin of=old.bin option=f
     +++ update the firmware image to new.bin
     +++ bacup the old firmware to old.bin
     +++ force to update without comparision
5.Flash Utility Usage (Legacy Interface):
- Run in Command Prompt
- Format:  
  >> Normal: SOCFlash [the update soc file*] [the backup file*] [Chip Select] [Flash Type] [Start Offset] [Programming Size]
  >> Backup Only: SOCFlash -b [the backup file*] [Chip Select] [Flash Type] [Start Offset] [Programming Size]
  >> Skip Backup: SOCFlash -s [the update soc file*] [Chip Select] [Flash Type] [Start Offset] [Programming Size]
     ++ The fields add * means must have
- Options:  
  >> Chip Select:
     ++ AST1000/2000: 0/1 (default: 0)
     ++ AST1100/2050/2100: 0/1/2
     +++ default: get from SCU trapping
     ++++ if Boot Trapping is disabled, then set to 0 for AST2100, and 2 for others     
  >> Flash Type: (AST1100/2050/2100)
     ++ 0/1/2: NOR/NAND/SPI   
  >> Start Offset: start offset from image file (default: 0x0)
  >> Programming Size: The size need to program to Flash
- Example: socflash all.bin old.bin
6.Return Code:
- 0: success
- 1: failed
7.Support Flash Chip List:
- NOR:
  >> MXIC MX29LV640DT, MX29GL128E, MX29GL128DT/B, MX29GL256E
  >> Spansion S29xx064MxxR4, S29GL128Nx8, S29GL256Nx8
  >> SST 39VF640
  >> ST STM29W640F, M20EW256M, M29W256G, M29W640G
- NAND:
  >> Micron MT29F2G08
  >> Samsung K9F1G08U0A
- SPI:
  >> Spansion S25FL64A, S25FL128P, S25FL128S
  >> SST 25VF016B, 25VF064C
  >> ST M65P64, M25P128 
  >> Winbond W25X16, W25X32, W25X64, W25Q16V, W25Q32BV, W25Q64BV, W25Q128BV 
  >> MXIC MX25L12805D, MX25l2005C, MX25L3205D, MX25L6445E
  >> Numonyx N25Q128
  >> ATMEL AT26DF321, AT25DF321, AT25DF161     
  >> [AST2300/2400] Spansion S25FL256S            
  >> [AST2300/2400] Winbond 25Q256FV
  >> [AST2300/2400] MXIC MX25L25635E/F, MX25L25735E, MX66L512
  >> [AST2300/2400] Numonyx N25Q256, N25Q512                                            
8.FAQ
- The program cannot run properly though LPC path
  >> Root Cause: the previous WDM driver did not clear registry properly
  >> Phenomenon:
  +++ show "Cannot Load Windows WDM Driver Properly"
  +++ show "Can't Get LPC Inforamtion"
  >> Solution:
  +++ run "registry_clean.reg"
  +++ reboot system and re-run it
- The program can't run under x64 environment
  >> Possible reason: WOW64 didn't be included in the execution environment
  >> Solution:
  +++ M1: use batch file
  +++ M2: run x64 program (socflash_x64.exe) directly
- SOCFlash through LPC Path: AST1010/1050/1250
  >> add "option=l"
- SOCFlash through co-precessor: AST2400/1400 + AST1070
  >> add "option=m"          
- New support chips from v.0.96
  >> MXIC MX29GL128E, MX29GL256E
  >> SST 39VF640
  >> ST M20EW256M, M29W256G 
- New support chips from v.0.97
  >> ST M29W640G 
- New support chips from v.0.98
  >> SST 25VF064C 
- New support chips from v.1.02
  >> MXIC MX29GL128DT/B 
  >> Winbond W25Q64BV, W25Q128BV 
  >> Numonyx N25Q128  
- New support chips from v.1.03
  >> Winbond W25Q16V, W25Q32BV, W25X32
  >> ATMEL AT26DF321, AT25DF321
  >> MXIC MX25L3205D, MX25L6445E, MX25L25635E(AST2300), MX25L25735E(AST2300)
- New support chips from v.1.05
  >> Spansion S29GL064 8-bits mode for AST1300/2100/2150/2200/2300 
- New support chips from v.1.06
  >> Support Numonyx N25Q256, Spansion S25FL256S on AST1050/1300/2300
- New support chips from v.1.07
  >> Numonyx N25Q512 on AST1050/1300/2300
  >> MXIC MX25L25635F on AST1050/1300/2300 
  >> ATMEL AT25DF161 
  >> Winbond 25Q256FV 
- New support chips from v.1.08
  >> Spansion S25FL128/256S 256KB sector size
  >> MXIC MX66L512                       
9.Contact Window:
- yc_chen@aspeedtech.com
- 886.3.578.9568 ext. 810
