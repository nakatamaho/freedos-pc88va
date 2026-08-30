#!/usr/bin/env python3
"""Deterministically census platform-dependent source surfaces.

The scanner reads tracked component blobs through Git at the component
gitlinks recorded by the parent lock.  It is a lead generator, not a compiler
frontend, call graph, or hardware specification.
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath


BASELINE_PARENT_COMMIT = "0babe66669b0e0eeb543cedaf427a3ff56eb5d83"
SCANNER_NAME = "m03-port-surface-scanner"
SCANNER_VERSION = 1

SURFACES = (
    "build",
    "boot",
    "disk",
    "dma",
    "console_output",
    "console_input",
    "timer_clock",
    "interrupts",
    "memory",
    "firmware",
    "nls_dbcs",
    "device_init",
    "exec_runtime",
    "unknown",
)
MECHANISMS = (
    "build_conditional",
    "bios_or_firmware",
    "io_port",
    "memory_mapped_io",
    "interrupt_vector",
    "direct_memory",
    "data_table",
    "function_boundary",
    "file_layout",
    "comment_lead",
    "unknown",
)
DISPOSITIONS = ("reuse", "adapt", "replace", "investigate", "exclude")
CLASSIFICATIONS = ("SOURCE_FACT", "DOCUMENT_FACT", "OBSERVATION", "INFERENCE", "HYPOTHESIS", "UNKNOWN")
PLATFORMS = ("shared", "ibmpc", "nec98")
TARGET_MILESTONES = tuple(f"M{number:02d}" for number in range(4, 19))


def rule(
    rule_id,
    description,
    scope,
    matcher,
    surface,
    mechanism,
    disposition,
    confidence,
    target_milestone,
    candidate_boundary,
    notes,
    platform="shared",
):
    return {
        "id": rule_id,
        "description": description,
        "scope": scope,
        "matcher": matcher,
        "surface": surface,
        "mechanism": mechanism,
        "platform": platform,
        "disposition": disposition,
        "confidence": confidence,
        "target_milestone": target_milestone,
        "candidate_boundary": candidate_boundary,
        "notes": notes,
    }


RULES = (
    rule(
        "PATH-IBMCPC-DIRECTORY",
        "Tracked path names the IBM PC platform directory.",
        "path",
        r"(^|/)ibmpc(/|$)",
        "build",
        "build_conditional",
        "investigate",
        "high",
        "M05",
        "independent pc88va build target",
        "Path evidence identifies a platform variant; it does not establish hardware equivalence.",
        "ibmpc",
    ),
    rule(
        "PATH-NEC98-DIRECTORY",
        "Tracked path names the NEC98 platform directory.",
        "path",
        r"(^|/)nec98(/|$)",
        "build",
        "build_conditional",
        "investigate",
        "high",
        "M05",
        "independent pc88va build target",
        "Path evidence identifies a platform variant; it does not establish VA hardware behavior.",
        "nec98",
    ),
    rule(
        "BUILD-PLATFORM-CONDITIONAL",
        "Build/configuration text selects a platform, compiler, model, or language variant.",
        "content",
        r"\b(?:NEC98|IBMPC|DBCS|JAPANESE|COMPILER|MODEL|WATCOM|TARGET)\b",
        "build",
        "build_conditional",
        "adapt",
        "high",
        "M05",
        "explicit pc88va platform selection",
        "A conditional or build variable is a selection lead, not a complete build graph.",
    ),
    rule(
        "BUILD-INCLUDE-RELATION",
        "Source text names an include relationship.",
        "content",
        r"(?:#\s*include|\binclude\s+[\"<])",
        "build",
        "file_layout",
        "reuse",
        "medium",
        "M05",
        "platform-neutral interface include boundary",
        "The scanner records the textual relationship without resolving compiler search paths.",
    ),
    rule(
        "BOOT-LOADER-LAYOUT",
        "Tracked source or build text names boot, loader, IPL, or boot-sector layout.",
        "path_or_content",
        r"\b(?:boot|bootn32|oemboot|ipl|b_fat(?:12f?|16|32)?|loader)\b",
        "boot",
        "file_layout",
        "replace",
        "high",
        "M04",
        "pc88va IPL and boot-sector contract",
        "Boot naming is NEC98/source evidence only; it is not a VA IPL claim.",
    ),
    rule(
        "DISK-FAT-BLOCK-IO",
        "Tracked text names disk, FAT, BPB, sector, media, geometry, or block I/O behavior.",
        "content",
        r"\b(?:blockio|fat(?:fs|dir|tab)?|bpb|sector|media|geometry|disk|dsk|drive|block)\b",
        "disk",
        "function_boundary",
        "adapt",
        "high",
        "M04",
        "pc88va block-I/O and media contract",
        "The hit identifies a source surface; geometry and firmware semantics remain unresolved.",
    ),
    rule(
        "DMA-FDC-SIGNAL",
        "Tracked text names DMA, FDC, floppy, or controller operations.",
        "content",
        r"\b(?:dma|fdc|upd765|floppy|fdc_dma)\b",
        "dma",
        "io_port",
        "replace",
        "high",
        "M04",
        "pc88va FDC/DMA interface",
        "NEC98 controller references cannot be promoted to a VA contract without VA evidence.",
    ),
    rule(
        "CONSOLE-OUTPUT-SIGNAL",
        "Tracked text names console, character, printer, screen, or display output.",
        "content",
        r"\b(?:console|chario|printer|screen|display|video|putc|write_char)\b",
        "console_output",
        "function_boundary",
        "adapt",
        "medium",
        "M07",
        "pc88va early diagnostic console interface",
        "Output path names are not evidence of a VA firmware or video register contract.",
    ),
    rule(
        "CONSOLE-INPUT-SIGNAL",
        "Tracked text names keyboard, enhanced input, terminal, or console input.",
        "content",
        r"\b(?:conkey|keyboard|enhanced|termhook|input|keycode|read_char)\b",
        "console_input",
        "function_boundary",
        "adapt",
        "medium",
        "M08",
        "pc88va keyboard and console-input interface",
        "Input naming is a port-surface lead and not a Japanese-runtime validation.",
    ),
    rule(
        "TIMER-CLOCK-SIGNAL",
        "Tracked text names timer, clock, tick, or time initialization.",
        "content",
        r"\b(?:timer|clock|sysclk|initclk|systime|8253|tick)\b",
        "timer_clock",
        "io_port",
        "replace",
        "high",
        "M09",
        "pc88va timer and clock interface",
        "Timer names do not establish interrupt frequency or BIOS time semantics.",
    ),
    rule(
        "INTERRUPT-VECTOR-SIGNAL",
        "Tracked text names interrupts, IRQ, PIC, vectors, or interrupt handlers.",
        "content",
        r"\b(?:interrupt|intr|irq|pic|int2f|int29|vector|iret|irqstack)\b",
        "interrupts",
        "interrupt_vector",
        "replace",
        "high",
        "M09",
        "pc88va interrupt and exception interface",
        "Interrupt references are source observations and do not define VA vector ownership.",
    ),
    rule(
        "MEMORY-STARTUP-SIGNAL",
        "Tracked text names memory, segments, stack, startup, or memory-resident services.",
        "content",
        r"\b(?:memory|memdisk|segment|stack|startup|entry|hmap|xms|memmgr|inithma)\b",
        "memory",
        "direct_memory",
        "investigate",
        "high",
        "M04",
        "pc88va load, segment, and startup contract",
        "Names identify startup-sensitive code but do not resolve VA addresses or register state.",
    ),
    rule(
        "FIRMWARE-BIOS-SIGNAL",
        "Tracked text names BIOS, firmware, port I/O, or low-level firmware calls.",
        "content",
        r"\b(?:bios|firmware|int\s+(?:10|13|1b|1ch)|port|io_port)\b",
        "firmware",
        "bios_or_firmware",
        "investigate",
        "high",
        "M04",
        "pc88va firmware boundary",
        "PC-98 BIOS references are not PC-88VA evidence.",
    ),
    rule(
        "ASM-IO-OPERATION",
        "Assembly text contains an input/output instruction lead.",
        "content",
        r"\b(?:in|out)[bwd]?\s+",
        "firmware",
        "io_port",
        "replace",
        "high",
        "M04",
        "pc88va low-level I/O interface",
        "Instruction syntax is recorded as a lead; port numbers and device semantics require review.",
    ),
    rule(
        "ASM-INT-OPERATION",
        "Assembly text contains an interrupt instruction or interrupt return lead.",
        "content",
        r"\b(?:int|iret)(?:\s|$)",
        "interrupts",
        "interrupt_vector",
        "replace",
        "high",
        "M09",
        "pc88va interrupt entry interface",
        "The scanner does not infer vector numbers or calling conventions from this token.",
    ),
    rule(
        "NLS-DBCS-SIGNAL",
        "Tracked text names Country, NLS, DBCS, Japanese, or codepage behavior.",
        "content",
        r"\b(?:nls|country|dbcs|japanese|codepage|932|437|multibyte)\b",
        "nls_dbcs",
        "data_table",
        "reuse",
        "high",
        "M06",
        "platform-neutral NLS/DBCS interface",
        "NLS data and DBCS logic are separate from unresolved VA hardware services.",
    ),
    rule(
        "DEVICE-INIT-SIGNAL",
        "Tracked text names devices, drivers, or initialization paths.",
        "content",
        r"\b(?:device|driver|init|serial|printer)\b",
        "device_init",
        "function_boundary",
        "adapt",
        "medium",
        "M10",
        "pc88va device initialization boundary",
        "Initialization order and device names require an explicit later contract.",
    ),
    rule(
        "EXEC-RUNTIME-SIGNAL",
        "Tracked text names command execution, shell, SYS, spawn, or runtime transfer.",
        "content",
        r"\b(?:command|exec|shell|sys\.com|system\s+transfer|lowexec|spawn|freecom)\b",
        "exec_runtime",
        "function_boundary",
        "reuse",
        "medium",
        "M11",
        "platform-neutral DOS execution boundary",
        "A command/runtime hit does not claim that a NEC98 binary runs on VA.",
    ),
    rule(
        "COMMENT-PLATFORM-LEAD",
        "Comment text names a platform or hardware lead for human review.",
        "comment",
        r"\b(?:NEC98|IBMPC|PC-98|VGA|BIOS|Japanese)\b",
        "unknown",
        "comment_lead",
        "investigate",
        "low",
        "M18",
        "documented PC-88VA integration boundary",
        "Comments are leads only and are never sufficient hardware evidence.",
    ),
)


class ScanError(Exception):
    """A bounded scanner failure."""


def canonical_json_bytes(value):
    if contains_float(value):
        raise ScanError("canonical JSON must not contain floating-point values")
    try:
        return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ScanError(f"cannot encode canonical JSON: {exc}") from exc


def contains_float(value):
    if isinstance(value, float):
        return True
    if isinstance(value, dict):
        return any(contains_float(item) for item in value.values())
    if isinstance(value, list):
        return any(contains_float(item) for item in value)
    return False


def git(root, *args, check=True):
    result = subprocess.run(["git", *args], cwd=root, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if check and result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip().replace("\n", " | ")
        raise ScanError(f"git command failed: {' '.join(args)}: {detail}")
    return result


def git_text(root, *args):
    return git(root, *args).stdout.decode("utf-8").strip()


def load_lock(root):
    path = Path(root) / "manifests/components.lock.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ScanError(f"cannot parse component lock: {path}: {exc}") from exc
    components = value.get("components")
    if not isinstance(components, list) or {item.get("name") for item in components} != {"fdkernel", "freecom", "country"}:
        raise ScanError("component lock does not contain the required three components")
    return sorted(components, key=lambda item: item["name"])


def ruleset_descriptors():
    return [dict(item) for item in sorted(RULES, key=lambda item: item["id"])]


def ruleset_sha256():
    return hashlib.sha256(canonical_json_bytes(ruleset_descriptors())).hexdigest()


def path_platform(path):
    parts = set(PurePosixPath(path).parts)
    if "nec98" in parts:
        return "nec98"
    if "ibmpc" in parts:
        return "ibmpc"
    return "shared"


def tracked_files(root, component):
    result = git(root / component["path"], "ls-files", "-z")
    paths = [item.decode("utf-8") for item in result.stdout.split(b"\0") if item]
    if paths != sorted(paths):
        raise ScanError(f"tracked file list is not sorted for {component['name']}")
    return paths


def blob_bytes(root, component, relative):
    result = git(root / component["path"], "show", f"HEAD:{relative}")
    return result.stdout


def is_text_candidate(relative):
    name = PurePosixPath(relative).name.lower()
    suffix = PurePosixPath(relative).suffix.lower()
    return name in {"makefile", "platform.mak", "config.m", "config.b", "config.h"} or suffix in {
        ".c", ".h", ".asm", ".inc", ".s", ".mak", ".m", ".bat", ".sh", ".cfg", ".ld"
    }


def comment_line(line):
    stripped = line.lstrip()
    return stripped.startswith((b";", b"#", b"//", b"/*", b"*"))


def infer_symbol(lines, line_number):
    for prior in range(line_number - 1, max(-1, line_number - 80), -1):
        text = lines[prior].decode("latin-1", errors="replace").strip()
        asm = re.match(r"^([A-Za-z_.$?][A-Za-z0-9_.$?]*)\s*:\s*(?:;.*)?$", text)
        if asm:
            return f"{asm.group(1)} (line {line_number})"
        proc = re.match(r"^([A-Za-z_.$?][A-Za-z0-9_.$?]*)\s+(?:proc|label|equ)\b", text, re.I)
        if proc:
            return f"{proc.group(1)} (line {line_number})"
        function = re.match(r"^(?:[A-Za-z_][\w\s*]*\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*\([^;]*\)\s*\{?", text)
        if function:
            return f"{function.group(1)} (line {line_number})"
    return f"line:{line_number}"


def entry_id(entry):
    identity = "|".join(str(entry[key]) for key in ("component", "path", "symbol_or_section", "matched_rule", "evidence_excerpt_or_token"))
    return hashlib.sha256(identity.encode("ascii", errors="strict")).hexdigest()[:16]


def make_entry(component, component_commit, path, symbol, matched, token, platform=None):
    item = {
        "id": "",
        "component": component,
        "component_commit": component_commit,
        "platform": platform or path_platform(path),
        "path": path,
        "symbol_or_section": symbol,
        "surface": matched["surface"],
        "mechanism": matched["mechanism"],
        "matched_rule": matched["id"],
        "evidence_excerpt_or_token": token,
        "classification": "OBSERVATION",
        "candidate_boundary": matched["candidate_boundary"],
        "disposition": matched["disposition"],
        "confidence": matched["confidence"],
        "target_milestone": matched["target_milestone"],
        "notes": matched["notes"],
    }
    item["id"] = entry_id(item)
    return item


def match_path(rule_item, path):
    return re.search(rule_item["matcher"].encode("ascii"), path.encode("ascii"), re.I) is not None


def scan_component(root, component):
    commit = component["commit"]
    actual = git_text(root / component["path"], "rev-parse", "HEAD")
    if actual != commit:
        raise ScanError(f"component commit mismatch for {component['name']}: {actual} != {commit}")
    paths = tracked_files(root, component)
    entries = []
    for relative in paths:
        repository_path = f"{component['path']}/{relative}"
        for matched in RULES:
            if matched["scope"] in {"path", "path_or_content"} and match_path(matched, relative):
                entries.append(make_entry(component["name"], commit, repository_path, "tracked-path", matched, relative, matched["platform"]))
        if not is_text_candidate(relative):
            continue
        data = blob_bytes(root, component, relative)
        if b"\0" in data:
            continue
        lines = data.splitlines()
        for line_number, line in enumerate(lines, 1):
            for matched in RULES:
                if matched["scope"] not in {"content", "path_or_content", "comment"}:
                    continue
                if matched["scope"] == "comment" and not comment_line(line):
                    continue
                if matched["id"].startswith("ASM-") and PurePosixPath(relative).suffix.lower() not in {".asm", ".inc", ".s"}:
                    continue
                if matched["id"].startswith("ASM-") and comment_line(line):
                    continue
                if matched["scope"] != "comment" and comment_line(line) and matched["id"] == "ASM-IO-OPERATION":
                    continue
                match = re.search(matched["matcher"].encode("ascii"), line, re.I)
                if not match:
                    continue
                token = match.group(0).decode("ascii", errors="replace")[:80]
                entries.append(make_entry(component["name"], commit, repository_path, infer_symbol(lines, line_number), matched, token))
    return entries, paths


def counts(entries, key):
    result = {value: 0 for value in (SURFACES if key == "surface" else MECHANISMS if key == "mechanism" else DISPOSITIONS if key == "disposition" else TARGET_MILESTONES if key == "target_milestone" else ("fdkernel", "freecom", "country"))}
    for item in entries:
        result[item[key]] = result.get(item[key], 0) + 1
    return result


def scan_repository(root):
    root = Path(root).resolve()
    components = load_lock(root)
    entries = []
    component_records = []
    parent_gitlinks = []
    for component in components:
        component_root = root / component["path"]
        tree = git_text(component_root, "rev-parse", "HEAD^{tree}")
        status = git(component_root, "status", "--porcelain=v1", "--untracked-files=all").stdout
        if status:
            raise ScanError(f"component worktree is dirty: {component['path']}")
        component_entries, paths = scan_component(root, component)
        entries.extend(component_entries)
        parent_gitlinks.append({"path": component["path"], "commit": component["commit"]})
        component_records.append(
            {
                "name": component["name"],
                "path": component["path"],
                "commit": component["commit"],
                "tree": tree,
                "tracked_file_count": len(paths),
            }
        )
    entries.sort(key=lambda item: (item["component"], item["path"], item["matched_rule"], item["symbol_or_section"], item["evidence_excerpt_or_token"], item["id"]))
    deduplicated = []
    seen = set()
    for item in entries:
        if item["id"] in seen:
            continue
        seen.add(item["id"])
        deduplicated.append(item)
    entries = deduplicated
    result = {
        "schema_version": 1,
        "scanner": {
            "name": SCANNER_NAME,
            "version": SCANNER_VERSION,
            "ruleset_sha256": ruleset_sha256(),
            "baseline_parent_commit": BASELINE_PARENT_COMMIT,
        },
        "parent_gitlinks": sorted(parent_gitlinks, key=lambda item: item["path"]),
        "components": sorted(component_records, key=lambda item: item["name"]),
        "surface_coverage": list(SURFACES),
        "rules": ruleset_descriptors(),
        "entries": entries,
        "counts": {
            "component": counts(entries, "component"),
            "surface": counts(entries, "surface"),
            "mechanism": counts(entries, "mechanism"),
            "disposition": counts(entries, "disposition"),
            "target_milestone": counts(entries, "target_milestone"),
        },
        "limitations": [
            "This is a deterministic tracked-source signal census, not a complete call graph.",
            "Comments and path names are leads and do not establish hardware contracts.",
            "Generated build output, binaries, archives, logs, and private documents are not scanned.",
            "PC-98/NEC98 source evidence does not establish PC-88VA behavior.",
        ],
    }
    return result


def write_output(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        write_output(args.output, scan_repository(args.repo_root))
        print(f"M03 port-surface census written: {args.output}")
    except ScanError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
