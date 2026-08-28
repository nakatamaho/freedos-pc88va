#!/usr/bin/env bash
set -eu

umask 022

probe_dir=

cleanup_probe_dir() {
    case "${probe_dir-}" in
        "") ;;
        /tmp/m01-wcc-probe.*)
            if [ -d "$probe_dir" ]; then
                rm -rf -- "$probe_dir"
            fi
            ;;
        *)
            printf 'error: refusing to clean an unexpected WCC probe path: %s\n' "$probe_dir" >&2
            ;;
    esac
}

trap cleanup_probe_dir EXIT

usage() {
    printf '%s\n' "Usage: $0 COMPONENT RUN_ID ARCHIVE_NAME ARCHIVE_SHA256 CONFIGURATION_SHA256" >&2
    exit 64
}

component=${1-}
run_id=${2-}
archive_name=${3-}
archive_sha256=${4-}
configuration_sha256=${5-}
[ -n "$component" ] && [ -n "$run_id" ] && [ -n "$archive_name" ] && [ -n "$archive_sha256" ] && [ -n "$configuration_sha256" ] || usage

case "$component" in
    fdkernel)
        source_root=/work/src/fdkernel
        work_directory=/work/src/fdkernel/nec98
        required_artifacts='fdkernel-nec98|nec98/bin/kernel.sys
fdkernel-nec98|nec98/bin/KWC8616.sys
fdkernel-nec98|nec98/bin/sys.com
fdkernel-country|nec98/bin/country.sys
fdkernel-nec98|nec98/boot/b_fat12f.bin
fdkernel-nec98|nec98/boot/b_fat12.bin
fdkernel-nec98|nec98/boot/b_fat16.bin
fdkernel-nec98|nec98/boot/b_fat32.bin'
        ;;
    freecom)
        source_root=/work/src/freecom
        work_directory=/work/src/freecom
        required_artifacts='freecom-nec98-japanese|command.com'
        ;;
    country)
        source_root=/work/src/country
        work_directory=/work/src/country
        required_artifacts='fdos-country|country.sys'
        ;;
    *)
        printf 'error: unknown component: %s\n' "$component" >&2
        exit 64
        ;;
    esac

case "$run_id" in
    run-1|run-2) ;;
    *)
        printf 'error: unknown run identifier: %s\n' "$run_id" >&2
        exit 64
        ;;
esac

case "$archive_name" in
    fdkernel.tar|freecom.tar|country.tar) ;;
    *)
        printf 'error: unexpected source archive name: %s\n' "$archive_name" >&2
        exit 64
        ;;
esac

input_archive=/input/${archive_name}
configuration_template=
output_root=/output
source_parent=/work/src
log_root=${output_root}/logs
manifest_path=${output_root}/container-manifest.json

verify_readonly_input() {
    local path=$1 expected_basename=$2 expected_sha256=$3 actual_sha256 mode
    [ -f "$path" ] && [ ! -L "$path" ] || { printf 'error: input is not a regular file: %s\n' "$path" >&2; exit 66; }
    [ "$(basename -- "$path")" = "$expected_basename" ] || {
        printf 'error: input basename mismatch: expected %s\n' "$expected_basename" >&2
        exit 66
    }
    mode=$(stat -c '%a' "$path")
    [ "$mode" = 444 ] || {
        printf 'error: input mode is not exactly 0444: %s (%s)\n' "$path" "$mode" >&2
        exit 66
    }
    actual_sha256=$(sha256sum "$path" | awk '{print $1}')
    [ "$actual_sha256" = "$expected_sha256" ] || {
        printf 'error: input SHA-256 mismatch: %s expected %s, got %s\n' "$path" "$expected_sha256" "$actual_sha256" >&2
        exit 65
    }
}

[ -d "$output_root" ] && [ -w "$output_root" ] || { printf 'error: output destination is unavailable\n' >&2; exit 66; }
verify_readonly_input "$input_archive" "$archive_name" "$archive_sha256"
actual_archive_sha256=$archive_sha256

if [ "$component" = fdkernel ]; then
    configuration_template=/input/fdkernel-nec98.mak
    [ "$configuration_sha256" != none ] || { printf 'error: fdkernel configuration digest is missing\n' >&2; exit 66; }
    verify_readonly_input "$configuration_template" fdkernel-nec98.mak "$configuration_sha256"
    actual_configuration_sha256=$configuration_sha256
