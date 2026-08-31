# M04 Downstream Readiness

| milestone | public readiness | private-local readiness | reason |
| --- | --- | --- | --- |
| M05 | ready_with_assumptions | ready_with_assumptions | candidate geometry and FAT12 arithmetic are complete; no bootability claim |
| M06 | ready_with_assumptions | ready_with_assumptions | independent platform and payload role are defined; runtime addresses remain provisional |
| M07 | blocked | blocked | signature/acceptance and complete entry state are unresolved |
| M08 | blocked | blocked | callable disk entry and kernel destination/entry/handoff are unresolved |

M04 passes because M05 and M06 have implementable, bounded contracts. M07 and
M08 do not pass through implication. Each remains blocked until its explicit
unknowns are resolved by the named source or emulator validation.

The M05 state authorizes deterministic host-side filesystem/image assembly
only. The M06 state authorizes the first compile-only platform boundary. It
does not authorize runtime or boot claims.
