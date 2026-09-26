#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Build the public M13 source/probe pair twice in isolated directories. The
# full Open Watcom target is selected by M13_BUILD_COMMAND in the accepted
# Linux/amd64 image; no host build product is ever copied into Git.
set -euo pipefail
root=$(git rev-parse --show-toplevel)
cd "$root"
child=${1:-33da21f248fa7af25f9dd17a7a981c34f8ebec37}
[[ "$child" =~ ^[0-9a-f]{40}$ ]] || { echo M13_CHILD_SHA_INVALID >&2; exit 2; }
test "$(git -C components/fdkernel rev-parse "$child^{commit}")" = "$child"
mkdir -p build
result=$(mktemp -d "$root/build/m13-public.XXXXXX")
export SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH:-1787814827}
for n in 1 2; do
  run="$result/run-$n"
  mkdir -p "$run/probes" "$run/source"
  git -C components/fdkernel archive --format=tar "$child" > "$run/source/fdkernel.tar"
  shasum -a 256 "$run/source/fdkernel.tar" | awk '{print $1}' > "$run/source/fdkernel.archive.sha256"
  nasm -f bin tests/m13/fixtures/com_probe.asm -o "$run/probes/com_probe.com"
  nasm -f obj tests/m13/fixtures/mz_probe.asm -o "$run/probes/mz_probe.obj"
  python3 - "$run" "$child" "$SOURCE_DATE_EPOCH" <<'PY'
import hashlib, json, pathlib, sys
run, child, epoch = pathlib.Path(sys.argv[1]), sys.argv[2], int(sys.argv[3])
def ident(p):
    b=p.read_bytes(); return {"size":len(b),"sha256":hashlib.sha256(b).hexdigest()}
record={"schema_version":1,"milestone":"M13","child_commit":child,
        "source_archive_sha256":run.joinpath("source/fdkernel.archive.sha256").read_text().strip(),
        "source_epoch":epoch,"probe_artifacts":{
          "com_probe":ident(run/"probes/com_probe.com"),
          "mz_probe_object":ident(run/"probes/mz_probe.obj")}}
(run/"build-record.json").write_text(json.dumps(record,sort_keys=True,indent=2)+"\n",encoding="utf-8")
PY
done
cmp "$result/run-1/build-record.json" "$result/run-2/build-record.json"
cmp "$result/run-1/probes/com_probe.com" "$result/run-2/probes/com_probe.com"
cmp "$result/run-1/probes/mz_probe.obj" "$result/run-2/probes/mz_probe.obj"
echo "M13 public source/probe builds are byte-identical"
echo "M13_BUILD_ROOT=$result"
