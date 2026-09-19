# M2 — Drive the DOS arena from VA-native capacity

## Outcome

**BLOCKED.** The M1 decoder is reached and the 640-KiB arena is initialized
with a valid MCB chain ending at `A0000h`. The three smaller native capacities
are rejected by the existing resident-arena guard before the first MCB is
created. Relocating the resident image so that those capacities can be
represented is a low-memory-layout change and is outside M2; M3 is therefore
not eligible until this dependency is resolved.

No source change was retained by M2. A temporary private arena-value probe was
used while diagnosing the boundary, then removed; the component worktree is
clean at the M1 child commit.

## Eligibility and identities

| Identity | Value |
| --- | --- |
| M2 parent `START_SHA` | `f7a41cc532d6d5bb08384a5e221541a7741774fc` |
| fdkernel implementation | `a11c72dc9ce17cc2742d457b39d26629c1aca4df` |
| fdkernel source archive | `8fc8db64adde28f902a3803decf79a7623cca11e023609d23bc0f2d2587ef157` |
| build image configuration | `212ce9c9d812c45708c57ef632257d885394a37cc01dd351233798f263452abe` |
| Open Watcom archive | `f7484be27eb70028010303fc16bb2acc5a785679567a568b940c28190ddbf3f3` |
| clean-build `KERNEL.SYS` | `00ee98637d7bf23c9717c4f4acff6228794460299cded8d1c7692b084aa7e030` |
| clean-build `KVA8616.exe` | same as `KERNEL.SYS` |
| normalized clean-build map | `86012239b7ba2a1eee0b5ad6820c6ff5ac4c5bcdc714d3cf3212a40986871258` |
| VAEG qualification | private evidence record `msdos211-m2-native-capacity-20260919` |

The exact ROM, D88, backup-memory images, launch manifests, screens, and raw
traces remain in the persistent private evidence record and are not copied
into Git.

## Contract and source boundary

`init_oem()` calls the PC-88VA `pc88va_memory_kb()` adapter. The adapter reads
the native backup/common-memory field and returns only 256, 384, 512, or 640
KiB. `PreConfig2()` converts the selected value to paragraphs as
`arena_limit = ram_top * 64U`, then checks that the already-relocated resident
image fits before writing any MCB.

The relevant existing guard is equivalent to:

```c
resident_end = resident_start + resident_paras;
if ((resident_end + 1U) >= arena_limit)
    init_fatal("PC88VA resident arena");
```

This is the first failing boundary for 256/384/512 KiB. It is not an MCB
corruption and it is not a decoder fallback.

## Capacity and arena results

The clean linked candidate places the resident copy at approximately segment
`9800h` and uses `00A8h` paragraphs for the resident range, ending at
`98A8h`. The following table uses the selected native capacity as the only
arena limit; no IBM-PC BIOS result is used.

| Native capacity | `arena_limit` | Resident range | First MCB/MCB walk | Result |
| ---: | ---: | --- | --- | --- |
| 256 KiB | `4000h` / `40000h` | `9800h–98A8h` | not created | guarded `Internal kernel error`, then halt |
| 384 KiB | `6000h` / `60000h` | `9800h–98A8h` | not created | guarded `Internal kernel error`, then halt |
| 512 KiB | `8000h` / `80000h` | `9800h–98A8h` | not created | guarded `Internal kernel error`, then halt |
| 640 KiB | `A000h` / `A0000h` | `9800h–98A8h` | `1000h` / `1001h` | valid chain, exclusive end `A0000h` |

The 256/384/512 runs all stopped before `pc88va_init_mcb()`. Consequently a
full walk and an `AH=48h/BX=FFFFh` query cannot honestly be reported for those
capacities. This is the precise missing acceptance evidence, not a reason to
invent a lower MCB boundary.

## 640-KiB MCB accounting

The current candidate's native diagnostic walked 14 MCBs. The `S` column is
the data-paragraph count; each row also has one 16-byte MCB header. The rows
advance by `header + size + data` and the final `Z` row ends exactly at
`A0000h`.

