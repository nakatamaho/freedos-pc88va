"""Keep the designated distribution bound to its compressed bytes and source."""
import hashlib
import json
import lzma
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools/m05'), str(ROOT / 'tools/m14')]
from inspect_fat12 import inspect


class DistributionTests(unittest.TestCase):
    def test_archive_source_binding_and_contents(self):
        directory = ROOT / 'images/milestones/m15'
        manifest = json.loads((directory / 'manifest.json').read_text())
        compressed = (directory / 'media.d88.xz').read_bytes()
        media = lzma.decompress(compressed)
        for name, data in [('media.d88.xz', compressed), ('media.d88', media)]:
            self.assertEqual({'size': len(data), 'sha256': hashlib.sha256(data).hexdigest()}, manifest[name])
        self.assertTrue(manifest['two_clean_builds_equal'])
        for component in ('fdkernel', 'freecom', 'country'):
            pin = subprocess.check_output(['git', 'rev-parse',
                    manifest['sources']['parent'] + ':components/' + component], cwd=ROOT, text=True).strip()
            self.assertEqual(pin, manifest['sources'][component])
        spec = json.loads((ROOT / 'config/m05/media.json').read_text())
        spec['d88']['disk_name'] = 'FDOS-PC88VA-M15'
        spec['image']['volume_label'] = 'PC88VA-M15'
        report, files = inspect(media, spec)
        self.assertTrue(report['fat_copies_equal'])
        self.assertEqual(set(files), {'KERNEL.SYS', 'LOADER.BIN', 'COMMAND.COM',
                                     'COUNTRY.SYS', 'SYSVA.EXE', 'SYS.ID'})
