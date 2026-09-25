# M15 FreeDOS PC-88VA port and writable-session qualification

Status: **IN PROGRESS. M15 PASS is not claimed.**

## Scope

M15 ports the selected FreeDOS kernel and FreeCOM to the existing PC-88VA
profile. This is not a FreeDOS fork or an MS-DOS compatibility project.
Microsoft DOS references are context only. Preserve the selected FreeDOS
behavior, including existing FreeDOS errors or mismatches; fix VA-specific
adapter, ABI, memory-placement, and integration defects.

The locked V4 API boundary has 221 dispatch-entry QA keys: 113 active
services, 82 profile exclusions, and 26 undocumented observations. These are
not 221 independent behavior contracts. The key set is anchored to the pinned
kernel dispatch/build guards, selected FreeCOM callers, and M15 feature
profile. The selected FreeDOS source defines the DOS behavior being ported;
MS-DOS references are context only. Six separate MS-DOS comparison questions
remain deferred under parent issues #3-#6 and do not gate the port.

## Revisions

- START_SHA: ed7fb3c4fac2597a08c8ce9f76390e90d975c86c (M14 G14 parent baseline).
- fdkernel M14 baseline: ac16c8a7401526f99787e03babdb2f4223d48fc4.
- fdkernel M15 implementation commit: 3498c982584867367d2b917a79363f76143c514e.
- Parent M15 placement/capacity fix commit:
  aa23f9e27560f60a3f0e20b6a9fdd19354820a4b.
- Current QA-contract correction commit:
  e1a7b6c948e1c646aa78af56e209dacdc529010b; its exact-head M15 workflow
  passed as run 36129861539.
- M15 qualified implementation SHA: pending; full integrated M15 acceptance
  remains open.
- The report publication tip will be recorded in the post-push local handoff.
  The final downstream base remains unset until M15 qualification is complete.

## Current checkpoint

Common FreeDOS changes that were present in an earlier M15 candidate were
removed when they proved unrelated to the VA port. The source retains the
existing FreeDOS behavior for generic error classification, EXEC errors,
NLS fallback errors, character-device errors, JFT resizing, console EOF state,
and INT 2Fh carry handling. M15 does not correct these behaviors merely to
match an MS-DOS reference.

The remaining implementation changes are scoped to the PC-88VA build or
adapter: medium-model FAR call frames, relocated VA entry placement, the
native session clock, the VA console-key path, VA FAT12/media transfer
handling, and the compressed carrier layout needed by the existing memory
contract. The guest SYS utility and its ABI/volume tests are included in the
M15 worktree.

The V4 inventory verifier and five boundary tests pass for the locked
221-entry scope, pinned M14 source identities, and six separately deferred
questions. On implementation commit
`a47a5d35af92a49857e25287ffa492b26d3436b2`, Linux/amd64 verification passed:
all 307 kernel PC-88VA tests, all 16 parent M15 tests, all 29 parent acceptance
tests, all 20 M13 memory-placement tests, and the M13 adapter-selection
regression. That commit first added the startup build ID, but its `%s` formatter
path displayed an empty value in the guest. Commit
`3498c982584867367d2b917a79363f76143c514e` places the generated 40-character
ID directly in the adjacent startup string literals, avoiding the init
formatter's near-pointer segment limitation. A clean pinned Linux/amd64 build
confirmed the exact ID in the kernel banner bytes; the M13 carrier build and
linked-placement verifier also passed. The fdkernel native Build workflow
passed on that exact child head (run 36097330671).

The fdkernel topic branch now points to implementation commit
`3498c982584867367d2b917a79363f76143c514e` on the fork. Parent integration
commit `cd60877bba0c47a811ffb10b649e909454d8fe7a` updates the gitlink to that
exact child head. Parent M15 host workflow run 36098380721 passed on that exact
integration head, including the finite port boundary, parent M15 acceptance
and memory-placement regressions, and complete PC-88VA kernel component suite.
The backup-RAM placement correction is parent commit
`aa23f9e27560f60a3f0e20b6a9fdd19354820a4b`; native M15 workflow run
36124174958 passed on that exact head, including M15 acceptance, M13 placement,
and the full PC-88VA kernel component tests.
The report-only publication tip and its own workflow are recorded in the
post-push handoff.

