"""Fresh-media allocation and readback must not require historical media."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('compose_image', ROOT / 'tools/m15/compose_image.py')
composer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(composer)


class SourceImageTests(unittest.TestCase):
    def test_public_profile_schema(self):
        import jsonschema
        schema = json.loads((ROOT / 'schema/m15-loader-overlay.schema.json').read_text())
        jsonschema.Draft202012Validator.check_schema(schema)
        profile = json.loads((ROOT / 'config/m15/loader.json').read_text())
        jsonschema.validate(profile, schema)
        profile['layout']['profile_class'] = 'unknown'
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(profile, schema)

    def test_roundtrip_fragment_boundary_and_empty_file(self):
        profile = json.loads((ROOT / 'config/m15/loader.json').read_text())
        payloads = {'LOADER.BIN': bytes(1500), 'EMPTY.TXT': b'',
                    'BOUNDARY.DAT': bytes(range(256)) * 8 + b'x'}
        with tempfile.TemporaryDirectory() as tmp:
            composer.compose(payloads, profile, Path(tmp), 1787814827)
            record = json.loads((Path(tmp) / 'media.json').read_text())
            self.assertEqual(record['allocations']['LOADER.BIN']['sector_count'], 2)
            self.assertEqual(record['allocations']['BOUNDARY.DAT']['sector_count'], 3)
            self.assertTrue(record['filesystem']['fat_copies_equal'])

    def test_reject_oversize_payload(self):
        profile = json.loads((ROOT / 'config/m15/loader.json').read_text())
        with tempfile.TemporaryDirectory() as tmp, self.assertRaisesRegex(ValueError, 'capacity'):
            composer.compose({'LOADER.BIN': bytes(1500), 'HUGE.DAT': bytes(1400000)},
                             profile, Path(tmp), 1787814827)
