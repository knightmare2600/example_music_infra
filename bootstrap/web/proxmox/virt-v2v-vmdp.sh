#!/bin/bash

#SOURCE=${BASH_SOURCE[0]}
#SCRIPTDIR=$(dirname "$0")
BASENAME=$(basename "$0")
SCRIPTDIR="$( cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
BASEDIR=$(dirname $SCRIPTDIR)
VWIN=/usr/share/virtio-win

if test "$1" = ""
then
    echo "usage: $BASENAME <base_file_name e.g VMDP-WIN-2.5.4.3>"
    exit 1
fi

mkdir -p /usr/share/virt-tools
cp -p $BASEDIR/Server2016-19-Win10/x86/pvvxsvc.exe /usr/share/virt-tools

rm -rf $VWIN/drivers
mkdir -p $VWIN
cp -p $SCRIPTDIR/$1_virtio_win.tar.gz $VWIN

cd $VWIN
tar -xzvf $1_virtio_win.tar.gz
mv $1/drivers .
cp -p $BASEDIR/$1.*exe /usr/share/virt-tools/vmdp.exe
rmdir $1
rm $1_virtio_win.tar.gz

cd drivers
for i in */ ; do
    cd $i
    for d in */ ; do
        cd $d

        touch balloon.sys
        touch balloon.inf
        touch balloon.cat

        touch fwcfg.sys
        touch fwcfg.inf
        touch fwcfg.cat

        touch pvpanic.sys
        touch pvpanic.inf
        touch pvpanic.cat

        touch viorng.sys
        touch viorng.inf
        touch viorng.cat

        touch vioser.sys
        touch vioser.inf
        touch vioser.cat

        touch virtio_net.sys
        touch virtio_net.inf
        touch virtio_net.cat

        cd ..
    done
    cd ..
done

# Map server versions on client ones
# Note: There is no 32bits servers after 2008

ln -s Win8 $VWIN/drivers/amd64/Win2012
ln -s Win8.1 $VWIN/drivers/amd64/Win2012r2
ln -s Win10 $VWIN/drivers/amd64/Win2016
ln -s Win10 $VWIN/drivers/amd64/Win2019
ln -s Win11 $VWIN/drivers/amd64/Win2022
ln -s Win11 $VWIN/drivers/amd64/Win2025
