#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Two clean network-free kernel/probe builds in the pinned M01 container."""
import argparse
import gzip
import io
import json
from pathlib import Path
import subprocess
import tarfile

from verify_m14 import COMPONENTS, ROOT, digest, require


def call(*args):
    return subprocess.check_output(args)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--image", default="freedos-pc88va-m01:local")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    image = json.loads(call("docker", "image", "inspect", args.image))[0]
    require(image["Architecture"] == "amd64" and image["Os"] == "linux", "IMAGE_ARCHITECTURE")
    image_id = image["Id"]
    source = call("git", "-C", str(ROOT / "components/fdkernel"), "archive", "--format=tar",
                  "--prefix=fdkernel/", COMPONENTS["fdkernel"])
    (output / "source.tar.gz").write_bytes(gzip.compress(source, mtime=0))
    freecom = call("git", "-C", str(ROOT / "components/freecom"), "archive", "--format=tar",
                   "--prefix=freecom/", COMPONENTS["freecom"])
    (output / "freecom.tar.gz").write_bytes(gzip.compress(freecom, mtime=0))
    # Export only public fixture/build inputs, never a host source bind mount.
    with tarfile.open(output / "inputs.tar.gz", "w:gz") as archive:
        paths = list((ROOT / "tests/m14/fixtures").glob("*.asm")) + [
            ROOT / "tools/m14/build_block_probe.sh", ROOT / "config/m05/media.json",
            ROOT / "manifests/toolchains.lock.json", ROOT / "config/m01/freecom-build-timestamp.json"]
        for path in sorted(paths):
            data = path.read_bytes()
            entry = tarfile.TarInfo(path.relative_to(ROOT).as_posix())
            entry.size = len(data)
            entry.mode = 0o644
            entry.mtime = 1787814827
            archive.addfile(entry, io.BytesIO(data))
    command = """set -eu
test "$(uname -m)" = x86_64
test "$(dpkg --print-architecture)" = amd64
mkdir -p /work/source /work/inputs /work/result
tar -xf /tmp/source.tar.gz -C /work/source
tar -xf /tmp/freecom.tar.gz -C /work/source
tar -xf /tmp/inputs.tar.gz -C /work/inputs
python3 - <<'PY'
import hashlib,json,pathlib
lock=json.loads(pathlib.Path('/work/inputs/manifests/toolchains.lock.json').read_text())
for entry in lock['canonical']['open_watcom']['host_tools']:
    data=pathlib.Path('/opt/openwatcom-1.9',entry['path']).read_bytes()
    assert len(data)==entry['size'] and hashlib.sha256(data).hexdigest()==entry['sha256']
PY
export PATH=/opt/openwatcom-1.9/binl:$PATH
export SOURCE_DATE_EPOCH=1787814827
cd /work/source/fdkernel/pc88va
wmake -ms -h -f makefile.m13.wc clean all
cp bin/KERNEL.SYS /work/result/
cp build/KVA8616.map /work/result/
for name in file full swap io read; do
    nasm -f bin /work/inputs/tests/m14/fixtures/m14_${name}_probe.asm -o /work/result/m14_${name}.com
done
bash /work/inputs/tools/m14/build_block_probe.sh /work/source/fdkernel /work/inputs/tests/m14/fixtures /work/inputs/config/m05/media.json /work/raw
cp /work/raw/*.exe /work/result/
cd /work/source/freecom
python3 - <<'PY'
import json,pathlib
stamp=json.loads(pathlib.Path('/work/inputs/config/m01/freecom-build-timestamp.json').read_text())
source=pathlib.Path('config.std').read_text()
line='CFLAGS2 = -DFREECOM_BUILD_DATE=\\\\"'+stamp['formatted_date']+'\\\\" -DFREECOM_BUILD_TIME=\\\\"'+stamp['formatted_time']+'\\\\"\\n'
assert source.count('$(CFG):')==1
pathlib.Path('config.mak').write_text(source.replace('$(CFG):',line+'$(CFG):',1))
PY
# Only this build-host resource utility uses the locked native GCC. All DOS
# objects and the final shell still use the canonical Open Watcom 1.9 tools.
gcc utilsc/critstrs.c -o utilsc/critstrs.exe
bash build.sh generic no-xms-swap wc english
cp command.com /work/result/COMMAND.COM
"""
    records = []
    for number in (1, 2):
        run = output / f"run-{number}"
        cid = call("docker", "create", "--platform", "linux/amd64", "--network", "none",
                   "--entrypoint", "bash", image_id, "-ec", command).decode().strip()
        (output / f"container-{number}.json").write_text(json.dumps(
            {"container": cid, "image": image_id, "command": command}, indent=2) + "\n")
        for name in ("source.tar.gz", "freecom.tar.gz", "inputs.tar.gz"):
            subprocess.run(["docker", "cp", str(output / name), cid + ":/tmp/" + name], check=True)
        with (output / f"build-{number}.log").open("xb") as log:
            process = subprocess.run(["docker", "start", "-a", cid], stdout=log, stderr=subprocess.STDOUT)
        final = json.loads(call("docker", "inspect", cid))[0]
        (output / f"container-{number}-final.json").write_text(json.dumps(final, indent=2) + "\n")
        require(process.returncode == 0 and final["State"]["ExitCode"] == 0, "BUILD_FAILED")
        subprocess.run(["docker", "cp", cid + ":/work/result", str(run)], check=True)
        artifacts = {}
        for path in sorted(run.iterdir()):
            # Raw maps contain wall-clock headers. Retain them as evidence;
            # compare the actual executable artifacts, not timestamp text.
            if path.suffix.lower() == ".map":
                continue
            data = path.read_bytes()
            artifacts[path.name] = {"size": len(data), "sha256": digest(data)}
        record = {"child_commit": COMPONENTS["fdkernel"], "source_archive_sha256": digest(source),
                  "freecom_commit": COMPONENTS["freecom"], "freecom_archive_sha256": digest(freecom),
                  "freecom_timestamp_sha256": digest((ROOT / "config/m01/freecom-build-timestamp.json").read_bytes()),
                  "toolchain_sha256": digest((ROOT / "manifests/toolchains.lock.json").read_bytes()),
                  "architecture": "amd64", "uname": "x86_64", "source_date_epoch": 1787814827,
                  "upx": False, "artifacts": artifacts}
        (run / "build-record.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
        records.append(record)
        print(f"M14 clean build {number} completed", flush=True)
        subprocess.run(["docker", "rm", cid], check=True, stdout=subprocess.DEVNULL)
    require(records[0] == records[1], "TWO_CLEAN_BUILDS_DIFFER")
    print("M14_BUILD_ROOT=" + str(output))


if __name__ == "__main__":
    main()
