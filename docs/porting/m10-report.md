# M10 minimal machine-services initialization report

Status: implementation qualified; final publication handoff pending.

HOST PASS and VAEG PASS are independently established below. Final publication
CI and remote equality are not claimed by this pre-publication report.
HARDWARE NOT RUN. DEFERRED HARDWARE VALIDATION.

## Identity and publication boundary

- START_SHA / M09 publication: `6b29d4f9b2b732ced9bc25a9b33b453877cbd7f0`.
- Prior M09 qualified implementation: `b2e766d91403635bed3e2434cebe093109a5554b`.
- QUALIFIED_IMPLEMENTATION_SHA: `eaadb757c4c3e2a4a7d405c0e250e96c1f4c222c`.
- Parent: `nakatamaho/freedos-pc88va`, branch
  `topic/m10-pc88va-machine-services-init`.
- Starting fdkernel: `ef46a7ad4b381cf7a301899bee00fec99f5e37a7`.
- Qualified fdkernel: `54c067af9764ace07459b0c2f5df4f70294d0c50`,
  fork `nakatamaho/fdkernel`, branch `topic/m10-pc88va-machine-services-init`.
- Unchanged FreeCOM: `855281a3114b43ad4b8d9a320f2aca39be046bba`,
  fork branch `deterministic-build-timestamp`.
- Unchanged Country: `23f189cca3420606eae8723884fa92ccd65eb307`,
  repository branch `master`.
- Unchanged VAEG: `7463f9501d84701f50f3243d5067b6a9dfd0c2e7`.
  An independent detached checkout was used; no observer/source change or
  VAEG topic branch was needed. The separate user checkout was not changed.

Child-first push and exact fork-branch reachability were verified before the
parent gitlink update. Final component worktrees and gitlinks are exact and
clean; kernel/FreeCOM origin/upstream provenance is preserved. The qualified
parent is pushed, equals its remote branch tip at qualification and descends
from START_SHA.

PUBLICATION_TIP_SHA and DOWNSTREAM_BASE_SHA will be recorded only in the
post-push Goal handoff. They are not assumed to equal the implementation SHA.
The publication allowlist permits only this report and the machine contract's
`status` / `parent_ci` fields. Source, build, schema, golden, qualification,
verifier, workflow and gitlinks must remain unchanged. Final-tip CI must invoke
the same acceptance verifier. No self-referential report commit is planned.

## CI evidence

Each row below is attempt 1, conclusion `success`, with exact head checked.

| Repository | Run | Exact head SHA | Required job or workflow |
| --- | --- | --- | --- |
| nakatamaho/freedos-pc88va | 34020956366 | `eaadb757c4c3e2a4a7d405c0e250e96c1f4c222c` | `m10-machine-services.yml`: `public-machine-services`, `historical-regression` |
| nakatamaho/fdkernel | 34019124058 | `54c067af9764ace07459b0c2f5df4f70294d0c50` | `pc88va-compile.yml`: `structure` |
| nakatamaho/fdkernel | 34019124154 | `54c067af9764ace07459b0c2f5df4f70294d0c50` | `ci-build.yml`: `build` |
| nakatamaho/freedos-pc88va | 34003567110 | `b2e766d91403635bed3e2434cebe093109a5554b` | M09 qualified `public-console` |
| nakatamaho/freedos-pc88va | 34003878132 | `6b29d4f9b2b732ced9bc25a9b33b453877cbd7f0` | M09 final-tip `public-console` |
| nakatamaho/vaeg | 33937050536 | `7463f9501d84701f50f3243d5067b6a9dfd0c2e7` | `build.yml`, all eleven required jobs |

M10 native x64 run 34020956366 reproduces the main/fatal artifacts and binds
the main manifest below. Required job conclusions were verified through the
Actions API. Public CI does not execute private qualification.

Failed M10 runs 34020702274 and 34020843863 are superseded, not accepted.
The early license job also exposed an old JSON Schema dependency. Dependency
provisioning and fresh M01R1 object-diagnostic generation were fixed and retested
within M10. No evidence pins were changed to conceal those harness defects.

