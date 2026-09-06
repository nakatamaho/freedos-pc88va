#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Emit only the closed abstract qualification model. Never run an emulator."""
import argparse
import json
from pathlib import Path
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]


def project(value, schema):
    try:
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(value)
    except Exception:
        raise ValueError('qualification projection rejected; details withheld') from None
    # Closed schemas reject unknown fields at every level, rather than silently
    # dropping data that might conceal an incorrectly assembled qualification.
    return json.dumps(value, sort_keys=True, indent=2) + '\n'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.input.is_symlink() or not args.input.is_file():
            raise ValueError('regular input required')
        schema = json.loads((ROOT/'schema/m09-public-qualification.schema.json').read_text())
        encoded = project(json.loads(args.input.read_text()), schema)
        with args.output.open('x') as stream:
            stream.write(encoded)
    except (OSError, ValueError):
        raise SystemExit('qualification redaction failed; details withheld') from None
