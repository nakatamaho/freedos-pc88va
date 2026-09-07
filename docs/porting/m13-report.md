# M13 common FreeDOS core and read-only FreeCOM session

Status: **M13 BLOCKED — PRIVATE QUALIFICATION AND FINAL PUBLICATION HANDOFF
NOT ESTABLISHED.**

This tracked report records the bounded implementation work. The separate
local `M13-final-handoff.md` is the only post-push handoff record and must not
be committed merely to record its own future SHA.

## Fixed identities

- START_SHA / M12 downstream base:
  `66138e6539e4220ae7b6d3ffee24581e0d674267`.
- M12 qualified implementation:
  `9b508a80eb3c4d33e1bb683f7963ae350067fd14`.
- fdkernel M13 child: `326c5481da09eafa9d1503e95c1339732bec20f5`.
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
  selector. Child CI run 34077732724 attempt 1 succeeded at exact child SHA
  `326c5481da09eafa9d1503e95c1339732bec20f5` with `build` success.
- A network-disabled Open Watcom 1.9 full common-core link at this child
  produced a deterministic DOS MZ `KERNEL.SYS` of 91,575 bytes (body 91,239
  bytes). The retained M08 loader ABI represents the kernel file and
  allocation capacities as single bounded word/segment intervals, whose
  maximum validated owned extent is 65,520 bytes. The kernel therefore cannot
  be loaded or transformed through the accepted M08 path without an explicit
  multi-segment loader/ABI change and fresh M08-M13 qualification.
- Parent M13 public schema/instance, deterministic two-build, historical
  regression and implementation-tip CI gates pass. Parent CI run 34073545757
  attempt 1 tested implementation tip
  `80ea2814eb83b643d90d3d478b348bba117584f9` and both required jobs
  (`public-readonly-freecom`, `historical-regression`) succeeded.
- The generic checker passes content/topology/source checks and fails closed at
  `PRIVATE_QUALIFICATION_PENDING` for `--accept`.

## Explicitly not run / not claimed

No private VAEG M13 session has been run. The pinned VAEG checkout at
`7dd453cbd36014ba453a26765b00cd0cc9a99655` is available and builds, but the
accepted M08 loader cannot accept the 91,575-byte common kernel: its validated
single owned interval is capped at 65,520 bytes and its MZ/file records are
bounded words. Running VAEG would therefore stop before kernel entry and would
not establish S0-S9/E0-E4. Real FreeCOM startup, DIR/TYPE, COM/MZ execution,
allocator recovery, alternate-fixture behavior and backend-fault recovery are
not claimed. The required loader/ABI extension is a specification and
qualification boundary, not a safe documentation-only repair.
`M13 HANDOFF READY` and `DOWNSTREAM_BASE_SHA` are not established. Hardware
was not run. Writable DOS, Japanese/NLS, ANSI, HDD, TSR, networking and broad
DOS compatibility remain outside M13.
