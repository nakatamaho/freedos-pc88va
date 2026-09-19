# FreeDOS(88VA) compatibility with MS-DOS 2.11 VA memory behavior

Status: normative redo specification

## 1. Objective

Make the PC-88VA FreeDOS target determine conventional-memory capacity by the
VA-native mechanism and expose a valid DOS memory arena with MS-DOS 2.11 VA-like
availability. The 640-KiB target is compared with these recorded observations:

| System | Measurement | Recorded value |
| --- | --- | ---: |
| MS-DOS 2.11 VA | total memory reported by `CHKDSK` | 655360 bytes |
| MS-DOS 2.11 VA | available memory reported by `CHKDSK` | 530176 bytes |
| FreeDOS(88VA), recorded baseline | first MCB segment | `219Fh` |
| FreeDOS(88VA), recorded baseline | largest executable program | 423008 bytes |

The MS-DOS reference has 125184 bytes unavailable to applications
(`655360 - 530176`). The recorded FreeDOS largest-program result is 107168
bytes below the MS-DOS available-memory observation. These numbers are a
comparison baseline, not proof that the two utilities measure an identical
instant or use identical accounting. A milestone may claim recovered bytes
only after a same-image, same-configuration DOS allocator probe accounts for
them.

## 2. Correct platform contract

### 2.1 Native conventional-memory source

PC-88VA obtains the selected conventional-memory capacity from its native
backup/common-memory data. In the emulator environment, that state is persisted
by `VABKUPMEM.DAT` or `VA2BKUPMEM.DAT`. The supported capacity choices are:

| Native selection | Bytes | Physical top |
| ---: | ---: | ---: |
| 256 KiB | 262144 | `40000h` |
| 384 KiB | 393216 | `60000h` |
| 512 KiB | 524288 | `80000h` |
| 640 KiB | 655360 | `A0000h` |

The two `.DAT` names describe emulator-side persistence. Unless repository or
platform evidence explicitly proves otherwise, the DOS kernel must not try to
open them as guest files. The PC-88VA adapter must read the mapped VA-native
backup/common-memory field through the documented access path.

This specification intentionally does not invent the field address, bit
encoding, checksum, precedence between the two persistence variants, invalid
value handling, or fallback. The milestone implementing the decoder must cite
the exact private technical note, existing VA source symbol, emulator source,
or reproducible trace that establishes each of those facts. If the evidence is
missing, the milestone is blocked and must say exactly what is missing.

### 2.2 DOS allocator interface

After native capacity detection, the selected physical top is an input to DOS
arena initialization. Applications observe usable memory through DOS services,
principally:

- `INT 21h/AH=52h` to reach the DOS List of Lists and locate the MCB arena by
  the version-appropriate documented layout;
- the MCB chain itself, including ownership, block sizes, `M`/`Z` signatures,
  and the exclusive end address;
- `INT 21h/AH=48h` with `BX=FFFFh`, which must fail normally and return in `BX`
  the largest available paragraph count for the current allocation state;
- normal allocate, resize, free, and process-lifetime behavior.

`INT 21h` does not substitute an IBM BIOS query. Its allocator must be
initialized from the VA-native capacity result.

### 2.3 Interfaces that are not requirements

IBM-compatible `INT 12h` and `INT 15h/AH=88h` semantics are not defined by the
PC-88VA contract used here. Therefore:

- do not install PC-88VA handlers merely to return `AX=0280h` from `INT 12h`;
- do not install a handler merely to return `AX=8600h`, set CF, or report an
  IBM-style extended-memory result from `INT 15h/AH=88h`;
- do not mark any particular result from those interrupts as PASS or FAIL;
- do not use those interrupts to size the DOS arena;
- do not make a PC-oriented `MEM.EXE` appear correct by adding fake BIOS
  compatibility beneath it.

An observation of either vector may be recorded only as non-normative
characterization. A future optional IBM-compatibility layer requires a
separate specification and cannot be counted toward this project.

