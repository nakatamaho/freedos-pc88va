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

The five M10 services have a first implementation in the independent child
topic branch. The ADR documents the selected conservative arena map, read-only
interrupt-state adoption, bounded observed-VRTC-edge clock, single-shot
transaction and separate nonreturning fatal path. M08 loader source and M09
console implementation are unchanged. Platform probe, input and NLS remain
fail-closed; no new DOS runtime is introduced.

Initial child implementation `e2c995e36c768cd58d688ff73fbaa329660621eb` is
development history, not QUALIFIED_IMPLEMENTATION_SHA. Its 202 ROM-free child
tests passed in a network-disabled Linux/amd64 QA container. The reusable
acceptance checker passed 26 focused tests. The new fixed-loader-extent media
allocator passed eight positive/negative tests.

Two clean network-disabled Open Watcom 1.9 builds of that development commit
matched in objects, artifacts and canonical manifests. The strict existing
map comparator alone excludes the allowed map timing lines. Both accepted
loader stages and the FreeCOM/Country payloads remained byte-identical.
Kernel growth initially moved the bootstrap extent under sequential allocation;
M10 now reserves the accepted loader extent and independently validates the
remaining FAT chains. Historical allocator and loader code were not changed.

The first exploratory M10 guest run preserved inputs, completed M08/M09 and
correctly failed its initialization entry guard. The guard had confused the
stack's segment base with the linker's actual intra-paragraph stack start.
That failure is retained. A correction deriving the stack offset from the
public MZ stack contract and live caller state is under regression test.
This exploratory stop is not M10 initialization acceptance.

## Outstanding mandatory gates

The corrected child needs clean rebuild and private qualification. Two formal
I0-I9 main runs and two separate F0-F4 fatal controls have not passed. M10's
closed public contract, evidence schemas, qualified golden and qualification
record are not final. Full M01R1-M09 parent regressions, final privacy/cleanup,
child-first publication, parent gitlink update and native/final-tip M10 CI
remain pending. No unrun gate is counted as successful.

QUALIFIED_IMPLEMENTATION_SHA is not established. PUBLICATION_TIP_SHA and
DOWNSTREAM_BASE_SHA will be recorded only in the post-push handoff after exact
final-tip CI, remote equality, ancestry and the bounded diff are verified.

Private ROMs, D88s, manuals, raw traces, concrete observations, input identities
and private paths are not distributed. Console input, Japanese/NLS, ANSI,
disk writes, HDD, COMMAND.COM execution, full DOS and M11 are not started.
HARDWARE NOT RUN. DEFERRED HARDWARE VALIDATION.

M10 IN PROGRESS.
M10 HANDOFF NOT READY.
