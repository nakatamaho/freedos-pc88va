#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Run the active ROM-free M14 suites without accepting skipped cases."""
import importlib.util
from pathlib import Path
import platform
import unittest

ROOT = Path(__file__).resolve().parents[2]


def main():
    if platform.system() != "Linux" or platform.machine() not in ("x86_64", "AMD64"):
        raise SystemExit("Run the complete Unicorn gate on Linux/amd64")
    import unicorn
    if unicorn.__version__ != "2.1.4":
        raise SystemExit("Unicorn 2.1.4 is required")
    suites = [unittest.defaultTestLoader.discover(str(ROOT / "tests/m14"), pattern="test_*.py")]
    # The historical read-only M13 verifier stays bound to its own checkout.
    for name in ("test_memory_placement", "test_lzss_encoder", "test_init_lifetime_contract"):
        spec = importlib.util.spec_from_file_location(name, ROOT / "tests/m13" / (name + ".py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        suites.append(unittest.defaultTestLoader.loadTestsFromModule(module))
    suites.append(unittest.TestLoader().discover(str(ROOT / "components/fdkernel/pc88va/tests"),
                                                 pattern="test_*.py"))
    result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(suites))
    return 0 if result.wasSuccessful() and not result.skipped else 1


if __name__ == "__main__":
    raise SystemExit(main())
