# M13 common FreeDOS core and read-only FreeCOM session

Status: **M13 PASS — FINAL PUBLICATION HANDOFF PENDING.**

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
