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
- fdkernel M15 implementation commit: 1545db0201f78588df6a524fc2c07de04533c3e3.
- M15 qualified implementation SHA: pending; current source has not passed
  final source-bound qualification.
- Publication tip and downstream base: pending and will remain distinct
  from the start and implementation identities.

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
questions. The parent acceptance suite passes (29 tests). On the current source
commit, Linux/amd64 verification passed: all 307 kernel PC-88VA tests, all 16
parent M15 tests, 20 M13 memory-placement tests, and the M13 adapter-selection
regression. The fdkernel topic push and native CI are verified at implementation
commit `1545db0201f78588df6a524fc2c07de04533c3e3` (run 36078361707, success).
The current kernel and FreeCOM source also rebuilt byte-identically in two
isolated Linux/amd64 containers. The current SYS utility and 38 8086 fixture
COM files likewise rebuilt byte-identically in two isolated containers. These
are reproducible build results, not guest execution. Private VA and VA2
candidate disks were assembled from those outputs and passed independent host
FAT12 inspection: the source boot records and contiguous loader extents remain
intact, current payloads match the builds, and stale result files are absent.
A separate disposable SYS target passed host inspection with its reserved
zero-filled loader area and sentinel files; it contains no system payload.
These host checks do not qualify boot, transfer, or persistence in a guest.
The public inventory contains no per-case private-run outcome or concrete
observation. Parent commits
`526fd67b8fea64c7259741c06b37f6f55de3e969` and
`9263edfbefcda8b18ae5bb3e9815a3b6ff6b01fa` and the child implementation are
pushed and remote-equal. The new branch-specific M15 host workflow passed on
exact head `9263edfbefcda8b18ae5bb3e9815a3b6ff6b01fa` (run 36081226448).
The report-only descendant `4a4c0d287ddaf1597b681982e5eaada7757f1a07` also
passed the same workflow (run 36081372418).
Earlier M01-M09 workflows also ran on the first M15 push and failed their
historical baseline gates: most rejected the newer exact gitlink; the M08
historical rebuild hit an Ubuntu index-digest mismatch. Their push filters now
exclude M15.

## Acceptance still open

Earlier user-confirmed SYS human acceptance applies to its then-tested
candidate; it does not qualify the current source revision. Current-source
VA/VA2 guest qualification remains required for ordinary FreeCOM and batch
workflows, writable media, the guest SYS transfer, independent boot of the
transferred disk, and persistence after restart. The exact current-source
candidate media are prepared in private, Git-excluded storage for this gate.
Parent publication/CI and the exact tested-image handoff also remain open.

Current-source VAEG validation: **NOT RUN**.
Hardware validation: **DEFERRED HARDWARE VALIDATION**.
