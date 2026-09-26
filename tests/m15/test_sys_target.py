# SPDX-License-Identifier: GPL-2.0-or-later
"""SYS target preparation must work with the public M15 disk layout."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/m15'))
from compose_image import compose
from prepare_sys_target import prepare
from media import inspect


class SysTargetTests(unittest.TestCase):
    def test_empty_target_reserves_loader_without_copying_system_code(self):
        profile = json.loads((ROOT / 'config/m15/loader.json').read_text())
        spec = json.loads((ROOT / 'config/m15/media.json').read_text())
        payloads = {'LOADER.BIN': b'x' * 1500, 'KERNEL.SYS': b'kernel',
                    'COMMAND.COM': b'shell', 'SYS.ID': b'M15SOURCE\r\n'}
        with tempfile.TemporaryDirectory() as tmp:
            source = compose(payloads, profile, Path(tmp), 1787814827)
            target, record = prepare(source, spec, 'M15TARGET')
        original, _ = inspect(source, spec)
        after, files = inspect(target, spec)
        self.assertEqual(set(files), {'LOADER.BIN', 'SYS.ID', 'SENTINEL.TXT'})
        self.assertEqual(files['LOADER.BIN'], bytes(1500))
        self.assertEqual(files['SYS.ID'], b'M15TARGET\r\n')
        self.assertEqual(original['files']['LOADER.BIN']['clusters'],
                         after['files']['LOADER.BIN']['clusters'])
        self.assertFalse(record['source_boot_code_copied'])
        self.assertFalse(record['system_payloads_copied'])
