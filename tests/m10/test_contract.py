# SPDX-License-Identifier: GPL-2.0-or-later
import copy
import importlib.util
import json
from pathlib import Path
import sys
import subprocess
import os
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/m10'))
spec=importlib.util.spec_from_file_location('m10_verifier',ROOT/'tools/m10/verify_m10.py')
v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)


class ContractTests(unittest.TestCase):
    def test_actual_instances(self):v.content()

    def test_verifier_calls_instance_validation(self):
        with patch.object(v.gate,'validate_instance',wraps=v.gate.validate_instance) as call:
            v.content();self.assertEqual(call.call_count,6)

    def test_all_records_reject_missing_and_unknown_fields(self):
        contract=v.read(ROOT/'config/m10/machine-contract.json')
        pairs=[('config/m10/machine-contract.json','schema/m10-machine-contract.schema.json')]
        pairs += [(p['record']['path'],p['schema']['path']) for p in contract['instances']]
        for record,schema in pairs:
            good=v.read(ROOT/record);s=v.read(ROOT/schema)
            for key in good:
                bad=copy.deepcopy(good);del bad[key]
                with self.subTest(record=record,key=key),self.assertRaises(v.gate.Rejected):v.gate.validate_instance(s,bad)
            bad=copy.deepcopy(good);bad['unknown']=True
            with self.assertRaises(v.gate.Rejected):v.gate.validate_instance(s,bad)

    def test_false_private_claim_rejected(self):
        q=v.read(ROOT/'config/m10/vaeg-qualification.json');q['two_main_runs_equal']=False
        with self.assertRaises(v.gate.Rejected):v.gate.validate_instance(v.read(ROOT/'schema/m10-public-qualification.schema.json'),q)

    def test_invalid_clock_contract_rejected(self):
        q=v.read(ROOT/'config/m10/services.json');q['services']['pc88va_clock_read']['host_time']=True
        with self.assertRaises(v.gate.Rejected):v.gate.validate_instance(v.read(ROOT/'schema/m10-services.schema.json'),q)

    def test_missing_reference_rejected(self):
        original=v.read
        def read(path):
            value=original(path)
            if path.name=='machine-contract.json':value['pins'].pop()
            return value
        with patch.object(v,'read',side_effect=read),self.assertRaises(v.gate.Rejected):v.content()

    def test_digest_drift_rejected(self):
        original=v.read
        def read(path):
            value=original(path)
            if path.name=='machine-contract.json':value['instances'][0]['record']['sha256']='0'*64
            return value
        with patch.object(v,'read',side_effect=read),self.assertRaises(v.gate.Rejected):v.content()

    def test_accepted_requires_exact_ci(self):
        c=v.read(ROOT/'config/m10/machine-contract.json');c['status']='accepted';c['parent_ci']=None
        with self.assertRaises(v.gate.Rejected):v.gate.validate_instance(v.read(ROOT/'schema/m10-machine-contract.schema.json'),c)

    def test_bad_fatal_selector_rejected(self):
        with self.assertRaises(ValueError):v.fatal_kernel(b'not a kernel',{'symbols':[]})

    def test_private_entry_without_inputs_fails_closed(self):
        env={k:x for k,x in os.environ.items() if not k.startswith('M10_PRIVATE_') and k!='CI'}
        p=subprocess.run([sys.executable,'-B','tools/m10/private_run.py'],cwd=ROOT,env=env,capture_output=True)
        self.assertNotEqual(p.returncode,0);self.assertIn(b'NOT RUN',p.stderr)

    def test_private_entry_prohibited_in_ci(self):
        env=dict(os.environ,CI='true')
        p=subprocess.run([sys.executable,'-B','tools/m10/private_run.py'],cwd=ROOT,env=env,capture_output=True)
        self.assertNotEqual(p.returncode,0);self.assertIn(b'prohibited',p.stderr)

    def test_fresh_history_requires_m01r1_diagnostics(self):
        with patch.dict(os.environ,clear=False):
            hs=importlib.util.spec_from_file_location('m10_history',ROOT/'tools/m10/historical.py')
            h=importlib.util.module_from_spec(hs);hs.loader.exec_module(h)
            with patch.object(h,'checkout',return_value=ROOT),patch.object(h,'run') as run:
                h.baseline()
                self.assertEqual(os.environ['M01_DIAGNOSTICS'],'1')
                commands=[c.args[1:] for c in run.call_args_list]
                self.assertTrue(any('m01-build' in c and 'm02-preflight' in c for c in commands))
                self.assertTrue(any('m02-preflight' in c and 'm06-verify' in c for c in commands))


if __name__=='__main__':unittest.main()