## Consumed M09 evidence

The reusable checker validated exact remote equality, direct publication
ancestry, bounded M09 diff, clean components, valid schemas, actual instances,
artifact bindings and live CI. The public M09 verifier passed. Accepted
historical evidence was not rewritten.

| Record | SHA-256 |
| --- | --- |
| Console contract | `1bbd08cbedb4793624c7a438ed436508c759af0917063384bec244e886b6e348` |
| Artifact schema | `9534b9f088bb4dd3db8a6489e2f0d3c31f1fd026af16d586d41c21533873bba4` |
| Qualification schema | `3ea6d2c252884bc86b0a8b06093ec4087c8156bf900acb04217f427dc1ff3c8a` |
| Artifact manifest | `19db1c0056b3153f9584359f7eb51293f99a4ca40871162d79d909c1df854497` |
| Public qualification | `fae44680924fcf63bb4ea79da612f2e96099342c5b165ea46f6363fceb239f71` |
| Component lock | `9f6fc653d22655ff797d722237994f1251b93306d3fbc4f0a145baaec565fa58` |
| Toolchain lock | `39c5b3052d71463235a26e8704ab54c1fedb51ee75bb4efb55e6229391a95162` |

## Fresh prerequisite and selected services

M10 FRESH PREREQUISITE PASS. The owner authorized a new canonical private
launch contract from preserved inputs and fixed identities. Two clean
production-memory runs preserved executable/input identity and matched complete
traces, display and projections byte-for-byte. Actual schemas and instances
validated. This is current prerequisite evidence, not reconstruction of lost
historical M09 evidence; M09's public acceptance remains valid.

Exactly the five assigned M06 stubs were replaced. The detailed public-source
locators, ABI, ownership and rejected alternatives are in
`m10-machine-services-adr.md` and `config/m10/services.json`. Machine-specific
constants have pinned public VAEG/accepted-contract provenance; private values
and PC-98 precedent were not promoted into evidence.

| Service | Mechanism and failure boundary |
| --- | --- |
| `pc88va_machine_init` | Bounded single-shot transaction: entry/ownership, memory, read-only interrupt adoption, clock origin and observed edge, unchanged M09 output, final preservation check, readiness commit. Failure invalidates public readiness/records; repeated attempts reject. |
| `pc88va_memory_query` | Three half-open intervals reserve everything except a linked 256-byte owned arena. Bounds, overflow and stack/arena ownership are checked. No RAM-size guess or destructive probe. |
| `pc88va_interrupts_init` | Validate/snapshot IVT and inherited PIC masks with IF clear, then compare before readiness. No vector clearing, mask/mode/EOI programming or controller reinitialization. |
| `pc88va_clock_read` | Valid modeled read-only VRTC status establishes origin zero; subsequent calls require a bounded low-to-high edge and increment modulo 2^32. IF-clear/non-reentrant atomicity; failure leaves records unchanged. No fabricated progress, elapsed/calendar time or host clock. |
| `pc88va_fatal_stop_request` | Separate control only: no diagnostic/reason printing, CLI and nonreturning HLT loop. Guest quiescence must be observed under an external bound; timeout/host markers alone reject. |

The near Watcom register ABI uses AX for argument/result, zero success and
minus-one failure. Other general registers, segments, architectural FLAGS and
caller stack are preserved. IF/DF, record ownership and single-shot/reentrancy
rules are explicit. Fatal stop is the nonreturning exception. Input/NLS and
platform probe remain unavailable; no common-core DOS boot was introduced.

## Runtime qualification

VAEG PASS: two clean main runs established I0-I9; two separate clean fatal
controls established F0-F4. Each pair matched launch, preservation, result,
analysis, complete raw trace, display and canonical projection bytes. Private
main/fatal carriers matched both public build pairs exactly. Production-memory
tracing was used, with test-flat-memory absent.

