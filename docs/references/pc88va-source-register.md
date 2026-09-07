# PC-88VA Public Source Register

This public register contains sanitized provenance metadata and source
identifiers only. It contains no private document text, page image, firmware
bytes, extracted table, download link, local hash, or absolute local path.
M03 registered candidates without reviewing their contents. M04 accepts
born-digital text with section and decoded-line locators as provisional
evidence; missing page images limit only claims that depend on those images.

## Tracked public sources

| source ID | category | title/description | commit or identity | document number | edition/revision/date | page | size | SHA-256 | provenance/owner | redistribution | review status |
| --- | --- | --- | --- | --- | --- | --- | ---: | --- | --- | --- | --- |
| `SRC-FDKERNEL-6523ACDB` | component-source | pinned fdkernel source tree | `6523acdb87f4665e6068ea331859885267242005` | N/A | N/A | N/A | N/A | N/A | parent submodule at accepted gitlink | public | reviewed-source-identity |
| `SRC-FREECOM-855281A3` | component-source | pinned FreeCOM source tree | `855281a3114b43ad4b8d9a320f2aca39be046bba` | N/A | N/A | N/A | N/A | N/A | parent submodule at accepted gitlink | public | reviewed-source-identity |
| `SRC-COUNTRY-23F189CC` | component-source | pinned Country source tree | `23f189cca3420606eae8723884fa92ccd65eb307` | N/A | N/A | N/A | N/A | N/A | parent submodule at accepted gitlink | public | reviewed-source-identity |
| `SRC-PARENT-M01R1` | parent-contract | accepted M01R1 locks, contract, and golden | parent baseline and tracked manifests | N/A | N/A | N/A | N/A | N/A | parent repository history | public | reviewed-baseline-identity |
| `SRC-PARENT-M02R1` | parent-contract | accepted M02R1 artifact contract and golden | parent baseline and tracked manifests | N/A | N/A | N/A | N/A | N/A | parent repository history | public | reviewed-baseline-identity |

## Locally reviewed electronic sources

Distribution basenames are public locators. Exact local paths, byte sizes, and
hashes remain in ignored local evidence. The electronic sources are not CI
inputs, and CI does not claim to inspect their contents.

| source ID | category | neutral description | distribution basename | identity/revision | locator model | redistribution | review status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `PRV-TEKUMANI-DOC` | electronic-document | Distribution provenance and revision header | `TEKUMANI.DOC` | self-identified electronic edition | CP932 section plus decoded lines | restricted | reviewed-for-M04 |
| `PRV-TEKUMANI-MAIN-INDEX` | electronic-document | Distribution-wide topic index | `INDEX.TXT` | same distribution | CP932 section plus decoded lines | restricted | reviewed-for-M04-routing |
| `PRV-TEKUMANI-BIOS-INDEX` | electronic-document | BIOS chapter routing index | `600INDEX.TXT` | same distribution | CP932 section plus decoded lines | restricted | reviewed-for-M04 |
| `PRV-VA-FDD` | electronic-document | PC-88VA FDD BIOS interface and parameter tables | `601FDD.TXT` | same distribution | Shift_JIS-2004-compatible decoding, section plus decoded lines | restricted | reviewed-for-M04 |
| `PRV-VA-KEYB` | electronic-document | PC-88VA keyboard BIOS interface | `603KEYB.TXT` | same distribution | Shift_JIS-2004-compatible decoding, section plus decoded lines | restricted | reviewed-for-deferral-only |
| `PRV-VA-TEXT` | electronic-document | PC-88VA text BIOS interface | `604TEXT.TXT` | same distribution | Shift_JIS-2004-compatible decoding, section plus decoded lines | restricted | reviewed-for-M04 |
| `PRV-VA-MISC` | electronic-document | PC-88VA miscellaneous BIOS interface | `619ETC.TXT` | same distribution | Shift_JIS-2004-compatible decoding, section plus decoded lines | restricted | reviewed-for-context-only |
| `PRV-VA-MANUAL-EXPORT` | text-export | PC-88VA technical-manual Markdown export | `PC88VA_テクニカルマニュアル_BNN.md` | transcription/export; original scan not registered | UTF-8 section plus decoded lines | restricted | reviewed-provisional-medium-confidence |
| `PRV-TSP-EXPORT` | text-export | Display-processor Markdown export | `uPD72022.md` | transcription/export | UTF-8 section plus decoded lines | restricted | contextual-not-used-for-normative-M04-value |
| `PRV-VA-MANUAL` | source-family alias | M03 PC-88VA manual candidate retained for blocker-ledger continuity | specific members above | umbrella identifier only | use a specific member ID for every M04 claim | restricted | retained-not-a-claim-locator |

## Local-only comparative and binary categories

These identifiers reveal no filename, hash, address, sector, string, or
extracted value. They record only that a bounded local fallback was attempted.
Exact observations require separate user approval before any public use.

| source ID | category | neutral description | redistribution | review status |
| --- | --- | --- | --- | --- |
| `PRV-M04-ROM-LOCAL` | private-firmware-observation | model-separated bounded static fallback | user-owned | reviewed-locally-no-public-value-promoted |
| `PRV-M04-D88-LOCAL` | private-disk-observation | bounded container and sector-structure fallback | restricted | reviewed-locally-no-public-value-promoted |
| `PRV-NEC98-BIOS` | private-document | NEC98 BIOS comparison candidate | unknown | metadata-only-not-used-for-VA-fact |
| `PRV-NEC98-FDD` | private-document | NEC98 floppy comparison candidate | unknown | metadata-only-not-used-for-VA-fact |
| `PRV-NEC98-DMA` | private-document | NEC98 DMA comparison candidate | unknown | metadata-only-not-used-for-VA-fact |

## Register counts

| category | count | redistribution statuses |
| --- | ---: | --- |
| component-source | 3 | public: 3 |
| parent-contract | 2 | public: 2 |
| electronic-document | 7 | restricted: 7 |
| text-export | 2 | restricted: 2 |
| source-family alias | 1 | restricted: 1 |
| private-firmware-observation | 1 | user-owned: 1 |
| private-disk-observation | 1 | restricted: 1 |
| private-document comparison | 3 | unknown: 3 |
| total | 20 | public metadata only: 20 |

The private sources are not CI inputs. M04 public claims cite the source ID,
distribution basename, encoding, section, and decoded-line range. PC-98
documentation cannot support a PC-88VA fact. Private binary observations stay
redacted and cannot become public constants without a separate decision.