elif [ "$component" = freecom ]; then
    configuration_template=/input/freecom-nec98.mak
    [ "$configuration_sha256" != none ] || { printf 'error: FreeCOM configuration digest is missing\n' >&2; exit 66; }
    verify_readonly_input "$configuration_template" freecom-nec98.mak "$configuration_sha256"
    actual_configuration_sha256=$configuration_sha256
else
    [ "$configuration_sha256" = none ] || { printf 'error: unexpected configuration template for %s\n' "$component" >&2; exit 66; }
fi

filesystem_type=$(stat -f -c %T /work)
case "$filesystem_type" in
    virtiofs|9p|fuse.sshfs|fuse.*)
        printf 'error: build root is not a container-local Linux filesystem: %s\n' "$filesystem_type" >&2
        exit 66
        ;;
esac

rm -rf "$source_parent"
mkdir -p "$source_parent" "$log_root" "$output_root/artifacts"
tar -xf "$input_archive" -C "$source_parent"
[ -d "$source_root" ] || { printf 'error: archive did not create expected source root\n' >&2; exit 66; }

export WATCOM=/opt/openwatcom-1.9
export EDPATH=/opt/openwatcom-1.9/eddat
export INCLUDE=/opt/openwatcom-1.9/h
export LIB=/opt/openwatcom-1.9/lib286
export PATH=/opt/openwatcom-1.9/binl:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export LC_ALL=C
export LANG=C
export TZ=UTC
unset XUPX UPXOPT

