#!/usr/bin/env python3
"""Small fail-closed filesystem helper for commands executed on the host."""

import hashlib
import os
import stat
import sys
from pathlib import Path


def regular_file(path_text: str):
    path = Path(path_text)
    try:
        file_stat = os.stat(path, follow_symlinks=False)
    except OSError as exc:
        raise SystemExit(f"cannot stat {path}: {exc}") from exc
    if not stat.S_ISREG(file_stat.st_mode):
        raise SystemExit(f"not a regular file: {path}")
    return path, file_stat


def digest(path: Path, algorithm: str) -> str:
    hasher = hashlib.new(algorithm)
    try:
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                hasher.update(block)
    except OSError as exc:
        raise SystemExit(f"cannot read {path}: {exc}") from exc
    return hasher.hexdigest()


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: host_fs.py {mode|size|sha256|md5} PATH")
    operation, path_text = sys.argv[1:]
    path, file_stat = regular_file(path_text)
    if operation == "mode":
        print(f"{stat.S_IMODE(file_stat.st_mode):04o}")
    elif operation == "size":
        print(file_stat.st_size)
    elif operation in {"sha256", "md5"}:
        print(digest(path, operation))
    else:
        raise SystemExit(f"unsupported operation: {operation}")


if __name__ == "__main__":
    main()
