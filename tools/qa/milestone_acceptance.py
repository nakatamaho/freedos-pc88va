#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Reusable fail-closed milestone identity, evidence and publication checks.

Content, Git topology, and live CI checks are independently callable for
focused negative tests. The command-line gate always composes all three.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from jsonschema import Draft202012Validator


class Rejected(ValueError):
    """Stable diagnostics contain no evidence values or paths."""


def require(value, code):
    if not value:
        raise Rejected(code)


def exact_fields(value, names, code):
    require(isinstance(value, dict) and set(value) == set(names), code)


def commit_id(value):
    require(isinstance(value, str) and re.fullmatch(r'[0-9a-f]{40}', value)
            and value != '0' * 40, 'INVALID_COMMIT_ID')


def digest(value):
    require(isinstance(value, str) and re.fullmatch(r'[0-9a-f]{64}', value),
            'INVALID_DIGEST')


def relative_path(value):
    require(isinstance(value, str) and value and not Path(value).is_absolute()
            and all(p not in ('', '.', '..') for p in value.split('/')),
            'INVALID_RELATIVE_PATH')
    return value


def regular(root, value):
    path = root / relative_path(value)
    require(not any(p.is_symlink() for p in (path, *path.parents)), 'SYMLINK_REFERENCE')
    require(path.is_file(), 'MISSING_ARTIFACT')
    return path


def bound_bytes(root, reference, sized=False):
    exact_fields(reference, ('path', 'sha256', 'size') if sized else ('path', 'sha256'),
                 'INVALID_ARTIFACT_REFERENCE')
    digest(reference['sha256'])
    data = regular(root, reference['path']).read_bytes()
    if sized:
        require(type(reference['size']) is int and reference['size'] >= 0,
                'INVALID_ARTIFACT_SIZE')
        require(len(data) == reference['size'], 'ARTIFACT_SIZE_DRIFT')
    require(hashlib.sha256(data).hexdigest() == reference['sha256'], 'ARTIFACT_DIGEST_DRIFT')
    return data


def validate_instance(schema, instance):
    def closed_references(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key in ('$ref', '$dynamicRef'):
                    require(isinstance(child, str) and
                            (child == '#' or child.startswith('#/')), 'UNBOUND_SCHEMA_REFERENCE')
                closed_references(child)
        elif isinstance(value, list):
            for child in value:
                closed_references(child)
    closed_references(schema)
    try:
        Draft202012Validator.check_schema(schema)
    except Exception:
        raise Rejected('INVALID_SCHEMA') from None
    try:
        Draft202012Validator(schema).validate(instance)
    except Exception:
        raise Rejected('INVALID_INSTANCE') from None


def json_value(data):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'DUPLICATE_JSON_FIELD')
            result[key] = value
        return result
    return json.loads(data, object_pairs_hook=unique)


def verify_content(root, record):
    exact_fields(record, ('schema_version', 'repository', 'remote', 'branch',
                         'identities', 'components', 'publication_policy',
                         'pins', 'instances', 'artifacts', 'ci'), 'INVALID_ACCEPTANCE_FIELDS')
    require(type(record['schema_version']) is int and record['schema_version'] == 1,
            'INVALID_ACCEPTANCE_VERSION')
    require(re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', record['repository']),
            'INVALID_REPOSITORY')
    require(re.fullmatch(r'[A-Za-z0-9_.-]+', record['remote']), 'INVALID_REMOTE')
    require(isinstance(record['branch'], str) and record['branch']
            and not record['branch'].startswith('-'), 'INVALID_BRANCH')
    ids = record['identities']
    exact_fields(ids, ('START_SHA', 'QUALIFIED_IMPLEMENTATION_SHA',
                      'PUBLICATION_TIP_SHA', 'DOWNSTREAM_BASE_SHA'), 'INVALID_IDENTITY_FIELDS')
    for value in ids.values():
        commit_id(value)
    require(ids['PUBLICATION_TIP_SHA'] == ids['DOWNSTREAM_BASE_SHA'], 'DOWNSTREAM_BASE_DRIFT')
    require(isinstance(record['components'], dict) and record['components'], 'MISSING_COMPONENTS')
    for path, sha in record['components'].items():
        relative_path(path)
        commit_id(sha)
    known = {}

    def register(ref, sized=False):
        data = bound_bytes(root, ref, sized)
        path = ref['path']
        require(path not in known or known[path] == ref['sha256'], 'AMBIGUOUS_BINDING')
        known[path] = ref['sha256']
        return data

    for ref in record['pins']:
        register(ref)
    for ref in record['artifacts']:
        register(ref, True)
    instances = []
    for item in record['instances']:
        exact_fields(item, ('record', 'schema'), 'INVALID_INSTANCE_REFERENCE')
        try:
            schema = json_value(register(item['schema']))
            value = json_value(register(item['record']))
        except (UnicodeError, json.JSONDecodeError):
            raise Rejected('INVALID_JSON') from None
        validate_instance(schema, value)
        instances.append(value)

    def visit(value):
        if isinstance(value, dict):
            if 'path' in value and 'sha256' in value:
                path = relative_path(value['path'])
                digest(value['sha256'])
                require(known.get(path) == value['sha256'], 'INCOMPLETE_EVIDENCE_BINDING')
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
    for value in instances:
        visit(value)
    require(record['instances'], 'INSTANCE_VALIDATION_MISSING')


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()