verify_tool_selection() {
    local tool tool_path resolved
    local wcc_resolved wmake_resolved wcc_file_info wmake_file_info
    local wcc_sha256 wmake_sha256 wcc_output wcc_status
    local wmake_output wmake_status probe_source probe_object probe_file
    local tool_file_info tool_size tool_sha256 tool_banner tool_banner_status
    local wmake_probe_dir wmake_probe_makefile wmake_probe_output wmake_probe_expected
    for tool in wcc wcl wmake wlink wasm wlib; do
        tool_path=$(command -v "$tool") || {
            printf 'error: required Open Watcom tool is unavailable: %s\n' "$tool" >&2
            exit 69
        }
        resolved=$(readlink -f "$tool_path")
        case "$resolved" in
            "$WATCOM/binl/"*) ;;
            *)
                printf 'error: %s resolved outside %s/binl: %s\n' "$tool" "$WATCOM" "$resolved" >&2
                exit 69
                ;;
        esac
    done
    for tool in wcc wcl wmake wlink wasm wlib; do
        tool_path=$(command -v "$tool")
        resolved=$(readlink -f "$tool_path")
        tool_file_info=$(file "$resolved")
        tool_size=$(stat -c '%s' "$resolved")
        tool_sha256=$(sha256sum "$resolved" | awk '{print $1}')
        printf '%s_size=%s\n' "$tool" "$tool_size"
        printf '%s_file=%s\n' "$tool" "$tool_file_info"
        printf '%s_sha256=%s\n' "$tool" "$tool_sha256"
        case "$tool_file_info" in
            *'ELF 32-bit'*'Intel 80386'*'statically linked'*) ;;
            *) printf 'error: %s is not a statically linked ELF i386 executable: %s\n' "$tool" "$tool_file_info" >&2; exit 69 ;;
        esac
        case "$tool" in
            wcc) [ "$tool_size" = 861645 ] && [ "$tool_sha256" = d882c85922da81aa7956cc5ee5aacc3e2a85932ef346c424ce508ff499d1aba6 ] || { printf 'error: wcc identity mismatch\n' >&2; exit 69; } ;;
            wcl) [ "$tool_size" = 51343 ] && [ "$tool_sha256" = 47911ca4b28875d5d9157e9054a68e88180eedd08a5f66a82e1cd864e6f38ba3 ] || { printf 'error: wcl identity mismatch\n' >&2; exit 69; } ;;
            wmake) [ "$tool_size" = 188973 ] && [ "$tool_sha256" = d13292a724fb000b51e719bf3a411c6870ab26e13b8e32855e88458a850de5b4 ] || { printf 'error: wmake identity mismatch\n' >&2; exit 69; } ;;
            wlink) [ "$tool_size" = 457386 ] && [ "$tool_sha256" = e285c328f48b17e115cb6fd0f91f348a915adfd9eeb932eb3e7b4f3b50fc2838 ] || { printf 'error: wlink identity mismatch\n' >&2; exit 69; } ;;
            wasm) [ "$tool_size" = 282185 ] && [ "$tool_sha256" = d4bc79eddea9afba5b6244203dd4ee4ef670161a099d0ea06f2a2943d4f23579 ] || { printf 'error: wasm identity mismatch\n' >&2; exit 69; } ;;
            wlib) [ "$tool_size" = 188291 ] && [ "$tool_sha256" = 0391b9363048520eb3e1da0712c42d096f9ef8407b2a450c2ae97b345a08ed84 ] || { printf 'error: wlib identity mismatch\n' >&2; exit 69; } ;;
        esac
        tool_banner=
        tool_banner_status=0
        tool_banner=$("$resolved" -? 2>&1) || tool_banner_status=$?
        printf '%s_banner_status=%s\n' "$tool" "$tool_banner_status"
        printf '%s\n' "$tool_banner"
        case "$tool" in
            wcc) printf '%s\n' "$tool_banner" | grep -F 'Open Watcom C16 Optimizing Compiler Version 1.9' >/dev/null ;;
            wcl) printf '%s\n' "$tool_banner" | grep -F 'Open Watcom C/C++16 Compile and Link Utility Version 1.9' >/dev/null ;;
            wmake) printf '%s\n' "$tool_banner" | grep -F 'Open Watcom Make Version 1.9' >/dev/null ;;
            wlink) printf '%s\n' "$tool_banner" | grep -F 'Open Watcom Linker Version 1.9' >/dev/null ;;
            wasm) printf '%s\n' "$tool_banner" | grep -F 'Open Watcom Assembler Version 1.9' >/dev/null ;;
            wlib) printf '%s\n' "$tool_banner" | grep -F 'Open Watcom Library Manager Version 1.9' >/dev/null ;;
        esac
    done
    wcc_resolved=$(readlink -f "$(command -v wcc)")
    wmake_resolved=$(readlink -f "$(command -v wmake)")
    wcc_file_info=$(file "$wcc_resolved")
    wmake_file_info=$(file "$wmake_resolved")
    wcc_sha256=$(sha256sum "$wcc_resolved" | awk '{print $1}')
    wmake_sha256=$(sha256sum "$wmake_resolved" | awk '{print $1}')
    case "$wcc_file_info" in
        *'ELF 32-bit'*'Intel 80386'*'statically linked'*) ;;
        *) printf 'error: wcc is not a statically linked ELF i386 executable: %s\n' "$wcc_file_info" >&2; exit 69 ;;
    esac
    case "$wmake_file_info" in
        *'ELF 32-bit'*'Intel 80386'*'statically linked'*) ;;
        *) printf 'error: wmake is not a statically linked ELF i386 executable: %s\n' "$wmake_file_info" >&2; exit 69 ;;
    esac
    [ "$wcc_sha256" = d882c85922da81aa7956cc5ee5aacc3e2a85932ef346c424ce508ff499d1aba6 ] || {
        printf 'error: wcc executable SHA-256 mismatch: %s\n' "$wcc_sha256" >&2
        exit 69
    }
    [ "$wmake_sha256" = d13292a724fb000b51e719bf3a411c6870ab26e13b8e32855e88458a850de5b4 ] || {
        printf 'error: wmake executable SHA-256 mismatch: %s\n' "$wmake_sha256" >&2
        exit 69
    }
    probe_dir=$(mktemp -d /tmp/m01-wcc-probe.XXXXXX)
    probe_source=$probe_dir/probe.c
    probe_object=$probe_dir/probe.obj
    printf '%s\n' \
        'int m01_wcc_probe(void)' \
        '{' \
        '    return 0;' \
        '}' >"$probe_source"
    printf 'wcc_probe_command=wcc -bt=dos %s -fo=%s\n' "$probe_source" "$probe_object"
    wcc_output=
    wcc_status=0
    wcc_output=$(wcc -bt=dos "$probe_source" "-fo=$probe_object" 2>&1) || wcc_status=$?
    printf '%s\n' "$wcc_output"
    printf 'wcc_probe_status=%s\n' "$wcc_status"
    [ "$wcc_status" -eq 0 ] || {
        printf 'error: WCC smoke test failed with status %s\n' "$wcc_status" >&2
        exit 69
    }
    printf '%s\n' "$wcc_output" | grep -F 'Open Watcom C16 Optimizing Compiler Version 1.9' >/dev/null || {
        printf 'error: WCC smoke output lacks the expected version banner\n' >&2
        exit 69
    }
    [ -s "$probe_object" ] || {
        printf 'error: WCC smoke test did not produce a non-empty object\n' >&2
        exit 69
    }
    probe_file=$(file "$probe_object")
    printf 'wcc_probe_object_size=%s\n' "$(stat -c '%s' "$probe_object")"
    printf 'wcc_probe_object_file=%s\n' "$probe_file"
    case "$probe_file" in
        *8086*relocat*|*relocat*8086*) ;;
        *) printf 'error: WCC smoke object is not identified as an 8086 relocatable object: %s\n' "$probe_file" >&2; exit 69 ;;
    esac
    {
        printf 'WATCOM=%s\n' "$WATCOM"
        printf 'PATH=%s\n' "$PATH"
        type -a wcc wcl wmake wlink wasm wlib
        printf 'wcc_resolved=%s\n' "$wcc_resolved"
        printf 'wmake_resolved=%s\n' "$wmake_resolved"
        printf 'wcc_file=%s\n' "$wcc_file_info"
        printf 'wmake_file=%s\n' "$wmake_file_info"
        printf 'wcc_sha256=%s\n' "$wcc_sha256"
        printf 'wmake_sha256=%s\n' "$wmake_sha256"
        printf '%s\n' '--- wmake real execution probe ---'
        wmake_probe_dir=$probe_dir/wmake
        mkdir -p "$wmake_probe_dir"
        wmake_probe_makefile=$wmake_probe_dir/probe.mak
        wmake_probe_output=$wmake_probe_dir/probe.ok
        wmake_probe_expected=$wmake_probe_dir/expected.ok
        {
            printf '%s\n' 'probe.ok:'
            printf '\t%s\n' '@echo M01_WMAKE_PROBE_OK'
            printf '\t%s\n' '@echo OK > probe.ok'
        } >"$wmake_probe_makefile"
        printf '%s\n' 'OK' >"$wmake_probe_expected"
        wmake_output=
        wmake_status=0
        wmake_output=$(cd "$wmake_probe_dir" && wmake -f probe.mak probe.ok 2>&1) || wmake_status=$?
        printf '%s\n' "$wmake_output"
        printf 'wmake_probe_status=%s\n' "$wmake_status"
        [ "$wmake_status" -eq 0 ] || {
            printf 'error: WMake real execution probe failed with status %s\n' "$wmake_status" >&2
            exit 69
        }
        printf '%s\n' "$wmake_output" | grep -Fx 'M01_WMAKE_PROBE_OK' >/dev/null || {
            printf 'error: WMake real execution output lacks the probe token\n' >&2
            exit 69
        }
        test -f "$wmake_probe_output"
        test -s "$wmake_probe_output"
        cmp -s "$wmake_probe_expected" "$wmake_probe_output"
        printf 'wmake_probe_output_size=%s\n' "$(stat -c '%s' "$wmake_probe_output")"
        printf 'wmake_probe_output_sha256=%s\n' "$(sha256sum "$wmake_probe_output" | awk '{print $1}')"
        printf 'wmake_probe_output_match=true\n'
        printf '%s\n' "$wmake_output" | grep -F 'Open Watcom Make Version 1.9' >/dev/null || {
            printf 'error: WMake probe output lacks the expected version banner\n' >&2
            exit 69
        }
    }
}

