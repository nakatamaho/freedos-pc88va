# M13 common FreeDOS core and read-only FreeCOM session

Status: **M13 IMPLEMENTATION IN PROGRESS — PRIVATE QUALIFICATION AND FINAL
PUBLICATION HANDOFF PENDING.**

This tracked report records the bounded implementation work. The separate
local `M13-final-handoff.md` is the only post-push handoff record and must not
be committed merely to record its own future SHA.

## Fixed identities

- START_SHA / M12 downstream base:
  `66138e6539e4220ae7b6d3ffee24581e0d674267`.
- M12 qualified implementation:
  `9b508a80eb3c4d33e1bb683f7963ae350067fd14`.
- fdkernel M13 child: `33da21f248fa7af25f9dd17a7a981c34f8ebec37`.
- FreeCOM: `855281a3114b43ad4b8d9a320f2aca39be046bba`.
- Country: `23f189cca3420606eae8723884fa92ccd65eb307`.
- VAEG baseline: `7dd453cbd36014ba453a26765b00cd0cc9a99655`.

## Implemented scope

The child target now links the common FreeDOS startup, DOS dispatch, FAT12,
memory/process, EXEC and I/O objects with PC-88VA adapters. The M12 request
and 4 KiB kernel-owned buffer remain the only disk backend; the adapter
translates bounded reads and rejects write, format, verify and unsupported LBA
operations before the callback. M09 output and M11 input are exposed through
the common CON table. The historical M06-M12 carrier target is unchanged.

Public COM and relocatable MZ probe sources are present under
`tests/m13/fixtures`; generated binaries and media remain ignored build
outputs. The contracts, schemas, component lock, manifest and verifier bind
only public source/metadata and contain no private firmware values.

## Verification actually completed

- M12 publication, component pins, artifact/schema instances and exact parent
  CI runs 34068685333 and 34069044160 were revalidated before mutation.
- Common and adapter NASM objects assemble with `PC88VA` and no IBMPC/NEC98
  selector. Child CI run 34072626987 attempt 1 succeeded at the exact child
  SHA with `build` success.
- Parent M13 public schema/instance, build-pair, VAEG private-session,
  deterministic two-build, VAEG runtime, historical regression and final-tip
  CI gates are not yet complete.

## Explicitly not run / not claimed

No private VAEG M13 session has been run; therefore S0-S9 and E0-E4, real
FreeCOM startup, DIR/TYPE, COM/MZ execution, allocator recovery, alternate
fixture behavior and backend-fault recovery are not claimed. Hardware was not
run. Writable DOS, Japanese/NLS, ANSI, HDD, TSR, networking and broad DOS
compatibility remain outside M13.
