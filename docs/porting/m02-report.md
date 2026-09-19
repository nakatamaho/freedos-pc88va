# M02 porting report — native-capacity arena

Status: **BLOCKED**

M2 consumed the completed M1 child `a11c72dc9ce17cc2742d457b39d26629c1aca4df`
from parent start `f7a41cc532d6d5bb08384a5e221541a7741774fc`. No component
source change was made in M2; the temporary arena probe used for diagnosis was
removed before the clean builds.

The native decoder feeds `ram_top`, and the 640-KiB run produced a valid
non-overlapping MCB chain ending at `A0000h`. The 256/384/512-KiB runs stop
at the existing resident-arena guard because the relocated resident range is
near `9800h–98A8h`, above each corresponding arena limit. Thus the lower
capacity MCB and allocation tests cannot be run without a placement design
change. M3 is not started.

## Verification summary

| Gate | Result |
| --- | --- |
| Pinned Linux/amd64 clean build, run A | `HOST PASS` |
| Pinned Linux/amd64 clean build, run B | `HOST PASS` |
| Byte comparison and normalized map comparison | `HOST PASS` |
| M1/M13/target unit tests (19) | `HOST PASS` |
| Guarded NEC98 compilation | `HOST PASS` |
| 640-KiB native MCB walk and AH=48h query | `VAEG PASS` |
| 640-KiB MZPROBE/MEMFREE2/MEMFREE3/MEMLIFE | `VAEG PASS` |
| 256/384/512-KiB full MCB/allocator matrix | `NOT RUN` — pre-MCB guard |
| Physical PC-88VA | `DEFERRED HARDWARE VALIDATION` |

The complete byte-accounted MCB table, commands, and private artifact
identities are in `docs/msdos211-memory-compat/reports/M2-native-capacity-arena.md`.
The formal M0 comparison values remain unchanged and are not replaced by the
current candidate's 640-KiB largest-block result.

No M2 qualified implementation SHA exists because the milestone is blocked;
the parent checkpoint will contain documentation and the restartable handoff
only.
