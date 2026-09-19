# M0 — Remove unsupported BIOS-shim conformance and rebaseline

Status: COMPLETE (`VAEG PASS` for the M0 scope; physical hardware is
`DEFERRED HARDWARE VALIDATION`).

## Eligibility and scope

M0 was the first eligible milestone in the corrected memory-compatibility
specification. The isolated parent validation tree started at
`1ec3101ec5ffcd9babf306f2e553125a604934d9`; its fdkernel gitlink was
`e432296345f1ccc783a42c02baa7ffe4bd2a6eb8`. The original dirty M13 worktree
and the VAEG checkout were not reset or modified.

The exact source archive, kernel/map/carrier/media/VAEG hashes, launch
manifest, private backup-memory input and raw screen are retained in the
persistent private M0 evidence record. They are intentionally not copied into
this public report because D88/ROM/raw-trace and private-derived identities
must remain outside Git.

## Superseded BIOS-shim work

Commit `49335bb547348e5e899285f0535e26284c388834` was inspected in the
superseded fdkernel worktree. It added PC-88VA IVT installation for INT 12h
and INT 15h/AH=88h, IBM-PC-style handlers, tests asserting those values, and
an unrelated INT 2Fh/AX=4300h branch.

That commit is not an ancestor of the selected M0 validation source. Source,
linked map, and linked KERNEL.SYS checks found no current
`pc88va_bios_int12`, `pc88va_bios_int15`, or `m1_install_bios_vectors` shim
symbols. The shared INT 2Fh behavior was not changed or classified by M0. No
source inverse patch was needed.

The observed INT 12h/15h values are characterization only; they are not
PC-88VA capacity contracts or M0 PASS criteria.

## Build and configuration

The selected candidate was built with the pinned Open Watcom 1.9 Linux/amd64
toolchain in the existing Colima container. The effective command was:

```text
SOURCE_DATE_EPOCH=1660000000 WATCOM=/opt/openwatcom-1.9 \
PATH=/opt/openwatcom-1.9/binl:$PATH \
wmake -ms -h -f makefile.m13.wc clean all
```

The build completed with status 0. The run used the recorded PC-88VA `va`/
FDD1 configuration, SDL2 software rendering, and the preserved 640-KiB native
backup-memory input. The first clean gitlink-only carrier was retained as a
discarded control because it stopped before DOS startup without the current
dirty M13 placement/carrier changes; it was not used for acceptance.

## Fresh native DOS/MCB probe

The fresh M0PROBE run completed from the command prompt. It used DOS
INT 21h/AH=52h and INT 21h/AH=48h and did not use INT 12h or INT 15h/AH=88h
to size the arena.

| Observation | Result |
| --- | --- |
| Native configured case | 640 KiB / 640-KiB arena |
| First MCB header | `219Fh` |
| First MCB data | header plus one paragraph (`21A0h`) |
| AH=48h/BX=FFFFh | normal largest-block failure; exact registers retained privately |
| Complete MCB walk | no cycle or overlap; exact rows retained privately |
| Final exclusive arena end | `A0000h` |

The full register/flag state, every MCB type/owner/size/range, and the
paragraph/byte accounting are in the private evidence record. Publicly,
the chain is established to advance by size + one MCB paragraph, terminate
with one `Z` block, and end exactly at `A0000h`.

## Named regression probes

The probes ran on the matching current M13 source family; exact media and
screen identities remain private:

| Probe | Result | Evidence |
| --- | --- | --- |
| `MZPROBE.EXE` | relocation smoke test completed | `VAEG PASS` |
| `MEMFREE2.COM` | maximum-block probe completed | `VAEG PASS` |
| `MEMFREE3.COM` | MCB/largest-block cross-check completed | `VAEG PASS` |
| `MEMLIFE.COM` | lifetime probe completed | `VAEG PASS` |

The formal FreeDOS comparison values remain unchanged: first MCB `219Fh` and
largest executable size 423008 bytes. The fresh candidate's exact largest
block is retained separately because it is a different dirty M13
configuration; it is not silently substituted for the formal baseline.

## Baseline and boundary

The MS-DOS 2.11 VA human baseline remains 655360 bytes total and 530176 bytes
available. M0 made no allocator, native-capacity, BIOS, XMS, or
memory-reclamation change. Physical PC-88VA validation was not run and is
`DEFERRED HARDWARE VALIDATION`.

M0 is complete. The next eligible milestone is M1, which must establish the
VA-native backup/common-memory capacity decoder. No M1 implementation was
started in this milestone.
