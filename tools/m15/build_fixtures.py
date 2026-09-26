#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Build original 8086 COM fixtures twice from an isolated source export."""
import argparse,hashlib,io,json,subprocess,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def digest(data):return hashlib.sha256(data).hexdigest()
def call(*args):return subprocess.check_output(args)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--image',default='freedos-pc88va-m01:local');args=p.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
 image=json.loads(call('docker','image','inspect',args.image))[0];assert image['Architecture']=='amd64' and image['Os']=='linux'
 source=ROOT/'tests/m15/fixtures';paths=sorted(source.glob('*'));identities={}
 with tarfile.open(out/'inputs.tar','w') as t:
  for f in paths:
   assert f.suffix in ('.asm','.inc','.bat','.txt','.json');data=f.read_bytes();identities[f.name]=digest(data);i=tarfile.TarInfo(f.name);i.size=len(data);i.mode=0o644;i.mtime=1787814827;t.addfile(i,io.BytesIO(data))
 command='''set -eu
test "$(uname -m)" = x86_64
test "$(dpkg --print-architecture)" = amd64
mkdir -p /work /work/result
tar -xf /tmp/inputs.tar -C /work
cd /work
nasm -v > /work/result/assembler.txt
for file in *.asm; do
 name=${file%.asm}
 nasm -f bin -I /work/ -l /work/result/$name.lst "$file" -o /work/result/$name.com
done
'''
 results=[]
 for number in (1,2):
  cid=call('docker','create','--platform','linux/amd64','--network','none','--entrypoint','bash',image['Id'],'-ec',command).decode().strip();record={'container':cid,'image':image['Id'],'command':command,'inputs':identities};(out/f'build-{number}.json').write_text(json.dumps(record,indent=2)+'\n');subprocess.run(['docker','cp',str(out/'inputs.tar'),cid+':/tmp/inputs.tar'],check=True)
  with (out/f'build-{number}.log').open('xb') as h:rc=subprocess.run(['docker','start','-a',cid],stdout=h,stderr=subprocess.STDOUT).returncode
  final=json.loads(call('docker','inspect',cid))[0];(out/f'container-{number}.json').write_text(json.dumps(final,indent=2)+'\n');assert rc==0 and final['State']['ExitCode']==0
  target=out/f'run-{number}';subprocess.run(['docker','cp',cid+':/work/result',str(target)],check=True);results.append({f.name:{'size':f.stat().st_size,'sha256':digest(f.read_bytes())} for f in sorted(target.glob('*.com'))});subprocess.run(['docker','rm',cid],check=True,stdout=subprocess.DEVNULL)
 assert results[0] and results[0]==results[1];(out/'comparison.json').write_text(json.dumps({'inputs':identities,'image':image['Id'],'artifacts':results[0],'two_builds_equal':True},indent=2)+'\n');print('Original guest fixture pairs are byte-identical')
if __name__=='__main__':main()
