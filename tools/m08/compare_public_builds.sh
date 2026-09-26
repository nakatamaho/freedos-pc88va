#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Two clean, network-disabled builds; no component worktree build or bind mount.
set -euo pipefail
root=$(git rev-parse --show-toplevel)
cd "$root"
test "$#" = 2 || { echo 'usage: compare_public_builds.sh COMMAND.COM COUNTRY.SYS' >&2; exit 2; }
test -f "$1" && test -f "$2"
mkdir -p build
result=$(mktemp -d "$root/build/m08r2-public.XXXXXX")
mkdir "$result/qa"
cp -R qa/golden "$result/qa/golden"
image=${M08_BUILD_IMAGE:-freedos-pc88va-m01:local}
context=${M08_DOCKER_CONTEXT:-default}
docker_cmd=(docker --context "$context")
git -C components/fdkernel archive --format=tar --prefix=fdkernel/ 105d49a72ec41afe07fc1e7b080bdbd1b3026ae2 > "$result/kernel.tar"
test "$(shasum -a 256 "$result/kernel.tar" | cut -d ' ' -f1)" = 599da73e96e08118b199dbcb3540f1da8fd639c0eee03e49d5ddc58f5d4064f4
container=''
trap 'if test -n "$container"; then "${docker_cmd[@]}" rm -f "$container" >/dev/null; fi' EXIT
for n in 1 2; do
  container=$("${docker_cmd[@]}" create --platform linux/amd64 --network none --user root --entrypoint bash \
    -e SOURCE_DATE_EPOCH=1787814827 -e WATCOM=/opt/openwatcom-1.9 -e INCLUDE=/opt/openwatcom-1.9/h \
    -e PATH=/opt/openwatcom-1.9/binl:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    "$image" -ec '
      test "$(uname -m)" = x86_64
      test "$(dpkg --print-architecture)" = amd64
      mkdir -p /work/components /work/payload
      tar -xf /input/kernel.tar -C /work/components
      cp /input/COMMAND.COM /input/COUNTRY.SYS /work/payload/
      cd /work/components/fdkernel/pc88va
      wmake -ms -h -f makefile.wc clean all
      python3 tools/collect_build.py --repo-root /work/components/fdkernel --output /output/kernel-evidence --component-commit 105d49a72ec41afe07fc1e7b080bdbd1b3026ae2 --source-archive-sha256 599da73e96e08118b199dbcb3540f1da8fd639c0eee03e49d5ddc58f5d4064f4
      cp bin/KERNEL.SYS /work/payload/
      cp -r build /output/objects
      cd /work
      python3 tools/m08/rebuild_public.py --payload-dir /work/payload --output /output/media
    ')
  "${docker_cmd[@]}" cp "$result/kernel.tar" "$container:/input/kernel.tar"
  for p in tools config qa/golden; do
    if test "$p" = qa/golden; then
      "${docker_cmd[@]}" cp "$result/qa" "$container:/work/qa"
    else
      "${docker_cmd[@]}" cp "$p" "$container:/work/$p"
    fi
  done
  "${docker_cmd[@]}" cp "$1" "$container:/input/COMMAND.COM"
  "${docker_cmd[@]}" cp "$2" "$container:/input/COUNTRY.SYS"
  "${docker_cmd[@]}" start -a "$container" > "$result/run-$n.log" 2>&1
  "${docker_cmd[@]}" cp "$container:/output" "$result/run-$n"
  "${docker_cmd[@]}" rm "$container" >/dev/null
  container=''
done
# Raw WLink maps contain the host creation time. The accepted child collector
# parses them into symbol-evidence.json; compare that canonical evidence, and
# retain both raw maps as diagnostics without claiming their byte identity.
diff -r -x KVA8616.map "$result/run-1" "$result/run-2"
python3 - "$result" <<'PY'
from pathlib import Path
import sys
root = Path(sys.argv[1])
maps = [(root / f"run-{n}/objects/KVA8616.map").read_text() for n in (1, 2)]
def semantic(text):
    lines = text.splitlines()
    assert sum(line.startswith("Created on:") for line in lines) == 1
    return [line for line in lines if not line.startswith("Created on:")]
assert semantic(maps[0]) == semantic(maps[1]), "Link map differs beyond creation time"
PY
echo 'M08 two clean public builds: objects, artifacts and canonical manifests byte-identical'
echo "Public generated evidence: $result"
