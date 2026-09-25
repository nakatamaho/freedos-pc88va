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
- M15 qualified implementation SHA: pending; current-source VA/VA2 banner
  confirmation and parent CI on the updated gitlink remain open.
- Publication tip and downstream base: recorded in the post-push handoff and
  kept distinct from the start and implementation identities.

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
passed on that exact child head (run 36097330671). Parent CI for the updated
gitlink is pending.

The fdkernel topic branch now points to implementation commit
`3498c982584867367d2b917a79363f76143c514e` on the fork. The prior parent
gitlink publication at integration commit
`b4e5c10394182d8447fd31d5e4d395ec021c53a9` and parent M15 workflow run
36095708531 qualify the preceding source, not this banner correction. The
updated parent gitlink and its exact workflow result will be recorded after
publication.

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
The corrected candidates still require guest boot, transfer, and persistence
validation.
The public inventory contains no per-case private-run outcome or concrete
observation. Earlier parent revisions passed the branch-specific M15 host
workflow on exact heads `9263edfbefcda8b18ae5bb3e9815a3b6ff6b01fa` (run
36081226448) and `4a4c0d287ddaf1597b681982e5eaada7757f1a07` (run 36081372418).
Those runs predate the current fdkernel implementation and do not qualify its
parent gitlink. Earlier M01-M09 workflows also ran on the first M15 push and
failed their historical baseline gates: most rejected the newer exact gitlink;
the M08 historical rebuild hit an Ubuntu index-digest mismatch. Their push
filters now exclude M15.

## Acceptance still open

The user passed the M15 SYS human gate on the earlier VA/VA2 candidates,
including transfer and persistence checks. The later banner correction changes
only startup text, so those SYS steps are not being repeated. The new
current-source VA/VA2 candidates are prepared in private, Git-excluded storage;
their focused remaining human check is to boot each mode and confirm the full
40-character build ID appears below `PC88VA kernel`. This does not close other
open M15 acceptance work. Current-source VAEG validation and human acceptance
remain open.

Current-source VAEG validation of the corrected candidates: **NOT RUN**. The
initially mispackaged candidate is not counted as qualification evidence.
Hardware validation: **DEFERRED HARDWARE VALIDATION**.
