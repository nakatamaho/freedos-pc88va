#!/bin/sh
set -eu

umask 022

fail() {
    printf 'error: %s\n' "$*" >&2
    exit 1
}

validate_sha256_value() {
    value=$1
    label=$2
    case "$value" in
        ''|*[!0-9a-f]*) fail "$label is not a lowercase SHA-256 value" ;;
    esac
    [ "${#value}" -eq 64 ] || fail "$label is not exactly 64 hexadecimal characters"
}

validate_readonly_input() {
    input_path=$1
    expected_basename=$2
    expected_sha256=$3
    [ -f "$input_path" ] && [ ! -L "$input_path" ] || fail "input is not a regular file: $input_path"
    [ "$(basename -- "$input_path")" = "$expected_basename" ] || fail "input basename mismatch: $input_path"
    [ "$(stat -c '%a' "$input_path")" = 444 ] || fail "input mode is not exactly 0444: $input_path"
    hash_line=$(sha256sum "$input_path")
    actual_sha256=${hash_line%% *}
    validate_sha256_value "$actual_sha256" "actual SHA-256 for $input_path"
    [ "$actual_sha256" = "$expected_sha256" ] || fail "input SHA-256 mismatch: $input_path"
}

script_path=$0
expected_script_sha256=${M01_PROBE_SCRIPT_SHA256-}
expected_data_sha256=${M01_PROBE_DATA_SHA256-}
expected_data_path=${M01_PROBE_DATA_PATH-}
[ -n "$expected_script_sha256" ] || fail 'M01_PROBE_SCRIPT_SHA256 is missing'
[ -n "$expected_data_sha256" ] || fail 'M01_PROBE_DATA_SHA256 is missing'
[ -n "$expected_data_path" ] || fail 'M01_PROBE_DATA_PATH is missing'
validate_sha256_value "$expected_script_sha256" 'expected image probe script SHA-256'
validate_sha256_value "$expected_data_sha256" 'expected image probe data SHA-256'

# Verify staged inputs before reading tool-selection data or selecting a tool.
validate_readonly_input "$script_path" image_tool_probe.sh "$expected_script_sha256"
validate_readonly_input "$expected_data_path" image-tool-probe.env "$expected_data_sha256"

expected_wcc_size=
expected_wcc_sha256=
expected_wcc_banner=
expected_wcl_size=
expected_wcl_sha256=
expected_wcl_banner=
expected_wmake_size=
expected_wmake_sha256=
expected_wmake_banner=
expected_wlink_size=
expected_wlink_sha256=
expected_wlink_banner=
expected_wasm_size=
expected_wasm_sha256=
expected_wasm_banner=
expected_wlib_size=
expected_wlib_sha256=
expected_wlib_banner=
while IFS='=' read -r key value; do
    case "$key" in
        M01_PROBE_WCC_SIZE) expected_wcc_size=$value ;;
        M01_PROBE_WCC_SHA256) expected_wcc_sha256=$value ;;
        M01_PROBE_WCC_BANNER) expected_wcc_banner=$value ;;
        M01_PROBE_WCL_SIZE) expected_wcl_size=$value ;;
        M01_PROBE_WCL_SHA256) expected_wcl_sha256=$value ;;
        M01_PROBE_WCL_BANNER) expected_wcl_banner=$value ;;
        M01_PROBE_WMAKE_SIZE) expected_wmake_size=$value ;;
        M01_PROBE_WMAKE_SHA256) expected_wmake_sha256=$value ;;
        M01_PROBE_WMAKE_BANNER) expected_wmake_banner=$value ;;
        M01_PROBE_WLINK_SIZE) expected_wlink_size=$value ;;
        M01_PROBE_WLINK_SHA256) expected_wlink_sha256=$value ;;
        M01_PROBE_WLINK_BANNER) expected_wlink_banner=$value ;;
        M01_PROBE_WASM_SIZE) expected_wasm_size=$value ;;
        M01_PROBE_WASM_SHA256) expected_wasm_sha256=$value ;;
        M01_PROBE_WASM_BANNER) expected_wasm_banner=$value ;;
        M01_PROBE_WLIB_SIZE) expected_wlib_size=$value ;;
        M01_PROBE_WLIB_SHA256) expected_wlib_sha256=$value ;;
        M01_PROBE_WLIB_BANNER) expected_wlib_banner=$value ;;
        '') ;;
        *) fail "unexpected image probe input key: $key" ;;
    esac
