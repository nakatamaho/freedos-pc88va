# SPDX-License-Identifier: GPL-2.0-or-later
"""Focused negative checks start with valid, ROM-free evidence fixtures."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('acceptance', ROOT/'tools/qa/milestone_acceptance.py')
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


class ContentTests(unittest.TestCase):
    def setUp(self):
        scratch = ROOT/'build/acceptance-tests'
        scratch.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.schema = {'$schema': 'https://json-schema.org/draft/2020-12/schema',
                       'type':'object','additionalProperties':False,'required':['ready'],
                       'properties':{'ready':{'const':True}}}
        self.instance = {'ready':True}
        self.record = {
            'schema_version':1,'repository':'owner/project','remote':'origin','branch':'topic/accepted',
            'identities':dict(START_SHA='1'*40,QUALIFIED_IMPLEMENTATION_SHA='2'*40,
                              PUBLICATION_TIP_SHA='3'*40,DOWNSTREAM_BASE_SHA='3'*40),
            'components':{'components/kernel':'4'*40},'publication_policy':{},'pins':[],
            'instances':[{'record':self.put('record.json',self.instance),
                          'schema':self.put('schema.json',self.schema)}],
            'artifacts':[],'ci':[]}
        gate.verify_content(self.root,self.record)

    def put(self,name,value):
        path=self.root/name
        path.write_text(json.dumps(value,sort_keys=True)+'\n')
        return {'path':name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}

    def rejected(self,code,callback):
        with self.assertRaises(gate.Rejected) as result:callback()
        self.assertEqual(str(result.exception),code)

    def test_identity_placeholders_and_short_hashes(self):
        gate.commit_id('1'*40)
        for value in ['1'*39,'<DOWNSTREAM_BASE_SHA>','0'*40,'A'*40,None]:
            self.rejected('INVALID_COMMIT_ID',lambda:gate.commit_id(value))

    def test_unknown_acceptance_field(self):
        self.record['unknown']=True
        self.rejected('INVALID_ACCEPTANCE_FIELDS',lambda:gate.verify_content(self.root,self.record))

    def test_required_acceptance_field(self):
        del self.record['identities']
        self.rejected('INVALID_ACCEPTANCE_FIELDS',lambda:gate.verify_content(self.root,self.record))

    def test_downstream_base_mismatch(self):
        self.record['identities']['DOWNSTREAM_BASE_SHA']='5'*40
        self.rejected('DOWNSTREAM_BASE_DRIFT',lambda:gate.verify_content(self.root,self.record))

    def test_invalid_schema(self):
        self.schema['type']='imaginary'
        self.record['instances'][0]['schema']=self.put('schema.json',self.schema)
        self.rejected('INVALID_SCHEMA',lambda:gate.verify_content(self.root,self.record))

    def test_invalid_actual_instance_rebound_digest(self):
        self.record['instances'][0]['record']=self.put('record.json',{'ready':False})
        self.rejected('INVALID_INSTANCE',lambda:gate.verify_content(self.root,self.record))

    def test_missing_instance_field_rebound_digest(self):
        self.record['instances'][0]['record']=self.put('record.json',{})
        self.rejected('INVALID_INSTANCE',lambda:gate.verify_content(self.root,self.record))

    def test_unknown_instance_field_rebound_digest(self):
        self.record['instances'][0]['record']=self.put('record.json',{'ready':True,'unknown':1})
        self.rejected('INVALID_INSTANCE',lambda:gate.verify_content(self.root,self.record))

    def test_artifact_digest_drift(self):
        (self.root/'record.json').write_text('{}')
        self.rejected('ARTIFACT_DIGEST_DRIFT',lambda:gate.verify_content(self.root,self.record))

    def test_malformed_digest(self):
        self.record['instances'][0]['record']['sha256']='short'
        self.rejected('INVALID_DIGEST',lambda:gate.verify_content(self.root,self.record))

    def test_missing_artifact(self):
        (self.root/'record.json').unlink()
        self.rejected('MISSING_ARTIFACT',lambda:gate.verify_content(self.root,self.record))

    def test_artifact_size(self):
        ref=self.put('artifact.json',{'public':True})
        self.record['artifacts']=[dict(ref,size=(self.root/'artifact.json').stat().st_size)]
        gate.verify_content(self.root,self.record)
        self.record['artifacts'][0]['size']+=1
        self.rejected('ARTIFACT_SIZE_DRIFT',lambda:gate.verify_content(self.root,self.record))

    def test_incomplete_reference(self):
        ref=self.put('artifact.json',{'public':True})
        self.schema['required'].append('binding')
        self.schema['properties']['binding']={'type':'object','additionalProperties':False,
            'required':['path','sha256'],'properties':{'path':{'type':'string'},'sha256':{'type':'string'}}}
        self.record['instances'][0]['schema']=self.put('schema.json',self.schema)
        self.record['instances'][0]['record']=self.put('record.json',{'ready':True,'binding':ref})
        self.record['pins']=[ref]
        gate.verify_content(self.root,self.record)
        self.record['pins']=[]
        self.rejected('INCOMPLETE_EVIDENCE_BINDING',lambda:gate.verify_content(self.root,self.record))

    def test_instance_validation_cannot_be_omitted(self):
        self.record['instances']=[]
        self.rejected('INSTANCE_VALIDATION_MISSING',lambda:gate.verify_content(self.root,self.record))

    def test_unbound_schema_reference_rejected_without_fetch(self):
        self.schema['properties']['ready']={'$ref':'https://example.invalid/unbound.json'}
        self.record['instances'][0]['schema']=self.put('schema.json',self.schema)
        self.rejected('UNBOUND_SCHEMA_REFERENCE',lambda:gate.verify_content(self.root,self.record))

    def test_duplicate_json_key_is_ambiguous(self):
        self.rejected('DUPLICATE_JSON_FIELD',lambda:gate.json_value('{"ready":false,"ready":true}'))


class PublicationTests(unittest.TestCase):
    def test_json_acceptance_metadata_only(self):
        policy={'contract.json':{'kind':'json_fields','fields':['status']}}
        gate.verify_publication_diff([('contract.json',{'status':'pending','abi':1},
                                                    {'status':'accepted','abi':1})],policy)
        for before,after in [({'abi':1},{'abi':2}), ({'abi':1},{'abi':1,'new':None})]:
            with self.assertRaisesRegex(gate.Rejected,'^BEHAVIORAL_PUBLICATION_DIFF$'):
                gate.verify_publication_diff([('contract.json',before,after)],policy)

    def test_source_change_rejected(self):
        gate.verify_publication_diff([('report.md','before','after')],{'report.md':{'kind':'documentation','fields':[]}})
        with self.assertRaisesRegex(gate.Rejected,'^UNAPPROVED_PUBLICATION_PATH$'):
            gate.verify_publication_diff([('source.c','before','after')],{})

    def test_make_help_does_not_allow_build_rule(self):
        policy={'Makefile':{'kind':'make_help','fields':[]}}
        before='help:\n\t@echo before\n\nbuild:\n\t@compile\n'
        gate.verify_publication_diff([('Makefile',before,before.replace('before','after'))],policy)
        with self.assertRaisesRegex(gate.Rejected,'^BEHAVIORAL_MAKE_DIFF$'):
            gate.verify_publication_diff([('Makefile',before,before.replace('compile','skip'))],policy)


class TopologyTests(unittest.TestCase):
    def setUp(self):
        scratch = ROOT/'build/acceptance-tests'
        scratch.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)/'parent'
        self.root.mkdir()
        self.git('init', '-q')
        self.git('config', 'user.name', 'Synthetic Test')
        self.git('config', 'user.email', 'test@example.invalid')
        child = self.root/'components/kernel'
        child.mkdir(parents=True)
        self.child = child
        self.git('init', '-q', str(child))
        self.childgit('config', 'user.name', 'Synthetic Test')
        self.childgit('config', 'user.email', 'test@example.invalid')
        self.childgit('commit', '--allow-empty', '-qm', 'fixture')
        sha = self.childgit('rev-parse', 'HEAD')
        self.git('update-index', '--add', '--cacheinfo', '160000,'+sha+',components/kernel')
        self.git('commit', '-qm', 'start')
        start = self.git('rev-parse', 'HEAD')
        (self.root/'source.c').write_text('implementation\n')
        self.git('add', 'source.c')
        self.git('commit', '-qm', 'qualified')
        qualified = self.git('rev-parse', 'HEAD')
        (self.root/'report.md').write_text('accepted\n')
        self.git('add', 'report.md')
        self.git('commit', '-qm', 'publication')
        tip = self.git('rev-parse', 'HEAD')
        self.git('branch', '-M', 'topic/accepted')
        self.remote = Path(self.temp.name)/'remote.git'
        self.git('clone', '-q', '--bare', str(self.root), str(self.remote))
        self.git('remote', 'add', 'origin', str(self.remote))
        self.record = {'identities':dict(START_SHA=start,QUALIFIED_IMPLEMENTATION_SHA=qualified,
            PUBLICATION_TIP_SHA=tip,DOWNSTREAM_BASE_SHA=tip), 'remote':'origin',
            'branch':'topic/accepted','components':{'components/kernel':sha},
            'publication_policy':{'report.md':{'kind':'documentation','fields':[]}}}
        gate.verify_topology(self.root,self.record)

    def git(self,*args):
        return subprocess.check_output(['git','-C',str(self.root),*args],
                                       text=True,stderr=subprocess.PIPE).strip()

    def childgit(self,*args):
        return subprocess.check_output(['git','-C',str(self.child),*args],
                                       text=True,stderr=subprocess.PIPE).strip()

    def test_remote_tip_mismatch(self):
        subprocess.run(['git','--git-dir',str(self.remote),'update-ref',
                        'refs/heads/topic/accepted',self.record['identities']['START_SHA']],check=True)
        with self.assertRaisesRegex(gate.Rejected,'^REMOTE_TIP_MISMATCH$'):
            gate.verify_topology(self.root,self.record)

    def test_ancestry_mismatch(self):
        tree = self.git('rev-parse','HEAD^{tree}')
        unrelated = self.git('commit-tree',tree,'-m','unrelated')
        self.record['identities']['START_SHA']=unrelated
        with self.assertRaisesRegex(gate.Rejected,'^ANCESTRY_MISMATCH$'):
            gate.verify_topology(self.root,self.record)

    def test_gitlink_drift(self):
        self.record['components']['components/kernel']='4'*40
        with self.assertRaisesRegex(gate.Rejected,'^COMPONENT_GITLINK_DRIFT$'):
            gate.verify_topology(self.root,self.record)

    def test_dirty_component(self):
        (self.child/'untracked').write_text('preserved\n')
        with self.assertRaisesRegex(gate.Rejected,'^DIRTY_COMPONENT$'):
            gate.verify_topology(self.root,self.record)

    def test_component_head_drift(self):
        self.childgit('commit','--allow-empty','-qm','drift')
        with self.assertRaisesRegex(gate.Rejected,'^COMPONENT_HEAD_DRIFT$'):
            gate.verify_topology(self.root,self.record)

    def test_wrong_publication_checkout(self):
        self.git('checkout','--detach',self.record['identities']['QUALIFIED_IMPLEMENTATION_SHA'])
        with self.assertRaisesRegex(gate.Rejected,'^PUBLICATION_CHECKOUT_DRIFT$'):
            gate.verify_topology(self.root,self.record)


class CiTests(unittest.TestCase):
    def setUp(self):
        self.claim={'repository':'owner/project','run_id':1,'attempt':2,'head_sha':'1'*40,
                    'workflow_path':'.github/workflows/test.yml','required_jobs':['accept'],
                    'manifest':{'path':'manifest.json','sha256':'2'*64}}
        self.run={'repository':{'full_name':'owner/project'},'id':1,'run_attempt':2,
                  'head_sha':'1'*40,'path':'.github/workflows/test.yml',
                  'status':'completed','conclusion':'success'}
        self.jobs=[{'name':'accept','conclusion':'success','head_sha':'1'*40}]
        gate.verify_ci_claim(self.claim,self.run,self.jobs)

    def test_stale_ci_head(self):
        self.run['head_sha']='3'*40
        with self.assertRaisesRegex(gate.Rejected,'^CI_HEAD_SHA_DRIFT$'):
            gate.verify_ci_claim(self.claim,self.run,self.jobs)

    def test_failed_run(self):
        self.run['conclusion']='failure'
        with self.assertRaisesRegex(gate.Rejected,'^CI_NOT_SUCCESS$'):
            gate.verify_ci_claim(self.claim,self.run,self.jobs)

    def test_attempt_mismatch(self):
        self.run['run_attempt']=1
        with self.assertRaisesRegex(gate.Rejected,'^CI_ATTEMPT_DRIFT$'):
            gate.verify_ci_claim(self.claim,self.run,self.jobs)

    def test_wrong_job_head(self):
        self.jobs[0]['head_sha']='3'*40
        with self.assertRaisesRegex(gate.Rejected,'^CI_JOB_NOT_QUALIFIED$'):
            gate.verify_ci_claim(self.claim,self.run,self.jobs)


if __name__=='__main__':unittest.main()
