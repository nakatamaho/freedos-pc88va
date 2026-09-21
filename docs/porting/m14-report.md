# M14 floppy writes and media changes

Status: **M14 runtime qualified; final parent CI and handoff pending.**

The common FreeDOS kernel now writes FAT12 media through the resident VA block
path. Changed or unknown media invalidates old handles, dirty buffers and pending
requests; an explicit new pathname operation is required. The filesystem remains
in the common kernel. The [write/media contract](m14-write-media-contract.md)
records request units, ownership, ABI, completion, verification and retry policy.

## Source and prerequisite identities

- START_SHA: `e324fa6c7132c7daaa7b936c0902563f47a3e528`.
- Starting fdkernel: `b4af4c6c55979ae22843f1b1ec33d5512e4fdc38`.
- Current fdkernel: `ac16c8a7401526f99787e03babdb2f4223d48fc4`.
- Current FreeCOM: `9cf57b28abf1d98fab7655fb811375a2aa16c6d9`.
- COUNTRY: `23f189cca3420606eae8723884fa92ccd65eb307`.

The predecessor's FreeCOM gitlink was
`2296365f5a00e3bea7cb5b931030a175a6598f2f`. The initial M14 parent commit
`14d4b66ab83ce3b3fbe8f543756c7f0b98bc9f35` records the reachable FreeCOM MEM
alias repair and task instructions. That repair is distinct from the predecessor
pin; historical locks and acceptance records have not been rewritten.

The owner supplied the accepted M13 control for private prerequisite checks.
Its bytes remain immutable. The historical qualified M13 revision is
`7ddca85c1bf3ee74fea396a27a3a75d91cb78a21`; its CI run `35138781354`, attempt 1,
succeeded. This historical result does not qualify the later starting tip:
that tip's M13 CI run `35515388304` failed. The new M14 source bindings, fresh
private checks and final M14 CI must close the current integration separately.
No retroactive M13 publication success is claimed.

## Implementation and verification

The child adds bounded writes, truthful completion/error translation,
read-and-compare verification and conservative media lifetimes. Focused repairs
preserve firmware read status, avoid advancing a copied destination twice,
exclude an IBM diskette-table assumption, and use the actual VA FAR frame for
critical-error handling. Common rejection paths now clear completed transfer
counts and reject the first index outside the command table.

The parent carrier encoder minimizes the byte cost of the existing LZSS format;
the decoder and history format are unchanged. Its smaller in-place prefix and
reserved FAR-return frame avoid overlap with live relocation data. The active
placement tests retain explicit memory ownership and reject aliases and wraps.
The ordinary delivered profile must match its tested explicit launch/layout.
Selectable capacities are not all qualified by a placement-only test.

Completed focused evidence includes:

- All 263 child tests in the pinned Linux/amd64 environment, including emitted
  ABI execution, common-C failure/retry policies and unchanged non-VA behavior.
- Exact-head child CI `35645181467` (Build) and `35645181236` (structure),
  attempt 1, successful at the current child. Child remote reachability checked.
- Two clean deterministic source exports/builds of the real common kernel,
  five original DOS probes and five exclusive block probes. Executable pairs
  are byte-identical; timestamp-bearing raw maps are retained separately.
- Exclusive pre-DOS production-object probes for boundaries, verification,
  invalid requests, protection, absence, partial completion and later recovery.
- Current-candidate DOS create/write/read/seek/extend/rename/delete/subdirectory
  operations, root-full/data-full failure and reuse, all FAT copies, neighboring
  FAT12 entries, a FAT-sector-straddling entry and independent corruption checks.
- Clean exchanges, open dirty handles, in-flight removal/direct replacement,
  explicit Retry, protected replacement media and subsequent valid operations.
  Replacement media stays unchanged until an explicit new valid operation.
- Ordinary no-helper boot/write/read and fresh-boot persistence, plus full-file
  fresh-boot reread and continued TYPE/COM/MZ/prompt operation. Frontend Backspace
  automation is identified separately from ordinary boot/write execution.
- Explicit native 512-KiB allocation/fill/verify/free followed by DOS I/O.
  The resident transfer buffer remains kernel-owned and bounded. Other selectable
  memory capacities are not M14 runtime qualifications.
- Immutable M08-M13 public regressions run from the accepted M12/M13 checkouts.
  Historical read-only write-rejection tests are not changed into writable tests.

## Acceptance operations and remaining gates

`tools/m14/verify_m14.py` is the shared local/native-CI verifier. It validates
actual schema instances, source/archive/gitlink identities, dependency closure,
the real build pair and the complete active test suite. Negative tests reject
missing/unknown fields, malformed hashes, digest drift, incomplete or duplicate
references, source topology errors and stale CI head/attempt/job claims.
Private qualification is a separate optional local input; public CI never runs
private guest media or derives its own VAEG result from a public test pass.

Legacy milestone workflows are excluded only from the M14 topic push because
their current-tree assertions pin older component revisions. The M14 workflow
runs the active acceptance suite and immutable historical regressions. Historical
workflows, locks, goldens and reports retain their original meaning.

Private/source closure has passed actual instance and artifact checks, including
negative dependency cases. The final source-bound FreeCOM has been rebuilt
twice and the affected normal/write/exchange/editing matrix rerun with its
exact bytes. The complete current parent/child suite passes all 308 tests.

Scoped parent commit/push, parent qualification CI, metadata-only publication
CI and exact tested image delivery remain pending.
The [acceptance matrix](m14-acceptance.md) separates passed runtime rows from pending closure. QUALIFIED_IMPLEMENTATION_SHA, PUBLICATION_TIP_SHA and
DOWNSTREAM_BASE_SHA have not been assigned. A tracked report cannot name its
own future commit; the final publication identities belong in the post-push
local handoff.

Manual physical-keyboard validation and actual hardware are **NOT RUN**;
hardware remains **DEFERRED HARDWARE VALIDATION**. No M15 or later storage work
has started. Generated images, binaries, logs, private source material and
concrete private identities remain in persistent Git-excluded storage.
