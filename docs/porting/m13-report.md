# M13 common FreeDOS core and read-only FreeCOM session

Status: **M13 PARTIAL — implementation and private VAEG qualification are
advanced; final acceptance and handoff are not yet established.**

This report records the current public contracts and the latest private
qualification boundary. It does not claim M13 PASS or HANDOFF READY.

## Fixed identities

- START_SHA / M12 downstream base:
  `66138e6539e4220ae7b6d3ffee24581e0d674267`.
- M12 qualified implementation:
  `9b508a80eb3c4d33e1bb683f7963ae350067fd14`.
- fdkernel M13 child:
  `e432296345f1ccc783a42c02baa7ffe4bd2a6eb8`.
- FreeCOM:
  `6cd372bdd8d54cecbde1635f1296795eb78712af`.
- Country:
  `23f189cca3420606eae8723884fa92ccd65eb307`.
- VAEG baseline contract:
  `7dd453cbd36014ba453a26765b00cd0cc9a99655`.

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
  editing cases also returned to the prompt. These are private VAEG results,
  not public CI or manual-hardware claims.
- The ROM-free M11 consumer contract test passed in the pinned Linux/amd64
  environment. The current FreeCOM date-parser change is kept as a separate
  component commit and was not conflated with kernel evidence.

## Remaining gates and explicit non-claims

- The parent branch still needs its identity/qualification publication
  commits and a successful parent CI run at the final parent tip.
- The private qualification record remains pending: repeated peek/read and
  press-release-press coverage must be bound to the final candidate, the full
  shell command matrix must be reconciled with the accepted contract, and the
  final D88 must be copied and hash-checked as the exact qualified image.
- Manual physical-keyboard input was not run. Automated SDL/headless input is
  labelled as automated and does not establish the manual gate.
- Hardware validation was not run (`DEFERRED HARDWARE VALIDATION`). Writable
  DOS, Japanese/NLS, ANSI, HDD, XMS/EMS, TSR, networking and broad DOS
  compatibility remain outside M13.
- `M13 PRIVATE VAEG QUALIFICATION PASS`, `M13 PASS`, `M13 HANDOFF READY`, and
  `DOWNSTREAM_BASE_SHA` are not established by this report.

Generated binaries, D88 images, ROMs, traces and concrete VAEG-derived values
remain in the persistent private evidence area and are not committed.
