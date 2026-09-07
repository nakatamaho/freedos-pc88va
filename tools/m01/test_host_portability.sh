#!/usr/bin/env bash
set -eu

M01_TEST_DIR=$(mktemp -d /tmp/m01-host-portability.XXXXXX)

cleanup() {
    case "$M01_TEST_DIR" in
        /tmp/m01-host-portability.*)
            rm -rf -- "$M01_TEST_DIR"
            ;;
        *)
            printf 'error: refusing to clean unexpected test path: %s\n' "$M01_TEST_DIR" >&2
            ;;
    esac
}
trap cleanup EXIT

M01_ROOT=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
M01_HOST_FS=$M01_ROOT/tools/m01/host_fs.py

portable_file_mode() {
    [ "$#" -eq 1 ] || {
        printf '%s\n' 'expected exactly one path' >&2
        return 64
    }
    python3 "$M01_HOST_FS" mode "$1"
}

require_staging_mode() {
    [ "$#" -eq 1 ] || return 64
    local mode
    mode=$(portable_file_mode "$1")
    case "$mode" in
        0[0-7][0-7][0-7]) ;;
        *) return 1 ;;
    esac
    [ "$mode" = 0444 ]
}

regular_0444=$M01_TEST_DIR/regular-0444
regular_other=$M01_TEST_DIR/regular-other
symlink_path=$M01_TEST_DIR/symlink
printf '%s\n' 'probe' >"$regular_0444"
printf '%s\n' 'probe' >"$regular_other"
chmod 0444 "$regular_0444"
chmod 0644 "$regular_other"
ln -s "$regular_0444" "$symlink_path"

[ "$(portable_file_mode "$regular_0444")" = 0444 ]
if require_staging_mode "$regular_other"; then
    printf '%s\n' 'error: writable regular file was accepted by staging validation' >&2
    exit 1
fi
if portable_file_mode "$symlink_path" >/dev/null; then
    printf '%s\n' 'error: symlink was accepted by portable_file_mode' >&2
    exit 1
fi
if portable_file_mode "$M01_TEST_DIR/missing" >/dev/null; then
    printf '%s\n' 'error: missing path was accepted by portable_file_mode' >&2
    exit 1
fi

for malformed in '' 044 04444 mode; do
    if case "$malformed" in
        0[0-7][0-7][0-7]) [ "$malformed" = 0444 ] ;;
        *) false ;;
    esac
    then
        printf 'error: malformed mode was accepted: %s\n' "$malformed" >&2
        exit 1
    fi
done

python3 - "$M01_ROOT/tools/m01/build_baseline.sh" <<'PY'
import sys
from pathlib import Path

text = Path(sys.argv[1]).read_text(encoding="utf-8")
audit_start = text.index("record_host_portability_audit() {")
audit_end = text.index("\ndownload_verified_openwatcom()", audit_start)
text = text[:audit_start] + text[audit_end:]
for forbidden in ("stat -c", "sha256sum", "shasum"):
    if forbidden in text:
        raise SystemExit(f"host harness still invokes {forbidden} directly")
PY

printf '%s\n' 'host portability regression passed: mode, regular-file, symlink, missing-path, malformed-mode, and GNU-command checks'