verify_tool_selection > /output/tool-selection.txt 2>&1

assert_no_compressor_environment() {
    if env | grep -E '^(XUPX|UPXOPT)=' >/dev/null; then
        printf 'error: compressor control variable reached a build command environment\n' >&2
        exit 68
    fi
}

verify_freecom_timestamp() {
    local timestamp_date=${M01_FREECOM_BUILD_DATE-}
    local timestamp_time=${M01_FREECOM_BUILD_TIME-}
    local timestamp_epoch=${SOURCE_DATE_EPOCH-}
    [ -n "$timestamp_date" ] && [ -n "$timestamp_time" ] && [ -n "$timestamp_epoch" ] || {
        printf 'error: deterministic FreeCOM timestamp environment is incomplete\n' >&2
        return 1
    }
    python3 - "$timestamp_epoch" "$timestamp_date" "$timestamp_time" "$configuration_template" "$work_directory/shell/watcomc.cfg" "$command_log" "$work_directory/shell/ver.obj" "$work_directory/shell/command.exe" "$work_directory/command.com" /output/freecom-timestamp.json <<'PY'
import hashlib
import json
import re
import sys
from pathlib import Path

epoch, expected_date, expected_time = sys.argv[1:4]
configuration_path = Path(sys.argv[4])
response_path = Path(sys.argv[5])
command_log_path = Path(sys.argv[6])
artifact_paths = [Path(value) for value in sys.argv[7:10]]
output_path = Path(sys.argv[10])
date_pattern = re.compile(rb"[A-Z][a-z]{2} [ 0-9][0-9] [0-9]{4}")
time_pattern = re.compile(rb"[0-9]{2}:[0-9]{2}:[0-9]{2}")
if not re.fullmatch(r"[0-9]+", epoch):
    raise SystemExit("SOURCE_DATE_EPOCH is not a decimal integer")
if not re.fullmatch(r"[A-Z][a-z]{2} [ 0-9][0-9] [0-9]{4}", expected_date) or len(expected_date) != 11:
    raise SystemExit("FreeCOM build date is not a C-compatible 11-byte value")
if not re.fullmatch(r"[0-9]{2}:[0-9]{2}:[0-9]{2}", expected_time) or len(expected_time) != 8:
    raise SystemExit("FreeCOM build time is not an 8-byte value")
config_line = f'CFLAGS2 = -DFREECOM_BUILD_DATE=\\"{expected_date}\\" -DFREECOM_BUILD_TIME=\\"{expected_time}\\"'
response_line = f'-DFREECOM_BUILD_DATE="{expected_date}" -DFREECOM_BUILD_TIME="{expected_time}"'
configuration_text = configuration_path.read_text(encoding="utf-8")
if configuration_text.count(config_line) != 1:
    raise SystemExit("staged FreeCOM configuration lacks exactly one deterministic CFLAGS2 line")
response_text = response_path.read_text(encoding="utf-8")
if response_text.count(response_line) != 1:
    raise SystemExit("generated watcomc.cfg lacks exactly one deterministic timestamp line")
command_log = command_log_path.read_text(encoding="utf-8", errors="replace")
if not re.search(r"wcc[^\n]*ver\.c[^\n]*watcomc\.cfg", command_log):
    raise SystemExit("FreeCOM ver.c was not visibly recompiled")
stamp_date = expected_date.encode("ascii")
stamp_time = expected_time.encode("ascii")
records = {}
for path in artifact_paths:
    if not path.is_file() or path.is_symlink() or path.stat().st_size == 0:
        raise SystemExit(f"FreeCOM timestamp artifact is missing or empty: {path}")
    data = path.read_bytes()
    dates = set(date_pattern.findall(data))
    times = set(time_pattern.findall(data))
    if dates != {stamp_date} or times != {stamp_time}:
        raise SystemExit(f"FreeCOM timestamp artifact does not contain only the canonical stamp: {path}")
    digest = hashlib.sha256(data).hexdigest()
    records[str(path)] = {"sha256": digest, "size": len(data)}
output_path.parent.mkdir(parents=True, exist_ok=True)
with output_path.open("w", encoding="utf-8", newline="\n") as stream:
    json.dump({
        "component": "freecom",
        "source_date_epoch": int(epoch),
        "timezone": "UTC",
        "formatted_date": expected_date,
        "formatted_time": expected_time,
        "date_macro": "FREECOM_BUILD_DATE",
        "time_macro": "FREECOM_BUILD_TIME",
        "wmake_configuration_variable": "CFLAGS2",
        "configuration_response_file": "shell/watcomc.cfg",
        "configuration_response_file_sha256": hashlib.sha256(response_path.read_bytes()).hexdigest(),
        "ver_recompiled": True,
        "current_wall_clock_stamp_absent": True,
        "artifacts": records,
    }, stream, indent=2, sort_keys=True)
    stream.write("\n")
PY
    cp "$work_directory/shell/watcomc.cfg" /output/freecom-watcomc.cfg
}