The current SYS utility and 38 8086 fixture
COM files likewise rebuilt byte-identically in two isolated containers. These
are reproducible build results, not guest execution. The first private VA/VA2
candidate package mistakenly used the raw Watcom-linked MZ kernel instead of
the M13 zero-relocation carrier required by the loader. That package is
invalid for guest qualification. The current linked kernel has now been
transformed with the M13 carrier builder in two isolated Linux/amd64 runs; the
carrier outputs are byte-identical, and the actual linked-placement verifier
executed each bridge through the kernel entry with Unicorn 2.1.4. Corrected
private VA/VA2 candidates package that carrier and pass independent host FAT12
inspection. Their source boot records and contiguous loader extents remain
intact, current payloads match the builds, and stale result files are absent.
A separate disposable SYS target passed host inspection with its reserved
zero-filled loader area and sentinel files; it contains no system payload.
The user has now confirmed that current-source boots in both VA and VA2 display
the exact 40-character build ID and continue through InitDisk into FreeCom.
The user confirmed these were VAEG runs. This is **VAEG PASS** for the focused
startup-banner boot check only; it does not qualify the full M15 integration.
The public inventory contains no per-case private-run outcome or concrete
observation. Earlier parent revisions passed the branch-specific M15 host
workflow on exact heads `9263edfbefcda8b18ae5bb3e9815a3b6ff6b01fa` (run
36081226448) and `4a4c0d287ddaf1597b681982e5eaada7757f1a07` (run 36081372418).
Those runs predate the current fdkernel implementation and do not qualify its
parent gitlink. Earlier M01-M09 workflows also ran on the first M15 push and
failed their historical baseline gates: most rejected the newer exact gitlink;
the M08 historical rebuild hit an Ubuntu index-digest mismatch. Their push
filters now exclude M15.

The repeated low-memory startup failure was caused by treating the carrier's
build-time memory ceiling as the machine's runtime ceiling. The M13 carrier
builder now places split INIT and its initial stack above the bounded live
carrier/scratch ranges, records the minimum runtime capacity, and keeps the
DOS arena ceiling dynamic so the adapter can read the PC-88VA backup-RAM
selection. The low-memory case uses its matching in-place loader and carrier
profile as one unit. The linked-placement verifier now checks the unpacked
descriptor against the exact generated placement plan.

Focused verification of this changed low-memory profile is **HOST PASS** for
23/23 M13 placement tests, 16/16 parent M15 tests, linked-carrier execution,
and D88/FAT12 readback checks. The same matched loader and kernel candidate is
**VAEG PASS** in VA and VA2 at 256, 384, 512, and 640 KiB. All eight runs
reached FreeCom, completed ordinary DIR/TYPE/COM/MZ and file-write/readback
probes, and recorded the configured capacity in backup RAM. Host inspection
confirmed the kernel payload and existing disk files remained intact after
the guest writes. These results qualify all four supported capacities in both
modes on the matched profile.

The broader M13 test discovery ran 34 tests: 33 passed. Its remaining
historical public-contract test could not be qualified from the exported
Linux/amd64 tree because Git and checkout metadata are absent. That test also
binds to the earlier accepted M13 component pin, while this branch integrates
the later M15 component; the M13 acceptance record was left unchanged. The
focused placement suite and M15 suite are independent of that historical gate.

On 2026-09-25 the ordinary `SYSTEM`, `ALIAS` and `SYSMISC` recorder fixtures
were corrected to follow the selected FreeDOS source. `new_psp()` copies the
PSP memory-end field unchanged while refreshing the interrupt vectors and DOS
version word. The no-NLSFUNC country lookup follows FreeDOS's NLS MUX
`DE_INVLDFUNC` path when the requested package is absent, and AH=59h reports
the preserved FreeDOS error value. These were QA expectation and inventory
corrections; no kernel behavior changed, no API row was added, and no deferred
MS-DOS comparison was pulled into scope.

Focused ordinary QA then passed in VAEG VA and VA2 on the current
capacity-matched candidate. The three guest recorders produced complete
host-verified results with no assertion failures or stack imbalance. Normal
DIR/TYPE, COM/MZ execution, and file write/readback completed, and existing
guest files remained intact. This is a focused **VAEG PASS**, not a claim that
all 113 required services or all 221 inventory entries have been qualified.
On the exact QA-contract correction commit, M15 host workflow run
[36129861539](https://github.com/nakatamaho/freedos-pc88va/actions/runs/36129861539)
passed the finite inventory check, parent acceptance and memory-placement
regressions, and the full PC-88VA kernel component suite.

## Acceptance still open

The user passed the M15 SYS human gate on the earlier VA/VA2 candidates,
including transfer and persistence checks. The later banner correction changes
only startup text, so those SYS steps are not being repeated. The new
current-source banner check has now been owner-confirmed in both modes. This
focused startup-banner check is **VAEG PASS** in VA and VA2. The focused
placement checks are **VAEG PASS** in VA and VA2 at all four supported memory
capacities, and the focused ordinary recorder QA above is **VAEG PASS** in
both modes. These do not close full M15 acceptance: qualification of the
remaining mandatory workflow families and final M15 acceptance are still
open. The initially mispackaged candidate is not counted as qualification
evidence. Hardware validation remains **DEFERRED HARDWARE VALIDATION**.