`INT 2Fh/AX=4300h` is also not evidence of conventional-memory size. Any XMS
detection behavior must stand on its own contract. A rollback must not remove
or preserve such behavior merely because it shared a commit with the invalid
`INT 12h`/`INT 15h` work.

## 3. Arena invariants

For every configured capacity:

1. The MCB chain starts at the exact segment reported by the selected,
   version-correct List-of-Lists interpretation.
2. Every block advances by `size + 1` paragraphs, counting its MCB paragraph.
3. All intermediate signatures are `M`; exactly one final signature is `Z`.
4. No block overlaps a previous block, wraps the 20-bit address space, or
   extends beyond the selected physical top.
5. The exclusive end of the final MCB equals the selected native boundary.
6. For the recorded 640-KiB configuration, that exclusive end is exactly
   `A0000h`. This invariant may not be relaxed to make a test pass.
7. The lowest arena boundary may move downward only when every released byte
   has an evidenced former owner and is proven dead, relocated, or no longer
   reserved.

The probe and reports must label separately:

- the List-of-Lists pointer used;
- the first MCB header segment;
- the first MCB data segment, which is normally header + 1 paragraph;
- each block's size in paragraphs and bytes;
- the final exclusive end segment and physical byte address.

This prevents an off-by-one paragraph or a data-segment value from being
reported as an MCB header.

## 4. Configuration and evidence discipline

All before/after comparisons must use one fixed configuration identity,
including at least:

- source commit and dirty-worktree description;
- compiler, assembler, linker, and relevant version strings;
- exact build command;
- boot image SHA-256;
- kernel and shell SHA-256;
- emulator name/version and full launch command;
- machine model, CPU mode, sector-size setting, RAM selection, and the identity
  or SHA-256 of the applicable backup-memory persistence input;
- exact `CONFIG.SYS` and `AUTOEXEC.BAT` bytes or SHA-256;
- exact diagnostic binary hashes.

The recorded `219Fh` first-MCB and 423008-byte largest-program values remain
the formal FreeDOS comparison baseline requested for this project. If they
cannot be reproduced, preserve them as recorded baseline data and report the
fresh result separately; do not silently replace or average them. Results from
another sector-size or boot configuration are a separate series.

Real-hardware evidence is never required unless it is actually available. An
emulator result must be labelled as such. A photographed or transcribed result
that cannot be regenerated by the worker remains human-supplied evidence, not
a worker reproduction.

## 5. Required diagnostic behavior

Use or add a PC-88VA-native diagnostic. A PC-oriented FreeDOS `MEM.EXE` may be
adapted with a guarded PC-88VA backend, or a separate `MEMVA`/probe utility may
be used. Either choice must:

- report the native selected capacity and cite how it was decoded;
- report the first MCB header and data segments distinctly;
- walk and validate the entire MCB chain;
- report the final exclusive end;
- query `INT 21h/AH=48h` with `BX=FFFFh` and report returned paragraphs and
  bytes;
- avoid `INT 12h` and `INT 15h/AH=88h` as memory-size sources;
- avoid reporting arbitrary PC BIOS results as conventional, reserved, XMS, or
  extended memory on PC-88VA.

The existing named probes are retained for allocator regression coverage:

| Program | Required purpose |
| --- | --- |
| `MZPROBE.EXE` | executable loading and relocation smoke test |
| `MEMFREE2.COM` | allocation/free error and maximum-block behavior |
| `MEMFREE3.COM` | MCB-chain and largest-block cross-check |
| `MEMLIFE.COM` | allocation ownership across process lifetime |

If their actual repository behavior differs from these labels, document the
real behavior before changing a test. Do not rewrite a probe merely to match a
desired result.

## 6. Milestone order

Only the first unfinished milestone whose dependencies are complete is
eligible. One `/goal` invocation completes at most one milestone, runs only
that milestone's named tests plus necessary build smoke tests, writes one
report, updates `status.md` and `handoff.md`, and stops.

