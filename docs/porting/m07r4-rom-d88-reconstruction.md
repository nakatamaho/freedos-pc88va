# M07R4 private ROM/D88 boot-path reconstruction

## Status

`M07R4 BLOCKED — B2 PREDICATE NOT DISTINGUISHABLE`

M07R4 supersedes the earlier requirement that a verified positive control must
exist before bounded private reconstruction begins. It does not turn a local
candidate into a positive control and does not promote private observations.

The public record is intentionally abstract. Local text review, bounded ROM
static analysis, and bounded D88/trace comparison were performed outside the
repository. Exact input identities, addresses, instruction bytes, branch
predicates, sector contents, traces, and derived values remain private.

## Abstract result

The repeatable public boundary record reaches B0 and B1. B2 is not
distinguishable from the retained evidence, so the result is `UNKNOWN`; it is
not a claim that the firmware does not access the floppy subsystem. No
controlled marker execution was observed, and none of the eight M08 fields was
resolved.

The private runs preserved their inputs and produced byte-identical abstract
projections for repeated trials. The static and dynamic records do not yet
agree on a uniquely attributable B1-to-B2 predicate. The next action is a
separately bounded telemetry or source review focused on the main-CPU to
subsystem handshake boundary. It must not broaden into M08 loader work.

## Evidence boundary

The current VAEG public source identifies separate production CPU memory,
main/subsystem interface, subsystem execution, and FDD backends. Those source
facts support the abstract B0--B7 vocabulary and the need to observe the
handshake path; they do not establish private firmware behavior or real
hardware behavior. The local electronic/text sources were used as provisional
evidence where their provenance permits, with image-dependent claims kept
unresolved.

The existing generic D88 parser and abstract boundary classifier remain the
public tools. They contain no private disk data and no input-specific rule.

## Disposition

- Classification: `UNKNOWN`.
- Last reached boundary: `B1`.
- First unobserved boundary: `B2`.
- B2 blocker category: `UNKNOWN`.
- Evidence-backed candidate settings recorded privately: 6 of the maximum 16.
- Marker: not reached.
- M08 mandatory fields: 0 resolved, 8 unresolved.
- Promotion: `prohibited_pending_user_approval`.

M08 remains not started. No private value is a public contract, and this
record makes no firmware-acceptance, boot, or hardware claim.

## Public CI boundary

The public workflow validates the redacted status, prior public milestone
identities, component pins, schema, abstract boundary rules, and privacy
guards. CI has no access to private ROMs, D88 inputs, manuals, or local
analysis output; it therefore validates the derived public record, not the
private source contents.
