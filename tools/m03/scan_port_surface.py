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
ACCEPTED_M03_COMMIT = "1d885d24ab1aaf5e23b9b5e00b376c5a93165f31"
SCANNER_NAME = "m03-port-surface-scanner"
SCANNER_VERSION = 2
CENSUS_SCHEMA_VERSION = 2
PROJECTION_SCHEMA_VERSION = 1
CENSUS_SCHEMA_RELATIVE = "config/m03/census-schema.json"
ROUTING_POLICY_RELATIVE = "config/m03/milestone-routing.json"
MILESTONES = tuple(f"M{number:02d}" for number in range(4, 20))
ROUTING_STATUSES = ("coarse", "curated", "not_applicable", "unresolved")
MEMBERSHIP_COUNT_SEMANTICS = "Milestone membership counts overlap and are not task counts, effort estimates, or an exclusive partition of the census."

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
OBSERVATION_FIELDS = (
    "id",
    "component",
    "component_commit",
    "platform",
    "path",
    "symbol_or_section",
    "surface",
    "mechanism",
    "matched_rule",
    "evidence_excerpt_or_token",
    "classification",
    "candidate_boundary",
    "disposition",
    "confidence",
    "notes",
)


def rule(
    rule_id,
    description,
    scope,
    matcher,
    surface,
    mechanism,
    disposition,
    confidence,
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


def sorted_milestones(values):
    return sorted(values, key=lambda value: int(value[1:]))


def validate_routing_policy(policy):
    required = {"membership_count_semantics", "policy_id", "roadmap", "routing_statuses", "rules", "schema_version"}
    if set(policy) != required:
        raise ScanError(f"routing policy schema mismatch: {sorted(set(policy) ^ required)}")
    if policy["schema_version"] != 1 or policy["policy_id"] != "m03r1-milestone-routing":
        raise ScanError("routing policy identity is not accepted")
    if policy["membership_count_semantics"] != MEMBERSHIP_COUNT_SEMANTICS:
        raise ScanError("routing membership-count semantics are missing")
    if policy["routing_statuses"] != list(ROUTING_STATUSES):
        raise ScanError("routing status vocabulary is not canonical")
    roadmap = policy["roadmap"]
    if not isinstance(roadmap, list) or [item.get("milestone") for item in roadmap] != list(MILESTONES):
        raise ScanError("routing roadmap does not define M04 through M19 in order")
    if any(set(item) != {"milestone", "scope"} or not isinstance(item["scope"], str) or not item["scope"] for item in roadmap):
        raise ScanError("routing roadmap entry is malformed")

    rules = policy["rules"]
    if not isinstance(rules, list) or not rules:
        raise ScanError("routing policy has no rules")
    priorities = [item.get("priority") for item in rules]
    if priorities != sorted(priorities, reverse=True) or len(priorities) != len(set(priorities)):
        raise ScanError("routing rules must have unique descending priorities")
    rule_ids = set()
    allowed_match = {"any_text_regex", "component", "matched_rule", "mechanism", "path_regex", "surface"}
    for item in rules:
        if set(item) != {"contract_milestones", "description", "id", "implementation_milestones", "match", "notes", "priority", "status"}:
            raise ScanError("routing rule schema is malformed")
        rule_id = item["id"]
        if not isinstance(rule_id, str) or not re.fullmatch(r"route-[a-z0-9-]+", rule_id) or rule_id in rule_ids:
            raise ScanError(f"routing rule ID is invalid or duplicated: {rule_id!r}")
        rule_ids.add(rule_id)
        if item["status"] not in ROUTING_STATUSES:
            raise ScanError(f"routing rule status is invalid: {rule_id}")
        for field in ("contract_milestones", "implementation_milestones"):
            values = item[field]
            if not isinstance(values, list) or values != sorted_milestones(values) or len(values) != len(set(values)) or any(value not in MILESTONES for value in values):
                raise ScanError(f"routing milestones are invalid: {rule_id}.{field}")
        if item["status"] in {"unresolved", "not_applicable"} and (item["contract_milestones"] or item["implementation_milestones"]):
            raise ScanError(f"empty routing is required for status {item['status']}: {rule_id}")
        if "M04" in item["implementation_milestones"]:
            raise ScanError(f"contract-only M04 cannot be an implementation milestone: {rule_id}")
        if "M19" in item["contract_milestones"] or "M19" in item["implementation_milestones"]:
            raise ScanError(f"ordinary source observations cannot be routed automatically to M19: {rule_id}")
        if "M18" in item["implementation_milestones"] and rule_id != "route-explicit-hdd-extension":
            raise ScanError(f"M18 requires the explicit HDD routing rule: {rule_id}")
        if "M05" in item["implementation_milestones"] and rule_id not in {"route-boot-image-layout", "route-build-image-layout"}:
            raise ScanError(f"M05 requires explicit image-layout evidence: {rule_id}")
        match = item["match"]
        if not isinstance(match, dict) or not match or not set(match).issubset(allowed_match):
            raise ScanError(f"routing match is invalid: {rule_id}")
        for field, values in match.items():
            if field.endswith("_regex"):
                if not isinstance(values, str) or not values:
                    raise ScanError(f"routing regex is invalid: {rule_id}.{field}")
                try:
                    re.compile(values, re.I)
                except re.error as exc:
                    raise ScanError(f"routing regex is invalid: {rule_id}.{field}: {exc}") from exc
            elif not isinstance(values, list) or not values or len(values) != len(set(values)) or values != sorted(values):
                raise ScanError(f"routing match values must be unique and sorted: {rule_id}.{field}")
    return policy


def load_routing_policy(root):
    path = Path(root) / ROUTING_POLICY_RELATIVE
    try:
        raw = path.read_bytes()
        policy = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ScanError(f"cannot parse routing policy: {ROUTING_POLICY_RELATIVE}: {exc}") from exc
    if raw != canonical_json_bytes(policy):
        raise ScanError(f"routing policy is not canonical JSON: {ROUTING_POLICY_RELATIVE}")
    return validate_routing_policy(policy)


def load_census_schema(root):
    path = Path(root) / CENSUS_SCHEMA_RELATIVE
    try:
        raw = path.read_bytes()
        schema = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ScanError(f"cannot parse census schema: {CENSUS_SCHEMA_RELATIVE}: {exc}") from exc
    if raw != canonical_json_bytes(schema):
        raise ScanError(f"census schema is not canonical JSON: {CENSUS_SCHEMA_RELATIVE}")
    expected = {
        "census_schema_version": CENSUS_SCHEMA_VERSION,
        "entry_fields": list(OBSERVATION_FIELDS) + ["routing"],
        "milestones": list(MILESTONES),
        "observation_projection_fields": list(OBSERVATION_FIELDS),
        "observation_projection_schema_version": PROJECTION_SCHEMA_VERSION,
        "routing_fields": ["contract_milestones", "implementation_milestones", "notes", "rule_ids", "status"],
        "routing_statuses": list(ROUTING_STATUSES),
        "schema_id": "m03-port-surface-census",
    }
    if schema != expected:
        raise ScanError("census schema fields or vocabulary are not accepted")
    return schema


def census_schema_sha256(root):
    return hashlib.sha256((Path(root) / CENSUS_SCHEMA_RELATIVE).read_bytes()).hexdigest()


def routing_policy_sha256(root):
    return hashlib.sha256((Path(root) / ROUTING_POLICY_RELATIVE).read_bytes()).hexdigest()


def routing_rule_matches(entry, rule_item):
    match = rule_item["match"]
    for field in ("component", "matched_rule", "mechanism", "surface"):
        if field in match and entry[field] not in match[field]:
            return False
    if "path_regex" in match and re.search(match["path_regex"], entry["path"], re.I) is None:
        return False
    evidence_text = "\n".join((entry["path"], entry["symbol_or_section"], entry["evidence_excerpt_or_token"]))
    if "any_text_regex" in match and re.search(match["any_text_regex"], evidence_text, re.I) is None:
        return False
    return True


def route_observation(entry, policy):
    for rule_item in policy["rules"]:
        if not routing_rule_matches(entry, rule_item):
            continue
        return {
            "status": rule_item["status"],
            "contract_milestones": list(rule_item["contract_milestones"]),
            "implementation_milestones": list(rule_item["implementation_milestones"]),
            "rule_ids": [rule_item["id"]],
            "notes": rule_item["notes"],
        }
    raise ScanError(f"no milestone routing rule matched observation: {entry['id']}")


def observation_projection(entries):
    projected = [{field: entry[field] for field in OBSERVATION_FIELDS} for entry in entries]
    return {
        "schema_version": PROJECTION_SCHEMA_VERSION,
        "fields": list(OBSERVATION_FIELDS),
        "entry_count": len(projected),
        "entries": projected,
    }


def observation_projection_identity(entries):
    encoded = canonical_json_bytes(observation_projection(entries))
    return {
        "schema_version": PROJECTION_SCHEMA_VERSION,
        "entry_count": len(entries),
        "size": len(encoded),
        "sha256": hashlib.sha256(encoded).hexdigest(),
    }


def path_platform(path):
    parts = set(PurePosixPath(path).parts)
    if "nec98" in parts:
        return "nec98"
    if "ibmpc" in parts:
        return "ibmpc"
    return "shared"


def tracked_files(root, component):
    result = git(root / component["path"], "ls-tree", "-r", "--name-only", "-z", component["commit"])
    paths = [item.decode("utf-8") for item in result.stdout.split(b"\0") if item]
    if paths != sorted(paths):
        raise ScanError(f"tracked file list is not sorted for {component['name']}")
    return paths


def blob_bytes(root, component, relative):
    result = git(root / component["path"], "show", f"{component['commit']}:{relative}")
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
        "notes": matched["notes"],
    }
    item["id"] = entry_id(item)
    return item


