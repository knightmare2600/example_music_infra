*****************************************************

LSI Corporation SAS2 MPT UEFI BSD HII Driver Release

*****************************************************

====================== 
Supported Controllers:
======================
SAS2004  
SAS2008  
SAS2108
SAS2116
SAS2208
SAS2308


Component:
=========
Binary image name: ebcsas2.rom (for Flashing on EBC Compatible supported Platforms)
Binary image name: ebcsas2.efi (for Shell load test on EBC Compatible supported platforms)
Binary image name: x64sas2.rom (for Flashing on X64 platforms)
Binary image name: x64sas2.efi (for Shell load test on X64 platforms)

For all practical purposes use x64sas2.rom file.

Installation:
=============
Use SAS2Flash.efi to install the SAS2 BSD HII Driver binary.
The SAS2Flash utility is included in the package zip file.
UEFI version of SAS2Flash can be downloaded from the Support & Downloads section of www.lsi.com.

The command line installation instruction to flash the UEFI SAS2 BSD HII Driver is:

1. Run 'drivers' command under uefi shell
2. Locate the driver handles for existing SAS2 MPT Drivers
3. unload <dh>
where <dh> is the driver handle for already loaded driver.

4.sas2flash -c <n> -b ebcsas2.rom  (for EBC compatible supported platforms)
or
sas2flash -c <n> -b x64sas2.rom (for X64 platforms)

where <n> is the controller number (starting with zero (0)).

If you need further help, please contact the LSI FAE associated with your Organization.

Notes: 
1) UEFI BSD with or without HII does not require Legacy BIOS to be loaded on to the controller.
2) A latest Firmware either IR or IT version with proper NVData is required.
3) To load the images for testing under shell only:
a. load ebcsas2.efi
or
loadpcirom ebcsas2.rom
or
load pcirom x64sas2.rom