command_log=${log_root}/${component}.log
status=0
if [ "$component" = fdkernel ]; then
    (
        cd "$work_directory"
        cp "$configuration_template" config.mak
        if grep -E '^[[:space:]]*(XUPX|UPXOPT)[[:space:]]*=' config.mak >/dev/null; then
            printf 'error: compressor control variable is present in the M01 configuration\n' >&2
            exit 68
        fi
        assert_no_compressor_environment
        env -u XUPX -u UPXOPT make clobber COMPILER=owlinux
        assert_no_compressor_environment
        env -u XUPX -u UPXOPT make all COMPILER=owlinux
    ) >"$command_log" 2>&1 || status=$?
elif [ "$component" = freecom ]; then
    (
        cd "$work_directory"
        cp "$configuration_template" config.mak
        ./build.sh -r dbcs nec98 watcom japanese
    ) >"$command_log" 2>&1 || status=$?
else
    (
        cd "$work_directory"
        make clean all
        python3 ./ci_validate.py
    ) >"$command_log" 2>&1 || status=$?
fi

# Keep diagnostics bounded while retaining the status and tool versions.
tail -n 4000 "$command_log" >"${command_log}.bounded"
mv "${command_log}.bounded" "$command_log"

if [ "$component" = freecom ] && [ "$status" -eq 0 ]; then
    verify_freecom_timestamp || status=$?
