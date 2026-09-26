#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Reject incomplete, stale and misbound acceptance evidence."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import shutil

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("m14_acceptance", ROOT / "tools/m14/verify_m14.py")
VERIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)


class AcceptanceTests(unittest.TestCase):
    def test_actual_instances_and_complete_public_references(self):
        VERIFY.content(ROOT, check_git=False)

    def test_missing_unknown_and_malformed_fields(self):
        schema = VERIFY.load(ROOT / "schema/m14-acceptance.schema.json")
        for path in ("manifests/m14-components.lock.json", "qa/golden/m14/manifest.json",
                     "qa/golden/m14/qualification.json", "config/m14/machine-contract.json"):
            original = VERIFY.load(ROOT / path)
            for field in original:
                value = copy.deepcopy(original)
                del value[field]
                with self.subTest(path=path, missing=field), self.assertRaises(Exception):
                    VERIFY.validate(value, schema)
            value = copy.deepcopy(original)
            value["unknown"] = True
            with self.assertRaises(Exception):
                VERIFY.validate(value, schema)
        value = VERIFY.load(ROOT / "config/m14/machine-contract.json")
        value["artifact_manifest"]["sha256"] = "0" * 63
        with self.assertRaises(Exception):
            VERIFY.validate(value, schema)
        value = VERIFY.load(ROOT / "qa/golden/m14/qualification.json")
        del value["gates"]["M14-CHANGE"]
        with self.assertRaises(Exception):
            VERIFY.validate(value, schema)
        value = VERIFY.load(ROOT / "qa/golden/m14/qualification.json")
        value["hardware"] = "HARDWARE PASS"
        with self.assertRaises(Exception):
            VERIFY.validate(value, schema)

    def test_reference_missing_drift_and_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "evidence.json"
            path.write_text("{}\n")
            value = {"path": path.name, "sha256": VERIFY.digest(path.read_bytes())}
            self.assertEqual(VERIFY.reference(root, value), path)
            for bad in ({**value, "sha256": "f" * 64}, {**value, "path": "missing.json"},
                        {**value, "path": "../evidence.json"}, {**value, "path": str(path)},
                        {**value, "unknown": True}):
                with self.subTest(bad=bad), self.assertRaises(VERIFY.Rejected):
                    VERIFY.reference(root, bad)
            link = root / "link.json"
            link.symlink_to(path)
            with self.assertRaises(VERIFY.Rejected):
                VERIFY.reference(root, {**value, "path": link.name})

    def test_rehashed_but_incomplete_dependency_topology_is_rejected(self):
        paths = [item["path"] for item in VERIFY.load(ROOT / "qa/golden/m14/manifest.json")["artifacts"]]
        paths += ["schema/m14-acceptance.schema.json", "config/m14/machine-contract.json",
                  "manifests/m14-components.lock.json", "manifests/toolchains.lock.json",
                  "qa/golden/m14/manifest.json", "qa/golden/m14/qualification.json"]
        for defect in ("missing-artifact", "duplicate-artifact", "wrong-component", "unknown-gate"):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                for name in paths:
                    target = root / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(ROOT / name, target)
                manifest = VERIFY.load(root / "qa/golden/m14/manifest.json")
                qual = VERIFY.load(root / "qa/golden/m14/qualification.json")
                if defect == "missing-artifact":
                    manifest["artifacts"].pop()
                elif defect == "duplicate-artifact":
                    manifest["artifacts"].append(manifest["artifacts"][0])
                elif defect == "wrong-component":
                    qual["components"]["fdkernel"] = "f" * 40
                else:
                    qual["gates"]["M14-UNKNOWN"] = "VAEG PASS"
                def save(name, value):
                    (root / name).write_text(json.dumps(value))
                    return {"path": name, "sha256": VERIFY.digest((root / name).read_bytes())}
                mref = save("qa/golden/m14/manifest.json", manifest)
                qual["artifact_manifest"] = mref
                qref = save("qa/golden/m14/qualification.json", qual)
                contract = VERIFY.load(root / "config/m14/machine-contract.json")
                contract.update(artifact_manifest=mref, qualification=qref)
                save("config/m14/machine-contract.json", contract)
                with self.assertRaises(Exception):
                    VERIFY.content(root, check_git=False)

    def test_ci_head_attempt_and_required_jobs(self):
        head = "a" * 40
        good = {"headSha": head, "attempt": 2, "status": "completed", "conclusion": "success",
                "jobs": [{"name": "build", "status": "completed", "conclusion": "success",
                          "steps": [{"name": "compile", "conclusion": "success"}]}]}
        VERIFY.check_ci(good, head, ["build"], 2)
        mutations = []
        for key, value in (("headSha", "b" * 40), ("attempt", 1), ("status", "in_progress"),
                           ("conclusion", "failure"), ("jobs", [])):
            mutations.append({**good, key: value})
        for key, value in (("name", "unrelated"), ("conclusion", "skipped"), ("steps", [])):
            bad = copy.deepcopy(good)
            bad["jobs"][0][key] = value
            mutations.append(bad)
        bad = copy.deepcopy(good)
        bad["jobs"].append(copy.deepcopy(bad["jobs"][0]))
        mutations.append(bad)
        for bad in mutations:
            with self.subTest(bad=bad), self.assertRaises(VERIFY.Rejected):
                VERIFY.check_ci(bad, head, ["build"], 2)


if __name__ == "__main__":
    unittest.main()
