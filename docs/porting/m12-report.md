# M12 resident read-only floppy service

Status: **M12 PASS — FINAL PUBLICATION HANDOFF PENDING.**

This report records the implementation qualification. The separate local
`M12-final-handoff.md` records the publication tip after final-tip CI; this
tracked report is not changed merely to replace that wording.

## Fixed identities

- START_SHA / M11 publication: `c5ddf7c87cac46d357cfe75d132a819c7cf3fbe4`.
- QUALIFIED_IMPLEMENTATION_SHA: `9b508a80eb3c4d33e1bb683f7963ae350067fd14`.
- fdkernel child: `21d9f3450276d42e5fedd1ddb9e80485b888cc07`.
- FreeCOM: `855281a3114b43ad4b8d9a320f2aca39be046bba`.
- Country: `23f189cca3420606eae8723884fa92ccd65eb307`.
- VAEG observer: `7dd453cbd36014ba453a26765b00cd0cc9a99655`.
- Artifact manifest: `46427247cf2a347361c3a69ba81fd9981141485693d150213efed38ec4b72c77`.
- Qualification record: `7096190b41614dc207de32759e19ce93dbceb9efdc610b79142648f553af7ff6`.

## Implementation

M12 exposes a kernel-resident, non-reentrant read-only request entry backed by
the accepted M08 firmware callback. The request and 4 KiB destination are
kernel-owned, with typed contract/range/capacity/short/firmware errors,
bounded retries and no write or format path. M08 loader stages and M09 console
behavior are unchanged; M10 initialization and M11 input run before the
service. DOS writes, COMMAND.COM, Japanese/NLS, full DOS and hardware are
outside this milestone.

## Private qualification

Two clean production-memory main runs reached R0–R9 and read the independent
fixture sectors through the emulated FDC path. Their canonical projections,
executable identity, stop reason and input-preservation manifests match. Two
fault-control runs reached E0–E4 with a bounded invalid-sector controller
failure (AX=5 after finite retries); the range-control pair records AX=2
rejection without a backend request. A clean normal pair after fault removal
records recovery. All private ROMs, D88 images, traces and concrete values
remain under persistent ignored `.private-evidence/m12` and are not published.

## Public gates

The public schema instances, artifact and qualification bindings, component
lock, resident source checks, ROM-free M12 tests, two clean network-disabled
Open Watcom builds and M08–M11 historical regression passed. Qualification CI
was run 34068685333, attempt 1, exact head
`9b508a80eb3c4d33e1bb683f7963ae350067fd14`; required jobs
`public-resident-floppy` and `historical-regression` concluded success.

No hardware result is claimed: `DEFERRED HARDWARE VALIDATION`.

## Handoff

The final documentation/publication commit, exact final-tip CI, remote-tip
equality, ancestry, bounded publication diff and generic handoff checker are
still required before declaring **M12 HANDOFF READY**. No M13 work has begun.
