# ADR 0003: Parameterized PC-88VA kernel loader

Status: implementation and two-run private execution verified; final public
build, regression, publication and CI gates pending.

## Scope and evidence boundary

M08 consumes the accepted M07 handoff through a regular-file, local-only
overlay. No private-derived address, service selector, register value, or
media identity belongs in this ADR, public configuration, or synthetic tests.
The M06 carrier is not a working DOS kernel. Its entry marker, not execution
of COMMAND.COM, is the terminal guest observation for M08.

The PC-88VA implementation belongs in the fdkernel child. FreeCOM and Country
remain unchanged. No NEC98 or IBM-PC disk implementation is a fallback.

## Stages and memory ownership

Use a small firmware-loaded stage 1 and a separately loaded stage 2.
The initial loaded extent is an overlay input, not an assumption that all
loader code fits in one sector. Stage 1 may read a builder-declared stage-2
extent only after the firmware disk adapter has been qualified. This exception
does not permit a fixed-sector KERNEL.SYS load: kernel loading traverses the
root directory and FAT12 chain.

All memory regions are half-open physical intervals [start, end). Addition,
paragraph conversion, and segment-window calculations must reject overflow
before comparing intervals. The private overlay supplies placement constraints;
the public validator enforces them identically for synthetic inputs.

| Region | Owner and lifetime | Reuse rule |
| --- | --- | --- |
| Firmware workspace | Firmware, through the last firmware call | Never reuse in M08 |
| Initial loaded region | Stage 1, until stage 2 takes control | Keep live for diagnostics |
| Stage 2 | Loader, through the final far transfer | Never overlap kernel or stack |
| Root/FAT/sector scratch | Loader, during traversal and reads | Reuse only after its current consumer finishes |
| MZ file staging | Loader, through validation and byte comparison | Release only after successful transformation |
| Kernel body and allocation | Kernel, from transformation onward | No loader scratch reuse |
| Loader stack | Loader, after explicit initialization | Keep separate from firmware and kernel stacks |
| Kernel stack | Kernel, before final far transfer | Initialize only after MZ validation |

Freeze the qualified boot-drive context from the private overlay before
modifying entry registers. A trace-correlated inserted-drive identity is not
automatically a guest register ABI: when the retained contract supplies that
form of context, stage 1 carries it explicitly instead of inventing a firmware
register convention. Preserve it as an opaque validated object through every
disk call. Record incoming FLAGS/IF;
the qualified adapter specifies its call-time interrupt requirement. Disable
interrupts across stack replacement and final handoff; do not pretend that
an unimplemented kernel interrupt service is usable. A required incompatible
firmware interrupt policy must fail qualification, not be silently normalized.

## Disk ABI

Qualification starts with a project-authored interrupt-call probe using the
locally documented firmware read interface. Its register setup and interrupt
selector are generated exclusively from the private adapter profile. The first
request re-reads the initial sector to the same firmware-loaded region: source
and destination bytes must remain identical, so no unqualified scratch region
is needed. It retains the firmware-provided stack for this single firmware
call. The bounded observer distinguishes success and error return sites and
must verify a completed transfer, not just an error flag. This is an adapter
qualification probe, not the final loader or permission to claim M08 success.

The public disk request contains logical sector, sector count, destination
capacity, geometry, and boot-drive context. Validate the whole range before
I/O. Split calls at track, transfer-size, and segment-window limits established
by the qualified adapter. Read complete sectors into owned scratch and copy
only the requested final file bytes into the destination.

The selected candidate is a parameterized firmware interrupt adapter. Private
documentation and two clean VAEG self-read trials establish a no-retry call,
completed transfer, exact destination bytes, and preserved return state. This
alone did not qualify a different destination or loader-owned stack. Subsequent
owned-buffer qualification and two complete loader executions verified the
actual additional sector sequence, return state and destination bytes. This
does not establish an unrestricted firmware service or a second drive binding.

Accept a firmware-service adapter only after private source/trace evidence
establishes the call entry, request fields, success/error convention, clobbers,
stack/workspace requirements, drive propagation, and bounded completion. These
are private overlay parameters, including request-register binding and status
interpretation. There is no direct FDC implementation or secondary fallback.

Public callers receive explicit success, range, capacity, firmware-error, or
unsupported-contract results. No short transfer is success. The default retry
ceiling is zero; any nonzero retry/reset policy needs separately qualified
evidence and a fixed ceiling. Exhaustion enters a diagnostic stop without
kernel handoff. Preserve caller registers except documented return values;
firmware register and memory clobbers must be recorded in the adapter contract.

## FAT12 policy

Use accepted BPB/layout inputs, validate all computed extents against media
capacity, and require the expected FAT12 layout. Locate the exact short name
KERNEL.SYS in the root directory. Skip deleted entries, long names, volume
labels, and directories. Reject invalid first clusters, zero/oversized files,
duplicate matching entries, out-of-range directory/FAT references, and early
directory termination without the file.

Decode even and odd FAT12 entries including sector-boundary crossings. Track
visited clusters with a bounded bitmap and independently bound traversal by
the file size and data-cluster count. Reject free, reserved, bad, out-of-range,
cyclic, prematurely terminated, and overlong chains. Require end-of-chain at
the file's final cluster. Never write past the exact directory file size or
destination capacity. Verify the loaded file bytes before MZ transformation.

## MZ and handoff policy

Initially support zero-relocation DOS MZ only; reject a nonzero relocation
count rather than ignoring relocations. Validate signature, header paragraphs,
encoded page/last-page size, relocation-table bounds, allocation fields, entry
CS:IP, stack SS:SP, file/body bounds, and every placement arithmetic operation.
Define zero last-page bytes as a full final page and reject inconsistent sizes.

Place the executable body, excluding the MZ header, in the validated kernel
region. Allocate and zero the required additional region within the accepted
memory budget. Prove that entry fetch lies in the body and the initial stack
lies within the kernel allocation. Do not execute the MZ header as code.

The handoff record identifies the validated loaded image, transformed body,
kernel entry, stack, drive context, and interrupt policy. Validate it before
changing SS:SP. Perform one one-way far transfer; an error must never return a
fabricated successful handoff. The observed M06 entry marker is required twice.

## Qualification and publication

This ADR cannot become accepted until the machine-readable contract, synthetic
positive/negative tests, deterministic clean builds, two private runs, byte
checks, and public CI all pass. M01R1 through M07 historical contracts remain
unchanged. Publish the child first and prove remote reachability before updating
the parent gitlink. Private-derived parameters are not promoted by M08 success.