### M0 — Remove invalid BIOS-shim conformance and rebaseline

Dependencies: none. This is the first eligible milestone.

Scope:

1. Inspect all root/scoped `AGENTS.md`, the worktree, and commit
   `49335bb547348e5e899285f0535e26284c388834` if it exists locally.
2. Identify every change that installs or tests PC-88VA `INT 12h` or
   `INT 15h/AH=88h` handlers as conformance behavior.
3. Remove only those unsupported changes. Use a normal `git revert` only if the
   entire commit is unwanted and contains no unrelated or separately valid
   behavior; otherwise apply a targeted inverse patch. Never reset or rewrite
   history.
4. Do not decide the fate of a shared `INT 2Fh` change without independent
   evidence.
5. Build the unchanged PC-88VA configuration, boot it, and record a fresh
   native DOS/MCB baseline while retaining `219Fh` and 423008 bytes as the
   recorded comparison values.

Named tests:

- PC-88VA target build and boot smoke test;
- source/linked-image check showing that the PC-88VA path no longer installs
  the unsupported shim handlers;
- native capacity/MCB diagnostic if already available;
- `MZPROBE.EXE`;
- `MEMFREE2.COM`;
- `MEMFREE3.COM`;
- `MEMLIFE.COM`.

Acceptance:

- No PC-88VA conformance claim or PASS criterion remains for `INT 12h` or
  `INT 15h/AH=88h`.
- Unsupported shim code/vector installation is absent from the built path.
- Unrelated work is preserved.
- The 640-KiB MCB walk is valid and ends at `A0000h`, or the milestone is
  marked BLOCKED with the exact first failing MCB; the invariant is not
  weakened.
- The report contains exact commands, hashes, configuration identity, fresh
  first-header/data semantics, largest-block paragraphs/bytes, and a byte
  comparison with the recorded baseline.

Stop after M0. Do not begin native decoder implementation in the same run.

### M1 — Establish and test the VA-native capacity decoder

Dependencies: M0 complete.

Scope:

1. Locate evidence for the mapped backup/common-memory field populated from
   `VABKUPMEM.DAT` or `VA2BKUPMEM.DAT`.
2. Record the exact address/symbol, encoding, validation, variant selection,
   and invalid/missing-data behavior with citations to repository/private
   evidence.
3. Implement one guarded PC-88VA decoder that returns 256, 384, 512, or
   640 KiB in an internal unit that cannot overflow paragraph conversion.
4. Do not wire a newly written decoder into unrelated allocators in this
   milestone unless the existing target already calls the exact replaced
   function and the behavior is inseparable.

Named tests:

- decoder fixtures for all four supported values;
- variant fixture for each evidenced `VABKUPMEM`/`VA2BKUPMEM` layout;
- invalid/checksum/missing-data fixtures exactly matching documented behavior;
- guarded build test proving non-PC-88VA targets are unchanged.

Acceptance: four supported capacities decode exactly; every fallback is
evidenced; no BIOS shim or invented address exists. Stop after M1.

### M2 — Drive the DOS arena from native capacity

Dependencies: M1 complete.

Scope: feed the decoded native capacity into PC-88VA DOS arena initialization
and make `INT 21h` allocation behavior respect it without altering unrelated
targets.

Named tests:

- native diagnostic at 256, 384, 512, and 640 KiB;
- full MCB walk at each capacity;
- `INT 21h/AH=48h, BX=FFFFh` maximum-block query at each capacity;
- allocate/resize/free boundary tests;
- `MZPROBE.EXE`, `MEMFREE2.COM`, `MEMFREE3.COM`, and `MEMLIFE.COM`;
- guarded non-PC-88VA regression build.

Acceptance: the final exclusive MCB end is respectively `40000h`, `60000h`,
`80000h`, and `A0000h`; the 640-KiB case still ends exactly at `A0000h`; no
allocation crosses the selected boundary. Stop after M2.

### M3 — Account for the 640-KiB low-memory layout

