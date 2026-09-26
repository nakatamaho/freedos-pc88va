# M13 common FreeDOS core and read-only FreeCOM session

Historical status: **M13 PASS — FINAL PUBLICATION HANDOFF PENDING.**

## Subsequent memory-placement work (not covered by the historical qualification)

The current worktree contains a newer PC-88VA placement/lifetime implementation.
The following historical identities and CI results do **not** qualify these
changes. The newer component baseline and subsequent uncommitted changes must
not be relabeled as the earlier qualified implementation.

The new design decouples carrier transport from low resident placement, gives
INIT-only code and its temporary stack explicit ownership, and releases the
temporary envelope from the permanent process-zero stack. Shared NEAR data and
resident error paths remain live. Enumerated MZ fixups, not a whole-image opcode
scan, establish the copied code targets. Non-PC88VA paths remain separately
compiled. Supporting ROM-free placement, actual linked-entry, lifetime-negative,
and DOS-owned memory-reuse probes are included in the working changes.

Focused local implementation checks have run. Private candidate identities,
actual memory values, command-screen evidence and the tested D88 are retained
outside Git. The public verifier correctly rejects the current worktree's
component identity drift from this historical record. Final dependency rebinding,
scoped child/parent publication and CI qualification for the new implementation
are **NOT RUN / pending**. No updated M13 PASS or HANDOFF READY is claimed here.
Manual physical-keyboard and hardware checks for this change are also NOT RUN.

## Historical qualification record

This report records the qualified implementation and its public and private
evidence boundary. Manual physical-keyboard and real-hardware validation are
not claimed.

## Fixed identities

- START_SHA / M12 downstream base:
  `66138e6539e4220ae7b6d3ffee24581e0d674267`.
- M12 qualified implementation:
  `9b508a80eb3c4d33e1bb683f7963ae350067fd14`.
- QUALIFIED_IMPLEMENTATION_SHA:
  `7ddca85c1bf3ee74fea396a27a3a75d91cb78a21`.
- fdkernel M13 child:
  `e432296345f1ccc783a42c02baa7ffe4bd2a6eb8`.
- FreeCOM:
  `6cd372bdd8d54cecbde1635f1296795eb78712af`.
- Country:
  `23f189cca3420606eae8723884fa92ccd65eb307`.
- VAEG baseline contract:
  `7dd453cbd36014ba453a26765b00cd0cc9a99655`.
- Qualification record:
  `qa/golden/m13/qualification.json` (SHA-256
  `edf0cc28c69b707cf27428a249379425769a30f4b80eb7c64b9f82e9d2726833`).

## Implemented scope

The child target links the common FreeDOS startup, DOS dispatch, FAT12,
memory/process, EXEC and I/O objects with PC-88VA adapters. The M12 request
and 4 KiB kernel-owned buffer remain the only disk backend; bounded reads are
translated by the adapter and write, format, verify and unsupported LBA
operations are rejected before the callback. M09 output and M11 input are
exposed through the common CON table. Previously accepted wrapper FAR frames,
resident-memory reservation, FL_READ arithmetic, clock handling, and helper
ABI repairs are retained.

Public COM and relocatable MZ probe sources remain under
`tests/m13/fixtures`; generated binaries and media are ignored outputs. The
M13 contracts, schemas, component lock, manifest and verifier contain no
private firmware or media contents.

## Verification completed

- M12 prerequisite publication, component pins, artifact/schema instances and
  the recorded M12 CI runs were revalidated before the current child update.
- The fdkernel child source is clean, its remote topic branch equals the
  recorded child SHA, and child CI run `35132779485` (attempt 1) tested
  `e432296345f1ccc783a42c02baa7ffe4bd2a6eb8`; its `build` and `test` jobs
  succeeded.
- Two pinned Linux/amd64 Open Watcom builds from the child source were
  byte-identical. The resulting PC-88VA kernel and map identities are held in
  the private qualification record; no generated binary is committed.