def match_path(rule_item, path):
    return re.search(rule_item["matcher"].encode("ascii"), path.encode("ascii"), re.I) is not None


def scan_component(root, component):
    commit = component["commit"]
    resolved = git_text(root / component["path"], "rev-parse", f"{commit}^{{commit}}")
    if resolved != commit:
        raise ScanError(f"component commit cannot be resolved for {component['name']}: {resolved} != {commit}")
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
    result = {value: 0 for value in (SURFACES if key == "surface" else MECHANISMS if key == "mechanism" else DISPOSITIONS if key == "disposition" else ("fdkernel", "freecom", "country"))}
    for item in entries:
        result[item[key]] = result.get(item[key], 0) + 1
    return result


def routing_counts(entries, policy):
    status = {value: 0 for value in ROUTING_STATUSES}
    contract = {value: 0 for value in MILESTONES}
    implementation = {value: 0 for value in MILESTONES}
    rule_ids = {item["id"]: 0 for item in policy["rules"]}
    multiplicity = {"multiple": 0, "one": 0, "zero": 0}
    unresolved_component = {value: 0 for value in ("country", "fdkernel", "freecom")}
    unresolved_surface = {value: 0 for value in SURFACES}
    for entry in entries:
        routing = entry["routing"]
        status[routing["status"]] += 1
        for milestone in routing["contract_milestones"]:
            contract[milestone] += 1
        for milestone in routing["implementation_milestones"]:
            implementation[milestone] += 1
        for rule_id in routing["rule_ids"]:
            rule_ids[rule_id] += 1
        candidates = set(routing["contract_milestones"]) | set(routing["implementation_milestones"])
        multiplicity["zero" if not candidates else "one" if len(candidates) == 1 else "multiple"] += 1
        if routing["status"] == "unresolved":
            unresolved_component[entry["component"]] += 1
            unresolved_surface[entry["surface"]] += 1
    return {
        "contract_milestone_membership": contract,
        "implementation_milestone_membership": implementation,
        "milestone_multiplicity": multiplicity,
        "routing_rule_membership": rule_ids,
        "status": status,
        "unresolved_by_component": unresolved_component,
        "unresolved_by_surface": unresolved_surface,
    }