done <"$expected_data_path"
for value in "$expected_wcc_size" "$expected_wcl_size" "$expected_wmake_size" "$expected_wlink_size" "$expected_wasm_size" "$expected_wlib_size"; do
    case "$value" in
        ''|*[!0-9]*) fail 'Open Watcom tool size input is missing or invalid' ;;
    esac
done
for value in "$expected_wcc_sha256" "$expected_wcl_sha256" "$expected_wmake_sha256" "$expected_wlink_sha256" "$expected_wasm_sha256" "$expected_wlib_sha256"; do
    validate_sha256_value "$value" 'Open Watcom tool SHA-256 input'
done
for value in "$expected_wcc_banner" "$expected_wcl_banner" "$expected_wmake_banner" "$expected_wlink_banner" "$expected_wasm_banner" "$expected_wlib_banner"; do
    [ -n "$value" ] || fail 'Open Watcom tool banner input is missing'
done

export WATCOM=/opt/openwatcom-1.9
export PATH="$WATCOM/binl:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
printf 'WATCOM=%s\n' "$WATCOM"
printf 'PATH=%s\n' "$PATH"
for tool in wcc wcl wmake wlink wasm wlib; do
    tool_path=$(command -v "$tool") || fail "required Open Watcom tool is unavailable: $tool"
    [ -n "$tool_path" ] || fail "required Open Watcom tool resolved to an empty path: $tool"
    resolved=$(readlink -f "$tool_path")
    [ "$resolved" = "$WATCOM/binl/$tool" ] || fail "$tool resolved outside the locked binl path: $resolved"
    tool_file_info=$(file "$resolved")
    tool_size=$(stat -c '%s' "$resolved")
    hash_line=$(sha256sum "$resolved")
    tool_sha256=${hash_line%% *}
    validate_sha256_value "$tool_sha256" "actual SHA-256 for $tool"
    case "$tool" in
        wcc) expected_size=$expected_wcc_size; expected_sha256=$expected_wcc_sha256; expected_banner=$expected_wcc_banner ;;
        wcl) expected_size=$expected_wcl_size; expected_sha256=$expected_wcl_sha256; expected_banner=$expected_wcl_banner ;;
        wmake) expected_size=$expected_wmake_size; expected_sha256=$expected_wmake_sha256; expected_banner=$expected_wmake_banner ;;
        wlink) expected_size=$expected_wlink_size; expected_sha256=$expected_wlink_sha256; expected_banner=$expected_wlink_banner ;;
        wasm) expected_size=$expected_wasm_size; expected_sha256=$expected_wasm_sha256; expected_banner=$expected_wasm_banner ;;
        wlib) expected_size=$expected_wlib_size; expected_sha256=$expected_wlib_sha256; expected_banner=$expected_wlib_banner ;;
    esac
    case "$tool_file_info" in
        *'ELF 32-bit'*'Intel 80386'*'statically linked'*) ;;
        *) fail "$tool is not a statically linked ELF i386 executable: $tool_file_info" ;;
    esac
    [ "$tool_size" = "$expected_size" ] || fail "$tool size mismatch"
    [ "$tool_sha256" = "$expected_sha256" ] || fail "$tool SHA-256 mismatch"
    printf '%s_path=%s\n' "$tool" "$tool_path"
    printf '%s_resolved=%s\n' "$tool" "$resolved"
    printf '%s_file=%s\n' "$tool" "$tool_file_info"
    printf '%s_size=%s\n' "$tool" "$tool_size"
    printf '%s_sha256=%s\n' "$tool" "$tool_sha256"
    tool_banner=
    tool_banner_status=0
    tool_banner=$("$resolved" -? 2>&1) || tool_banner_status=$?
    printf '%s_banner_status=%s\n' "$tool" "$tool_banner_status"
    printf '%s\n' "$tool_banner" | sed -n '1,40p'
    printf '%s\n' "$tool_banner" | grep -F "$expected_banner" >/dev/null || fail "$tool banner mismatch"
