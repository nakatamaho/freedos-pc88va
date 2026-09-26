# M14 writable floppy integration contract

Status: runtime qualified; final parent CI and publication closure pending.
This contract describes the current source boundaries. See
[the acceptance matrix](m14-acceptance.md) for required evidence.

## Common request ownership

The authoritative request and status definitions are in the pinned component's
`hdr/device.h`. `kernel/blockio.c` constructs the request and calls `execrh`;
`kernel/dsk.c` dispatches it through `blk_driver` and `blockio`. The request's
transfer address is a FAR pointer. Its count and starting sector are in sectors,
not bytes; the extended start is selected by the common `HUGECOUNT` convention.
The resident VA request is separate and records completed bytes.

| Common command | Dispatch and ownership |
| --- | --- |
| `C_INIT` (0) | Common disk initialization constructs the device state; runtime dispatch rejects this entry. |
| `C_MEDIACHK` (1) | `mediachk` queries the adapter and returns unchanged, changed or unknown. |
| `C_BLDBPB` (2) | `bldbpb` rereads and validates the boot record through the normal read path. |
| `C_INPUT` (4) | `blockio` and `LBA_Transfer` reach `FL_READ`. |
| `C_OUTPUT` (8) | The same common path reaches `FL_WRITE`. |
| `C_OUTVFY` (9) | The common path writes, then performs the supported read-and-compare verification. |
| `C_OFLUSH` (11) | The device entry has no private write cache; the common DOS buffer layer owns actual dirty-buffer flushing. |

The common request receives `S_DONE` on success. Rejections carry `S_ERROR`
and `S_DONE` with the appropriate DOS device error, and transfer rejections
complete zero sectors. Successful partial progress is retained on a later
device failure. The first index outside the command table must be rejected
before dereferencing a table entry or looking up a device.

A valid zero-count common transfer completes zero sectors without device I/O.
The direct `FL_*` adapter ABI rejects a zero-count call; these are distinct
interfaces and their tests retain that distinction. Invalid starting sectors
are not made valid by a zero count.

## VA transport, ABI and recovery

The production adapter uses the existing single supported floppy geometry and
resident request/buffer. Whole-request sector arithmetic and caller-buffer
coverage are checked before a callback. The adapter copies one sector through
its owned resident buffer and never treats an unexplained memory gap as free.
Segment-offset wrapping and the physical address limit are checked separately.
The port does not add an IBM-PC DMA-wiring assumption.

The medium-model C adapters return FAR and clean their declared arguments.
The resident core preserves its declared caller registers and segments; its
request pointer belongs to the caller. The common critical-error bridge uses
the matching FAR C frame, including reentry and context restoration. Tests
execute those emitted instructions as well as the compiled common C policy.

The legacy `fl_write` return value cannot express a partial sector count.
Consequently, the common VA path dispatches one write sector per call and
updates the common completed count only after that sector succeeds. It does
not replay a completed prefix. Write-with-verification counts a sector only
after the real verification operation succeeds.

The resident transfer owns bounded firmware retries. The common VA write path
does not add a second automatic retry loop or an extra global BIOS reset.
Unavailable-media/timeout outcomes leave the resident write retry loop.
Common read retries remain finite. A user-requested critical-error retry is
subject to media revalidation and the original request's lifetime; it cannot
silently authorize an old buffer against replacement media.

## Media lifetime and filesystem policy

The owner-selected policy is conservative: changed or unknown media invalidates
the drive's cached buffers and existing local handles. `media_invalidate`
marks those handles stale and advances the request generation. An explicit
new pathname operation may revalidate the BPB and open a new handle; it does
not revive an old handle. A stale close releases its reference without writing
old metadata to the replacement. Uncertainty can discard pending writes even
when the same disk is still present. This behavior must be documented in the
final exchange procedure and exercised with protected and absent media.

FAT, directory entries, allocation, file sizes and flushing remain in the
common FreeDOS filesystem and buffer layers. There is no second FAT allocator,
FreeCOM storage API, private cache or emulator-created DOS success path.
An interrupted write is not transactional; its returned status/count and
persisted prefix must be checked independently. The replacement medium must
remain unchanged until an explicit new operation valid for it is issued.

## Qualification boundary

Keep immutable M13 read-only evidence separate. The M14 writable configuration
changes historical write-rejection expectations only for supported writable
media. Actual protection and invalid-request checks remain mandatory.
Record each candidate's native memory configuration, resident/buffer/stack
ownership and allocation probes. A supported emulator capacity or a placement
unit test alone does not qualify that capacity for the real shell workload.
Ordinary boot/write runs, instrumented fault runs, frontend key automation,
manual input and hardware results remain separate evidence classes.

The selected FreeCOM source variant is the existing generic ASCII build using
DOS input/output services, integrated with the PC-88VA common kernel. The active
MEM alias source pin must match the packaged COMMAND.COM; an older accepted
shell image is a control, not proof of that newer source identity. The build
harness exports both components, uses the established deterministic timestamp
configuration, and compares the actual kernel, shell and probe binaries twice.
