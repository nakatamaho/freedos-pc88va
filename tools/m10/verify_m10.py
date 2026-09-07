#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Shared local/native-CI M10 gate. Live publication is a separate final gate."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/qa'))
sys.path.insert(0,str(ROOT/'tools/m09'))
import milestone_acceptance as gate
from record_public_builds import record,identity
from build_controls import fatal_kernel
privacy_spec=importlib.util.spec_from_file_location('m10_privacy',ROOT/'tools/m10/privacy_guard.py')
privacy=importlib.util.module_from_spec(privacy_spec);privacy_spec.loader.exec_module(privacy)
audit=privacy.audit

START='6b29d4f9b2b732ced9bc25a9b33b453877cbd7f0'
CHILD='54c067af9764ace07459b0c2f5df4f70294d0c50'
SCHEMAS={
 'artifact-manifest':'5eb5ac7c26e2fe9699a4eb73d2a7ce1f011328ad316202e35c4872f1b6888bf6',
 'components':'fdcb4f61ebd1fd3b875788f3ac943fb11dec1d05fe37685203a7e560b9477d38',
 'fatal-controls':'6f67badd96eca3ab1803834093df5ea9146e04f046ac15685dc56b33d12fbd46',
 'machine-contract':'914d28530f4250d7558f27b703b7c981e58095dd3108263740b825e58ee6ac07',
 'build-records':'b22c7c7aceeff6e2861f06e3dc5d80ccb32d12d58a9422ec058ea96d8ab772f4',
 'public-qualification':'72d4ae08c969baf2615fcf6d6bd53eb873a1be25b490dfb1e2db4e4f25fbdb48',
 'services':'f862f67cd352080ef5e95a0cd8cbbf18dda4381a56b84ac2bd8fe84c96e510c5'}


def read(path):return gate.json_value(path.read_text())


def content(root=ROOT):
    for name,sha in SCHEMAS.items():
        gate.bound_bytes(root,{'path':'schema/m10-'+name+'.schema.json','sha256':sha})
    contract=read(root/'config/m10/machine-contract.json')
    gate.validate_instance(read(root/'schema/m10-machine-contract.schema.json'),contract)
    known={}
    instances=[]
    def bind(ref):
        data=gate.bound_bytes(root,ref)
        gate.require(ref['path'] not in known or known[ref['path']]==ref['sha256'],'AMBIGUOUS_BINDING')
        known[ref['path']]=ref['sha256']
        return data
    for ref in contract['pins']:bind(ref)
    for pair in contract['instances']:
        schema=gate.json_value(bind(pair['schema']));value=gate.json_value(bind(pair['record']))
        gate.validate_instance(schema,value);instances.append(value)
    def closure(value):
        if isinstance(value,dict):
            if 'path' in value and 'sha256' in value:
                gate.require(known.get(value['path'])==value['sha256'],'INCOMPLETE_EVIDENCE_BINDING')
            for v in value.values():closure(v)
        elif isinstance(value,list):
            for v in value:closure(v)
    for value in instances:closure(value)
    lock=read(root/'manifests/m10-components.lock.json')
    manifest=read(root/'qa/golden/m10/manifest.json')
    fatal=read(root/'qa/golden/m10/fatal-controls.json')
    qualification=read(root/'config/m10/vaeg-qualification.json')
    gate.require(manifest['source']['commit']==qualification['child_commit']==lock['components'][0]['commit']==CHILD,'CHILD_BINDING_DRIFT')
    gate.require(manifest['source']['archive_sha256']==lock['components'][0]['source_archive_sha256'],'ARCHIVE_BINDING_DRIFT')
    gate.require(fatal['baseline_kernel']=={k:manifest['artifacts']['kernel_sys'][k] for k in ('size','sha256')},'FATAL_BASELINE_DRIFT')
    m09=read(root/'qa/golden/m09/manifest.json')
    for name in ('loader_stage1','loader_stage2','extracted_command_com','extracted_country_sys'):
        gate.require(manifest['artifacts'][name]==m09['artifacts'][name],'ACCEPTED_PAYLOAD_DRIFT')
    return contract


