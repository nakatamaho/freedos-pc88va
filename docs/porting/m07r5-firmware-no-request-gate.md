# M07R5 firmware request-gate diagnosis

M07R5 is a bounded continuation of the PC-88VA boot-path investigation. It
does not change the M04 geometry, M05 media, M06 carrier, boot-sector bytes, or
component gitlinks.

The earlier `NO_REQUEST` result is retained as historical evidence only. A
fresh production-memory trace with valid repeated inputs observed the abstract
main-to-subsystem request, subsystem scheduling and execution, and a drive
motor-stable transition. The first IRQ difference re-converged architecturally
and is classified as `NONCAUSAL_IRQ`.

The current abstract predicate is `HANDSHAKE_INIT`. The wait loop is located,
but its response producer is not fully attributable from the available public
trace interface. The request boundary is therefore reached (`B2`); the next
independent boundary, controller progress (`B3`/`B4`), is not established.
No FDC command, sector transfer, or project marker execution is claimed.

The public record intentionally contains no firmware identity, private input
identity, trace contents, addresses, registers, opcodes, or derived concrete
values. Exact private observations remain local and require owner review
before any promotion. The eight M08 fields remain unresolved, and M08 is not
started.

The M07R5 public gate checks canonical JSON, accepted predecessor identities,
component cleanliness, the accepted causal-trace VAEG pin, the abstract
boundary result, and the privacy boundary. It does not execute VAEG or read
private material.

Status: `M07R5 BLOCKED — FIRMWARE PREDICATE PRODUCER UNOBSERVABLE`.
