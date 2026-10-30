#!/bin/bash
# usage: qm-copyspec.sh <src_vmid> <dst_vmid> <new_name>
set -euo pipefail
SRC=$1; DST=$2; NAME=$3
C=/etc/pve/qemu-server
[ -e "$C/$DST.conf" ] && { echo "VM $DST already exists"; exit 1; }

# main section only (drop snapshot sections)
TMP=$(mktemp); awk '/^\[/{exit} {print}' "$C/$SRC.conf" > "$TMP"

DISKRE='^((ide|sata|scsi|virtio)[0-9]+|efidisk0|tpmstate0):'
{
  grep -Ev "$DISKRE|^(unused[0-9]+|vmgenid|smbios1|parent|name|lock|net[0-9]+):" "$TMP" || true
  grep -E '^(ide|sata|scsi)[0-9]+:.*media=cdrom' "$TMP" || true
} > "$C/$DST.conf"

qm set "$DST" --name "$NAME" --vmgenid 1 --smbios1 "uuid=$(cat /proc/sys/kernel/random/uuid)"

# NICs: drop MAC so PVE generates a new one
grep -E '^net[0-9]+:' "$TMP" | while read -r line; do
  k=${line%%:*}; v=${line#*: }
  qm set "$DST" --"$k" "$(sed -E 's/=([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}//' <<<"$v")"
done

# Disks: new empty volume, same storage/size/options
grep -E "$DISKRE" "$TMP" | grep -v 'media=cdrom' | while read -r line; do
  k=${line%%:*}; v=${line#*: }
  vol=${v%%,*}; store=${vol%%:*}
  opts=$(sed -E 's/^[^,]*,?//; s/(^|,)size=[^,]*//; s/^,//' <<<"$v")
  case $k in
    efidisk0|tpmstate0) size=1 ;;
    *) s=$(grep -oP 'size=\K[0-9]+[GT]' <<<"$v")
       [[ $s == *T ]] && size=$(( ${s%T} * 1024 )) || size=${s%G} ;;
  esac
  qm set "$DST" --"$k" "$store:$size${opts:+,$opts}"
done

rm -f "$TMP"
qm config "$DST"