- The public source/probe pair builds are byte-identical, and the public M13
  schema, instance, component-binding and common-core source checks pass with
  the current identities.
- Private normal VAEG headless runs reached the real FreeCOM command loop and
  completed controlled root and subdirectory `DIR`, `TYPE`, COM and relocated
  MZ probes, returning to a prompt. Invalid-command recovery and automated
  Backspace editing cases also returned to the prompt. Repeated root-DIR and
  invalid-command/recovery runs had equal normalized projections. These are
  private VAEG results, not public CI or manual-hardware claims.
- The ROM-free M11 consumer contract test passed in the pinned Linux/amd64
  environment, including repeatable non-destructive peek, one-time consuming
  read, and press/release cases. The current FreeCOM date-parser change is
  kept as a separate component commit and was not conflated with kernel
  evidence.

## Acceptance boundary and explicit non-claims

- Public qualification CI run `35138781354`, attempt 1, tested exact head
  `7ddca85c1bf3ee74fea396a27a3a75d91cb78a21`; jobs
  `public-readonly-freecom` and `historical-regression` concluded success.
- Child CI run `35132779485`, attempt 1, tested exact child
  `e432296345f1ccc783a42c02baa7ffe4bd2a6eb8`; required build/test jobs
  concluded success.
- `VAEG PASS` applies to the private normal automated SDL/headless command
  path through real DOS/FreeCOM services. Manual physical-keyboard input was
  not run. Hardware validation was not run (`DEFERRED HARDWARE VALIDATION`).
- Writable DOS, Japanese/NLS, ANSI, HDD, XMS/EMS, TSR, networking and broad
  DOS compatibility remain outside M13.
- The final D88 is retained in the private handoff directory and is not
  published in this repository. `M13 HANDOFF READY` and `DOWNSTREAM_BASE_SHA`
  are recorded after the publication-tip and final-tip checks.

Generated binaries, D88 images, ROMs, traces and concrete VAEG-derived values
remain in the persistent private evidence area and are not committed.

## Current fixed-VA-loader implementation checkpoint

This historical report remains the record of the earlier qualified revision.
The current implementation has a newer fixed-entry source/profile integration;
it is not folded into the historical PASS above and is not a new M13 PASS.

The source-visible profile is `config/m08/va-fixed-3000-overlay.json`. It
keeps the VA bootstrap entry at `3000:0000`, the initial system-file load at
`1340:0000`, and the transformed resident allocation as separate ownership
intervals. Two pinned Linux/amd64 diagnostic-off builds from the current
fdkernel source produced identical kernel bytes. The source-bound placement
test passed in the pinned Unicorn environment (19/19 placement tests); the
five init-lifetime tests passed on the host.

The first newly composed media image exposed a stage-1 extent mismatch and
was retained as a failed diagnostic artifact. Rebuilding stage 1 from the
media-derived extent produced a source-rebuilt private image that was
VAEG-tested under the 512-KiB VA configuration to `PC88VA kernel`, `InitDisk`,
FreeCOM, a directory listing, and a returned `A:\>` prompt (exit status 0).
The image identity and raw runtime evidence remain in the private handoff
area and are intentionally not published here.

The user subsequently reported the issued M13 human gate as passed for this
candidate. This is a user-supplied gate result; the message did not identify
physical PC-88VA versus manual VAEG, so physical hardware remains
`DEFERRED HARDWARE VALIDATION` unless explicitly identified. This checkpoint
does not alter the historical acceptance identities, does not claim the
complete M13 matrix, and does not declare a new M13 PASS. Full details and
private runtime evidence remain in the ignored private evidence root and are
not part of this public report.

## User acceptance decision

The user accepted the M13 VAEG/private read-only and interactive scope as
**M13 PASS** while leaving physical hardware validation deferred. This does
not claim `HARDWARE PASS`, because the confirmation did not identify a
physical PC-88VA run. `M13 HANDOFF READY`, publication-tip identity, and
current implementation CI qualification remain separate and are not inferred
from this user-level acceptance decision.
