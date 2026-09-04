# M07 firmware boot-acceptance completion report

## Final status

`M07 PASS — VAEG FIRMWARE BOOT ACCEPTANCE CONTRACT COMPLETE`

This milestone establishes a reproducible PC-88VA firmware-to-diagnostic-probe
handoff in VAEG. It does not establish that the compile-only M06 kernel boots,
that DOS services work, or that real hardware behaves identically.

## Repository state

- FreeDOS branch: `topic/m07-boot-acceptance-completion`
- FreeDOS start: `98ac0c8d0ab9720c35d76ccfb57c6aa23d4933a2`
- FreeDOS final: the commit containing this report
- VAEG branch: `topic/freedos-m07-boot-acceptance-completion`
- VAEG start: `e1fddddc98c6534a1dc1d4938bd6fad2b246ebb3`
- VAEG final: `d68b1ab7392cedc7080927c24a8aa4b35c6756cb`
- VAEG full CI: run `33887608335`, success
- FreeDOS native CI: the M07 completion workflow must be successful on the
  report-containing commit before this status is accepted

Component source and gitlinks remain unchanged:

| Component | Gitlink |
| --- | --- |
| fdkernel | `69ccdd8699895722fc537d647ec490685532bdc4` |
| FreeCOM | `855281a3114b43ad4b8d9a320f2aca39be046bba` |
| Country | `23f189cca3420606eae8723884fa92ccd65eb307` |

## Boundary result

One consumed request is correlated through all request and response
boundaries:

| Path | Reached boundaries |
| --- | --- |
| Consumer | G0 request accepted through G9 response eligible |
| FDC and transfer | H0 response produced through H9 firmware record accepted |
| Handoff | first transferred-region fetch and project marker, repeated twice |

No final boundary is absent. The architectural entry checkpoint and canonical
private projections agree across the accepted clean run pairs.

## Root causes and changes

Two generic VAEG behavior defects blocked the accepted path:

1. The D88 loader opened read-only media with a host read/write mode. It now
   uses a read-only open for format inspection and data access, with a ROM-free
   read-only D88 regression test.
2. The subsystem bridge associated request consumption with the wrong PPI
   input port. The production main-to-subsystem latch is now consumed at its
   actual subsystem-side port, with positive and negative ROM-free tests.

The causal trace was extended without extra guest reads to retain one consumed
request across overlapping attention edges, FDC issue and completion, sector
transfer, and instruction fetch. Bounded start, event filtering, post-stop
capture, subsystem instruction observation, and fetch-watch controls support
the evidence collection. Trace-disabled behavior remains free of trace-only
state.

The public M07 probe source, five variant definitions, schemas, and accepted
probe golden are unchanged. No FreeDOS component source or media format was
modified.

## Reproducibility and verification

- Accepted private closure trials: 18 runs in 9 clean pairs
- Repeated private projections: byte-identical within every accepted pair
- Private input preservation: passed before and after every accepted run
- P0/P1/T0/T1: passed
- P1: production memory, tests disabled, flat test memory absent
- P1 clean builds: byte-identical
- P0/T0/T1 selftests: passed
- Focused causal tests: 4/4 passed
- Complete local T1 CTest: 87/87 passed; one explicit external-data test was
  skipped by its existing contract
- Public M07 probe and five media variants: two builds, byte-identical
- Existing public M07 tests: 55 passed before the completion gate
- VAEG full native workflow: all required jobs passed

The local Apple Silicon host adapter rebuilt the pinned M01 container image,
but its emulated FreeCOM build stopped reproducibly while executing a generated
host utility. This local adapter run is not recorded as `HOST PASS`. The native
x64 M07 completion workflow rebuilds M01 and M02 from clean generated state and
must pass before the report-containing FreeDOS commit is accepted.

## M08 handoff fields

All eight fields are `resolved_private`. Concrete values remain in the private
boot contract and are not included here.

| Field | Evidence class |
| --- | --- |
| `firmware_attempts_m05_geometry` | cross-validated |
| `accepted_signature_profile` | cross-validated |
| `initial_sector_reads` | dynamically observed |
| `loaded_extent` | dynamically observed |
| `physical_load_address` | dynamically observed |
| `first_cs_ip` | dynamically observed |
| `initial_register_state` | dynamically observed |
| `boot_drive_identity` | cross-validated |

Promotion remains `prohibited_pending_user_approval`. M08 may consume only an
owner-approved minimal subset or an independently public source.

## Privacy and limitations

Canonical launch, result, projection, input-preservation, and cleanup records
are retained in ignored persistent local evidence. Regenerable raw traces and
superseded build trees were removed after compact evidence was verified. No
ROM, D88, manual content, raw trace, private path, private identity, generated
image, binary, or private-derived concrete handoff value is tracked.

Real hardware was not run. VAEG observation is not hardware verification. The
M06 compile-only carrier was not executed as a functioning FreeDOS kernel.
No disk service, kernel loader, console, keyboard, timer, or DOS runtime was
implemented in M07.

M07 PASS — VAEG FIRMWARE BOOT ACCEPTANCE CONTRACT COMPLETE.
PRIVATE CANONICAL LAUNCH, RESULT, PROJECTION, AND INPUT-PRESERVATION MANIFESTS RETAINED OUTSIDE TEMPORARY STORAGE.
PRIVATE ROM, D88, MANUAL CONTENT, RAW TRACES, DISASSEMBLY, AND DERIVED CONCRETE VALUES NOT DISTRIBUTED.
VAEG PRODUCTION-MEMORY AND ROM-FREE REGRESSION GATES PASS.
COMPONENT SOURCES AND GITLINKS UNCHANGED.
HARDWARE NOT RUN.
M08 READY BUT NOT STARTED.