def verify_publication_diff(changes, policy):
    require(isinstance(policy, dict), 'INVALID_PUBLICATION_POLICY')
    for path, before, after in changes:
        require(path in policy, 'UNAPPROVED_PUBLICATION_PATH')
        entry = policy[path]
        exact_fields(entry, ('kind', 'fields'), 'INVALID_PUBLICATION_POLICY')
        if entry['kind'] == 'json_fields':
            require(isinstance(before, dict) and isinstance(after, dict), 'PUBLICATION_JSON_INVALID')
            require(isinstance(entry['fields'], list), 'INVALID_PUBLICATION_POLICY')
            changed = {k for k in set(before) | set(after)
                       if k not in before or k not in after or before[k] != after[k]}
            require(changed <= set(entry['fields']), 'BEHAVIORAL_PUBLICATION_DIFF')
        elif entry['kind'] == 'documentation':
            require(path.endswith('.md') and entry['fields'] == [], 'INVALID_DOCUMENTATION_POLICY')
        elif entry['kind'] == 'make_help':
            require(path == 'Makefile' and entry['fields'] == [], 'INVALID_MAKE_HELP_POLICY')
            # Only the body of the existing help recipe may differ.
            def without_help(text):
                lines = text.splitlines(keepends=True)
                start = lines.index('help:\n') + 1
                end = start
                while end < len(lines) and (lines[end].startswith('\t') or not lines[end].strip()):
                    end += 1
                return lines[:start] + lines[end:]
            require(without_help(before) == without_help(after), 'BEHAVIORAL_MAKE_DIFF')
        else:
            raise Rejected('INVALID_PUBLICATION_POLICY')


def verify_topology(root, record):
    ids = record['identities']
    tip = ids['PUBLICATION_TIP_SHA']
    require(git(root, 'rev-parse', 'HEAD') == tip, 'PUBLICATION_CHECKOUT_DRIFT')
    for sha in ids.values():
        require(git(root, 'rev-parse', sha + '^{commit}') == sha, 'UNREACHABLE_IDENTITY')
    remote = git(root, 'ls-remote', '--heads', record['remote'], 'refs/heads/' + record['branch']).split()
    require(len(remote) == 2 and remote[0] == tip
            and remote[1] == 'refs/heads/' + record['branch'], 'REMOTE_TIP_MISMATCH')
    for ancestor, descendant in ((ids['START_SHA'], ids['QUALIFIED_IMPLEMENTATION_SHA']),
                                 (ids['QUALIFIED_IMPLEMENTATION_SHA'], tip)):
        require(subprocess.run(['git', '-C', str(root), 'merge-base', '--is-ancestor',
                                ancestor, descendant], capture_output=True).returncode == 0,
                'ANCESTRY_MISMATCH')
    for path, sha in record['components'].items():
        tree = git(root, 'ls-tree', tip, '--', path).split()
        require(tree[:3] == ['160000', 'commit', sha], 'COMPONENT_GITLINK_DRIFT')
        require(git(root / path, 'rev-parse', 'HEAD') == sha, 'COMPONENT_HEAD_DRIFT')
        require(not git(root / path, 'status', '--porcelain', '--untracked-files=all'), 'DIRTY_COMPONENT')
    paths = git(root, 'diff', '--name-only', ids['QUALIFIED_IMPLEMENTATION_SHA'], tip).splitlines()
    changes = []
    for path in paths:
        def file_at(sha):
            result = subprocess.run(['git', '-C', str(root), 'show', sha + ':' + path], capture_output=True)
            if result.returncode:
                require(subprocess.run(['git', '-C', str(root), 'cat-file', '-e', sha + ':' + path],
                                       capture_output=True).returncode != 0, 'PUBLICATION_OBJECT_ERROR')
                return None
            return result.stdout.decode('utf-8')
        before = file_at(ids['QUALIFIED_IMPLEMENTATION_SHA'])
        after = file_at(tip)
        if record['publication_policy'].get(path, {}).get('kind') == 'json_fields':
            require(before is not None and after is not None, 'PUBLICATION_JSON_ADDED_OR_REMOVED')
            before, after = json.loads(before), json.loads(after)
        changes.append((path, before, after))
    verify_publication_diff(changes, record['publication_policy'])


