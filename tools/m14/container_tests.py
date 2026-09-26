#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Export public sources and offline wheels for the shared amd64 test suite."""
import argparse
import gzip
import io
import json
from pathlib import Path
import subprocess
import tarfile

from verify_m14 import ROOT, COMPONENTS, require


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    parser.add_argument("--wheelhouse", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    source = args.output / "public-source.tar.gz"
    with tarfile.open(source, "w:gz") as archive:
        paths = [ROOT / "Makefile", *list((ROOT / ".github/workflows").glob("*.yml"))]
        for name in ("tools", "tests", "config", "schema", "manifests", "qa/golden", "docs/porting"):
            paths.extend(p for p in (ROOT / name).rglob("*")
                         if p.is_file() and p.suffix in (".py", ".sh", ".asm", ".txt", ".json", ".md", ".inc"))
        for path in sorted(set(paths)):
            require(not path.is_symlink(), "SOURCE_SYMLINK")
            data = path.read_bytes()
            item = tarfile.TarInfo("repo/" + path.relative_to(ROOT).as_posix())
            item.size, item.mode = len(data), 0o755 if path.stat().st_mode & 0o111 else 0o644
            archive.addfile(item, io.BytesIO(data))
        for name, sha in COMPONENTS.items():
            data = subprocess.check_output(["git", "-C", str(ROOT / "components" / name),
                                            "archive", "--format=tar", sha])
            with tarfile.open(fileobj=io.BytesIO(data)) as child:
                for entry in child:
                    content = child.extractfile(entry) if entry.isfile() else None
                    entry.name = "repo/components/" + name + "/" + entry.name
                    archive.addfile(entry, content)
    wheels = list(args.wheelhouse.glob("*.whl"))
    require(bool(wheels), "OFFLINE_WHEELS_MISSING")
    with tarfile.open(args.output / "wheels.tar", "w") as archive:
        for path in wheels:
            archive.add(path, arcname=path.name)
    command = """set -eu
test "$(uname -m)" = x86_64
test "$(dpkg --print-architecture)" = amd64
mkdir -p /work/wheels /work/python
tar -xf /tmp/source.tar.gz -C /work
tar -xf /tmp/wheels.tar -C /work/wheels
python3 - <<'PY'
import pathlib,zipfile
for path in pathlib.Path('/work/wheels').glob('*.whl'):
    with zipfile.ZipFile(path) as wheel: wheel.extractall('/work/python')
PY
export PYTHONPATH=/work/python
export PYTHONDONTWRITEBYTECODE=1
cd /work/repo
python3 -B tools/m14/run_tests.py
"""
    cid = subprocess.check_output(["docker", "create", "--platform", "linux/amd64", "--network", "none",
                                   "--entrypoint", "bash", args.image, "-ec", command], text=True).strip()
    (args.output / "command.json").write_text(json.dumps({"container": cid, "command": command}, indent=2))
    for path, target in ((source, "source.tar.gz"), (args.output / "wheels.tar", "wheels.tar")):
        subprocess.run(["docker", "cp", str(path), cid + ":/tmp/" + target], check=True)
    with (args.output / "tests.log").open("xb") as log:
        process = subprocess.run(["docker", "start", "-a", cid], stdout=log, stderr=subprocess.STDOUT)
    final = json.loads(subprocess.check_output(["docker", "inspect", cid]))[0]
    (args.output / "container-final.json").write_text(json.dumps(final, indent=2))
    require(process.returncode == 0 and final["State"]["ExitCode"] == 0, "CONTAINER_TEST_FAILURE")
    subprocess.run(["docker", "rm", cid], check=True, stdout=subprocess.DEVNULL)
    print("Shared M14 tests passed in Linux/amd64")


if __name__ == "__main__":
    main()
