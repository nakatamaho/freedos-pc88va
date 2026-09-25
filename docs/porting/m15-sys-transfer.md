# M15 VA system transfer

Status: **IMPLEMENTED; focused guest checks complete, final qualification pending.**

The maintained kernel component contains `sys/pc88va.c`, `pc88va_io.asm` and
`makefile.pc88va`. The dedicated small-model 8086 executable uses the pinned
Open Watcom tools. Its command is `SYSVA A: SOURCE TARGET`, with distinct
tokens in the respective `SYS.ID` files followed by CR/LF. The root volume
must be flat; nested directories are outside this prepared-target contract.
`tools/m15/prepare_sys_target.py` prepares the empty target from the selected
source's loader allocation, without copying executable payloads or boot code.

The existing kernel SYS utility assumes a 512-byte PC boot record and PC disk
interfaces. The VA backend must use the accepted 1024-byte FAT12 layout and DOS
absolute disk APIs. The accepted first stage loads stage two from a builder
declared contiguous extent; stage two finds KERNEL.SYS through FAT12. The backend
must retain that loader and its memory ownership.

## Prepared target and source checks

The supported target is an already valid disposable VA FAT12 floppy. It contains
an all-zero LOADER.BIN placeholder occupying the same contiguous extent and file
length as the qualified source LOADER.BIN. It has a nonbooting boot record, no
KERNEL.SYS or COMMAND.COM, and independent sentinel files. Preparation reserves
loader space; it does not copy a functioning system. Incompatible BPB geometry,
missing or nonzero placeholder, different or fragmented loader extent, existing
system files, duplicate target identity and inadequate free space must be
rejected before target mutation.

This prepared-layout requirement follows the current fixed-extent first stage.
Copying the exact accepted source boot record is valid only after proving the
target loader occupies that same extent. Do not infer private firmware operands,
scan for instruction byte patterns, patch undocumented boot offsets or substitute
a new loader. Preserve the target's BPB and volume identity where they differ
from source fields that are not executable boot parameters.

The transfer command must positively identify source and target using an explicit
original marker file and expected token, not only a drive letter. Source files
and the source boot record must be read and checked before the single-drive
exchange. Each cache allocation remains process-owned and bounded; insufficient
memory is a preflight failure, not permission to reclaim another owner's memory.

## Guest operation and ordering

1. Read the qualified source boot record, LOADER.BIN, KERNEL.SYS, packaged
   COMMAND.COM and any explicitly required configuration/support files into
   bounded DOS-owned memory. Retain their exact lengths and checksums.
2. Close source handles and flush DOS before prompting for the identified target.
   Follow the M14 physical exchange protocol and perform a new pathname operation
   to bind the new medium. Never reuse old handles across the exchange.
3. Validate the target identity, BPB, full FAT chain consistency, zero placeholder,
   sentinel controls, required root slots and free clusters.
4. Write and close the payload files through DOS. Fill the reserved loader file
   without changing its required extent. Reopen and compare every payload.
5. Flush DOS; write the boot sector last through the qualified absolute interface.
   This sector is outside the live FAT/root/data cache. Read back and compare it,
   preserving the target's filesystem geometry and allowed identity fields.
6. Report success only after complete read-back. On failure, report the failed
   phase and completed writes; do not claim rollback or power-loss atomicity.
   Restore the identified source before returning if shell reload may need it.

The source control remains immutable; runtime uses its identified disposable
copy. The target must subsequently boot as the sole disk in a fresh emulator,
run the real shell and COM/MZ programs, write/reopen a file, then survive a
further saved-image reopen. Host inspection and image preparation are separate
from these guest operations.

Focused normal frontend runs confirm transfer, exact read-back, independent
target boot, COM/MZ return, and subsequent writes. Negative runs confirm
protection, wrong identity, unsupported geometry, missing loader reservation,
full data/root areas and a missing source component. Removing the medium during
transfer produces an honest failure and leaves the prepared boot record intact;
partial files are retained, with unrelated sentinels preserved. Source restoration
then permits the real parent shell to execute another child. These results are
bound to their individual candidate builds and do not replace final integrated
M15 qualification or publication.
