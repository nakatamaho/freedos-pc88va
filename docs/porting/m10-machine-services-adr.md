# M10 machine-services mechanism decision

Status: runtime-qualified implementation. Public acceptance and handoff are
separate gates recorded in the milestone report.

## Scope and ABI

The starting child is `ef46a7ad4b381cf7a301899bee00fec99f5e37a7`.
Its M06 declarations are near Watcom register-ABI functions returning `int`:
machine initialization and interrupt adoption have no arguments; memory and
clock accept an opaque near record pointer in AX; fatal stop accepts a reason
in AX. M10 retains those signatures, defines versioned records, and replaces
only these five stubs. The platform probe, input and NLS stubs remain unavailable.
Assembly implementations use explicit CS data references, preserve all other
general registers, segments and architectural FLAGS, and return zero only on
success. Failure returns minus one without publishing a partly valid record.
Fatal stop is the documented non-returning exception.

## Selected mechanisms

| Service | Mechanism | Failure and ownership policy |
| --- | --- | --- |
| machine_init | Single-shot transaction: entry checks, bounded memory map, read-only interrupt adoption, clock origin and observed progress, M09 output, final preservation checks, commit readiness | IF and DF must be clear; stack and kernel must fit disjointly below the public display window. Readiness remains false on failure; repeat calls are rejected. Temporary records belong to the kernel. |
| memory_query | Conservative map of an explicitly linked kernel-owned arena | Only the arena is allocatable. Everything else in the 20-bit address space remains reserved, including unclaimed conventional RAM. No RAM-size inference or destructive probe. Validate arena bounds and linear-address overflow before exposing it. |
| interrupts_init | Validate and snapshot inherited IVT and PIC masks with IF clear | No IVT, mask, mode, EOI or nesting-state writes. The already exercised M09 Text BIOS vector must remain nonzero and unchanged. Compare the complete IVT and both masks again before readiness. Hardware interrupts remain disabled. |
| clock_read | Source observation establishes origin zero; subsequent reads require a bounded low-to-high VRTC transition | Origin is not a claim of progress. Each subsequent tick requires an observed edge. This is a monotonic count of observed edges, not elapsed time or calendar time; edges between calls are not counted. Poll low then high, each with a finite instruction budget; failure leaves the previous count and output untouched. |
| fatal_stop_request | No final diagnostic; CLI and a guest HLT loop | Reason is not printed. No return, controller reinitialization or disk operation. External production tracing must establish repeated HLT execution with IF clear rather than treating a host timeout as success. |

Clock tick storage is a 32-bit counter modulo 2^32. The first valid status sample
establishes zero; subsequent successful reads advance it by exactly one only
after a source transition. Initialization requires both the origin sample and
the subsequent actual progress, so a stuck source never commits readiness.
The atomicity guarantee is
single-threaded, non-reentrant execution with IF clear; a record is committed
only after a complete sample. Synthetic tests cover carry, wrap, stuck-high,
stuck-low, invalid records and reentrancy. No host clock or build timestamp is
read. Frequency in seconds and unattended elapsed-time accounting are explicitly
outside this contract. A future interrupt-driven clock would require a new
ownership contract; this adapter does not install one implicitly.

The arena is carved from the linked carrier's own storage, not discovered free
RAM. A three-interval map partitions the address space into reserved prefix,
usable arena and reserved suffix. The kernel stack, loader, IVT, firmware,
display, ROM windows and any observer outside the arena remain reserved. A
caller may only request records in the explicitly exported service-record
storage; arbitrary near pointers are rejected. This intentionally narrow ABI
does not claim a general DOS allocator or conventional-memory enumeration.

The actual MZ stack may begin at a nonzero intra-paragraph offset. Entry checks
derive that offset from the accepted 4096-byte stack and the live caller SP;
they do not confuse SS:0 with the stack's first owned byte. Carry and bounds
checks reject unsupported stack layouts before readiness is established.

## Provenance and rejected routes

All machine-specific numeric constants require public provenance. The pinned
VAEG commit is `7463f9501d84701f50f3243d5067b6a9dfd0c2e7`:

- `io/sysportva.c`, `sysp_i040` and `sysportva_bind`: port 040h, bit 5 is
  the read-only VRTC status. This getter reads existing state without clearing
  it. Its modeled fixed status bits are checked before sampling; unsupported
  readback fails explicitly. `io/tsp.c`, `tsp.h`, and the display event scheduler
  define its source. This is a VAEG-qualified source, not a hardware claim.
- `io/pic.c`: PIC mask reads are observational; no controller initialization
  is required merely to leave CPU interrupts disabled.
- `memoryva/memoryva.c` and the accepted M08 ownership checks define the display
  window boundary. The carrier owns only its linked bytes and declared stack.
- `io/memctrlva.c` defines the observational ROM and SYSM bank getters at
  0152h and 0153h. The SYSM getter has status bits outside its low five bank
  bits. Initialization compares the ROM selector and those bank bits before
  and after its transaction; it never writes either selector.
- Accepted M09 `pc88va/kernel/console.asm` defines the Text BIOS vector and
  wrapper preservation policy. It is reused unchanged for the fixed ASCII
  `M10 INIT OK` diagnostic; no runtime value is emitted.
- `cpu/upd9002/upd9002_mn.c` defines the production HLT quiescence and FLAGS
  restoration semantics used by the private observer, not additional guest
  initialization requirements.

PIT adoption was examined but not selected: its latch/control paths alter
internal read sequencing, and the single-channel latch path also clears a PIC
request in the pinned implementation (`io/pit.c`, `pit_o77`). A read-back route
could avoid that request change but would still require a stronger inherited
mode and latch-ownership contract. Calendar firmware would add unneeded civil
time semantics. Neither is necessary for the bounded edge-clock contract.
Direct PIC, timer and memory-controller initialization, blanket IVT clearing,
IBM-PC fallbacks, NEC98 assumptions and speculative RAM probing are rejected.

Disk ownership qualification requires no post-entry disk command, transfer,
timer rearm or controller reset. A causal explanation alone does not waive
that guard. Exploratory device events and rejected hypotheses remain private;
they must not be normalized into an event-free acceptance projection. The
origin-sample clock contract avoids waiting for an unnecessary first edge.

Private launch values stay in the ignored schema-validated local overlay.
No private-derived constant is embedded in target code or this ADR. Private
qualification verified the ownership and clock behavior in two clean main and
two clean fatal runs; failed exploratory observations remain retained, not normalized.

## Acceptance boundary

Two clean main runs must establish I0-I9 and unchanged M08/M09 behavior; two
separate controls must establish F0-F4. Compare complete private projections,
input preservation, source and executable identities. Public synthetic tests
are not substitutes for those observations. Native build CI and final-tip CI
remain mandatory. Console input, Japanese/NLS, ANSI, disk writes, HDD,
COMMAND.COM, full DOS and hardware validation are not implemented or claimed.
