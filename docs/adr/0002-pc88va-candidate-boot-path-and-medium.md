# ADR 0002: Select a Provisional Medium and Firmware Disk Path

- Status: accepted as a provisional M04 decision
- Scope: M05-M08 contract planning; no implementation or boot claim

## Context

Current born-digital PC-88VA material provides a precise FDD operation and
geometry description, while the available startup manual is a medium-confidence
text export. It does not yet establish every firmware boot-acceptance detail,
common disk-call entry, or future VA kernel handoff. M04 therefore separates a
complete M05 filesystem candidate from the M07/M08 runtime blockers.

## Decision

1. Select the documented 2HD MFM geometry with 1024-byte sectors, eight
   sectors per track, two heads, and 80 cylinders as the first M05 candidate.
2. Define a project-owned FAT12 layout over that geometry. M05 may build it
   deterministically but may not call it bootable.
3. Prefer the documented firmware FDD operation family for the provisional
   M07/M08 disk path. Its known parameter and status fragments are preserved;
   the missing callable entry blocks M08.
4. Use trace-only observation as the M07 baseline. Visible console output is
   not an M07 acceptance requirement and remains M09 work.

## Alternatives

- An IBM-PC 512-byte FAT12 format is rejected: current VA evidence supports
  other sector sizes and does not establish IBM boot acceptance.
- Reusing or patching an NEC98 boot binary is rejected: those artifacts are
  baseline evidence only.
- Direct FDC/DMA/IRQ access is deferred: it expands the contract before the
  documented firmware candidate has been tested.
- Treating the text-export startup diagram as authoritative is rejected: its
  candidate values require M07 confirmation and one referenced image is absent.

## Consequences

M05 and M06 are ready with assumptions. M07 and M08 remain blocked on explicit
questions. Firmware is user-supplied for future emulator work and is never
distributed or generated. Public CI validates only the canonical derived
contract, arithmetic, citation graph, and privacy boundary.

If M07 contradicts the candidate geometry, entry/load assumption, or firmware
path, stop and supersede this ADR through M04R1. Do not patch bytes or silently
switch to a direct controller implementation.
