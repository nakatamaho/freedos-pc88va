# SPDX-License-Identifier: GPL-2.0-or-later
"""M10 FAT allocation reserves the accepted loader extent before payloads.

No loader source or byte is changed. Independent M05 parsing verifies the
result, including fragmented chains and unused-space ownership.
"""
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'m05'))
from common import ValidationError, derive_layout, sha256_bytes
from build_media import build_boot_record, build_directory_entry, set_fat12_entry, build_d88
from inspect_media import inspect_raw, validate_d88_round_trip


def compose(spec, records, stage2, stage1_factory, signatures, accepted):
    if [r['dos_name'] for r in records]!=['KERNEL.SYS','COMMAND.COM','COUNTRY.SYS']:
        raise ValidationError('M10 payload order or set differs')
    if not isinstance(stage2,bytes) or not stage2:
        raise ValidationError('stage two absent')
    if set(signatures)!={510,1022} or any(type(v) is not bool for v in signatures.values()):
        raise ValidationError('signature contract incomplete')
    derived=derive_layout(spec)
    fs=spec['filesystem']; bps=spec['geometry']['bytes_per_sector']
    if bps!=1024 or fs['sectors_per_cluster']!=1:
        raise ValidationError('unsupported bootstrap geometry')
    # This extent is derived only from the accepted public artifact sizes.
    first=2+sum((accepted[k]['size']+bps-1)//bps for k in
                ('kernel_sys','extracted_command_com','extracted_country_sys'))
    count=(len(stage2)+bps-1)//bps
    loader=list(range(first,first+count))
    if loader[-1]>derived['data_clusters']+1:
        raise ValidationError('loader extent exceeds medium')
    available=iter(c for c in range(2,derived['data_clusters']+2) if c not in loader)
    all_records=records+[{'dos_name':'LOADER.BIN','data':stage2,'size':len(stage2),
                         'sha256':sha256_bytes(stage2),'source_date_epoch':records[0]['source_date_epoch']}]
    image=bytearray(derived['total_bytes']); image[:bps]=build_boot_record(spec)
    fat=bytearray(derived['fat_capacity_bytes'])
    set_fat12_entry(fat,0,0xf00|fs['media_descriptor']);set_fat12_entry(fat,1,0xfff)
    directory=bytearray(derived['root_directory_sectors']*bps)
    allocations=[]
    for index,record in enumerate(all_records):
        data=record['data']
        if not data or len(data)!=record['size'] or sha256_bytes(data)!=record['sha256']:
            raise ValidationError('payload binding differs')
        needed=(len(data)+bps-1)//bps
        try:chain=loader if index==3 else [next(available) for _ in range(needed)]
        except StopIteration:raise ValidationError('payload exceeds medium') from None
        for position,cluster in enumerate(chain):
            set_fat12_entry(fat,cluster,chain[position+1] if position+1<len(chain) else 0xfff)
            offset=(derived['first_data_sector']+cluster-2)*bps
            chunk=data[position*bps:(position+1)*bps]
            image[offset:offset+len(chunk)]=chunk
        entry,timestamp=build_directory_entry(record,chain[0])
        directory[index*32:(index+1)*32]=entry
        allocations.append({'dos_name':record['dos_name'],'clusters':chain,'first_cluster':chain[0],
            'size':record['size'],'sha256':record['sha256'],'source_date_epoch':record['source_date_epoch'],
            'fat_timestamp':timestamp})
    fat_lba=fs['reserved_sectors']
    for index in range(2):
        start=(fat_lba+index*fs['sectors_per_fat'])*bps
        image[start:start+len(fat)]=fat
    start=(fat_lba+2*fs['sectors_per_fat'])*bps
    image[start:start+len(directory)]=directory
    _,extracted=inspect_raw(bytes(image),spec,derived,all_records)
    if extracted!={r['dos_name']:r['data'] for r in all_records}:
        raise ValidationError('independent payload extraction differs')
    extent={'first_lba':derived['first_data_sector']+first-2,'sector_count':count,'file_size':len(stage2)}
    boot=bytearray(stage1_factory(extent))
    if len(boot)!=bps or boot[:3]!=b'\xeb\x3c\x90' or any(boot[3:62]) or boot[510:512]!=bytes(2) or boot[1022:]!=bytes(2):
        raise ValidationError('bootstrap field ownership differs')
    boot[3:62]=image[3:62]
    for offset,enabled in signatures.items():boot[offset:offset+2]=b'\x55\xaa' if enabled else bytes(2)
    raw=bytes(boot)+bytes(image[bps:])
    _,checked=inspect_raw(build_boot_record(spec)+raw[bps:],spec,derived,all_records)
    if checked!=extracted:raise ValidationError('bootstrap changed payloads')
    d88=build_d88(spec,raw)
    validate_d88_round_trip(d88,raw,spec,derived)
    return raw,d88,{'stage2_extent':extent,'allocations':allocations,
                   'raw_sha256':sha256_bytes(raw),'d88_sha256':sha256_bytes(d88),
                   'bootstrap_sha256':sha256_bytes(bytes(boot)),
                   'payloads_verified':True,'round_trip_byte_identical':True}