def scan_repository(root):
    root = Path(root).resolve()
    components = load_lock(root)
    census_schema = load_census_schema(root)
    routing_policy = load_routing_policy(root)
    entries = []
    component_records = []
    parent_gitlinks = []
    for component in components:
        component_root = root / component["path"]
        tree = git_text(component_root, "rev-parse", f"{component['commit']}^{{tree}}")
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
    for item in entries:
        item["routing"] = route_observation(item, routing_policy)
    result = {
        "schema_version": CENSUS_SCHEMA_VERSION,
        "schema": {
            "path": CENSUS_SCHEMA_RELATIVE,
            "schema_id": census_schema["schema_id"],
            "sha256": census_schema_sha256(root),
            "version": census_schema["census_schema_version"],
        },
        "scanner": {
            "name": SCANNER_NAME,
            "version": SCANNER_VERSION,
            "ruleset_sha256": ruleset_sha256(),
            "baseline_parent_commit": BASELINE_PARENT_COMMIT,
            "accepted_m03_commit": ACCEPTED_M03_COMMIT,
        },
        "routing_policy": {
            "membership_count_semantics": MEMBERSHIP_COUNT_SEMANTICS,
            "path": ROUTING_POLICY_RELATIVE,
            "policy_id": routing_policy["policy_id"],
            "schema_version": routing_policy["schema_version"],
            "sha256": routing_policy_sha256(root),
        },
        "observation_projection": observation_projection_identity(entries),
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
            "routing": routing_counts(entries, routing_policy),
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
    encoded = canonical_json_bytes(value)
    path.write_bytes(encoded)
    sidecar = path.with_suffix(".sha256")
    sidecar.write_bytes(f"{hashlib.sha256(encoded).hexdigest()}  {path.name}\n".encode("ascii"))


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
