#!/bin/sh
cd linuxflash
res=`service ipmi status`
echo $res | grep 'not' >> /dev/null;
ipmi_status=$? # start:1 ; stop:0
if [ $ipmi_status -eq 1 ]; then
	printf  "############################## caution ##############################\n"
	printf  "Avoid KCS communication fail...\n"
	printf  "Before update BMC firmware, this shell script will stop ipmi service automatically\n"
	printf  "#####################################################################\n"
	res=`service ipmi stop`	
fi


./socflash.sh -s ../rom.ima


if [ $ipmi_status -eq 1 ]; then
	printf  "############################## caution ##############################\n"
	printf  "Wait for BMC ready, then start ipmi service...\n"
	printf  "#####################################################################\n"
	echo "Waiting..."
	sleep 65	
	printf  "############################## caution ##############################\n"
	res=`service ipmi start`
	printf  "ipmi service start now !!!\n"
	printf  "#####################################################################\n"	
fi
