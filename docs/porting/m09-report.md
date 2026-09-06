# M09 early console qualification report

Status: M09 PASS — PC-88VA EARLY CONSOLE OUTPUT AND DIAGNOSTIC MARKER COMPLETE.
HOST PASS applies to the native x64 public gates; VAEG PASS applies to the
private two-run console/loader qualification. DEFERRED HARDWARE VALIDATION.

## Source and publication

- Parent start: `cfdf5841857f9633a20bdb7b6edb0c1e35275969`.
- Parent branch: `topic/m09-pc88va-early-console-output-after-m08r1`.
- Qualified parent implementation: `b2e766d91403635bed3e2434cebe093109a5554b`,
  pushed and remotely reachable. The report publication revision adds only
  acceptance metadata, documentation and Make help to that qualified source.
- Initial parent implementation: `5ae8f0a9230365751d8a5cae06b135123505d466`.
- Native M09 workflows: [34003391977](https://github.com/nakatamaho/freedos-pc88va/actions/runs/34003391977)
  and [34003567110](https://github.com/nakatamaho/freedos-pc88va/actions/runs/34003567110),
  both success; each independently rebuilt the public artifacts twice.
- Child start: `105d49a72ec41afe07fc1e7b080bdbd1b3026ae2`.
- Child final: `ef46a7ad4b381cf7a301899bee00fec99f5e37a7`.
- Child branch: `topic/m09-pc88va-early-console-output`; pushed, fetched,
  and reachable before the parent gitlink was staged.
- VAEG: `7463f9501d84701f50f3243d5067b6a9dfd0c2e7`, detached and clean, unchanged;
  [accepted CI](https://github.com/nakatamaho/vaeg/actions/runs/33937050536).
- FreeCOM: `855281a3114b43ad4b8d9a320f2aca39be046bba`.
- Country: `23f189cca3420606eae8723884fa92ccd65eb307`.

The child replaces only the console putc stub. Seven unrelated fail-closed
stubs remain. M08 boot source and both public loader-stage artifacts remain
byte-identical. Kernel link input classification is three PC-88VA-owned
objects (startup, loader services, console), one temporary-stub object, and
the platform library. This remains a diagnostic carrier, not a common-core
FreeDOS runtime.

Child [PC-88VA QA](https://github.com/nakatamaho/fdkernel/actions/runs/34001962480)
passed with 190 tests at `4b6c96b3c293176edd7d10cc061ca0365d1c36b6`.
The final child's entire pc88va tree is identical to that tested tree.
[Final legacy Build](https://github.com/nakatamaho/fdkernel/actions/runs/34002178885)
passed at the final child. Earlier compatibility failures required a supported
runner, current artifact-upload action, and the upstream snapshot archive's
current extension. Those compatibility changes did not change PC-88VA code
or the canonical Open Watcom 1.9 toolchain.

## Mechanism, ABI and scope

The ADR is [m09-console-adr.md](m09-console-adr.md); the machine-readable ABI is
`components/fdkernel/pc88va/config/console-contract.json`.
The selected route is the preserved Text BIOS service documented independently
in public VAEG source. A one-byte NUL-terminated stack string uses the documented
service. No direct display/controller implementation is added.

The near register ABI takes AX, preserves other general/segment registers,
FLAGS under the pinned CPU's architectural POPF rules, and the caller's stack.
Unsupported characters or a missing vector return an error before firmware.
AX zero means firmware returned, not fabricated display success. C3-C9 requires
actual guest display mutations. The wrapper is non-reentrant and depends on
inherited firmware display, ROM-bank and interrupt-controller operational state.
Per-call bank/mask restoration, no PIC initialization, and no unexpected
disk/keyboard/clock/DMA activity were checked. This is not a zero-IO claim.

The public diagnostic is a CR-prefixed title, CR/LF, ninety decimal digits to
exercise wrapping, and CR/LF plus `CONSOLE OK` and CR/LF. Printable ASCII,
individual CR and LF, logical wrap, and inherited bottom-row scrolling are
qualified. Renderer raster width is not substituted for logical cursor width.
No input, Japanese/NLS, ANSI, M10 initialization, COMMAND.COM, full DOS boot,
or hardware validation is implemented or claimed.

## Two independent public builds

Build command inside two fresh network-disabled Linux/amd64 containers:

```sh
wmake -ms -h -f makefile.wc clean all
```

The public entrypoint is `tools/m09/compare_public_builds.sh`, with the final
child SHA and accepted COMMAND.COM/COUNTRY.SYS inputs. Sources are deterministic
git archives, not host bind-mounted component builds. Final Open Watcom 1.9
tools are selected by the immutable toolchain lock
`39c5b3052d71463235a26e8704ab54c1fedb51ee75bb4efb55e6229391a95162`.
SOURCE_DATE_EPOCH is the accepted build epoch. UPX is disabled.

Objects, source exports, artifacts and canonical JSON are byte-identical.
Raw link maps are retained but raw-map byte identity is not claimed: exactly
the creation-date and link-duration diagnostics are excluded by a strict
comparator; all other lines and canonical symbol evidence must match.

| Public artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| d88_media | 1331888 | `2db27fd5f9cdb24eea161d540a49603e73b96ebcdd8d64053c7dbce7d6d9f6f8` |
| extracted_command_com | 91143 | `fabe7744cc7c51c6f72519cc39d89bf77beaf908f994675a97a1e34c93549da1` |
| extracted_country_sys | 42614 | `04b2d2bc8df382090686f00e547d718d6706d22fb34c34dd77cd55083d5c34d5` |
| extracted_kernel_sys | 6034 | `a861eb4f12107f251f5cf25a260bec6661cf4d129ddacdb52a3a2c3a5e1f8fe9` |
| kernel_sys | 6034 | `a861eb4f12107f251f5cf25a260bec6661cf4d129ddacdb52a3a2c3a5e1f8fe9` |
| loader_stage1 | 1024 | `20efd8a66dde7feac3f48df4bd6e8c4564d70e80a5a8871a8293e735c1585f24` |
| loader_stage2 | 4304 | `db324cbdae11fd1e6085a7957ef171ccf9d6a9be6ea05f3df0eedf83d8f594f7` |
| raw_media | 1310720 | `064970c2be95b9b685b3b0390300c6365f02c47e2665026fdfcfa0ed0479ba4f` |

Kernel compile manifest:
`f609cfb10e86ad7b527c53328d05d3db192154369ab77c168a4bc8e3588a9aaa`.
Kernel interface:
`d794c1aa9968a8edbd8ea35d012d7996dac903cf057ff545b89ef78cb6c4d830`.
Symbol evidence:
`f97199ba8959e2fefedc5724799e005d2411c0b2e54094c25ecfa3b104b6e01d`.
Source archive:
`89da321a69e1d26e287ebc310f5c4eb87ec9db49214e5922c6760a6f819c4928`.

## Private guest qualification

Two fresh final-kernel runs have identical complete canonical causal
projections. Their complete M08 L0-L9 chain was independently audited in the
same executions: firmware handoff, FAT12 lookup, real sector returns and
bytes, MZ transformation, owned writes, entry registers and the carrier marker.
M07 established firmware acceptance; M08 established the loader handoff; M09
regresses both. Firmware acceptance is not incorrectly deferred.

| Boundary | Run 1 | Run 2 |
| --- | --- | --- |
| C0 accepted M08 L9 entry | observed | observed |
| C1 readiness before first putc | observed | observed |
| C2 first guest putc | observed | observed |
| C3 firmware request/return | observed | observed |
| C4 printable cell mutation | observed | observed |
| C5 cursor advancement | observed | observed |
| C6 CR/LF | observed | observed |
| C7 logical wrap | observed | observed |
| C8 exact guest diagnostic | observed | observed |
| C9 stable canonical projection | observed | observed |

A separate two-run project-authored control diagnostic from the same final
source qualifies individual CR/LF and bottom-row scrolling. It is not confused
with the final public diagnostic artifact. No proprietary boot code was copied.

All putc calls preserve the observed register/stack ABI. Writable FLAGS and
reserved-bit behavior follow the pinned public CPU POPF implementation;
no raw trace or canonical comparison field was normalized to hide a difference.
Actual firmware stack use stays inside the declared owned reserve. Owned
loader/kernel memory outside that stack is unchanged after entry. Inputs are
byte-identical before/after. This is emulator evidence, not hardware evidence.

Private launch/result/preservation records, complete projections, analyzer
source archive and cleanup record are retained in persistent ignored storage,
not temporary storage. Raw capture has not been deleted. Public records contain
only abstract qualification and public artifact identities. Promotion remains
`prohibited_pending_user_approval`.

## Public evidence identities

- `config/m09/console-contract.json`: `1bbd08cbedb4793624c7a438ed436508c759af0917063384bec244e886b6e348`.
- `schema/m09-artifact-manifest.schema.json`: `9534b9f088bb4dd3db8a6489e2f0d3c31f1fd026af16d586d41c21533873bba4`.
- `schema/m09-public-qualification.schema.json`: `3ea6d2c252884bc86b0a8b06093ec4087c8156bf900acb04217f427dc1ff3c8a`.
- `qa/golden/m09/manifest.json`: `19db1c0056b3153f9584359f7eb51293f99a4ca40871162d79d909c1df854497`.
- `config/m09/vaeg-qualification.json`: `fae44680924fcf63bb4ea79da612f2e96099342c5b165ea46f6363fceb239f71`.
- `manifests/m09-components.lock.json`: `9f6fc653d22655ff797d722237994f1251b93306d3fbc4f0a145baaec565fa58`.

The schema validates the actual manifest instance, not only its digest.
Qualification uses a closed schema and strict public projection. Parent M09
synthetic tests: 55 passed. Worktree/staged text privacy checks and the current
scaffold/license/M04 structural checks passed. M01R1-M08R2 native historical regressions passed, including the full M08
historical-regression job and its accepted M08 source/schema gate. Local M08
acceptance/media tests additionally passed 19 tests. Unrun hardware is not a success.

## Consumed M08 evidence

- `config/m08/loader-contract.json`: `c163ab5a1f1d1a3c3ae76e93bd24da7535393ea923f1d891cdbc1ab4460dae19`.
- `qa/golden/m08-artifact-manifest.json`: `2210a590a7d705f3936a9053e197d05eb94888254b708f4435a1e7c89d3ef5e0`.
- `schema/m08-artifact-manifest.schema.json`: `575086b668fb7f2439f17b63a33675978fef00861eb0b30f66a7b22d3279e7fe`.
- `qa/golden/m08-golden.json`: `bd611f5d6a0cb37c16114aec5b7382cb3bf7c18d340b762501d8bc2a574ad2a7`.
- `config/m08/vaeg-qualification.json`: `3ebbf58e18ea2acf0f92ba755cca99c3082b5ed419e6bfa51a5bd2d2fd8dbe47`.
- `manifests/m08-components.lock.json`: `c3e736596ce63ce006ba0363682259260f30a1792e59a04e3250ac9821544f07`.

These accepted records, their artifact content and M08 source are unchanged.
The accepted NEC98 regression kernel remains 83,774 bytes,
`3ebddb01abe5e39f16d27439836be283c57d454f012d3c990f01fa8a2b14101d`.

## Native CI and recoverable diagnostics

| Workflow | Qualified run | Conclusion |
| --- | --- | --- |
| Scaffold validation | [34003567169](https://github.com/nakatamaho/freedos-pc88va/actions/runs/34003567169) | success |
| M07R3 public FDD boot-path diagnosis record | [34003567118](https://github.com/nakatamaho/freedos-pc88va/actions/runs/34003567118) | success |
| M07R4 public boot-path reconstruction record | [34003567123](https://github.com/nakatamaho/freedos-pc88va/actions/runs/34003567123) | success |
| M07 firmware boot-acceptance completion | [34003567161](https://github.com/nakatamaho/freedos-pc88va/actions/runs/34003567161) | success |
| M09 PC-88VA early console public gate | [34003567110](https://github.com/nakatamaho/freedos-pc88va/actions/runs/34003567110) | success |
| M04 provisional boot and media contract | [34003391946](https://github.com/nakatamaho/freedos-pc88va/actions/runs/34003391946) | success |
| M04R1 root license policy | [34003391931](https://github.com/nakatamaho/freedos-pc88va/actions/runs/34003391931) | success |
| M07R5 firmware request-gate record | [34003391975](https://github.com/nakatamaho/freedos-pc88va/actions/runs/34003391975) | success |
| M07R6 subsystem FDC command-gate record | [34003391986](https://github.com/nakatamaho/freedos-pc88va/actions/runs/34003391986) | success |
| M03 port surface and integration ADR | [34003391943](https://github.com/nakatamaho/freedos-pc88va/actions/runs/34003391943) | success |
| M05 deterministic candidate media | [34003391920](https://github.com/nakatamaho/freedos-pc88va/actions/runs/34003391920) | success |
| M01 upstream baseline | [34003391980](https://github.com/nakatamaho/freedos-pc88va/actions/runs/34003391980) | success |
| M02 baseline artifact bundle | [34003391972](https://github.com/nakatamaho/freedos-pc88va/actions/runs/34003391972) | success |
| M06 PC-88VA kernel compile target | [34003391947](https://github.com/nakatamaho/freedos-pc88va/actions/runs/34003391947) | success |
| M08 PC-88VA loader public contract | [34003391987](https://github.com/nakatamaho/freedos-pc88va/actions/runs/34003391987) | success |
| M07 public boot-acceptance probe harness | [34003391978](https://github.com/nakatamaho/freedos-pc88va/actions/runs/34003391978) | success |

The native workflows above are the latest successful result for each required
gate on the qualified source lineage. The M07R3/M07R4/completion workflows
initially failed by running M06 against the M09 gitlink. Their recovery uses an
independent accepted M07 checkout; no validator or historical golden was relaxed.
The earlier failed runs remain historical failures, not relabeled successes.

The local ARM host-adapter historical build failed twice in the unchanged
FreeCOM host string utility with a segmentation fault. Both bounded diagnostics
were retained; neither local attempt is counted as passing. The same fixed
source/toolchain passed the native x64 M01/M02 and complete historical CI gates,
which are the canonical HOST PASS evidence. No pin or FreeCOM source was changed.
The owned historical scratch worktree was removed after retaining diagnostics;
it is reproducible from the accepted commit. No active M09 build container remains.

Existing user worktrees and reports, FreeCOM/Country sources and accepted M08
evidence remain unchanged. No generated binary/image/log/private evidence was
committed. The staged public blobs were also scanned against registered private
input tokens, without printing or exporting those tokens.

M09 PASS — PC-88VA EARLY CONSOLE OUTPUT AND DIAGNOSTIC MARKER COMPLETE.
M08 DISK, FAT12, MZ LOAD, AND KERNEL-ENTRY HANDOFF REGRESSION PASSES.
PRIVATE ROM, D88, MANUAL CONTENT, RAW TRACES, DISASSEMBLY, PATHS, IDENTITIES, AND DERIVED CONCRETE VALUES NOT DISTRIBUTED.
GUEST-ORIGINATED ASCII DIAGNOSTIC OUTPUT OBSERVED TWICE IN VAEG.
JAPANESE/NLS, CONSOLE INPUT, COMMAND.COM, FULL DOS RUNTIME, AND REAL HARDWARE NOT CLAIMED.
FREECOM AND COUNTRY SOURCES AND GITLINKS UNCHANGED.
HARDWARE NOT RUN.
M10 NOT STARTED.
