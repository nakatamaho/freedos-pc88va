#!/usr/bin/env python3
"""Bounded negative and portability tests for the M02 artifact contract."""

import copy
import os
import shutil
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path, PurePosixPath

TOOLS_DIR = Path(__file__).resolve().parent
ROOT = TOOLS_DIR.parents[1]
sys.path.insert(0, str(TOOLS_DIR))

from assemble_bundle import assemble_once  # noqa: E402
from common import (  # noqa: E402
    ValidationError,
    canonical_json_bytes,
    component_identity,
    flatten_collision,
    load_canonical_json,
    m02_artifacts,
    sha256_file,
    validate_artifact_contract_records,
    validate_m01_input,
    write_sha256_sidecar,
)
from compare_bundles import compare_file  # noqa: E402
from verify_bundle import validate_bundle  # noqa: E402


class M02ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.authority = component_identity(ROOT)
        cls.m01_run = ROOT / "qa/results/m01/run-1"
        cls.artifacts = m02_artifacts(cls.authority)

    def expect_failure(self, function):
        with self.assertRaises(ValidationError):
            function()

    def copy_m01(self, temporary):
        destination = Path(temporary) / "m01"
        shutil.copytree(self.m01_run, destination)
        return destination

    def test_authority_roles_and_flatten_collision(self):
        self.assertEqual(len(self.artifacts), 10)
        validate_artifact_contract_records(self.artifacts)
        self.expect_failure(lambda: flatten_collision(self.artifacts))

    def test_missing_and_unexpected_payload(self):
        with tempfile.TemporaryDirectory() as temporary:
            missing = self.copy_m01(temporary)
            first = self.authority["artifacts"][0]["artifact"]
            (missing / "artifacts" / PurePosixPath(first)).unlink()
            self.expect_failure(lambda: validate_m01_input(missing, self.authority))
        with tempfile.TemporaryDirectory() as temporary:
            extra = self.copy_m01(temporary)
            (extra / "artifacts" / "unexpected.bin").write_bytes(b"unexpected")
            self.expect_failure(lambda: validate_m01_input(extra, self.authority))

    def test_mutation_wrong_size_recomputed_hash_and_symlink(self):
        first = self.authority["artifacts"][0]
        with tempfile.TemporaryDirectory() as temporary:
            mutated = self.copy_m01(temporary)
            path = mutated / "artifacts" / PurePosixPath(first["artifact"])
            data = path.read_bytes()
            path.write_bytes(data[:-1] + bytes([data[-1] ^ 1]))
            self.expect_failure(lambda: validate_m01_input(mutated, self.authority))
        with tempfile.TemporaryDirectory() as temporary:
            wrong_size = self.copy_m01(temporary)
            path = wrong_size / "artifacts" / PurePosixPath(first["artifact"])
            path.write_bytes(path.read_bytes() + b"x")
            manifest_path = wrong_size / "manifest.json"
            manifest = __import__("json").loads(manifest_path.read_text())
            for record in manifest["artifacts"]:
                if record["artifact"] == first["artifact"]:
                    record["size"] = path.stat().st_size
                    record["sha256"] = sha256_file(path)
            manifest_path.write_bytes(canonical_json_bytes(manifest))
            self.expect_failure(lambda: validate_m01_input(wrong_size, self.authority))
        with tempfile.TemporaryDirectory() as temporary:
            symlinked = self.copy_m01(temporary)
            path = symlinked / "artifacts" / PurePosixPath(first["artifact"])
            target = symlinked / "manifest.json"
            path.unlink()
            path.symlink_to(target)
            self.expect_failure(lambda: validate_m01_input(symlinked, self.authority))

    def test_path_traversal_hardlink_and_swapped_country(self):
        first = self.authority["artifacts"][0]
        with tempfile.TemporaryDirectory() as temporary:
            traversal = self.copy_m01(temporary)
            manifest_path = traversal / "manifest.json"
            manifest = __import__("json").loads(manifest_path.read_text())
            manifest["artifacts"][0]["artifact"] = "../outside"
            manifest_path.write_bytes(canonical_json_bytes(manifest))
            self.expect_failure(lambda: validate_m01_input(traversal, self.authority))
        with tempfile.TemporaryDirectory() as temporary:
            hardlink = self.copy_m01(temporary)
            path = hardlink / "artifacts" / PurePosixPath(first["artifact"])
            target = hardlink / "artifacts" / PurePosixPath(self.authority["artifacts"][1]["artifact"])
            path.unlink()
            os.link(target, path)
            self.expect_failure(lambda: validate_m01_input(hardlink, self.authority))
        countries = [item for item in self.authority["artifacts"] if PurePosixPath(item["artifact"]).name.lower() == "country.sys"]
        with tempfile.TemporaryDirectory() as temporary:
            swapped = self.copy_m01(temporary)
            first_path = swapped / "artifacts" / PurePosixPath(countries[0]["artifact"])
            second_path = swapped / "artifacts" / PurePosixPath(countries[1]["artifact"])
            first_bytes, second_bytes = first_path.read_bytes(), second_path.read_bytes()
            first_path.write_bytes(second_bytes)
            second_path.write_bytes(first_bytes)
            self.expect_failure(lambda: validate_m01_input(swapped, self.authority))

    def test_superseded_m01_contract_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            stale = self.copy_m01(temporary)
            manifest_path = stale / "manifest.json"
            manifest = __import__("json").loads(manifest_path.read_text())
            # Deliberately use a superseded pre-M01R1 contract identity. This
            # is a negative fixture, never an accepted M02 input identity.
            manifest["contract_sha256"] = "85a3a9a96b4b5fb4f4d1d90f836c97eade24a639de4aa0f908640ca91057759c"
            manifest_path.write_bytes(canonical_json_bytes(manifest))
            self.expect_failure(lambda: validate_m01_input(stale, self.authority))

    def test_duplicate_role_and_bundle_path(self):
        duplicate_role = copy.deepcopy(self.artifacts)
        duplicate_role[1]["role"] = duplicate_role[0]["role"]
        self.expect_failure(lambda: validate_artifact_contract_records(duplicate_role))
        duplicate_path = copy.deepcopy(self.artifacts)
        duplicate_path[1]["bundle_path"] = duplicate_path[0]["bundle_path"]
        self.expect_failure(lambda: validate_artifact_contract_records(duplicate_path))

    def test_generated_metadata_json_rejections(self):
        from common import reject_generated_metadata_values

        self.expect_failure(lambda: reject_generated_metadata_values({"absolute": "/tmp/value"}))
        self.expect_failure(lambda: reject_generated_metadata_values({"generated_at": "2026-08-29T00:00:00Z"}))
        with tempfile.TemporaryDirectory() as temporary:
            malformed = Path(temporary) / "malformed.json"
            malformed.write_bytes(b"{not-json}\n")
            self.expect_failure(lambda: load_canonical_json(malformed))
            missing_newline = Path(temporary) / "missing-newline.json"
            missing_newline.write_bytes(b'{"schema_version": 1}')
            self.expect_failure(lambda: load_canonical_json(missing_newline))

    def test_tampered_copied_metadata_and_tar_attributes(self):
        with tempfile.TemporaryDirectory() as temporary:
            run = Path(temporary) / "run-1"
            assemble_once(ROOT, self.authority, self.m01_run, run, "run-1")
            lock = run / "baseline-artifact-bundle/metadata/components.lock.json"
            original_lock = lock.read_bytes()
            lock.write_bytes(original_lock[:-1] + bytes([original_lock[-1] ^ 1]))
            self.expect_failure(lambda: validate_bundle(ROOT, self.authority, run, self.m01_run))
            lock.write_bytes(original_lock)
            contract = run / "baseline-artifact-bundle/metadata/m01-build-contract.json"
            original_contract = contract.read_bytes()
            contract.write_bytes(original_contract[:-1] + bytes([original_contract[-1] ^ 1]))
            self.expect_failure(lambda: validate_bundle(ROOT, self.authority, run, self.m01_run))
            contract.write_bytes(original_contract)

            archive_path = run / "baseline-artifact-bundle.tar"
            original_archive = archive_path.read_bytes()
            original_sidecar = (run / "baseline-artifact-bundle.tar.sha256").read_bytes()
            for attribute, value in (("uid", 1), ("gid", 1), ("mode", 0o600), ("mtime", 1)):
                modified = Path(temporary) / f"modified-{attribute}.tar"
                with tarfile.open(archive_path, "r:") as source, tarfile.open(modified, "w", format=tarfile.USTAR_FORMAT) as destination:
                    for member in source.getmembers():
                        info = copy.copy(member)
                        if member.name.endswith("/KERNEL.SYS"):
                            setattr(info, attribute, value)
                        stream = source.extractfile(member) if member.isreg() else None
                        destination.addfile(info, stream)

                archive_path.write_bytes(modified.read_bytes())
                write_sha256_sidecar(archive_path, run / "baseline-artifact-bundle.tar.sha256")
                self.expect_failure(lambda: validate_bundle(ROOT, self.authority, run, self.m01_run))
                archive_path.write_bytes(original_archive)
                (run / "baseline-artifact-bundle.tar.sha256").write_bytes(original_sidecar)

    def test_tar_comparison_mismatch(self):
        with tempfile.TemporaryDirectory() as temporary:
            first = Path(temporary) / "run-1.tar"
            second = Path(temporary) / "run-2.tar"
            first.write_bytes(b"first")
            second.write_bytes(b"second")
            errors = []
            compare_file(first, second, "tar", errors)
            self.assertTrue(errors)


if __name__ == "__main__":
    unittest.main(verbosity=2)
