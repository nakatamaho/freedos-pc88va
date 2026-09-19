# MS-DOS 2.11 VA memory compatibility status

Last specification reset: 2026-09-19
M0 report: `reports/M0-remove-bios-shims-and-rebaseline.md`

## Baselines

| Item | Value | Status |
| --- | ---: | --- |
| MS-DOS 2.11 VA total memory | 655360 bytes | recorded human-supplied baseline |
| MS-DOS 2.11 VA available memory | 530176 bytes | recorded human-supplied baseline |
| FreeDOS(88VA) first MCB | `219Fh` | recorded baseline; header/data semantics must be labelled in M0 |
| FreeDOS(88VA) largest executable | 423008 bytes | recorded baseline |
| 640-KiB MCB exclusive end | `A0000h` | required invariant |

The old PC-oriented `MEM.EXE` values derived from `INT 12h` or
`INT 15h/AH=88h` are not valid PC-88VA conformance measurements.

## Superseded work

The previous milestone claim based on commit
`49335bb547348e5e899285f0535e26284c388834` is superseded. In particular,
`INT 12h -> AX=0280h` and `INT 15h/AH=88h -> AX=8600h, CF=1` are not PASS
criteria. M0 must inspect the actual commit and remove only unsupported shim
work while preserving unrelated or independently justified changes.

## Milestones

| Milestone | State | Dependency | Notes |
| --- | --- | --- | --- |
| M0 Remove invalid BIOS-shim conformance and rebaseline | COMPLETE | none | VAEG PASS; MCB chain validated to A0000h; hardware deferred |
| M1 Establish VA-native capacity decoder | COMPLETE | M0 | component `a11c72dc9ce17cc2742d457b39d26629c1aca4df`; HOST PASS for decoder, fixtures, guarded build, and pinned-toolchain build |
| M2 Drive DOS arena from native capacity | BLOCKED | M1 | 640-KiB chain passes; 256/384/512 KiB fail the resident-arena guard before MCB creation |
| M3 Account for 640-KiB low-memory layout | NOT STARTED | M2 | ineligible until M2's lower-capacity boundary is resolved |
| M4 Reclaim one proven low-memory loss | NOT STARTED | M3 | one reclaim per run |
| M5 Reach and verify memory target | NOT STARTED | M4/repeated reclaim work | full reconciliation |

## M0 completion boundary

M0 made no source or allocator change. The selected current PC-88VA source
contains no INT 12h/INT 15h shim installation, and the fresh native MCB probe
completed with a valid 640-KiB chain ending at A0000h. The recorded 219Fh and
423008-byte values remain comparison baselines; the fresh candidate result is
reported separately because it is a different dirty M13 configuration.

The VAEG M0 run is labelled `VAEG PASS` for the M0 probe scope. Physical
PC-88VA validation was not run and is `DEFERRED HARDWARE VALIDATION`.

## M1 completion boundary

M1 is complete for its defined source/fixture/build scope. The implementation
is component commit `a11c72dc9ce17cc2742d457b39d26629c1aca4df`; the detailed
report is `reports/M1-native-capacity-decoder.md` and the required porting
report is `docs/porting/m01-report.md`. The decoder reads the evidenced native
backup-memory field and returns only 256/384/512/640 KiB (invalid values fail
closed). No IBM-PC BIOS handler or allocator-layout change was added. VAEG
runtime validation was not run in M1; hardware remains DEFERRED HARDWARE
VALIDATION.

## M2 completion boundary

M2 is **BLOCKED** at the existing resident-arena guard for the 256, 384, and
512 KiB native capacities. The relocated resident range ends near `98A8h`,
above each of those arena limits, so no lower-capacity MCB can be created
without a placement/ownership change. The 640-KiB run does create a valid
non-overlapping chain whose exclusive end is `A0000h`; its complete walk and
maximum-block query are recorded in
`reports/M2-native-capacity-arena.md`. No M2 source change was retained.

M2 `START_SHA` is parent commit
`f7a41cc532d6d5bb08384a5e221541a7741774fc`; the documentation checkpoint
containing this boundary is `670cd75dd4353f64027bf56d767779fc5251296b` and
the fdkernel child remains `a11c72dc9ce17cc2742d457b39d26629c1aca4df`.
There is no qualified M2 implementation SHA because the milestone is blocked.
Physical validation is `DEFERRED HARDWARE VALIDATION`.

## Next eligible work

No later milestone is eligible while M2 is blocked. The restart action is a
scoped resident-placement/ownership analysis for the lower native limits;
that work belongs to the M3 dependency boundary and must not reclaim memory
without paragraph-level evidence.
