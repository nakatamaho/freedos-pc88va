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
| M1 Establish VA-native capacity decoder | NOT STARTED | M0 | backup/common-memory evidence required |
| M2 Drive DOS arena from native capacity | NOT STARTED | M1 | test 256/384/512/640 KiB |
| M3 Account for 640-KiB low-memory layout | NOT STARTED | M2 | paragraph-exact ownership map |
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

## Next eligible work

M1 only. M1 must establish and test the VA-native capacity decoder from the
mapped backup/common-memory state. Do not begin M2 in the same `/goal`
invocation.
