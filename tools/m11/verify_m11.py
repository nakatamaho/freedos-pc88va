#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Fail-closed M11 public verifier; private runtime records stay local."""
import argparse, hashlib, json, re, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/qa'))
import milestone_acceptance as gate

START='1acd1fbc0d556ec511ba71be833a1c7144eec841'
CHILD='b08ace36670a05992d8ddaa4279727d9b17bd11e'
VAEG='7dd453cbd36014ba453a26765b00cd0cc9a99655'
FREECOM='855281a3114b43ad4b8d9a320f2aca39be046bba'
COUNTRY='23f189cca3420606eae8723884fa92ccd65eb307'
JOBS=['uPD9002 architectural SST ratchet','production-memory CPU trace matrix','ubuntu asan compatibility','standalone compatibility conformance','repo invariants','PC-88VA guest-driver distribution','windows msys2 mingw64 compatibility','ubuntu clang compatibility','macos fetch-sdl2 compatibility','windows msys2 mingw64 release artifact','ubuntu gcc compatibility']

def read(p): return gate.json_value(Path(p).read_text())
def ident(p):
    b=Path(p).read_bytes(); return {'size':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def ref(root,r):
    gate.exact_fields(r,('path','sha256'),'INVALID_REFERENCE'); gate.bound_bytes(root,r); return read(root/r['path'])
def schema(root,name):
    p=root/('schema/m11-'+name+'.schema.json'); gate.require(p.is_file(),'MISSING_SCHEMA'); s=read(p)
    from jsonschema import Draft202012Validator
    try: Draft202012Validator.check_schema(s)
    except Exception: raise gate.Rejected('INVALID_SCHEMA')
    return s
def check_ci(claim):
    gate.exact_fields(claim,('schema_version','commit','repository','run_id','attempt','head_sha','workflow_path','required_jobs'),'INVALID_VAEG_CI')
    gate.require(claim['schema_version']==1 and claim['commit']==VAEG and claim['head_sha']==VAEG,'VAEG_IDENTITY_DRIFT')
    run=json.loads(subprocess.check_output(['gh','api','repos/'+claim['repository']+'/actions/runs/'+str(claim['run_id'])],text=True))
    pages=json.loads(subprocess.check_output(['gh','api','--paginate','--slurp','repos/'+claim['repository']+'/actions/runs/'+str(claim['run_id'])+'/attempts/'+str(claim['attempt'])+'/jobs?per_page=100'],text=True))
    gate.verify_ci_claim({'repository':claim['repository'],'run_id':claim['run_id'],'attempt':claim['attempt'],'head_sha':claim['head_sha'],'workflow_path':claim['workflow_path'],'required_jobs':claim['required_jobs'],'manifest':{}},run,[j for p in pages for j in p['jobs']])
def content(root=ROOT):
    mc=read(root/'config/m11/machine-contract.json'); gate.validate_instance(schema(root,'machine-contract'),mc)
    gate.require(mc['start_sha']==START and mc['child_commit']==CHILD and mc['vaeg_commit']==VAEG,'M11_IDENTITY_DRIFT')
    cc=read(root/'config/m11/console-contract.json'); gate.validate_instance(schema(root,'console-contract'),cc)
    lock=read(root/'manifests/m11-components.lock.json'); gate.validate_instance(schema(root,'components'),lock)
    gate.require(lock['components'][0]['commit']==CHILD and lock['components'][1]['commit']==FREECOM and lock['components'][2]['commit']==COUNTRY,'COMPONENT_LOCK_DRIFT')
    manifest=read(root/'qa/golden/m11/manifest.json'); gate.validate_instance(schema(root,'artifact-manifest'),manifest)
    qual=read(root/'qa/golden/m11/qualification.json'); gate.validate_instance(schema(root,'public-qualification'),qual)
    gate.require(qual['artifact_manifest']['sha256']==hashlib.sha256((root/'qa/golden/m11/manifest.json').read_bytes()).hexdigest(),'QUALIFICATION_MANIFEST_DRIFT')
    for item in (mc['artifact_manifest'],mc['qualification'],mc['console_contract'],mc['component_lock']): gate.bound_bytes(root,item)
    gate.require(mc['qualification']['path']=='qa/golden/m11/qualification.json','QUALIFICATION_PATH_DRIFT')
    gate.require(mc['parent_ci'] is None or isinstance(mc['parent_ci'],dict),'INVALID_PARENT_CI')
    check_ci(read(root/'config/m11/vaeg-qualification.json'))
    return mc,manifest,qual
def sources(root=ROOT):
    comps=read(root/'manifests/m11-components.lock.json')['components']
    for c in comps:
        p=root/c['path']; gate.require(gate.git(p,'rev-parse','HEAD')==c['commit'],'COMPONENT_HEAD_DRIFT'); gate.require(not gate.git(p,'status','--porcelain','--untracked-files=all'),'DIRTY_COMPONENT')
        tree=gate.git(root,'ls-tree','HEAD','--',c['path']).split(); gate.require(tree[:3]==['160000','commit',c['commit']],'COMPONENT_GITLINK_DRIFT')
    tar=subprocess.check_output(['git','-C',str(root/'components/fdkernel'),'archive','--format=tar','--prefix=fdkernel/',CHILD]); gate.require(hashlib.sha256(tar).hexdigest()==comps[0]['source_archive_sha256'],'SOURCE_ARCHIVE_DRIFT')
    gate.require(not gate.git(root/'components/fdkernel','diff','54c067af9764ace07459b0c2f5df4f70294d0c50',CHILD,'--','pc88va/boot','pc88va/kernel/console.asm','pc88va/kernel/machine_services.asm'),'M08_M10_SOURCE_DRIFT')
    for path in ('config/m09','schema/m09-artifact-manifest.schema.json','schema/m09-public-qualification.schema.json','qa/golden/m09','manifests/m09-components.lock.json','tools/m09'):
        gate.require(not gate.git(root,'diff',START,'--',path),'M09_ACCEPTED_DRIFT')
def generated(build,root=ROOT):
    build=Path(build); gate.require((build/'run-1').is_dir() and (build/'run-2').is_dir(),'BUILD_PAIR_REQUIRED')
    paths=['media/loader_stage1.artifact','media/loader_stage2.artifact','media/kernel_sys.artifact','media/raw_media.artifact','media/d88_media.artifact','media/extracted_kernel_sys.artifact','media/extracted_command_com.artifact','media/extracted_country_sys.artifact']
    for rel in paths:
        a=build/'run-1'/rel;b=build/'run-2'/rel; gate.require(ident(a)==ident(b),'BUILD_PAIR_DRIFT')
    manifest=read(root/'qa/golden/m11/manifest.json'); mapping={'loader_stage1':'media/loader_stage1.artifact','loader_stage2':'media/loader_stage2.artifact','kernel_sys':'media/kernel_sys.artifact','raw_media':'media/raw_media.artifact','d88_media':'media/d88_media.artifact','extracted_kernel_sys':'media/extracted_kernel_sys.artifact','extracted_command_com':'media/extracted_command_com.artifact','extracted_country_sys':'media/extracted_country_sys.artifact'}
    for name,rel in mapping.items():
        e=manifest['artifacts'][name]; actual=ident(build/'run-1'/rel); gate.require(actual['size']==e['size'] and actual['sha256']==e['sha256'],'BUILD_MANIFEST_DRIFT')
    for n in (1,2):
        run=build/f'run-{n}'; km=read(run/'kernel-evidence/compile-manifest.json'); ki=ident(run/'kernel-evidence/compile-manifest.json'); gate.require(ki['sha256']==manifest['artifacts']['kernel_sys']['compile_manifest_sha256'],'COMPILE_BINDING_DRIFT')
        gate.require(ident(run/'kernel-evidence/kernel-interface.json')['sha256']==manifest['artifacts']['kernel_sys']['kernel_interface_sha256'],'INTERFACE_BINDING_DRIFT'); gate.require(ident(run/'kernel-evidence/symbol-evidence.json')['sha256']==manifest['artifacts']['kernel_sys']['symbol_evidence_sha256'],'SYMBOL_BINDING_DRIFT')
        gate.require(not any(any(token in json.dumps(x).lower() for token in ('/users/','/private/','.d88','.rom','raw trace')) for x in km.get('objects',[])),'PRIVATE_BUILD_REFERENCE')
    gate.require(manifest['artifacts']['loader_stage1']['sha256']=='20efd8a66dde7feac3f48df4bd6e8c4564d70e80a5a8871a8293e735c1585f24','LOADER_STAGE1_DRIFT')
    gate.require(manifest['artifacts']['loader_stage2']['sha256']=='db324cbdae11fd1e6085a7957ef171ccf9d6a9be6ea05f3df0eedf83d8f594f7','LOADER_STAGE2_DRIFT')
def accept(build=None,root=ROOT):
    content(root); sources(root)
    if build: generated(build,root)
    subprocess.run([sys.executable,'-B','tools/m09/verify_m09.py'],cwd=root,check=True)
    print('M11 public schemas, actual instances, component identities and VAEG CI passed')
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--build-root',type=Path); ap.add_argument('--accept',action='store_true'); a=ap.parse_args()
    try:
        if a.accept: accept(a.build_root.resolve() if a.build_root else None)
        else: content(); sources(); print('M11 public content and live VAEG CI passed')
    except (gate.Rejected,ValueError,KeyError,TypeError,OSError,subprocess.CalledProcessError): print('M11_PUBLIC_GATE_REJECTED'); return 1
    return 0
if __name__=='__main__': raise SystemExit(main())
