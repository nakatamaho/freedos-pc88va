#!/bin/sh
# SPDX-License-Identifier: GPL-2.0-or-later
# Run inside the pinned amd64 build container on an exported source tree.
set -eu
test "$#" -eq 4 || { echo 'usage: build_block_probe.sh CHILD_EXPORT FIXTURES GEOMETRY_JSON OUTPUT' >&2; exit 2; }
child=$1
fixtures=$2
geometry=$3
output=$4
test "$(uname -m)" = x86_64
test -x /opt/openwatcom-1.9/binl/wlink
test ! -e "$child/.git"
test ! -e "$output"
mkdir -p "$output"
output=$(cd "$output" && pwd)
cd "$child/pc88va"
# Read public fixture geometry, not an image-size guess or private input.
definitions=$(python3 -c 'import json,sys; g=json.load(open(sys.argv[1]))["geometry"]; print(" ".join("-DM14_"+k.upper()+"="+str(g[k]) for k in ("bytes_per_sector", "sectors_per_track", "heads", "total_sectors")))' "$geometry")
definitions=$(printf '%s' "$definitions" | sed 's/M14_BYTES_PER_SECTOR/M14_SECTOR_BYTES/g; s/M14_SECTORS_PER_TRACK/M14_SECTORS_TRACK/g')
for name in m13_platform resident_disk machine_services; do
    nasm -f obj -DPC88VA -DPC88VA_M13 -DWATCOM -DXCPU=86 \
        -i../hdr/ -i../kernel/ -iboot/ -o "$output/$name.obj" "kernel/$name.asm"
done
for variant in 0 1 protect missing partial; do
    restore=$variant
    error_definition=
    case "$variant" in
        protect) restore=1; error_definition=-DM14_ERROR_STATUS=3 ;;
        missing) restore=1; error_definition=-DM14_ERROR_STATUS=128 ;;
        partial) restore=1; error_definition='-DM14_ERROR_STATUS=5 -DM14_PARTIAL=1' ;;
    esac
    nasm -f obj -DPC88VA -DPC88VA_M13 -DM14_RESTORE="$restore" $definitions $error_definition \
        -o "$output/probe-$variant.obj" "$fixtures/m14_block_boot.asm"
    /opt/openwatcom-1.9/binl/wlink system dos option quiet \
        option "map=$output/probe-$variant.map" \
        name "$output/probe-$variant.exe" \
        file "$output/probe-$variant.obj,$output/m13_platform.obj,$output/resident_disk.obj,$output/machine_services.obj"
    python3 -c 'import struct,sys; d=open(sys.argv[1],"rb").read(); h=struct.unpack_from("<14H",d); body=len(d)-h[4]*16; extent=((body+15)//16+h[5])*16; assert h[8]==4096 and h[7]*16>=body; assert h[7]*16+4096<=0xfbfe; assert extent>=0x10002; assert extent-body<=65535' "$output/probe-$variant.exe"
done