def verify_ci_claim(claim, run, jobs):
    exact_fields(claim, ('repository', 'run_id', 'attempt', 'head_sha', 'workflow_path',
                         'required_jobs', 'manifest'), 'INVALID_CI_CLAIM')
    commit_id(claim['head_sha'])
    require(run.get('repository', {}).get('full_name') == claim['repository'], 'CI_REPOSITORY_DRIFT')
    require(run.get('id') == claim['run_id'] and run.get('run_attempt') == claim['attempt'], 'CI_ATTEMPT_DRIFT')
    require(run.get('head_sha') == claim['head_sha'], 'CI_HEAD_SHA_DRIFT')
    require(run.get('path') == claim['workflow_path'], 'CI_WORKFLOW_DRIFT')
    require(run.get('status') == 'completed' and run.get('conclusion') == 'success', 'CI_NOT_SUCCESS')
    require(claim['required_jobs'], 'CI_REQUIRED_JOBS_MISSING')
    for name in claim['required_jobs']:
        matches = [j for j in jobs if j.get('name') == name]
        require(len(matches) == 1 and matches[0].get('conclusion') == 'success'
                and matches[0].get('head_sha') == claim['head_sha'], 'CI_JOB_NOT_QUALIFIED')


def verify_live_ci(root, record):
    require(record['ci'], 'CI_EVIDENCE_MISSING')
    required = {record['identities']['QUALIFIED_IMPLEMENTATION_SHA'],
                record['identities']['PUBLICATION_TIP_SHA']}
    require(required <= {claim['head_sha'] for claim in record['ci']}, 'CI_IDENTITY_COVERAGE_MISSING')
    for claim in record['ci']:
        repository = claim['repository']
        require(repository == record['repository'], 'CI_REPOSITORY_DRIFT')
        endpoint = 'repos/' + repository + '/actions/runs/' + str(claim['run_id'])
        run = json.loads(subprocess.check_output(['gh', 'api', endpoint], text=True))
        pages = json.loads(subprocess.check_output(['gh', 'api', '--paginate', '--slurp',
                           endpoint + '/attempts/' + str(claim['attempt']) + '/jobs?per_page=100'], text=True))
        verify_ci_claim(claim, run, [job for page in pages for job in page['jobs']])
        ref = claim['manifest']
        exact_fields(ref, ('path', 'sha256'), 'INVALID_CI_MANIFEST_BINDING')
        digest(ref['sha256']);relative_path(ref['path'])
        data = subprocess.check_output(['git', '-C', str(root), 'show', claim['head_sha'] + ':' + ref['path']])
        require(hashlib.sha256(data).hexdigest() == ref['sha256'], 'CI_MANIFEST_DRIFT')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--record', type=Path, required=True)
    args = parser.parse_args()
    try:
        record = json_value(args.record.read_text())
        verify_content(args.root, record)
        verify_topology(args.root, record)
        verify_live_ci(args.root, record)
    except (Rejected, OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as error:
        print(str(error) if isinstance(error, Rejected) else 'ACCEPTANCE_GATE_ERROR')
        return 1
    print('Milestone content, topology, publication and live CI checks passed')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
