# ADR 0001: Represent PC-88VA as an Independent Platform

- Status: accepted for M03 planning
- Date: not recorded; this ADR intentionally contains no wall-clock build
  value
- Scope: parent integration architecture only

## Context

The M01R1/M02R1 artifacts are a NEC98 baseline and are explicitly
`build-reference-only`. The pinned source tree contains shared DOS logic,
IBM-PC paths, and NEC98 hardware-facing paths. The M03 census locates build,
boot, disk, interrupt, memory, console, device, execution, and NLS surfaces,
but a textual hit is not a hardware contract.

The relevant lineage includes lpproj-derived FreeDOS components and the
existing NEC98 implementation. That lineage explains source organization and
historical reuse. It does not establish PC-88VA hardware equivalence. Source
fact: fdkernel commit
`6523acdb87f4665e6068ea331859885267242005`; FreeCOM commit
`855281a3114b43ad4b8d9a320f2aca39be046bba`; Country commit
`23f189cca3420606eae8723884fa92ccd65eb307`.

## Decision

Treat PC-88VA as an independent platform boundary alongside `ibmpc` and
`nec98`, initially named `pc88va`. Reuse platform-neutral code and explicit
interfaces, but do not inherit NEC98 hardware behavior by default.

This is an architecture decision and naming contract only. M03 does not
create a `pc88va` component, directory, target, boot sector, binary, or
emulator implementation.

## Alternatives considered

1. Hide VA behavior inside `nec98` conditionals. Rejected: it conflates two
   hardware contracts, makes source review and rollback difficult, and would
   allow a NEC98 assumption to become an accidental VA claim.
2. Treat VA as an IBM-PC variant. Rejected: shared DOS structure does not
   prove BIOS, FDC, DMA, interrupt, memory, or console equivalence.
3. Fork the complete component tree. Rejected for now: it duplicates stable
   DOS and NLS code before the required VA facts and increases drift.
4. Use a third platform boundary with explicit adapters. Accepted: it keeps
   the hardware contract visible and permits incremental reuse after evidence
   is accepted.

## Integration shape

The eventual directory/build naming is specified as `pc88va` beside the
existing `ibmpc` and `nec98` platform areas. The exact component repository and
target creation belong to later milestones. A small HAL/interface layer should
own boot entry, block I/O/media change, firmware calls, interrupt ownership,
timer, early console, keyboard input, and device initialization. Shared DOS
algorithms should depend on those interfaces rather than on broad platform
conditionals.

Selection should use a focused platform configuration and per-interface
implementation units. Avoid adding a new preprocessor branch at every call
site. Where a platform distinction is structural, keep it in a platform
directory or build graph; where it is behavioral, expose a narrow interface
with a documented contract and test seam.

DBCS/Japanese support begins as a separate build-matrix concern in M06. The
presence of `DBCS`/`JAPANESE` defines in FreeCOM and Country tables does not
select a VA keyboard or runtime contract.

## Migration and rollback

1. M04 records accepted VA boot/media evidence and defines the first adapter
   contracts.
2. Later milestones extract one boundary at a time, retaining the NEC98 and
   IBM-PC paths unchanged and running their existing checks.
3. Each adapter has an isolated source/build selection and a small regression
   fixture before shared callers move.
4. If an assumption is disproved, remove or disable the VA adapter and return
   callers to the unchanged baseline interface. Do not alter M01/M02 artifact
   identities to hide the failure.

An ADR supersedes this decision only when accepted source/document evidence
shows that the platform boundary, naming, or ownership model is wrong. A
later implementation result is not by itself permission to revise this ADR's
M03 evidence record.

## Consequences and risks

The independent boundary adds build and interface work, but makes VA claims
auditable and prevents NEC98 behavior from being silently reused. It may
temporarily duplicate low-level glue and requires a disciplined migration.
The largest risks are incomplete boot/firmware evidence, accidental shared
preprocessor sprawl, and treating Japanese/DBCS behavior as hardware proof.
Those risks remain explicit in the M04 blocker ledger.

M03R1 corrects only the milestone-routing consequence of this decision. A
source observation may inform several contracts or implementation stages, so
the census records separate, overlapping `contract_milestones` and
`implementation_milestones` arrays instead of one exclusive owner. M04 remains
specification-only, M06 remains the first PC-88VA code milestone, and M18 is
reserved for explicit SASI/SCSI/HDD evidence. This correction does not change
the independent-platform decision or resolve any of the twelve M04 blockers.
