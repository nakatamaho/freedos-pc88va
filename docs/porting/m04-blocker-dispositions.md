# M04 Blocker Dispositions

M04 classifies every M03 blocker without manufacturing missing values.

| M03 question | disposition | consequence |
| --- | --- | --- |
| `M04-BOOT-IPL-LOAD` | supported | candidate segment/offset and one-sector extent require M07 confirmation |
| `M04-BOOT-ENTRY-STATE` | working_assumption | partial stack/entry candidate; remaining state is recorded before normalization in M07 |
| `M04-BOOT-SECTOR-FORMAT` | unknown_reported | signature and acceptance rules block M07 |
| `M04-FLOPPY-GEOMETRY` | confirmed | selected geometry enables M05 arithmetic; boot acceptance remains separate |
| `M04-BPB-MEDIA` | design_choice | M05 uses project FAT12 layout; firmware BPB visibility remains an M07 question |
| `M04-DISK-SERVICE` | working_assumption | firmware operation family preferred; missing call entry blocks M08 |
| `M04-FDC-DMA-IRQ` | deferred_m12 | direct path belongs to M12/M14 unless firmware access fails |
| `M04-KERNEL-LOAD` | unknown_reported | destination, entry, and handoff block M08 |
| `M04-EARLY-CONSOLE` | design_choice | trace-only candidate for M07; full console deferred to M09 |
| `M04-BOOT-INTERRUPTS` | unknown_reported | M07 records entry flags and validates normalization |
| `M04-BOOT-TIMER` | deferred_m10 | not required by M05-M08 contract formation |
| `M04-KEYBOARD-ENCODING` | deferred_m11 | general input belongs to M11; Japanese behavior belongs to M17 |

Private fallback produced no publishable complete acceptance, disk-entry, or
handoff contract. Public fields remain redacted, and private-local M07/M08
readiness remains blocked.
