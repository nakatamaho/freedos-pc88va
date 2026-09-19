# M1 — VA-native capacity decoder

## Outcome

**COMPLETE (HOST PASS)** for the M1 source, fixture, guarded-build, and
pinned-toolchain scope. No VAEG boot was required by this milestone's named
tests; VAEG runtime qualification is **NOT RUN** here. Physical PC-88VA
validation remains **DEFERRED HARDWARE VALIDATION**.

M1 establishes the existing PC-88VA `init_oem()` call as a native decoder
call. It does not add an IBM-PC `INT 12h` or `INT 15h/AH=88h` contract and it
does not change the DOS arena or MCB layout.

## Identities and eligibility

| Identity | Value |
| --- | --- |
| `START_SHA` (parent) | `a01ec6c831e32e494a0256e7ae567b53622cff04` |
| component base | `a3d613c16b52e9bf6143f2223494db996eafd4fc` |
| component implementation | `a11c72dc9ce17cc2742d457b39d26629c1aca4df` |
| component branch | `topic/msdos211-m1-native-capacity` |
| component remote tip | `a11c72dc9ce17cc2742d457b39d26629c1aca4df` |
| toolchain | Open Watcom 1.9, Linux/amd64 container |
| locked Ubuntu amd64 manifest | `sha256:79676deb51ebb02885b0b9d33788e78a37cf1045ad79d1bb04c6a222c3556b3d` |
| local build image config | `sha256:212ce9c9d812c45708c57ef632257d885394a37cc01dd351233798f263452abe` |
| Open Watcom archive | `f7484be27eb70028010303fc16bb2acc5a785679567a568b940c28190ddbf3f3` |
| source snapshot archive | `dda4d1646591260f3948ecdea52a83d7fa68c18420e96ce3337ba61a6a6853bf` |

The component change is a child of the M0-era component base and was pushed
to the fork before this parent checkpoint. The parent gitlink is updated only
to that child commit; the existing dirty M13 worktree was not used or reset.

## Evidence for the native contract

The decoder contract is taken from the matching VAEG source, retained in the
private M1 evidence record, rather than inferred from an IBM-PC BIOS result:

| Evidence | Observed contract |
| --- | --- |
| `io/bkupmemva.c`, `bkupmemva_read` and `bkupmemva_load` | The frontend loads exactly `0x04000` bytes into native backup RAM; a missing/short file is zeroed then initialized from the selected main-RAM capacity. |
| `io/bkupmemva.c`, `bkupmemva_initialize_mainram` | Supported capacities are 256, 384, 512, and 640 KiB. The capacity code is `(capacity/128)-1` and is stored in the low bits of field `0x1fc4`; the surrounding signature/checksum bytes are not used by this kernel decoder. |
| `sdl2/np2.c`, `backup_memory_filename` | VA selects `vabkupmem.dat`; VA2/VA3 select the corresponding VA2 backup file. The record layout is the same. |
| `machine/pccore.c`, `pccore_normalize_mainram` | Only 256/384/512/640 KiB are accepted; an invalid frontend setting is normalized to 640 KiB before a missing image is seeded. |
| `memoryva/memoryva.c` and `io/memctrlva.c` | Backup RAM is mapped at physical `B0000h`; system-memory bank selection is exposed through port `0153h`, while the word access at `0152h` dispatches low byte then high byte. |

The PC-88VA assembly preserves the existing ROM-bank byte, selects system
bank 9 through the evidenced word-port interface, reads `B000:1fc4`, masks
the documented low three bits, and maps codes 1..4 to 256/384/512/640 KiB.
Zero and values above four return zero (fail closed). No host DAT file is
opened by DOS.

## Scoped implementation

Changed files in the component child commit:

* `pc88va/kernel/m13_platform.asm`: replace the constant 640-KiB return with
  the guarded native backup-memory decoder. `pushf`/`cli` protects the bank
  switch; the original word-port value and all added registers/ES are
  restored before the existing FAR return.
* `pc88va/tests/test_m1_native_memory.py`: fixture and source-contract tests
  for all capacities, both VA filename variants, high metadata bits,
  erased/unsupported values, checksum-invalid-but-readable records, and the
  non-PC-88VA conditional path.

