# M14 floppy-write and media-change acceptance record

This record is maintained during the M14 implementation work. It is the public,
private-value-free checklist for the current topic branch. Concrete D88 paths,
ROM identities, traces, and derived runtime values remain in persistent
Git-excluded storage.

## Starting bindings

| Item | Identity |
| --- | --- |
| Parent starting branch | `topic/m13-pc88va-readonly-freecom` |
| Parent starting tip | `e324fa6c7132c7daaa7b936c0902563f47a3e528` |
| fdkernel starting pin | `b4af4c6c55979ae22843f1b1ec33d5512e4fdc38` |
| FreeCOM predecessor pin | `2296365f5a00e3bea7cb5b931030a175a6598f2f` |
| Reachable FreeCOM repair | `9cf57b28abf1d98fab7655fb811375a2aa16c6d9` |
| COUNTRY starting pin | `23f189cca3420606eae8723884fa92ccd65eb307` |
| VA block contract | 1024-byte sectors, 8 sectors/track, 2 heads, 160 tracks |
| Existing VA write boundary | `FL_WRITE`, `FL_VERIFY`, and related mutation entries reject before firmware |

## Gate status

`NOT RUN` means no evidence has been collected yet; it is not a pass.
`PARTIAL` means focused checks exist but the required row is not qualified.

| Case ID | Contract under test | Expected evidence | Status |
| --- | --- | --- | --- |
| M14-BASE | M13 normal control | Real FreeCOM boot, edited input, DIR/TYPE/COM/MZ, prompt return | VAEG PASS; final publication closure pending |
| M14-MEM | Resident ownership and ABI | Write request/bounce bounds, stack/segment preservation, accepted arena unchanged | VAEG PASS; final publication closure pending |
| M14-BLOCK | Raw block writes | First/last/track-head boundary writes alter only intended sectors | VAEG PASS; final publication closure pending |
| M14-VERIFY | Write verification | Real verify or documented unsupported result; no false success | VAEG PASS; final publication closure pending |
| M14-REJECT | Invalid requests | Range/count/unit overflow rejected without media or guard mutation | VAEG PASS; final publication closure pending |
| M14-PROTECT | Protection/no media | Guest error and unchanged protected/absent media | VAEG PASS; final publication closure pending |
| M14-ERROR | Lower-layer failure | Bounded retry, status/count, partial completion and shell recovery | VAEG PASS; final publication closure pending |
| M14-CHANGE | Media identity/exchange | A/B revalidation and no stale A reads/writes on B | VAEG PASS; final publication closure pending |
| M14-FILES | DOS file workflows | Create/write/close/reopen/read/seek/extend/rename/delete/subdirectory | VAEG PASS; final publication closure pending |
| M14-FAT | FAT12 structure | Neighboring even/odd entries, FAT copies, chains, no cross-links | VAEG PASS; final publication closure pending |
| M14-FULL | Capacity failures | Root-full and data-full status/count/metadata and recovery | VAEG PASS; final publication closure pending |
| M14-PERSIST | Persistence | Close/flush, saved image, fresh boot and guest reread | VAEG PASS; final publication closure pending |
| M14-SHELL | FreeCOM continuity | Prompt and commands remain usable after writes/errors/exchange | VAEG PASS; final publication closure pending |
| M14-REGRESS | Earlier contracts | M08–M13 relevant host and integration tests | PARTIAL; parent CI and exact delivery pending |
| M14-NORMAL | Ordinary candidate | No private interposer, state patch, or diagnostic dependency | VAEG PASS; final publication closure pending |
| M14-CLOSE | Evidence closure | Source pins, records, CI, and delivered bytes agree | PARTIAL; parent CI and exact delivery pending |

## Scope boundary

M14 reuses the common FreeDOS FAT12 and DOS block/cache layers. The PC-88VA
adapter is responsible for VA CHS transfer, status, bounded retries, and media
identity; it does not implement a second filesystem. Formatting, HDD/SASI/MO,
LFN/Japanese work, and broad INT 21h conformance remain outside this milestone.

Hardware remains `DEFERRED HARDWARE VALIDATION` until an actual physical result
is supplied. A normal VAEG run is reported separately as `VAEG PASS` only after
the applicable gates pass.