Dependencies: M2 complete.

Scope: produce a paragraph-exact ownership/lifetime map from `00000h` through
the first allocatable MCB, using linker maps, boot-loader placement, kernel
initialization, device data, DOS tables, shell residency, and runtime traces.
Investigate inherited NEC98/segment-`2000h` assumptions as a hypothesis, not a
fact.

Named tests:

- linked-section/map reconciliation;
- boot-time high-water trace;
- first-MCB provenance check;
- MCB and largest-block diagnostic;
- existing four allocation/lifetime probes.

Acceptance: every paragraph below the first arena block has one named owner,
lifetime, and evidence source; totals reconcile exactly. Stop after M3.

### M4 — Reclaim or relocate one proven low-memory loss

Dependencies: M3 complete.

Scope: choose the first safe reclaim opportunity identified by M3. Change only
that owner or boundary, keep target guards, and preserve all arena invariants.
Do not combine independent optimizations.

Named tests:

- tests attached by M3 to the selected owner;
- full MCB walk and `AH=48h` maximum query;
- boot/load/allocate/free/lifetime probes;
- guarded non-PC-88VA tests.

Acceptance: before/after hashes and maps show the exact bytes recovered; no
live range is overwritten; 640-KiB end remains `A0000h`. Stop after M4.

### M5 — Reach and verify the memory target

Dependencies: M4 complete. Repeat M4 as separately reported milestones if more
than one independently proven reclaim is required before starting M5.

Targets for the fixed 640-KiB configuration:

| Level | Largest clean DOS allocation |
| --- | ---: |
| Required floor | 512000 bytes |
| Parity target | 520000 bytes |
| Stretch target | at least 521984 bytes, within 8192 of 530176 |

Scope: run the complete fixed-configuration matrix, reconcile the native
capacity, MCB total, resident allocations, largest free block, fragmentation,
and shell/test overhead. Explain why a reported largest allocation can differ
from the MS-DOS `CHKDSK` available-memory number.

Named tests: all native-capacity, MCB, `AH=48h`, executable-load,
allocation/free/resize, process-lifetime, and guarded cross-target tests.

Acceptance: at least the required floor is met without configuration hiding or
invariant weakening, and every byte between 655360 and the observed application
maximum is classified. Stop after M5.

## 7. Forbidden shortcuts

- Adding IBM `INT 12h` or `INT 15h/AH=88h` handlers and calling them VA
  conformance.
- Opening emulator host persistence files from guest DOS without evidence that
  this is the actual platform interface.
- Guessing a common-memory address, encoding, checksum, priority, or fallback.
- Treating the result of a PC-oriented `MEM.EXE` BIOS query as valid VA data.
- Moving `FILES`, `BUFFERS`, `STACKS`, shell environment, or other DOS data only
  through `CONFIG.SYS` to conceal an unchanged kernel/loader loss.
- Moving the first MCB downward without a complete owner/lifetime proof.
- Truncating the MCB chain before `A0000h` in the 640-KiB case.
- Comparing different sector-size, memory-selection, or boot-image
  configurations as before/after evidence.
- Claiming unrun real-hardware tests or converting human observations into
  machine-generated evidence.
- Starting another milestone after the selected one is complete or blocked.

## 8. Required milestone report

Write `docs/msdos211-memory-compat/reports/M<N>-<slug>.md` with:

1. outcome: COMPLETE or BLOCKED;
2. exact scope and files changed;
3. evidence for every platform assumption used;
4. exact build/test/emulator commands and exit status;
5. source, image, kernel, shell, config, diagnostic, and applicable backup-data
   SHA-256 values;
6. before/after native capacity, first MCB header/data, final exclusive end,
   largest-block paragraphs and bytes;
7. a byte-accounting table whose totals reconcile;
8. named-test results, including failures without suppression;
9. unrelated work observed and preserved;
10. remaining risks and the one next eligible milestone;
11. an explicit statement that no second milestone was started.