def sources(root=ROOT):
    for component in read(root/'manifests/m10-components.lock.json')['components']:
        path=root/component['path'];sha=component['commit']
        gate.require(gate.git(path,'rev-parse','HEAD')==sha,'COMPONENT_HEAD_DRIFT')
        gate.require(gate.git(root,'ls-files','--stage',component['path']).split()[:2]==['160000',sha],'COMPONENT_GITLINK_DRIFT')
        gate.require(not gate.git(path,'status','--porcelain','--untracked-files=all'),'DIRTY_COMPONENT')
        if component['source_archive_sha256']:
            data=subprocess.check_output(['git','-C',str(path),'archive','--format=tar','--prefix=fdkernel/',sha])
            gate.require(hashlib.sha256(data).hexdigest()==component['source_archive_sha256'],'SOURCE_ARCHIVE_DRIFT')
    child=root/'components/fdkernel'
    gate.require(not gate.git(child,'diff','ef46a7ad4b381cf7a301899bee00fec99f5e37a7',CHILD,'--',
                             'pc88va/boot','pc88va/kernel/console.asm','pc88va/config/console-contract.json'),'LOADER_CONSOLE_SOURCE_DRIFT')
    for path in ('config/m09','schema/m09-artifact-manifest.schema.json','schema/m09-public-qualification.schema.json',
                 'qa/golden/m09','manifests/m09-components.lock.json','tools/m09'):
        gate.require(not gate.git(root,'diff',START,'--',path),'M09_ACCEPTED_RECORD_DRIFT')


def generated(build,root=ROOT):
    gate.require(record(build)==read(root/'qa/golden/m10/manifest.json'),'GENERATED_MAIN_DRIFT')
    golden=read(root/'qa/golden/m10/fatal-controls.json')
    images=[]
    for n in (1,2):
        run=build/('run-'+str(n))
        records={name:read(run/'kernel-evidence'/(name+'.json')) for name in
                 ('compile-manifest','kernel-interface','symbol-evidence','build-evidence')}
        records['composition']=read(run/'media/rebuilt-manifest.json')
        gate.validate_instance(read(root/'schema/m10-build-records.schema.json'),records)
        compile_record=records['compile-manifest']
        for obj in compile_record['objects']:
            gate.require(identity(run/'objects'/Path(obj['object']).name)=={k:obj[k] for k in ('size','sha256')},'OBJECT_BINDING_DRIFT')
            for ref in obj['source_inputs']:gate.bound_bytes(root/'components/fdkernel',ref,True)
        for ref in compile_record['libraries']:
            gate.require(identity(run/'objects'/Path(ref['path']).name)=={k:ref[k] for k in ('size','sha256')},'LIBRARY_BINDING_DRIFT')
        gate.bound_bytes(root/'components/fdkernel',{k:compile_record['link_response'][k] for k in ('path','size','sha256')},True)
        evidence=records['build-evidence'];child=root/'components/fdkernel/pc88va'
        for key,file in (('build_plan_sha256','config/build-plan.json'),('stub_ledger_sha256','config/stubs.json')):
            gate.require(identity(child/file)['sha256']==evidence[key],'BUILD_SOURCE_RECORD_DRIFT')
        for key,file in (('compile_manifest_sha256','compile-manifest.json'),('kernel_interface_sha256','kernel-interface.json'),('symbol_evidence_sha256','symbol-evidence.json')):
            gate.require(identity(run/'kernel-evidence'/file)['sha256']==evidence[key],'BUILD_RECORD_BINDING_DRIFT')
        gate.require(evidence['stub_count']==2,'STUB_SCOPE_DRIFT')
        for ref in (evidence['artifact'],evidence['alias'],records['kernel-interface']['artifact']):
            gate.require({k:ref[k] for k in ('size','sha256')}==identity(run/'media/kernel_sys.artifact'),'KERNEL_RECORD_BINDING_DRIFT')
        kernel=(run/'media/kernel_sys.artifact').read_bytes()
        control,offset=fatal_kernel(kernel,read(run/'kernel-evidence/symbol-evidence.json'))
        gate.require(offset==golden['selector_file_offset'],'SELECTOR_OFFSET_DRIFT')
        for name,expected in golden['artifacts'].items():
            path=build/('fatal-'+str(n))/(name+'.artifact')
            gate.require(identity(path)==expected,'GENERATED_FATAL_DRIFT')
        gate.require(control==(build/('fatal-'+str(n))/'fatal_kernel_sys.artifact').read_bytes(),'SELECTOR_CONTENT_DRIFT')
        containers=read(build/('container-'+str(n)+'.json'));images.append(read(build/('image-'+str(n)+'.json'))[0])
        gate.require(len(containers)==1,'CONTAINER_IDENTITY_MISSING')
        c=containers[0]
        gate.require(c['HostConfig']['NetworkMode']=='none' and not c['Mounts'] and not c['HostConfig']['Binds'],'BUILD_ISOLATION_DRIFT')
        gate.require(images[-1]['Architecture']=='amd64' and images[-1]['Os']=='linux' and c['Image']==images[-1]['Id'],'BUILD_PLATFORM_DRIFT')
        gate.require('WATCOM=/opt/openwatcom-1.9' in c['Config']['Env'],'TOOLCHAIN_DRIFT')
    gate.require(images[0]['Id']==images[1]['Id'],'BUILD_IMAGE_DRIFT')


