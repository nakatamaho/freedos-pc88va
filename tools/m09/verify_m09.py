#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Fail-closed public M09 evidence gate. Never discovers private inputs."""
import hashlib
import json
from pathlib import Path
import subprocess
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
ACCEPTED_M08 = {
    'config/m08/loader-contract.json': 'c163ab5a1f1d1a3c3ae76e93bd24da7535393ea923f1d891cdbc1ab4460dae19',
    'qa/golden/m08-artifact-manifest.json': '2210a590a7d705f3936a9053e197d05eb94888254b708f4435a1e7c89d3ef5e0',
    'schema/m08-artifact-manifest.schema.json': '575086b668fb7f2439f17b63a33675978fef00861eb0b30f66a7b22d3279e7fe',
    'qa/golden/m08-golden.json': 'bd611f5d6a0cb37c16114aec5b7382cb3bf7c18d340b762501d8bc2a574ad2a7',
    'config/m08/vaeg-qualification.json': '3ebbf58e18ea2acf0f92ba755cca99c3082b5ed419e6bfa51a5bd2d2fd8dbe47',
    'manifests/m08-components.lock.json': 'c3e736596ce63ce006ba0363682259260f30a1792e59a04e3250ac9821544f07',
}


class VerificationError(ValueError):
    pass


def validate_contract(contract):
    required = {'schema_version', 'status', 'parent_start', 'toolchain_lock_sha256',
                'vaeg_commit', 'vaeg_accepted_ci', 'child_ci', 'parent_ci',
                'private_execution_in_ci', 'scope', 'artifact_schema',
                'artifact_manifest', 'component_lock', 'qualification',
                'qualification_schema', 'console_abi'}
    if set(contract) != required or contract['schema_version'] != 1:
        raise VerificationError('invalid public contract fields')
    if contract['parent_start'] != 'cfdf5841857f9633a20bdb7b6edb0c1e35275969':
        raise VerificationError('accepted parent start differs')
    if contract['vaeg_commit'] != '7463f9501d84701f50f3243d5067b6a9dfd0c2e7' or contract['vaeg_accepted_ci'] != 33937050536:
        raise VerificationError('accepted observation tool differs')
    if contract['toolchain_lock_sha256'] != '39c5b3052d71463235a26e8704ab54c1fedb51ee75bb4efb55e6229391a95162':
        raise VerificationError('canonical toolchain differs')
    if contract['status'] not in ('accepted', 'qualification_complete_ci_pending'):
        raise VerificationError('M09 acceptance remains incomplete')
    if contract['status'] == 'accepted':
        ci = contract['parent_ci']
        if not isinstance(ci, dict) or set(ci) != {'commit', 'run', 'conclusion'}:
            raise VerificationError('accepted contract lacks native CI identity')
        import re
        if not re.fullmatch('[0-9a-f]{40}', ci['commit']) or type(ci['run']) is not int or ci['run'] <= 0 or ci['conclusion'] != 'success':
            raise VerificationError('native CI record invalid')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def json_file(path):
    if not path.is_file() or path.is_symlink():
        raise VerificationError('required regular public record missing')
    return json.loads(path.read_text())


def bound_record(root, reference):
    if set(reference) != {'path', 'sha256'}:
        raise VerificationError('invalid evidence reference')
    relative = Path(reference['path'])
    if relative.is_absolute() or '..' in relative.parts:
        raise VerificationError('non-public evidence reference')
    path = root / relative
    if any(parent.is_symlink() for parent in [path, *path.parents] if parent != root.parent):
        raise VerificationError('symlink evidence reference rejected')
    value = json_file(path)
    if sha(path) != reference['sha256']:
        raise VerificationError('evidence digest mismatch')
    return value


def validate_manifest(schema, manifest):
    try:
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(manifest)
    except Exception as error:
        # Do not emit schema exception instance values in public diagnostics.
        raise VerificationError('artifact schema or instance invalid') from None


