# M15 FreeDOS PC-88VA service-test boundary

Status: **LOCKED FREE-DOS PC-88VA PORT PROFILE V4** (2026-09-25)

## Target and version policy

M15 ports the selected FreeDOS kernel and FreeCOM to the existing PC-88VA
ASCII/8.3, FAT12, conventional-memory profile. The pinned FreeDOS source is
the DOS implementation being ported. MS-DOS references help identify common
interfaces and historical release context; they are not an expected-behavior
oracle. Preserve the selected FreeDOS behavior, including existing FreeDOS
bugs and differences from MS-DOS. Fix defects introduced by the VA adapter,
platform integration, or port-specific configuration. The running FreeDOS
build may report its actual version as 5.2; M15 does not rewrite it.

## Fixed count

No DOS manual publishes a total of 221 APIs. The number 221 is the count of the
locked dispatch-entry IDs in [`config/m15/api-inventory.json`](../../config/m15/api-inventory.json),
derived from pinned kernel dispatch/build guards, selected FreeCOM callers,
and the accepted M15 feature profile. A row is one QA boundary key, not a
separate behavioral contract. The source identities anchoring the inventory
are recorded as `source_baseline` in that file. The inventory is not a claim
that every row is a separately documented MS-DOS function or that M15
implements a Microsoft DOS release.

| Classification | Rows | M15 meaning |
| --- | ---: | --- |
| `REQUIRED` | 113 | Active FreeDOS services selected for the VA port profile; ordinary workflow and guest evidence are required |
| `OUT_OF_PROFILE` | 82 | Excluded providers/capabilities and unsupported M15 features; they do not count toward this port's tested surface |
| `UNDOCUMENTED_OBSERVATION` | 26 | Preserve candidate observations without claiming a separate historical compatibility contract |
| **Total inventory entries** | **221** | Locked dispatch-entry key set |

The entries break down by interrupt as follows: INT 20h: 1; INT 21h: 204;
INT 25h: 2; INT 26h: 2; INT 27h: 1; INT 28h: 1; INT 29h: 1; INT 2Fh: 8;
and the PSP:0005h CALL 5 entry: 1. There are 221 unique IDs and 221 unique
`(interrupt, function, dispatch-variant)` tuples. Their sorted-ID SHA-256 is
`6abf7ebcad90f74e5b3183a91e04184deb79ca638ec89471b26a020be364cabf`.
The 113 required IDs have sorted-ID SHA-256
`62b20a19635d2f8a93f01d8334a8324671fb2e15993bbcd2ede7b2885f483663`.
The digest input is UTF-8 IDs, lexically sorted, one ID followed by LF.
`tools/m15/verify_api_inventory_scope.py` verifies the locked IDs, counts,
classifications, reference keys, and digests. Separately, six specific
MS-DOS-reference questions are tracked as deferred review items; they are not
additional API rows or a second denominator.

The public inventory contains scope, source references, and test plans; it
does not publish per-case outcomes or concrete observations. The report may
state reviewed aggregate verification. Private run records remain outside Git.

## Historical V2 inventory correction

V2 corrects two V1 dispositions without changing the 221-entry key set. V1
counted the `CX=FFFFh` packet forms of INT 25h and INT 26h as required. The
MS-DOS 3.3 Programmer's Reference documents the ordinary sector-count form;
the MS-DOS 4.0 Programmer's Reference describes `CX=-1` as the new absolute
format with a parameter packet. V2 moved those existing rows to `OUT_OF_PROFILE` for the selected feature
profile, with candidate records retained as observations only; this choice
does not make the Microsoft version boundary normative for FreeDOS behavior.
This changes the required count
from 115 to 113 and the out-of-profile count from 80 to 82; no API ID was
added or removed.

One coverage unit is one locked dispatch-entry ID. A documented subfunction or
target-relevant register-dispatch branch can have its own ID. Input values,
packet fields, state transitions, and documented errors are cases within that
ID; they are not new entries. In particular, AH=44h IOCTL packet minors stay
under their existing IDs. A newly discovered active FreeDOS service can be
added only by a reviewed, versioned scope amendment that records its active
dispatch path. Do not add rows for input permutations or undocumented values.

## Sources and classification

