# M04 Provisional PC-88VA Boot and Media Contract

## Status and boundary

This is a provisional, static contract. It converts currently available
born-digital text into an auditable M05/M06 input and routes unresolved boot
facts to M07/M08. It is not an authoritative hardware specification and makes
no bootability, emulator, or hardware claim.

The primary target proposal is PC-88VA first. VA2 compatibility is a later,
explicit review; model-specific firmware observations are never merged. The
accepted M02 kernel remains a NEC98 build-reference payload. M06 must produce
the first compile-only `pc88va` kernel before M08 can execute a VA payload.

## Candidate medium for M05

The selected candidate is a documented 2HD MFM geometry with the following
normative values. Hardware-facing values cite the electronic FDD document;
filesystem values are project design choices.

| field | value | status | confidence | claim |
| --- | ---: | --- | --- | --- |
| bytes per sector | 1024 | confirmed | high | `TXT-FDD-2HD-GEOMETRY` |
| sectors per track | 8 | confirmed | high | `TXT-FDD-2HD-GEOMETRY` |
| heads | 2 | confirmed | high | `TXT-FDD-LOGICAL-TRACK` |
| cylinders | 80 | confirmed | high | `TXT-FDD-2HD-GEOMETRY` |
| physical sector-ID base | 1 | confirmed | high | `TXT-FDD-SECTOR-ID` |
| total sectors | 1280 | derived design | high | `DER-FAT12-CAPACITY` |
| total bytes | 1310720 | derived design | high | `DER-FAT12-CAPACITY` |

Firmware media support is documented, but firmware boot acceptance for this
specific layout is `unknown_reported`. M05 may build an internally consistent
image candidate; it may not call the image bootable.

## FAT12 design contract

The M05 candidate uses one reserved sector, two FATs, two sectors per FAT, 192
root entries, and one 1024-byte sector per cluster. The root consumes six
sectors; data begins at LBA 11 and contains 1269 sectors/clusters. A FAT needs
1907 bytes for the cluster entries, while each selected FAT occupies 2048
bytes. The resulting cluster count is within the FAT12 range.

Logical sectors are zero-based. Physical sector IDs are one-based. Track order
is cylinder-major and head-minor, matching the documented logical-track rule.
All image intervals are start-inclusive/end-exclusive and on-disk integers are
little-endian. `KERNEL.SYS` is the selected uppercase ASCII 8.3 role name in
the root directory. These are project choices, not firmware BPB facts.

## Firmware-to-IPL candidate

The available technical-manual export supports, at medium confidence, a
one-sector load and candidate execution at segment `3000H`, offset zero. The
corresponding physical address is 196608. It also describes a candidate stack
at segment `3000H`, offset `FFFEH`. For the selected medium, treating the one
sector as 1024 bytes is a `working_assumption` that M07 must test.

CPU mode, data segments, interrupt state, boot-drive identity, complete usable
memory ranges, signature/checksum, and firmware acceptance rules remain
`unknown_reported`. The proposed prologue records incoming state, disables
interrupts, clears direction, and establishes project-owned segments before
use. M07 must prove that this sequence is safe; M04 creates no prologue code.

## Disk access candidate

The preferred provisional path is the documented firmware FDD operation
family. Current text establishes read parameters (count, logical drive/track,
starting sector, format/size, segmented buffer) and carry/AH result semantics.
It does not establish the common callable vector or entry address. Therefore:

- M07 may investigate and identify the callable entry;
- M08 remains blocked until the entry and transfer behavior are concrete;
- direct FDC/DMA/IRQ implementation is deferred to M12/M14 unless the
  firmware candidate fails, in which case M04R1 must define the minimum direct
  path first.

## Kernel and diagnostics

The accepted 83774-byte kernel identity is used only for capacity and role
provenance. It is not a VA kernel. M06 supplies a future compile-only VA
payload. Destination, entry point, memory intervals, and handoff registers are
unknown and block M08.

M07's preferred observation strategy is trace-only. The text BIOS provides a
documented character-output candidate, but the early callable entry is not yet
fixed. Trace-only success is not console output; full console belongs to M09.

## Firmware and private boundary

Future emulator validation is expected to use user-supplied PC-88VA firmware.
Firmware bytes are neither distributed nor generated. Public CI checks only
the derived contract. A bounded local firmware/disk fallback was performed,
but no exact private value was promoted; its inability to establish a complete
public ABI leaves M07 and M08 blocked.

The canonical contract is
`config/contracts/m04-provisional-pc88va-boot-media.json`. Its validator
recomputes media, FAT12, addressing, and payload-fit invariants using integer
arithmetic.