def verify(root=ROOT):
    for relative, expected in ACCEPTED_M08.items():
        if sha(root / relative) != expected:
            raise VerificationError('accepted M08 evidence changed')
    old_schema = json_file(root / 'schema/m08-artifact-manifest.schema.json')
    old_manifest = json_file(root / 'qa/golden/m08-artifact-manifest.json')
    validate_manifest(old_schema, old_manifest)
    contract = json_file(root / 'config/m09/console-contract.json')
    validate_contract(contract)
    schema = bound_record(root, contract['artifact_schema'])
    manifest = bound_record(root, contract['artifact_manifest'])
    validate_manifest(schema, manifest)
    lock = bound_record(root, contract['component_lock'])
    kernel = next(item for item in lock['components'] if item['name'] == 'fdkernel')
    if manifest['source'] != {'commit': kernel['commit'], 'archive_sha256': kernel['source_archive_sha256']}:
        raise VerificationError('artifact source differs from current lock')
    child = root / 'components/fdkernel'
    actual = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=child, text=True).strip()
    if actual != kernel['commit']:
        raise VerificationError('child worktree identity differs')
    archive = subprocess.check_output(['git','archive','--format=tar','--prefix=fdkernel/',actual], cwd=child)
    if hashlib.sha256(archive).hexdigest() != kernel['source_archive_sha256']:
        raise VerificationError('child source archive differs')
    changed = subprocess.check_output(['git','diff','--name-only','105d49a72ec41afe07fc1e7b080bdbd1b3026ae2',actual,'--','pc88va/boot'],cwd=child,text=True)
    if changed:
        raise VerificationError('M08 boot implementation changed')
    for key in ('loader_stage1','loader_stage2','extracted_command_com','extracted_country_sys'):
        old = old_manifest['artifacts'][key]
        if any(manifest['artifacts'][key][part] != old[part] for part in ('size','sha256')):
            raise VerificationError('unchanged loader or payload drift')
    if contract['status'] not in ('accepted', 'qualification_complete_ci_pending'):
        raise VerificationError('M09 acceptance remains incomplete')
    if contract['status'] == 'accepted' and not contract.get('parent_ci'):
        raise VerificationError('accepted contract lacks native CI identity')
    if sha(root/'manifests/toolchains.lock.json') != contract['toolchain_lock_sha256']:
        raise VerificationError('accepted toolchain identity differs')
    abi = bound_record(root, contract['console_abi'])
    if abi['public_source']['commit'] != contract['vaeg_commit'] or contract['private_execution_in_ci'] is not False:
        raise VerificationError('console provenance or private execution boundary differs')
    expected = {'components/freecom': '855281a3114b43ad4b8d9a320f2aca39be046bba',
                'components/country': '23f189cca3420606eae8723884fa92ccd65eb307',
                'components/fdkernel': actual}
    for path, commit in expected.items():
        head = subprocess.check_output(['git','rev-parse','HEAD'],cwd=root/path,text=True).strip()
        dirty = subprocess.check_output(['git','status','--porcelain','--untracked-files=all'],cwd=root/path,text=True)
        index = subprocess.check_output(['git','ls-files','--stage','--',path],cwd=root,text=True).split()
        if head != commit or dirty or index[:2] != ['160000',commit]:
            raise VerificationError('component gitlink or cleanliness differs')
    tested = contract['child_ci']['pc88va_tested_commit']
    if subprocess.check_output(['git','diff','--name-only',tested,actual,'--','pc88va'],cwd=child,text=True):
        raise VerificationError('final PC-88VA source differs from child QA source')
    qualification = bound_record(root, contract['qualification'])
    qualification_schema = bound_record(root, contract['qualification_schema'])
    try:
        Draft202012Validator.check_schema(qualification_schema)
        Draft202012Validator(qualification_schema).validate(qualification)
    except Exception:
        raise VerificationError('public qualification record invalid') from None
    if qualification['child_commit'] != actual or qualification['kernel_sha256'] != manifest['artifacts']['kernel_sys']['sha256']:
        raise VerificationError('qualification is not bound to the final artifact')
    return True


if __name__ == '__main__':
    try:
        verify()
    except (VerificationError, OSError, KeyError, ValueError) as error:
        print(str(error) if isinstance(error, VerificationError) else 'M09 public evidence incomplete or invalid')
        raise SystemExit(1)
    print('M09 public records verified; native CI conclusion is a separate gate; no private execution performed')
