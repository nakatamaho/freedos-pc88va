#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Public-only clean source exports; never build in a component or host bind mount.
set -euo pipefail
root=$(git rev-parse --show-toplevel)
cd "$root"
test "$#" = 3 || { echo 'usage: compare_public_builds.sh CHILD_SHA COMMAND.COM COUNTRY.SYS' >&2; exit 2; }
child=$1
[[ "$child" =~ ^[0-9a-f]{40}$ ]] || exit 2
test "$(git -C components/fdkernel rev-parse "$child^{commit}")" = "$child"
test -f "$2" && test -f "$3"
mkdir -p build
result=$(mktemp -d "$root/build/m10-public.XXXXXX")
image=${M10_BUILD_IMAGE:-freedos-pc88va-m01:local}
context=${M10_DOCKER_CONTEXT:-default}
docker_cmd=(docker --context "$context")
git -C components/fdkernel archive --format=tar --prefix=fdkernel/ "$child" > "$result/kernel.tar"
archive_sha=$(shasum -a 256 "$result/kernel.tar" | cut -d ' ' -f1)
container=''
trap 'if test -n "$container"; then "${docker_cmd[@]}" rm -f "$container" >/dev/null; fi' EXIT
for n in 1 2; do
  container=$("${docker_cmd[@]}" create --platform linux/amd64 --network none --user root --entrypoint bash \
    -e SOURCE_DATE_EPOCH=1787814827 -e WATCOM=/opt/openwatcom-1.9 -e INCLUDE=/opt/openwatcom-1.9/h \
    -e CHILD_COMMIT="$child" -e CHILD_ARCHIVE="$archive_sha" \
    -e PATH=/opt/openwatcom-1.9/binl:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    "$image" -ec '
      test "$(uname -m)" = x86_64
      test "$(dpkg --print-architecture)" = amd64
      mkdir -p /work/components /work/payload
      tar -xf /input/kernel.tar -C /work/components
      cp /input/COMMAND.COM /input/COUNTRY.SYS /work/payload/
      cd /work/components/fdkernel/pc88va
      wmake -ms -h -f makefile.wc clean all
      python3 tools/collect_build.py --repo-root /work/components/fdkernel --output /output/kernel-evidence --component-commit "$CHILD_COMMIT" --source-archive-sha256 "$CHILD_ARCHIVE"
      cp bin/KERNEL.SYS /work/payload/
      cp -r build /output/objects
      cd /work
      python3 tools/m10/rebuild_public.py --payload-dir /work/payload --output /output/media
    ')
  "${docker_cmd[@]}" cp "$result/kernel.tar" "$container:/input/kernel.tar"
  for p in tools config qa; do
    "${docker_cmd[@]}" cp "$p" "$container:/work/$p"
  done
  "${docker_cmd[@]}" cp "$2" "$container:/input/COMMAND.COM"
  "${docker_cmd[@]}" cp "$3" "$container:/input/COUNTRY.SYS"
  "${docker_cmd[@]}" inspect "$container" > "$result/container-$n.json"
  "${docker_cmd[@]}" image inspect "$image" > "$result/image-$n.json"
  "${docker_cmd[@]}" start -a "$container" > "$result/run-$n.log" 2>&1
  "${docker_cmd[@]}" cp "$container:/output" "$result/run-$n"
  "${docker_cmd[@]}" rm "$container" >/dev/null
  container=''
done
diff -r -x KVA8616.map "$result/run-1" "$result/run-2"
# Preserve both raw maps. Only their two host timing diagnostics may differ;
# canonical symbol evidence and all actual artifacts were compared above.
python3 tools/m09/compare_maps.py "$result/run-1/objects/KVA8616.map" "$result/run-2/objects/KVA8616.map"
echo 'M10 two clean public builds: objects, artifacts and canonical manifests byte-identical'
echo "Public generated evidence: $result"
