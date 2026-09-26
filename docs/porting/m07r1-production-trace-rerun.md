# M07R1 production-trace boot-probe rerun

M07I-R1 repaired the pre-existing VAEG ROADMAP master-gate identity without
relaxing the validator. VAEG commit
`16ad2e0619bf4ed82a739325f7291eba4a6ed8ad` passed the complete native
workflow on attempt 2, including production-memory tracing and every
compatibility job. Attempt 1 had one non-reproducing runtime-disabled trace
selftest failure; no source change was made between attempts.

The trace-enabled build selects production memory with tests disabled and does
not link the flat test-memory seam. P0 and P1 remain reproducible across two
clean builds. Their binary identities changed from the preceding commit only
because VAEG deliberately embeds the current Git commit identity in the
executable. The canonical trace projection remained unchanged.

The M07 public probe source, nine-byte probe, V00--V04 definitions, schemas,
and public golden are unchanged. The original blocked M07 trials remain
historical and are not M07R1 evidence.

Ten fresh bounded private trials ran: two independent production-memory VAEG
processes for each public variant. Private inputs remained unchanged and each
variant's two canonical projections were byte-identical. No variant reached
the public probe marker within the fixed instruction bound. Consequently all
eight boot-entry fields remain unresolved and the status is
`M07R1 BLOCKED -- NO CONTROLLED PROBE EXECUTION`.

Exact firmware identities, traces, addresses, registers, media copies, and
private results remain outside Git. The committed status contains only the
public VAEG capability and CI pin, public harness identities, counts, field
names, and nonpromotion state. M08 remains blocked.