`kernel/initoem.c` already calls `pc88va_memory_kb()` only under
`PC88VA`; the non-PC-88VA `#else` path remains the pre-existing target-specific
code. Because M1 replaces that already-called adapter, no new allocator wiring
was introduced. M2 is responsible for exercising the selected ceiling through
the full arena.

## Byte/accounting and generated-code checks

| Item | Before | After | Evidence |
| --- | --- | --- | --- |
| Capacity semantics | every input returned 640 | codes 1..4 return exactly 256/384/512/640; invalid returns 0 | source and fixture tests |
| `PC88VA_MEMORY_KB` linked span | constant stub | `0509:d0d3` through `0509:d111` (62 bytes) | Open Watcom map |
| PC-88VA `KERNEL.SYS` | not rebuilt for M1 | 85,863 bytes | two pinned container builds |
| first MCB / arena end | `219Fh` / `A0000h` M0 baseline | unchanged by M1 scope; no runtime MCB run | M0 report; M2 named tests pending |

The generated disassembly contains the expected `IN AX,152H`, bank-select
mask/OR, `OUT DX,AX`, `ES=B000h`, `ES:[1fc4h]` load, low-bit guard,
multiply by 128, restoration sequence, and `RETF`. The complete private
disassembly and maps are retained outside Git.

## Commands and results

All commands below used a container reporting `x86_64` and `amd64`, with no
network and no host source bind mount for the build:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v \
  pc88va.tests.test_m1_native_memory \
  pc88va.tests.test_m13_target \
  pc88va.tests.test_pc88va_target
=> exit 0 (19 tests)

PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v pc88va.tests.test_m1_native_memory
=> exit 0 (7 tests in the Linux/amd64 build container)

wmake -ms -h -f makefile.m13.wc clean all
=> exit 0, run 1; exit 0, run 2

wcc ... -DNEC98 ... -fo=initoem-nec98.obj ../kernel/initoem.c
=> exit 0; 8086 relocatable object produced

git diff --check
=> exit 0
```

The two-run byte comparison is:

| Artifact | Run 1 SHA-256 | Run 2 SHA-256 | Result |
| --- | --- | --- | --- |
| `KERNEL.SYS` | `00ee98637d7bf23c9717c4f4acff6228794460299cded8d1c7692b084aa7e030` | same | PASS |
| `KVA8616.exe` | same as `KERNEL.SYS` | same | PASS |
| `m13_platform.obj` | `387fb817ce519bad2fa3f61bb7b433c626db3b5709562ddbf9e9fcb58d7ea68c` | same | PASS |
| `KVA8616.map` | `2de7a840ea90e0fa371902e2b37205a4ac13668185c007c80d869875e21acc62` | `0d554429ffad3dcb7032dc16d0a5aef9cc32a3bc5905de142fceae584fb2352c` | volatile timestamp/link-time fields only; normalized map PASS |

The normalized map SHA-256 is
`86012239b7ba2a1eee0b5ad6820c6ff5ac4c5bcdc714d3cf3212a40986871258`.
The guarded NEC98 object SHA-256 is
`f02cc690a01708aa859902606a9194c5d1903aca9fdba60a4588f16207b0edae`.

## Explicitly unrun and boundary

* A VAEG boot using this new child image was not run in M1; `VAEG PASS` is
  not claimed for M1.
* No private backup-memory DAT was consumed by the guest build; only the
  evidenced source layout and in-memory fixtures were used.
* No MCB, `AH=48h`, allocation-boundary, MZ, or lifetime probe was run after
  changing the decoder. Those are M2 tests.
* No real PC-88VA hardware test was run (`DEFERRED HARDWARE VALIDATION`).
* Full historical component suites requiring the optional `unicorn` Python
  module were not run; the M1-specific and guarded target suites passed.

M1 is complete. The only next eligible milestone is M2, which must feed these
four native capacities through DOS arena initialization and verify the MCB end
and allocation behavior at each capacity. No second milestone was started in
this M1 report.
