# M03R1 Milestone Routing Policy

M03R1 replaces the M03 census's exclusive scalar milestone assignment with
overlapping candidate consumers. It does not rescan, add, remove, or
reclassify source observations. The accepted 14,455 observations remain
byte-identical under the routing-free projection defined in
`config/m03/census-schema.json`.

## Semantics

Each census entry contains a `routing` object:

- `contract_milestones` identifies specification or decision consumers.
- `implementation_milestones` identifies likely code or validation consumers.
- `rule_ids` identifies the deterministic policy rule that selected both
  arrays.
- `status=coarse` means a mechanical candidate awaiting human review.
- `status=curated` means a path, component, surface, or token-specific rule was
  applied.
- `status=unresolved` means no destination is justified.
- `status=not_applicable` is available for reviewed census evidence that is not
  scheduled as VA work.

The arrays are sorted and unique. M04 is contract-only. M18 is possible only
with explicit SASI/SCSI/HDD evidence. M19 is a release gate and is not
automatically assigned to component-source observations. Specific rules take
precedence over general surface defaults.

Milestone membership counts overlap and are not task counts, effort estimates,
or an exclusive partition of the census.

## Canonical roadmap

| milestone | scope |
| --- | --- |
| M04 | PC-88VA boot and media contract from cited evidence; specification only |
| M05 | deterministic host-built FAT12 filesystem and image assembly |
| M06 | first compile-only `pc88va` target, stub HAL, and DBCS build matrix |
| M07 | IPL reaches its first controlled instruction under VAEG |
| M08 | FAT loader reads and transfers control to the kernel |
| M09 | console output |
| M10 | memory, timer/clock, interrupt, and runtime foundation |
| M11 | keyboard and console input |
| M12 | kernel floppy read-only path |
| M13 | read-only COMMAND.COM and EXEC session |
| M14 | floppy write and media-change handling |
| M15 | writable DOS session, AUTOEXEC, clock, and system transfer |
| M16 | Japanese output and NLS runtime |
| M17 | Japanese input and DBCS filename behavior |
| M18 | optional SASI/SCSI HDD extension |
| M19 | release gate, provenance, documentation, CI, and license decision |

M04 and M05 contain no PC-88VA kernel port implementation. M06 is the first
milestone permitted to add PC-88VA porting code. Real hardware remains an
optional `HW-*` evidence track; VAEG evidence is emulator evidence.

## Rules

The machine-readable policy in `config/m03/milestone-routing.json` is
canonical. The following list documents every rule ID and its intended
boundary. Rules are evaluated in descending priority.

| rule ID | status | contract | implementation | qualification |
| --- | --- | --- | --- | --- |
| `route-unknown-unresolved` | unresolved | — | — | unknown surface; no automatic destination |
| `route-explicit-hdd-extension` | curated | M04 | M18 | explicit SASI, SCSI, HDD, or hard-disk evidence only |
| `route-boot-image-layout` | curated | M04 | M05 | boot-sector, BPB, FAT12, or image-layout evidence |
| `route-boot-ipl-entry` | curated | M04 | M07 | IPL entry or first-controlled-instruction evidence |
| `route-boot-loader-transfer` | curated | M04 | M08 | loader, kernel load, or transfer evidence |
| `route-boot-contract-default` | coarse | M04 | — | otherwise-unqualified boot evidence |
| `route-loader-disk-read` | curated | M04 | M08 | disk reads coupled to boot-loader paths or tokens |
| `route-floppy-write-media-change` | curated | M04 | M14 | floppy write, format, or media-change evidence |
| `route-kernel-floppy-read` | curated | M04 | M12 | fdkernel driver/kernel floppy or FDC read path |
| `route-disk-contract-default` | coarse | M04 | — | generic disk evidence with no implementation owner |
| `route-dma-contract-default` | coarse | M04 | — | generic DMA/FDC evidence with no read/write owner |
| `route-console-output-japanese` | curated | — | M09, M16 | console output with Japanese/NLS/glyph evidence |
| `route-console-output-general` | coarse | — | M09 | general console output |
| `route-console-input-japanese` | curated | — | M11, M17 | console input with Japanese/DBCS filename evidence |
| `route-console-input-general` | coarse | — | M11 | general keyboard or console input |
| `route-nls-build-matrix` | curated | — | M06 | NLS/DBCS evidence in make or configuration files |
| `route-nls-input-filename` | curated | — | M17 | NLS input, parsing, editing, or filename evidence |
| `route-nls-output-runtime` | curated | — | M16 | Country, codepage, collation, glyph, or output evidence |
| `route-nls-runtime-default` | coarse | — | M16, M17 | otherwise-unqualified NLS/DBCS runtime evidence |
| `route-build-image-layout` | curated | — | M05 | explicit host image-layout evidence in a build observation |
| `route-build-platform` | coarse | — | M06 | compiler, platform, HAL, and build selection |
| `route-memory-boot-entry` | curated | M04 | M08 | memory/startup evidence in a boot path |
| `route-memory-startup-layout` | curated | — | M06 | fdkernel compile/link/segment/startup layout |
| `route-memory-runtime-foundation` | coarse | — | M10 | general memory behavior |
| `route-timer-clock-foundation` | coarse | — | M10 | general timer and clock behavior |
| `route-interrupt-boot-contract` | curated | M04 | M10 | interrupt state in a boot path |
| `route-interrupt-runtime-foundation` | coarse | — | M10 | general interrupt behavior |
| `route-firmware-loader-disk` | curated | M04 | M08 | firmware disk evidence in a boot path |
| `route-firmware-early-console` | curated | M04 | M09 | firmware-coupled early console evidence |
| `route-firmware-contract-default` | coarse | M04 | — | generic firmware evidence, never broadcast |
| `route-device-console-init` | curated | — | M09 | console, video, display, or printer initialization |
| `route-device-input-init` | curated | — | M11 | keyboard or input-device initialization |
| `route-device-runtime-init` | coarse | — | M10 | otherwise-unqualified device initialization |
| `route-exec-writable-session` | curated | — | M15 | writable commands, AUTOEXEC, clock writes, or SYS transfer |
| `route-exec-japanese-session` | curated | — | M13, M16, M17 | Japanese command line or filename evidence |
| `route-exec-readonly-session` | coarse | — | M13 | general COMMAND.COM and EXEC behavior |

Zero observed membership does not invalidate a documented rule. Positive,
newly authored fixtures exercise explicit M18, Japanese input/output, and
other qualified paths that are absent from the pinned observation tokens.

## Reviewed distribution

| status | entries |
| --- | ---: |
| coarse | 11,438 |
| curated | 2,695 |
| unresolved | 322 |
| not applicable | 0 |

Candidate multiplicity is 322 entries with no milestone, 13,118 with one,
and 1,015 with more than one. All 322 unresolved entries have
`surface=unknown`: 266 are from fdkernel, 53 from FreeCOM, and 3 from Country.
Complete overlapping membership and per-rule counts remain in the canonical
golden JSON.

## Review limits

The routing policy categorizes source leads; it is not a call graph, work
estimate, implementation plan, or PC-88VA hardware contract. PC-98/NEC98
source cannot establish VA behavior. The accepted twelve-item M04 blocker
ledger remains unresolved, and neither VAEG nor hardware is run by M03R1.
