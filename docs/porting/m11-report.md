# M11 keyboard and early console input

Status: **M11 PASS — FINAL PUBLICATION HANDOFF PENDING.**
M11 HANDOFF READY remains pending final-tip CI and the generic handoff checker.
M12 is NOT STARTED.

## Fixed prerequisite

- START_SHA / M10 publication: `1acd1fbc0d556ec511ba71be833a1c7144eec841`.
- M10 qualified direct parent: `eaadb757c4c3e2a4a7d405c0e250e96c1f4c222c`.
- M10 qualification CI [34020956366](https://github.com/nakatamaho/freedos-pc88va/actions/runs/34020956366) and final-tip CI [34021647523](https://github.com/nakatamaho/freedos-pc88va/actions/runs/34021647523), attempt 1, exact heads and required jobs successful.
- fdkernel M11 child: `b08ace36670a05992d8ddaa4279727d9b17bd11e`, FreeCOM unchanged at `855281a3114b43ad4b8d9a320f2aca39be046bba`, Country unchanged at `23f189cca3420606eae8723884fa92ccd65eb307`.
- VAEG M11 observer: `7dd453cbd36014ba453a26765b00cd0cc9a99655`, exact workflow [34027160366](https://github.com/nakatamaho/vaeg/actions/runs/34027160366), attempt 1, all required jobs successful.
- QUALIFIED_IMPLEMENTATION_SHA: `46252bd514d26ddec06a7402f26591d6c6818919`.
- Native CI [34030038333](https://github.com/nakatamaho/freedos-pc88va/actions/runs/34030038333), attempt 1, exact qualified head, with public-console-input and historical-regression successful.

The M10 public handoff, actual schemas and instances, artifact bindings,
component cleanliness and bounded publication diff were reverified before
mutation. The changed child was pushed first and its branch reachability was
verified. Historical M10 evidence was not rewritten or replaced.

## Implementation and contract

The five assigned M06 stubs are implemented in the child: machine
initialization support remains unchanged and `pc88va_console_getc` now uses a
small read-only fifteen-port PC-88VA matrix poll. It preserves the documented
near ABI, stack, segments and flags; returns status 0/1/2/FFFF for success,
no-input, unsupported/ambiguous input and invalid preconditions; and owns only
its exported snapshot storage. It does not call firmware, program a
controller, install an interrupt, create a second queue or echo input.
Printable ASCII, Shift punctuation, Space, Enter→CR and Backspace are the
explicit tested subset. Japanese/NLS, ANSI, editing, function-key expansion,
full DOS and hardware are excluded. The concise ADR and machine-checkable
contract are in `docs/porting/m11-console-input-adr.md` and `config/m11/`.

## Private qualification

Because historical private bundles are not required, a new current launch
contract was bound to the fixed identities and retained inputs. Two clean
production-memory main runs established K0–K9, including normal make/break
events, repeated input, modifier handling, real getc calls, returned bytes,
caller-owned M09 echo and intentional completion. Two clean no-input/delayed
controls established N0–N4, including an explicit no-input interval followed
by one delayed normal event. Input-preservation manifests, executable and
launch identities, causal observations, display captures and canonical
projections matched within each pair. The matrix poll windows contained no
FDC command or transfer. This is recorded only as `M11 FRESH PREREQUISITE
PASS`; it is not a reconstruction claim about lost historical evidence.

Private raw inputs, traces, captures and derived concrete values remain in a
persistent ignored evidence root. No private value or path is present here or
in public CI.

## Public gates

The child passed its ROM-free matrix, ABI, mapping, invalid-state, release and
modifier tests (213 tests) and two clean network-disabled Open Watcom builds
produced byte-identical objects, maps/interfaces and media. Loader stages and
FreeCOM/Country payload identities remain bound to accepted M08/M09 values.
`tools/m11/preflight.py`, `tools/m11/verify_m11.py`, the M11 schemas, negative
instance tests, Make targets and native workflow provide the reusable enforced
checker. M01R1–M10 historical gates, privacy audits and the accepted M09
verifier remain required; no hardware result is claimed.

## Handoff state

The implementation is qualified at `46252bd514d26ddec06a7402f26591d6c6818919`.
The documentation-only publication commit and exact final-tip CI remain before
HANDOFF READY.
Until those steps establish remote equality, ancestry, bounded publication
diff, qualified implementation SHA, publication tip, downstream SHA and exact
CI head, M11 HANDOFF READY is intentionally not declared.

HARDWARE NOT RUN. DEFERRED HARDWARE VALIDATION. Full DOS, COMMAND.COM,
Japanese/NLS, complete keyboard coverage, a main-branch merge and M12 are not
implemented or claimed.