def execute(root,command):subprocess.run(command,cwd=root,check=True)


def accept(build,root=ROOT):
    contract=content(root);sources(root);generated(build,root)
    claim=dict(contract['child_ci'],manifest={})
    endpoint='repos/'+claim['repository']+'/actions/runs/'+str(claim['run_id'])
    run=json.loads(subprocess.check_output(['gh','api',endpoint]))
    pages=json.loads(subprocess.check_output(['gh','api','--paginate','--slurp',endpoint+'/attempts/'+str(claim['attempt'])+'/jobs?per_page=100']))
    gate.verify_ci_claim(claim,run,[j for p in pages for j in p['jobs']])
    execute(root,[sys.executable,'-B','tools/m10/preflight.py'])
    for folder,pattern in (('tests/qa','test_milestone_acceptance.py'),('tests/m10','test_*.py')):
        execute(root,[sys.executable,'-B','-m','unittest','discover','-s',folder,'-p',pattern])
    # Native CI executes the same instructions directly. macOS uses the identical
    # pinned wheel in the isolated Linux adapter, not its unsupported host JIT.
    if sys.platform=='darwin':
        import os
        wheel=os.environ.get('M10_UNICORN_WHEEL')
        gate.require(bool(wheel),'LINUX_INSTRUCTION_WHEEL_REQUIRED')
        execute(root,['bash','tools/m10/instruction_tests.sh',wheel])
    else:
        execute(root,[sys.executable,'-B','-m','unittest','discover','-s','components/fdkernel/pc88va/tests','-p','test_*.py'])
    execute(root,['make','verify-scaffold','m04r1-license-verify','m04-verify'])
    execute(root,[sys.executable,'-B','tools/m10/historical.py'])
    audit(root,START)
    print('M10 public acceptance gates passed; private qualification is attested, not executed in public CI')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-root',type=Path)
    parser.add_argument('--accept',action='store_true')
    args=parser.parse_args()
    try:
        if args.accept:
            gate.require(args.build_root is not None,'CLEAN_BUILD_PAIR_REQUIRED');accept(args.build_root.resolve())
        else:
            content();sources()
            if args.build_root:generated(args.build_root.resolve())
            print('M10 public schemas, actual instances, closed bindings and source identities valid')
    except (ValueError,OSError,KeyError,TypeError,subprocess.CalledProcessError) as e:
        print(str(e) if isinstance(e,gate.Rejected) else 'M10_PUBLIC_GATE_REJECTED');return 1
    return 0


if __name__=='__main__':raise SystemExit(main())