M07 firmware acceptance, M08 L0-L9, M09 C0-C9 and exact M09 display behavior
remained valid. The checks cover memory partition/ownership, complete IVT,
PIC masks, memory banks, ordered clock progress, registers/segments/architectural
FLAGS/stack and exact guest-originated `M10 INIT OK` display. No unexpected
disk, keyboard, NLS, DMA, timer rearm or controller reset was accepted. Fatal
controls initialized first, then demonstrated repeated guest HLT with IF clear,
no return, no observer timeout and no emulator crash.

Exploratory stack-interval and unnecessary-clock-wait defects were corrected.
Failed observations and rejected hypotheses remain retained. No disk-activity
exception or projection normalization was introduced. Actual private schemas
and instances passed; closure added 58 missing/unknown-field and digest
rejection controls, frozen-reference rechecks, ordered loader-boundary pairs
and current original/copy input-preservation checks.

## Deterministic artifacts and evidence graph

HOST PASS: two independent network-disabled Linux/amd64 Open Watcom 1.9 builds
matched all objects, libraries, carrier, media, extracted payloads and canonical
JSON. Isolation records establish no bind mounts and the same amd64 image.
Only the existing strict comparator excludes permitted raw-map timing lines.
Two independently generated fatal controls differ by exactly one public selector
byte per carrier/raw/D88 artifact. The accepted loader extent is reserved and
all FAT payloads are independently extracted and checked.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| Loader stage 1 | 1024 | `20efd8a66dde7feac3f48df4bd6e8c4564d70e80a5a8871a8293e735c1585f24` |
| Loader stage 2 | 4304 | `db324cbdae11fd1e6085a7957ef171ccf9d6a9be6ea05f3df0eedf83d8f594f7` |
| Main KERNEL.SYS (including extracted payload) | 8378 | `b6a1941fa3950aa0cd3cfc3cc6acf7b4f4efffb3897773a262b084b52e11e77d` |
| Main raw medium | 1310720 | `730fb9caa3d17be5dec244060f1d5ce599c106026ab7ffb10969072e74a7aa78` |
| Main D88 medium | 1331888 | `bb64d80cd0519e3fbb21d51ae4c1ae3617f73bf8789f78881723239313cd057e` |
| Fatal KERNEL.SYS | 8378 | `fe6fc4301f94b55527d008d25399a66ccf3f60c47f8d54e7770df10534b577d6` |
| Fatal raw medium | 1310720 | `050f5ca7b686a095ee88bcd13c2cf2a63ad5d0adac2e358fcaa0913fa84ccb79` |
| Fatal D88 medium | 1331888 | `62637c0e2e0944bc115781912fe032587d8bbc8ff96829d73d2eb2c9013cd480` |
| Unchanged COMMAND.COM payload | 91143 | `fabe7744cc7c51c6f72519cc39d89bf77beaf908f994675a97a1e34c93549da1` |
| Unchanged COUNTRY.SYS payload | 42614 | `04b2d2bc8df382090686f00e547d718d6706d22fb34c34dd77cd55083d5c34d5` |

