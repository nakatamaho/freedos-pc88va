# M10 minimal machine-services initialization report

Current status: M10 IN PROGRESS. M10 HANDOFF NOT READY.

The owner authorized fresh private prerequisite reconstruction for this same
M10 goal. The accepted M09 public handoff remains valid. The successful fresh
pair is current prerequisite evidence, not a reconstruction of missing
historical M09 evidence.

## Fixed starting identities

- START_SHA: `6b29d4f9b2b732ced9bc25a9b33b453877cbd7f0`.
- Prior M09 qualified implementation:
  `b2e766d91403635bed3e2434cebe093109a5554b`.
- Starting fdkernel: `ef46a7ad4b381cf7a301899bee00fec99f5e37a7`.
- Unchanged FreeCOM: `855281a3114b43ad4b8d9a320f2aca39be046bba`.
- Unchanged Country: `23f189cca3420606eae8723884fa92ccd65eb307`.
- Unchanged qualification VAEG:
  `7463f9501d84701f50f3243d5067b6a9dfd0c2e7`.

The exact M09 digests and publication-only allowlist are preserved in
`config/m10/m09-handoff.json`. The reusable checker validated the actual M09
schema instances, content identities, clean component checkout, exact remote
tip, ancestry and bounded publication diff. The public M09 verifier passed.
Live CI was checked at attempt 1: parent run 34003567110 succeeded at the M09
qualified implementation; parent run 34003878132 succeeded at the exact M09
publication tip; VAEG run 33937050536 succeeded at the fixed VAEG commit with
all eleven required jobs successful.

## Current evidence and implementation

M10 FRESH PREREQUISITE PASS: two clean production-memory VAEG runs preserve
their inputs and executable identity, and have byte-identical complete traces,
display captures and canonical projections. Their actual evidence instances
were schema-validated. M08 load/handoff, M09 guest-originated console output,
register/architectural FLAGS/stack preservation and intentional guest quiescence
were checked. Canonical evidence remains in persistent ignored local storage.

The five M10 services have a qualified runtime implementation in the independent child
topic branch. The ADR documents the selected conservative arena map, read-only
interrupt-state adoption, bounded observed-VRTC-edge clock, single-shot
transaction and separate nonreturning fatal path. M08 loader source and M09
console implementation are unchanged. Platform probe, input and NLS remain
fail-closed; no new DOS runtime is introduced.

Current child implementation is `54c067af9764ace07459b0c2f5df4f70294d0c50`.
Its 205 ROM-free child tests passed in a network-disabled Linux/amd64 QA
container. The reusable acceptance checker passed 29 focused tests. M10
parent media, scope, actual-contract and private-entry tests passed (21 tests).
Child publication
preceded the parent gitlink update: exact fork-branch reachability was checked.
Child CI runs 34019124058 and 34019124154, attempt 1, succeeded at that exact
child SHA. Earlier child commits are superseded development history.

Two clean network-disabled Open Watcom 1.9 builds of the current child commit
matched in objects, artifacts and canonical manifests. The strict existing
map comparator alone excludes the allowed map timing lines. Both accepted
loader stages and the FreeCOM/Country payloads remained byte-identical.
Kernel growth initially moved the bootstrap extent under sequential allocation;
M10 now reserves the accepted loader extent and independently validates the
remaining FAT chains. Historical allocator and loader code were not changed.

Exploration exposed a stack-interval assumption and an unnecessary clock wait.
Both were corrected and retested within M10. Failed observations and rejected
ownership hypotheses remain retained and are not accepted evidence. No disk
activity exception was introduced to obtain a pass.

Two formal clean main runs established I0-I9; two separate fatal controls
established F0-F4. Complete raw evidence, guest display, launch/input/result
records and canonical projections were byte-identical within each pair.
Production-memory tracing, executable identity, input preservation, register,
segment, architectural FLAGS and stack preservation, memory ownership, IVT,
PIC masks, memory banks, observed clock progress, exact post-init guest display,
disk ownership and intentional nonreturning guest halt were checked. M08 L0-L9
and M09 console behavior were independently rechecked in the immutable traces.
Actual private schemas and instances passed; a final closure audit also passed
58 missing/unknown-field and digest rejection controls. This is VAEG evidence,
not hardware evidence, and does not recreate lost historical M09 evidence.

The closed public contract binds actual service, component, main-artifact,
fatal-control and abstract qualification instances. The shared verifier checks
schemas, closed references, source/object/library and artifact identities,
component cleanliness, isolation metadata and positive/negative tests. Public
CI consumes only ROM-free artifacts and abstract qualification assertions.

## Outstanding mandatory gates

Local M01R1-M09 historical regressions have passed at their exact accepted
checkouts, including fresh M09 two-build golden comparison. The shared local
acceptance rerun passed, as did registered-private-identity privacy checks of
parent/child text, staged blobs and commit objects. Parent publication,
native/final-tip M10 CI and the final closure audit remain pending. No unrun
gate is counted as successful.

QUALIFIED_IMPLEMENTATION_SHA is not established. PUBLICATION_TIP_SHA and
DOWNSTREAM_BASE_SHA will be recorded only in the post-push handoff after exact
final-tip CI, remote equality, ancestry and the bounded diff are verified.

Private ROMs, D88s, manuals, raw traces, concrete observations, input identities
and private paths are not distributed. Console input, Japanese/NLS, ANSI,
disk writes, HDD, COMMAND.COM execution, full DOS and M11 are not started.
HARDWARE NOT RUN. DEFERRED HARDWARE VALIDATION.

M10 IN PROGRESS.
M10 HANDOFF NOT READY.
