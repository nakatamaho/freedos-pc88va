# M04 Open Questions

## Boot acceptance and entry state

- Unknown: required signature/checksum/magic and complete firmware acceptance
  rule. Sources searched: the technical-manual text export and Tekumani FDD
  and miscellaneous texts. Impact: M07 blocked. Next evidence: a complete
  primary boot description or a bounded VAEG acceptance matrix.
- Unknown: CPU mode, DS/ES, interrupt state, boot-drive identity, and complete
  usable memory ranges. Sources searched: startup and miscellaneous sections.
  Impact: M07 prologue finalization blocked. Next evidence: record incoming
  state before a controlled normalization sequence.

The startup export contains one missing image reference in the reviewed range.
Only diagram-dependent acceptance detail is affected; readable text remains
usable as supported provisional evidence.

## Disk access

- Unknown: common callable vector or entry for the documented FDD operation
  family. Sources searched: FDD overview, operation, and index texts. Impact:
  M08 blocked. Next evidence: authoritative common-call documentation or an
  M07 entry-identification experiment.
- Deferred: direct FDC/DMA/IRQ ownership. It is unnecessary for the selected
  firmware candidate and moves to M12/M14. If firmware access fails, M04R1
  must define the direct path before implementation.

## Kernel handoff

- Unknown: future VA kernel destination, entry point, memory intervals, and
  handoff registers. Sources searched: startup export and accepted M02 payload
  contract. Impact: M08 blocked. Next evidence: M06 compile/link startup
  contract followed by an M08 loader memory plan.

## Deferred runtime work

- Timer/clock runtime is deferred to M10.
- Keyboard and general console input are deferred to M11.
- Kernel floppy read is deferred to M12; write/media change to M14.
- Japanese output is deferred to M16; Japanese input and filenames to M17.

The bounded private fallback did not establish a complete public contract for
the unresolved boot-critical items. No exact private value is recorded here.
