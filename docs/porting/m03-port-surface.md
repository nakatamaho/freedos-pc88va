# M03 Port Surface Census

Status: `OBSERVATION` census complete; PC-88VA implementation is not started.

The M03 scanner reads only tracked component blobs at the pinned gitlinks. It
uses Git and the Python standard library, preserves legacy bytes while
matching text, and emits canonical UTF-8 JSON. It does not inspect generated
build output, binaries, archives, ignored files, private documents, or a
compiler-generated call graph. Path names, comments, and tokens are leads for
review, not hardware specifications.

The scanner identity is `m03-port-surface-scanner` version 1. Its ruleset
digest is `6d362672a193896e68531d2701f2645006d294d146cda408727981cefddddc52`.
Two clean runs produced byte-identical JSON: 14,455 entries, with output
SHA-256 `d075493a14b5913f968d30c284e625fc5e38f37300505fa557d948eabdc99f45`.
The committed golden is a reviewed copy of that canonical output; generated
run directories remain ignored under `qa/results/m03/`.

## Pinned source

| component | commit | tracked tree | tracked files |
| --- | --- | ---: | ---: |
| fdkernel | `6523acdb87f4665e6068ea331859885267242005` | `e26f73d60fa9361195295dd5c8f7f9a0b01b9e95` | 278 |
| freecom | `855281a3114b43ad4b8d9a320f2aca39be046bba` | `1d4beba3ff354331336c078dc91e41aa83a7017d` | 819 |
| country | `23f189cca3420606eae8723884fa92ccd65eb307` | `fa4d5d0d70b574d83086f59aea28b1d32e116901` | 9 |

The parent baseline is M02R1 commit
`0babe66669b0e0eeb543cedaf427a3ff56eb5d83`. The census records full parent
gitlinks, component commits, tree identities, rule descriptors, and all
closed-vocabulary fields so that a later review can reproduce the scan.

## Observed distribution

The largest surfaces are build selection, memory/startup, disk/block I/O,
execution/runtime, and device initialization. This distribution is a source
tree signal, not a ranking of implementation work: a single source line may
match several deliberately independent rules.

| component | entries |
| --- | ---: |
| fdkernel | 7,331 |
| freecom | 6,666 |
| country | 458 |
| total | 14,455 |

All required surfaces occur in the result. The machine-readable counts by
surface, mechanism, disposition, and target milestone are in the golden JSON.
The scanner currently has no `memory_mapped_io` or `exclude` hits; zero is a
measured result, not evidence that those concerns do not exist.

## Boundary conclusion

The pinned tree has explicit IBM-PC and NEC98 build/platform surfaces, with
shared DOS abstractions alongside hardware-specific assembly, interrupt,
firmware, disk, console, and startup code. M03 therefore records PC-88VA as a
separate proposed platform boundary named `pc88va`. No `pc88va` directory,
build target, component, boot image, binary, or emulator implementation is
created by this milestone.

The integration decision and source citations are in
`docs/adr/0001-pc88va-independent-platform.md` and
`docs/porting/m03-integration-matrix.md`. The unresolved boot and media facts
are deliberately routed to M04 in `docs/porting/m03-open-questions.md`.

## Evidence limits

The code census establishes where the pinned source refers to platform
selection and low-level services. It does not establish PC-88VA register
maps, IPL entry state, disk geometry, BIOS services, interrupt ownership,
keyboard protocol, or hardware timing. NEC98 and PC-98 material is used only
to explain the existing baseline and cannot resolve a VA blocker.
