# M04 Evidence Matrix

Born-digital TXT/DOC claims use distribution basename, encoding, section, and
decoded-line range. The Markdown manual is explicitly a text export and is not
promoted above medium confidence without corroboration. Exact local hashes and
all private binary details remain outside Git.

| claim ID | type / status | source locator or dependencies | contract use |
| --- | --- | --- | --- |
| `DEC-DISK-PATH` | design_choice | `TXT-FDD-READ-ABI`, `TXT-FDD-STATUS-ABI` | preferred disk path |
| `DEC-EARLY-TRACE` | design_choice | `TXT-TEXT-CHAR-OUTPUT` | M07 trace-only strategy |
| `DEC-FAT12-LAYOUT` | design_choice | `DER-FAT12-CAPACITY`, geometry claim | FAT12 fields |
| `DEC-KERNEL-ROLE` | design_choice | `SRC-M02-KERNEL-IDENTITY` | filename and future VA role |
| `DEC-MEDIUM-SELECTION` | design_choice | media and geometry claims | selected candidate |
| `DEFER-KEYBOARD` | deferred | project readiness boundary | M11/M17 |
| `DEFER-TIMER` | deferred | project readiness boundary | M10 |
| `DER-FAT12-CAPACITY` | derived_value | layout and geometry claims | media/FAT invariants |
| `MD-IPL-STARTUP` | text_export_fact / supported | `PC88VA_テクニカルマニュアル_BNN.md`, UTF-8, system startup, lines 3389-3448 | load/entry/stack candidate |
| `PRV-D88-FALLBACK` | d88_observation / private_observation | redacted local fallback | private-local readiness only |
| `PRV-ROM-FALLBACK` | rom_observation / private_observation | redacted local fallback | private-local readiness only |
| `SRC-M02-KERNEL-IDENTITY` | source_fact / confirmed | accepted M02 bundle manifest, kernel roles | capacity and provenance |
| `TXT-BIOS-INDEX` | electronic_document_fact / confirmed | `600INDEX.TXT`, CP932, BIOS index, lines 1-23 | source routing |
| `TXT-DOC-PROVENANCE` | electronic_document_fact / confirmed | `TEKUMANI.DOC`, CP932, distribution header, lines 4-7 | source provenance |
| `TXT-FDD-2HD-GEOMETRY` | electronic_document_fact / confirmed | `601FDD.TXT`, Shift_JIS-2004-compatible, parameter tables, lines 946-1009 | candidate geometry |
| `TXT-FDD-LOGICAL-TRACK` | electronic_document_fact / confirmed | `601FDD.TXT`, Shift_JIS-2004-compatible, logical track, lines 50-57 | head/track order |
| `TXT-FDD-MEDIA-SUPPORT` | electronic_document_fact / confirmed | `601FDD.TXT`, Shift_JIS-2004-compatible, overview, lines 1-10 | candidate inventory |
| `TXT-FDD-READ-ABI` | electronic_document_fact / confirmed | `601FDD.TXT`, Shift_JIS-2004-compatible, read data, lines 230-269 | known firmware parameter fragment |
| `TXT-FDD-SECTOR-ID` | electronic_document_fact / confirmed | `601FDD.TXT`, Shift_JIS-2004-compatible, traversal, lines 59-61 | physical ID base |
| `TXT-FDD-SECTOR-SIZE` | electronic_document_fact / confirmed | `601FDD.TXT`, Shift_JIS-2004-compatible, format/size, lines 63-80 | sector size |
| `TXT-FDD-STATUS-ABI` | electronic_document_fact / confirmed | `601FDD.TXT`, Shift_JIS-2004-compatible, status, lines 99-187 | result semantics |
| `TXT-TEXT-CHAR-OUTPUT` | electronic_document_fact / confirmed | `604TEXT.TXT`, Shift_JIS-2004-compatible, output, lines 148-227 | diagnostic alternative |
| `UNKNOWN-BOOT-ACCEPTANCE` | unknown_reported | startup export and FDD corpus search | blocks M07 |
| `UNKNOWN-DISK-ENTRY` | unknown_reported | FDD overview/read operation search | blocks M08 |
| `UNKNOWN-KERNEL-HANDOFF` | unknown_reported | startup export and accepted payload contract | blocks M08 |

The machine-readable matrix is `config/contracts/m04-evidence-matrix.json`.
Every contract field references one or more IDs above. Missing image references
are limitations, not a global failure. One missing image reference occurs in
the startup range and prevents diagram-specific acceptance rules from being
treated as confirmed; it does not invalidate the independently readable text.
