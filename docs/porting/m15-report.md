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
The original 8086 fixture set also rebuilt as 38 byte-identical COM files in
two isolated Linux/amd64 containers. This is reproducible fixture-build
evidence, not guest execution. The public inventory contains no per-case
private-run outcome or concrete observation. Parent publication and CI are
pending.

## Acceptance still open

Earlier user-confirmed SYS human acceptance applies to its then-tested
candidate; it does not qualify the current source revision. Current-source
VA/VA2 guest qualification remains required for ordinary FreeCOM and batch
workflows, writable media, the guest SYS transfer, independent boot of the
transferred disk, and persistence after restart. Parent publication/CI and the
exact tested-image handoff also remain open.

Current-source VAEG validation: **NOT RUN**.
Hardware validation: **DEFERRED HARDWARE VALIDATION**.