| MCB header | Type | Owner | Data paragraphs | Data range (exclusive end) |
| ---: | :---: | ---: | ---: | --- |
| `1000h` | M | `0008h` | `05E4h` | `1001h–15E5h` |
| `15E5h` | M | `0008h` | `00A8h` | `15E6h–168Eh` |
| `168Eh` | M | `0000h` | `0006h` | `168Fh–1695h` |
| `1695h` | M | `1696h` | `1045h` | `1696h–26DBh` |
| `26DBh` | M | `26E5h` | `0008h` | `26DCh–26E4h` |
| `26E4h` | M | `26E5h` | `004Ch` | `26E5h–2731h` |
| `2731h` | M | `0000h` | `40CDh` | `2732h–67FFh` |
| `67FFh` | M | `0008h` | `15C1h` | `6800h–7DC1h` |
| `7DC1h` | M | `0000h` | `1A3Dh` | `7DC2h–97FFh` |
| `97FFh` | M | `0008h` | `00A8h` | `9800h–98A8h` |
| `98A8h` | M | `0000h` | `067Ah` | `98A9h–9F23h` |
| `9F23h` | M | `1696h` | `0010h` | `9F24h–9F34h` |
| `9F34h` | M | `0000h` | `0080h` | `9F35h–9FB5h` |
| `9FB5h` | Z | `1696h` | `004Ah` | `9FB6h–A000h` |

The data sizes sum to `08FF2h` paragraphs (`589600` bytes). Fourteen headers
add `00E0h` paragraphs (`224` bytes), giving `09000h` paragraphs (`589824`
bytes) from `10000h` through the exclusive end `A0000h`. No MCB crosses the
selected 640-KiB boundary.

The maximum-block query in the same 640-KiB run returned `AX=0008h` with
carry set and `BX=40CDh`, i.e. `265424` bytes of largest immediately
allocatable data for that invocation. The diagnostic's DOS result is kept
separate from the recorded M0 comparison value of 423008 bytes because the
candidate and startup allocations differ.

## Named tests

| Test | 640-KiB result | 256/384/512 result |
| --- | --- | --- |
| Native MCB diagnostic | `VAEG PASS`: complete walk, final `A0000h` | `NOT RUN`: pre-MCB guard stops first |
| `INT 21h/AH=48h, BX=FFFFh` | `VAEG PASS`: `AX=0008h`, `CF=1`, `BX=40CDh` | `NOT RUN`: no DOS arena exists |
| `MZPROBE.EXE` | `VAEG PASS` return-to-prompt smoke run; no visible probe text | `NOT RUN` |
| `MEMFREE2.COM` | `VAEG PASS`: `TOTAL=6236h`, `MAX=40F9h` | `NOT RUN` |
| `MEMFREE3.COM` | `VAEG PASS`: `TOTAL=6224h`, `MAX=40E7h`, `PROBE=0032h` | `NOT RUN` |
| `MEMLIFE.COM` | `VAEG PASS`: `MEM-LIFETIME-OK` | `NOT RUN` |
| Guarded non-PC-88VA compile | `HOST PASS`: NEC98 `initoem.c` object produced | same source/build |

The native diagnostic also contains legacy BIOS-query display rows in its
private screen, but those rows are characterization only. INT 12h and
INT 15h/AH=88h are not PC-88VA compatibility requirements and are not used
for this result.

## Build and validation commands

The clean builds used the pinned `freedos-pc88va-m01:local` Linux/amd64 image
with the source archive as an input archive (no host source-tree bind mount):

```text
docker create --platform linux/amd64 --entrypoint /bin/sh \
  freedos-pc88va-m01:local -c '... extract fdkernel source archive ...; \
  SOURCE_DATE_EPOCH=315532800 WATCOM=/opt/openwatcom-1.9 \
  PATH=/opt/openwatcom-1.9/binl:$PATH \
  wmake -f makefile.m13.wc'
=> exit 0, run A; exit 0, run B

PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v \
  pc88va.tests.test_m1_native_memory \
  pc88va.tests.test_m13_target pc88va.tests.test_pc88va_target
=> exit 0, 19 tests

wcc ... -DNEC98 ... -fo=initoem-nec98.obj ../kernel/initoem.c
=> exit 0, guarded object produced

python3 tools/m09/compare_maps.py KVA8616.map-A KVA8616.map-B
=> exit 0; only WLink creation time differs
```

Both clean builds produced byte-identical `KERNEL.SYS`, executable, and
component objects. The normalized maps also compare equal. The exact VAEG
commands, backup-memory records, media identities, and screen dumps are in
the private evidence record named above.

## Blocker and next eligible work

The M2 acceptance matrix requires successful MCB termination at
`40000h/60000h/80000h/A0000h`. The current resident image occupies
`9800h–98A8h`, so the existing fail-closed check necessarily rejects the
first three limits. Moving or shrinking that resident range requires an
ownership/lifetime analysis and a placement change; doing that speculatively
in M2 would violate the milestone boundary.

M2 is therefore **BLOCKED**, with the first missing fact being a safe
resident placement that fits below each selected ceiling. M3 is not started
and is not eligible while M2 is blocked. No second milestone was started in
this invocation. Physical PC-88VA validation remains `DEFERRED HARDWARE
VALIDATION`.
