#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Linux QA adapter for hosts where Unicorn's JIT cannot execute. No mounts.
set -euo pipefail
test "$#" = 1 || { echo 'usage: instruction_tests.sh PINNED_UNICORN_WHEEL' >&2; exit 2; }
root=$(git rev-parse --show-toplevel)
cd "$root"
wheel=$1
test "$(shasum -a 256 "$wheel" | cut -d ' ' -f1)" = 9d6e6dea140560de4ebd8446661f7ef84a357d428c14a3ef09dacd306ec8c239
mkdir -p build
result=$(mktemp -d "$root/build/m10-instruction-tests.XXXXXX")
docker_cmd=(docker --context "${M10_DOCKER_CONTEXT:-default}")
container=''
trap 'if test -n "$container"; then "${docker_cmd[@]}" rm -f "$container" >/dev/null; fi' EXIT
container=$("${docker_cmd[@]}" create --platform linux/amd64 --network none --user root --entrypoint bash \
  -e PYTHONDONTWRITEBYTECODE=1 -e PYTHONPATH=/work/qa \
  "${M10_BUILD_IMAGE:-freedos-pc88va-m01:local}" -ec '
    test "$(uname -m)" = x86_64
    test "$(dpkg --print-architecture)" = amd64
    unzip -q /input/unicorn.whl -d /work/qa
    cd /work
    python3 -m unittest discover -s pc88va/tests -p "test_*.py"
  ')
"${docker_cmd[@]}" inspect "$container" > "$result/container-before.json"
"${docker_cmd[@]}" cp "$wheel" "$container:/input/unicorn.whl"
"${docker_cmd[@]}" cp components/fdkernel/pc88va "$container:/work/pc88va"
rc=0
"${docker_cmd[@]}" start -a "$container" > "$result/result.log" 2>&1 || rc=$?
"${docker_cmd[@]}" inspect "$container" > "$result/container-after.json"
"${docker_cmd[@]}" rm "$container" >/dev/null
container=''
tail -n 80 "$result/result.log"
exit "$rc"