done

probe_dir=$(mktemp -d /tmp/m01-image-wcc-probe.XXXXXX)
cleanup_probe_dir() {
    case "${probe_dir-}" in
        /tmp/m01-image-wcc-probe.*) [ ! -d "$probe_dir" ] || rm -rf -- "$probe_dir" ;;
        '') ;;
        *) printf 'error: refusing to clean unexpected image probe path: %s\n' "$probe_dir" >&2 ;;
    esac
}
trap cleanup_probe_dir EXIT
probe_source=$probe_dir/probe.c
probe_object=$probe_dir/probe.obj
printf '%s\n' 'int m01_wcc_probe(void)' '{' '    return 0;' '}' >"$probe_source"
printf 'wcc_probe_command=wcc -bt=dos %s -fo=%s\n' "$probe_source" "$probe_object"
wcc_output=
wcc_status=0
wcc_output=$(wcc -bt=dos "$probe_source" "-fo=$probe_object" 2>&1) || wcc_status=$?
printf '%s\n' "$wcc_output" | sed -n '1,80p'
printf 'wcc_probe_status=%s\n' "$wcc_status"
[ "$wcc_status" -eq 0 ] || fail "WCC smoke test failed with status $wcc_status"
printf '%s\n' "$wcc_output" | grep -F "$expected_wcc_banner" >/dev/null || fail 'WCC smoke output lacks the expected banner'
[ -s "$probe_object" ] || fail 'WCC smoke test produced no object'
probe_file=$(file "$probe_object")
printf 'wcc_probe_object_size=%s\n' "$(stat -c '%s' "$probe_object")"
printf 'wcc_probe_object_file=%s\n' "$probe_file"
case "$probe_file" in
    *8086*relocat*|*relocat*8086*) ;;
    *) fail "WCC smoke object is not an 8086 relocatable object: $probe_file" ;;
esac

wmake_probe_dir=$probe_dir/wmake
mkdir -p "$wmake_probe_dir"
wmake_probe_makefile=$wmake_probe_dir/probe.mak
wmake_probe_output=$wmake_probe_dir/probe.ok
wmake_probe_expected=$probe_dir/wmake/expected.ok
{
    printf '%s\n' 'probe.ok:'
    printf '\t%s\n' '@echo M01_WMAKE_PROBE_OK'
    printf '\t%s\n' '@echo OK > probe.ok'
} >"$wmake_probe_makefile"
printf '%s\n' 'OK' >"$wmake_probe_expected"
printf '%s\n' 'wmake_probe_command=wmake -f probe.mak probe.ok'
wmake_output=
wmake_status=0
wmake_output=$(cd "$wmake_probe_dir" && wmake -f probe.mak probe.ok 2>&1) || wmake_status=$?
printf '%s\n' "$wmake_output" | sed -n '1,80p'
printf 'wmake_probe_status=%s\n' "$wmake_status"
[ "$wmake_status" -eq 0 ] || fail "WMake smoke test failed with status $wmake_status"
printf '%s\n' "$wmake_output" | grep -Fx 'M01_WMAKE_PROBE_OK' >/dev/null || fail 'WMake smoke output lacks the probe token'
if printf '%s\n' "$wmake_output" | grep -E 'F38|E02|Error\(' >/dev/null; then
    fail 'WMake smoke output contains an error diagnostic'
fi
test -f "$wmake_probe_output"
test -s "$wmake_probe_output"
cmp -s "$wmake_probe_expected" "$wmake_probe_output" || fail 'WMake probe output does not match expected bytes'
printf 'wmake_probe_output_size=%s\n' "$(stat -c '%s' "$wmake_probe_output")"
hash_line=$(sha256sum "$wmake_probe_output")
wmake_probe_output_sha256=${hash_line%% *}
validate_sha256_value "$wmake_probe_output_sha256" 'WMake probe output SHA-256'
printf 'wmake_probe_output_sha256=%s\n' "$wmake_probe_output_sha256"
printf '%s\n' 'wmake_probe_output_match=true'
printf '%s\n' "$wmake_output" | grep -F "$expected_wmake_banner" >/dev/null || fail 'WMake probe output lacks the expected banner'
