# SPDX-License-Identifier: GPL-2.0-or-later
import copy, importlib.util, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('m11',ROOT/'tools/m11/verify_m11.py');m11=importlib.util.module_from_spec(spec);spec.loader.exec_module(m11)
class M11ContractTests(unittest.TestCase):
    def test_actual_schema_instances(self): m11.content()
    def test_verifier_uses_instance_validation(self):
        from unittest.mock import patch
        with patch.object(m11.gate,'validate_instance',wraps=m11.gate.validate_instance) as call:
            m11.content(); self.assertGreaterEqual(call.call_count,5)
    def test_missing_and_unknown_fields_rejected(self):
        for name,file in [('machine-contract','config/m11/machine-contract.json'),('console-contract','config/m11/console-contract.json'),('components','manifests/m11-components.lock.json'),('artifact-manifest','qa/golden/m11/manifest.json'),('public-qualification','qa/golden/m11/qualification.json')]:
            good=m11.read(ROOT/file); sch=m11.schema(ROOT,name)
            key=next(iter(good)); bad=copy.deepcopy(good); del bad[key]
            with self.subTest(name=name), self.assertRaises(m11.gate.Rejected):m11.gate.validate_instance(sch,bad)
            bad=copy.deepcopy(good);bad['unexpected']=True
            with self.subTest(name=name), self.assertRaises(m11.gate.Rejected):m11.gate.validate_instance(sch,bad)
    def test_synthetic_private_claim_rejected(self):
        q=m11.read(ROOT/'qa/golden/m11/qualification.json');q['production_memory_trace']=False
        with self.assertRaises(m11.gate.Rejected):m11.gate.validate_instance(m11.schema(ROOT,'public-qualification'),q)
    def test_bad_manifest_binding_rejected(self):
        q=m11.read(ROOT/'qa/golden/m11/qualification.json');q['artifact_manifest']['path']='qa/golden/m11/missing.json'
        with self.assertRaises(m11.gate.Rejected):m11.gate.validate_instance(m11.schema(ROOT,'public-qualification'),q)
if __name__=='__main__':unittest.main()