| Final public record | SHA-256 |
| --- | --- |
| `config/m10/machine-contract.json` | `d42904dcaa62d6ab3b7cedff0ae43b66daf227cbcb9739d34177527e894d6670` |
| `config/m10/services.json` | `509ef2f587cc47cef3caadd0ddd9c5969555dccc7617f65fce1a15a4244be2b2` |
| `config/m10/vaeg-qualification.json` | `174162bc3595a9f790de29d65155286fe9a03e77fc7e41b65fc13d63b225b211` |
| `qa/golden/m10/manifest.json` | `5ec22d0dd8bb700e2ecf46a0b5d166ae479717d3fe99d35b16e217a3e9e21046` |
| `qa/golden/m10/fatal-controls.json` | `ca05d76aa89fd8eac3f5c862b3fb9d26c6160f281295587f5d2cf6064f807aa1` |
| `schema/m10-artifact-manifest.schema.json` | `5eb5ac7c26e2fe9699a4eb73d2a7ce1f011328ad316202e35c4872f1b6888bf6` |
| `schema/m10-build-records.schema.json` | `b22c7c7aceeff6e2861f06e3dc5d80ccb32d12d58a9422ec058ea96d8ab772f4` |
| `schema/m10-components.schema.json` | `fdcb4f61ebd1fd3b875788f3ac943fb11dec1d05fe37685203a7e560b9477d38` |
| `schema/m10-fatal-controls.schema.json` | `6f67badd96eca3ab1803834093df5ea9146e04f046ac15685dc56b33d12fbd46` |
| `schema/m10-machine-contract.schema.json` | `914d28530f4250d7558f27b703b7c981e58095dd3108263740b825e58ee6ac07` |
| `schema/m10-public-qualification.schema.json` | `72d4ae08c969baf2615fcf6d6bd53eb873a1be25b490dfb1e2db4e4f25fbdb48` |
| `schema/m10-services.schema.json` | `f862f67cd352080ef5e95a0cd8cbbf18dda4381a56b84ac2bd8fe84c96e510c5` |
| `manifests/m10-components.lock.json` | `b6b6df02d03218a7f65e1a2a523e40e20f10eed7b9ea635266954a4f1cb8b9d0` |

The qualified pre-publication machine contract digest was
`2af3107ba5344b9224aad6295247eb2efdef8940c3b98986e2d8cb61d492ac5b`;
only acceptance status/CI metadata changes it to the final digest above.

## Tests, regressions and privacy

The shared `make m10-accept` passed locally and in native CI: 205 child
instruction/contract tests, 29 reusable acceptance-checker tests, 22 M10 parent
tests, actual schema/instance and build-record validation, source/object/library/
artifact bindings, component cleanliness, live prerequisite CI identity and
privacy checks. Negative coverage includes missing/unknown fields, invalid
schemas, external references, malformed hashes, digest/reference drift, stale
CI head, remote mismatch, placeholders and forbidden public payloads. Missing
private prerequisites and private execution in public CI fail closed.

M01R1-M09 regressions passed at exact accepted checkouts: timestamp/UTC/path
reproducibility controls, M01/M02 artifacts, M03 census, M04/license, M05 media,
M06 including NEC98 baseline, M07 through completion, M08 loader and M09 console.
A fresh independent M09 build pair matched its unchanged golden. Historical
blocked/diagnostic records retain their historical meanings.

Registered private input/observation identities were audited against parent/
child text, staged blobs and new commit objects. CI inputs contain only public
source and ROM-free generated artifacts. No private logs or artifacts were
selected for publication. Canonical private launch, preservation, result,
projection, schema and closure records remain in persistent ignored storage,
never solely temporary storage. Failed exploration is separate from acceptance.

## Cleanup and limitations

No active M10 containers remain. Two clean disposable verification checkouts
were removed and can be recreated from exact commits. Retained task checkouts
hold bound build/regression/private evidence and are intentional evidence stores.
User worktrees and accepted M07-M09 evidence were preserved. The isolated host
adapter remains running: its optional stop was denied at the host-signal
boundary, although its guest Docker service stopped. No permission expansion
or change to the user's default adapter was attempted.

Final publication-tip CI, exact remote equality, ancestry and the bounded diff
remain to be checked after this report is pushed. Until then, handoff is not
ready. The final handoff will record the exact downstream base without adding
a report-only commit to insert this report's own SHA.

Console input, Japanese/NLS, ANSI, disk write, HDD, COMMAND.COM execution,
full DOS runtime and M11 were not started. HARDWARE NOT RUN; DEFERRED HARDWARE
VALIDATION. The conservative arena map is not a physical RAM-size claim, and
the clock counts observed edges rather than elapsed/calendar time. The next
milestone may start only from the final verified DOWNSTREAM_BASE_SHA.

M10 IMPLEMENTATION QUALIFIED — FINAL PUBLICATION HANDOFF PENDING.
M10 HANDOFF NOT YET READY.
