#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Create a public fatal selector control from each clean build independently."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from media import compose

ROOT=Path(__file__).resolve().parents[2]


def identity(data):return {'size':len(data),'sha256':hashlib.sha256(data).hexdigest()}


def fatal_kernel(kernel,symbols):
    if kernel[:2]!=b'MZ' or len(kernel)<28:raise ValueError('invalid kernel container')
    header=struct.unpack_from('<H',kernel,8)[0]*16
    matches=[r for r in symbols['symbols'] if r['name']=='pc88va_m10_control_']
    if len(matches)!=1:raise ValueError('ambiguous fatal selector')
    segment,offset=(int(x,16) for x in matches[0]['address'].split(':'))
    position=header+segment*16+offset
    if not header<=position<len(kernel) or kernel[position]!=0:raise ValueError('invalid fatal selector binding')
    result=bytearray(kernel);result[position]=1
    return bytes(result),position


def build(run,output):
    source=run/'media';kernel=(source/'kernel_sys.artifact').read_bytes()
    symbols=json.loads((run/'kernel-evidence/symbol-evidence.json').read_text())
    control,offset=fatal_kernel(kernel,symbols)
    accepted=json.loads((ROOT/'qa/golden/m09/manifest.json').read_text())['artifacts']
    records=[]
    for name,key,epoch in (('KERNEL.SYS','kernel_sys',1787814827),('COMMAND.COM','extracted_command_com',1740233872),('COUNTRY.SYS','extracted_country_sys',1779123341)):
        data=control if name=='KERNEL.SYS' else (source/(key+'.artifact')).read_bytes()
        records.append({'dos_name':name,'data':data,**identity(data),'source_date_epoch':epoch})
    stage1=(source/'loader_stage1.artifact').read_bytes();stage2=(source/'loader_stage2.artifact').read_bytes()
    raw,d88,composition=compose(json.loads((ROOT/'config/m05/media.json').read_text()),records,stage2,
                                lambda extent:stage1,{510:False,1022:False},accepted)
    artifacts={'fatal_kernel_sys':control,'fatal_raw_media':raw,'fatal_d88_media':d88}
    for name,data in artifacts.items():
        baseline=(source/({'fatal_kernel_sys':'kernel_sys','fatal_raw_media':'raw_media','fatal_d88_media':'d88_media'}[name]+'.artifact')).read_bytes()
        if len(data)!=len(baseline) or sum(a!=b for a,b in zip(data,baseline))!=1:
            raise ValueError('fatal control changes more than its selector byte')
    output.mkdir(parents=True,exist_ok=False)
    for name,data in artifacts.items():(output/(name+'.artifact')).write_bytes(data)
    return {'schema_version':1,'baseline_kernel':identity(kernel),'selector_file_offset':offset,
            'selector_before':0,'selector_after':1,'changed_bytes_per_artifact':1,
            'artifacts':{name:identity(data) for name,data in artifacts.items()},
            'independent_extraction_verified':composition['payloads_verified'],
            'loader_stages_unchanged':True}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('build_root',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    first=build(args.build_root/'run-1',args.build_root/'fatal-1')
    second=build(args.build_root/'run-2',args.build_root/'fatal-2')
    if first!=second:raise ValueError('fatal control manifests differ')
    for p in (args.build_root/'fatal-1').iterdir():
        if p.read_bytes()!=(args.build_root/'fatal-2'/p.name).read_bytes():raise ValueError('fatal controls differ')
    first['two_clean_controls_equal']=True
    with args.output.open('x') as f:json.dump(first,f,sort_keys=True,indent=2);f.write('\n')
    print('Two public fatal controls matched; exactly one selector byte differs in each kernel and medium')


if __name__=='__main__':main()
