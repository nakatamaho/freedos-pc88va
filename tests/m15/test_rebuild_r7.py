# SPDX-License-Identifier: GPL-2.0-or-later
"""Keep the r7 recipe closed over its source-built inputs."""
import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/m15"))
from rebuild_r7 import REQUIRED_REBUILDS, RebuildError, validate_profile


class RebuildR7ProfileTests(unittest.TestCase):
    def setUp(self):
        self.profile = {
            "format": "m15-r7-input-profile-v1",
            "candidate_id": "M15-QA-r6",
            "source_lock": {
                "parent_baseline_commit": "1" * 40,
                "fdkernel_commit": "2" * 40,
                "freecom_commit": "3" * 40,
                "country_commit": "4" * 40,
                "m13_carrier_fix_commit": "5" * 40,
                "carrier_builder_blob_sha1": "6" * 40,
                "fixture_source_commit": "7" * 40,
                "sysva_source_commit": "8" * 40,
            },
            "seed_media": {"size": 100, "sha256": "a" * 64},
            "payloads": [
                {"dos_name": name, "origin": "source_build", "path": "artifact.bin",
                 "size": 1, "sha256": "b" * 64, "source": "locked-source"}
                for name in sorted(REQUIRED_REBUILDS)
            ] + [
                {"dos_name": "SENTINEL.TXT", "origin": "r6_seed",
                 "reason": "immutable non-code seed payload"}
            ],
        }

    def test_complete_profile_is_accepted(self):
        self.assertIs(validate_profile(self.profile), self.profile)

    def test_missing_major_binary_is_rejected(self):
        changed = copy.deepcopy(self.profile)
        changed["payloads"] = [item for item in changed["payloads"]
                               if item["dos_name"] != "COMMAND.COM"]
        with self.assertRaisesRegex(RebuildError, "mandatory rebuilt payloads"):
            validate_profile(changed)

    def test_duplicate_payload_name_is_rejected(self):
        changed = copy.deepcopy(self.profile)
        changed["payloads"].append(copy.deepcopy(changed["payloads"][0]))
        with self.assertRaisesRegex(RebuildError, "duplicate payload"):
            validate_profile(changed)

    def test_malformed_source_identity_is_rejected(self):
        changed = copy.deepcopy(self.profile)
        changed["source_lock"]["fdkernel_commit"] = "not-a-commit"
        with self.assertRaisesRegex(RebuildError, "malformed 40-hex"):
            validate_profile(changed)

    def test_unknown_payload_field_is_rejected(self):
        changed = copy.deepcopy(self.profile)
        changed["payloads"][0]["observed_result"] = "PASS"
        with self.assertRaisesRegex(RebuildError, "incomplete or has unknown fields"):
            validate_profile(changed)


if __name__ == "__main__":
    unittest.main()