| Source | Role |
| --- | --- |
| [Microsoft Press, *The MS-DOS Encyclopedia*, Section V](https://www.pcjs.org/documents/books/mspl13/msdos/encyclopedia/section5/) | Historical DOS API reference used to understand common interfaces; it does not impose exact MS-DOS behavior on the FreeDOS port. |
| [Microsoft Press, *The MS-DOS Encyclopedia*, Appendix A: MS-DOS Version 3.3](https://www.pcjs.org/documents/books/mspl13/msdos/encyclopedia/appendix-a/) and the [MS-DOS 3.3 Programmer's Reference](https://www.pcjs.org/documents/books/mspl13/msdos/dosref33/) | Primary evidence for 3.3 additions and NLS interfaces, including Functions 65h-68h. |
| [Microsoft, *MS-DOS Version 4.0 Programmer's Reference*](https://www.pcjs.org/documents/books/mspl13/msdos/dosref40/) | Historical reference for later DOS interfaces; not an acceptance oracle for the FreeDOS port. |
| [Microsoft, *MS-DOS Programmer's Reference*, version 5.0 (1991)](https://ftpmirror.your.org/pub/misc/bitsavers/pdf/microsoft/msdos_5/Microsoft_-_MS-DOS_Programmers_Reference_1991.pdf) | Historical reference for later DOS interfaces; not an acceptance oracle for the FreeDOS port. |
| [Microsoft MS-DOS 2.0 source, `SYSCALL.txt`](https://github.com/microsoft/MS-DOS/blob/main/v2.0/source/SYSCALL.txt) and [MS-DOS 4 source](https://github.com/microsoft/MS-DOS/tree/main/v4.0/src/DOS) | Original-source corroboration for specific calls; not a blanket replacement for published contracts. |
| Pinned FreeDOS dispatch, build guards, `docs/intfns.txt`, selected FreeCOM callers, and guest workflows | Establish the finite active entry set and the behavior this port must exercise; changes are checked against the selected upstream FreeDOS baseline and VA-specific integration. |

M15 feature exclusions include extended country/codepage services outside
the ASCII profile, handle-count and extended-open services outside tested
ordinary workflows, unsupported network/SHARE providers, the extended
absolute-I/O packet form, and UMB facilities unavailable in the VA memory
profile. Historical DOS version labels explain where an interface was
documented; release age alone does not define expected behavior. FreeDOS's
reported version is observed as returned and is not rewritten.

The scope lock is `M15-API-SCOPE-FREEDOS-VA-v4`. Changing the 221 IDs or any
disposition requires an explicit, versioned amendment and an updated verifier
pin. Ordinary review cannot silently expand the denominator.

Historical V30 references helped assemble the bounded service list; they do
not require V30-compatible results from FreeDOS. Expected port behavior comes
from the pinned FreeDOS baseline and accepted VA integration. Keep ordinary
workflow cases, implementation differences, and runtime observations separate
from MS-DOS comparison questions.

## Owner scope amendment V4 (2026-09-25)

The owner confirmed that this is a FreeDOS port to VA, not a FreeDOS fork or
an MS-DOS implementation. The fixed count remains 221 dispatch-entry IDs with
113 active FreeDOS services classified `REQUIRED`; this is a finite QA
boundary, not a count of behavioral contracts. Expected behavior follows the
pinned FreeDOS baseline and accepted VA integration. Do not change or reject
FreeDOS behavior solely because an MS-DOS reference differs. Six separate
MS-DOS reference questions remain deferred under the existing parent issues
and do not block the port. Their API rows remain active and their ordinary
observations remain distinct from the deferred comparisons:

| Inventory IDs | Parent issue | Deferred question |
| --- | ---: | --- |
| `21-1F`, `21-32` | #4 | V30 references for the two DPB-query interfaces |
| `21-3A` | #3 | Current-directory error value for remove-directory |
| `21-63-AL_00` | #6 | Historical applicability and empty-table representation |
| `25-CXnot_FFFF`, `26-CXnot_FFFF` | #5 | Failure-register detail for absolute logical-sector I/O |

For these rows, only the unresolved MS-DOS comparison is `DEFERRED_M15_PLUS` /
`NOT_RUN`; the API itself is not reclassified as out of profile and existing
FreeDOS runtime observations keep their own outcomes. V4 clarifies the port boundary without changing its 221 IDs or disposition counts.
