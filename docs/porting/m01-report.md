# M01 — VA-native capacity decoder

Status: COMPLETE for the M1 decoder scope (HOST PASS). VAEG runtime
qualification was not run for this milestone; physical PC-88VA validation is
DEFERRED HARDWARE VALIDATION.

## Selected milestone and identities

* `START_SHA`: `a01ec6c831e32e494a0256e7ae567b53622cff04`
* component implementation: `a11c72dc9ce17cc2742d457b39d26629c1aca4df`
* component branch: `topic/msdos211-m1-native-capacity`
* pinned toolchain: Open Watcom 1.9 in Linux/amd64 (`x86_64`/`amd64`)
* parent checkpoint and publication identities are recorded in the M1 memory
  compatibility report and handoff after the parent commit.

## Scope and result

The PC-88VA adapter previously returned a fixed 640 KiB value. The scoped
child change reads the evidenced native backup-memory field through the
PC-88VA banked memory interface and returns only the four supported values:
256, 384, 512, or 640 KiB. Zero and unsupported codes return zero. The
existing PC-88VA `init_oem()` call already invokes this adapter. No IBM-PC
BIOS memory handler was added, and no allocator layout was changed.

The VAEG contract evidence is summarized in
`docs/msdos211-memory-compat/reports/M1-native-capacity-decoder.md`; raw
private source projections and generated files remain outside Git.

## Verification

The M1 fixture suite passed all seven cases. Existing PC-88VA target and M13
contract suites passed, for 19 tests total. The same fixture suite passed in
the pinned Linux/amd64 build container. Open Watcom WMake produced a
KERNEL.SYS twice; KERNEL.SYS, KVA8616.EXE, and m13_platform.obj were
byte-identical. The generated map differed only in volatile creation/link-time
lines and matched after those lines were normalized. A guarded NEC98
`initoem.c` compile produced an 8086 relocatable object.

The M0 native baseline remains the comparison record: first MCB header
`219Fh`, first data `21A0h`, largest recorded executable 423008 bytes,
and 640-KiB exclusive end `A0000h`. M1 did not rerun those DOS probes.

## Unrun gates and risks

A VAEG boot with the new decoder and all M2 native-capacity/MCB probes are
not run; they are the next milestone's responsibility. No real hardware test
was run. Optional historical component tests that import `unicorn` were not
available in the host environment and were not relabelled as passes.

No second milestone was started in this report. The next eligible milestone
is M2.
