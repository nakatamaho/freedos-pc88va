#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Compare WLink maps except explicitly identified host timing diagnostics.

Neither raw map is a reproducible artifact. Canonical child symbol evidence
is compared independently with every object, executable and manifest.
"""
from pathlib import Path
import re
import sys


def semantic_lines(text):
    lines = text.splitlines()
    fields = (r"Created on:\s+\d{2}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}",
              r"Link time: \d{2}:\d{2}\.\d{2}")
    omitted = set()
    for pattern in fields:
        matches = [i for i, line in enumerate(lines) if re.fullmatch(pattern, line)]
        if len(matches) != 1:
            raise ValueError("unexpected WLink timing diagnostic format")
        omitted.add(matches[0])
    return [line for i, line in enumerate(lines) if i not in omitted]


def compare(first, second):
    if semantic_lines(first) != semantic_lines(second):
        raise ValueError("link map differs outside host timing diagnostics")


if __name__ == "__main__":
    compare(Path(sys.argv[1]).read_text(), Path(sys.argv[2]).read_text())
