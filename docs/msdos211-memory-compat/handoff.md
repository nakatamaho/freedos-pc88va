# Handoff: next eligible milestone

## M0 complete; execute M1 only

The prior plan incorrectly treated IBM-PC BIOS interrupt behavior as a
PC-88VA contract. M0 inspected the superseded shim commit and the selected
current source, found no current INT 12h/INT 15h shim installation, and froze
a fresh native MCB baseline. The detailed M0 report is:

`reports/M0-remove-bios-shims-and-rebaseline.md`

M0 is complete for its defined scope (`VAEG PASS`). Physical PC-88VA testing
was not run (`DEFERRED HARDWARE VALIDATION`).

## M0 evidence retained

The fresh 640-KiB M0 probe used the current boot-tested PC-88VA candidate and
native backup-memory input. It observed first MCB header `219Fh`, first MCB
data `21A0h`, a valid non-overlapping chain, and an exclusive end of `A0000h`.
The named MZ/allocator/lifetime probes are recorded in the M0 report. The
formal 219Fh and 423008-byte FreeDOS values remain comparison baselines; the
fresh candidate result is reported separately because it is a different dirty
M13 configuration.

## M1 handoff: VAEG backup-memory source

Read-only inspection of the matching VAEG source establishes that the VA
emulator loads a fixed-size `vabkupmem.dat` image (0x4000 bytes) through its
VA backup-memory module. The mapped VA backup memory is exposed at physical
`B0000h`; the VA memory-control ports expose the capacity/check bytes from the
loaded image. The VAEG source normalizes supported VA main-memory selections to
256, 384, 512, or 640 KiB. M1 must cite the exact field encoding, checksum and
validation, variant selection, and invalid/missing-image behavior from the
matching source and private technical evidence before changing the kernel.
The emulator filename is persistence state, not a guest DOS pathname, and the
kernel must not open it as a file.

Relevant local VAEG source references are `io/bkupmemva.c`, `io/memctrlva.c`,
`io/memoryva.c`, and the VA memory-selection code in `machine/pccore.c`. The
matching private input and source hashes remain outside Git under the M0
evidence record.

## Required M1 sequence

1. Read all applicable `AGENTS.md` files and every file/report in this spec
   set.
2. Verify the M0 report and exact source/artifact identities before editing.
3. Cite the native VA backup/common-memory field, supported encoding, variant
   selection, validation, and invalid/missing-data behavior.
4. Implement one guarded PC-88VA decoder for 256/384/512/640 KiB only. Do not
   wire it into unrelated allocators unless it is the exact existing target
   function.
5. Run all four value fixtures, variant fixtures, invalid/checksum/missing
   fixtures, and the non-PC-88VA guard build.
6. Write the M1 report, update `status.md` and this handoff, then stop. M2 is
   not eligible in the same invocation.

## M1 stop conditions

Mark M1 BLOCKED rather than guessing if the native field, encoding, or
invalid-data behavior cannot be established; if a guarded decoder would
require an invented address or BIOS shim; or if any supported-value fixture or
non-PC-88VA guard check fails.

The next eligible milestone is M1 only. Do not begin M2 in the same goal
invocation.