fi

if grep -E '(^|[[:space:]])(XUPX|UPXOPT|upx)([=[:space:]]|$)' "$command_log" >/dev/null; then
    printf 'error: compressor control reached a build command or diagnostic output\n' >&2
    status=68
fi

tool_versions=/output/tool-versions.txt
{
    printf 'uname_m=%s\n' "$(uname -m)"
    printf 'dpkg_architecture=%s\n' "$(dpkg --print-architecture)"
    printf 'nasm=%s\n' "$(nasm -v 2>&1 | head -n 1)"
    printf 'make=%s\n' "$(make --version 2>&1 | head -n 1)"
    printf 'python=%s\n' "$(python3 --version 2>&1 | head -n 1)"
    printf 'wmake=%s\n' "$(grep -F 'Open Watcom Make Version 1.9' /output/tool-selection.txt | head -n 1)"
} >"$tool_versions"

if [ "$component" = freecom ] && [ -f /output/freecom-timestamp.json ]; then
    printf 'freecom_timestamp=verified\n' >>"$tool_versions"
fi

artifact_count=0
if [ "$status" -eq 0 ]; then
    while IFS='|' read -r artifact_namespace relative_path; do
        [ -n "$relative_path" ] || continue
        artifact_path=${source_root}/${relative_path}
        [ -f "$artifact_path" ] || { printf 'error: required artifact is missing: %s\n' "$relative_path" >&2; status=67; break; }
        [ -s "$artifact_path" ] || { printf 'error: required artifact is empty: %s\n' "$relative_path" >&2; status=67; break; }
        resolved_artifact=$(readlink -f "$artifact_path")
        case "$resolved_artifact" in
            "$source_root"/*) ;;
            *) printf 'error: artifact escaped source tree: %s\n' "$relative_path" >&2; status=67; break ;;
        esac
        mkdir -p "${output_root}/artifacts/${artifact_namespace}/$(dirname "$relative_path")"
        cp -p "$artifact_path" "${output_root}/artifacts/${artifact_namespace}/${relative_path}"
        artifact_count=$((artifact_count + 1))
    done <<EOF
$required_artifacts
EOF
fi

manifest_tmp=${manifest_path}.tmp
printf '{\n  "schema_version": 1,\n  "component": "%s",\n  "run_id": "%s",\n  "source_archive_sha256": "%s",\n  "configuration_sha256": "%s",\n  "status": %s,\n  "artifact_count": %s,\n  "filesystem_type": "%s"\n}\n' \
    "$component" "$run_id" "$actual_archive_sha256" "$configuration_sha256" "$status" "$artifact_count" "$filesystem_type" >"$manifest_tmp"
mv "$manifest_tmp" "$manifest_path"

if [ "$status" -ne 0 ]; then
    printf 'error: %s %s build failed with status %s\n' "$component" "$run_id" "$status" >&2
    exit "$status"
fi

printf 'completed: %s %s (%s artifacts)\n' "$component" "$run_id" "$artifact_count"
