# M14 storage fixtures

These sources are ordinary 8086 DOS programs. `M14FILE.COM` exercises the
INT 21h create/write/zero-write/seek/reopen/read/rename/delete, subdirectory,
and nested-file services. `M14FULL.COM R` fills the root directory and
`M14FULL.COM D` fills the data area on separate disposable media.
The file probe writes an explicit deterministic gap pattern before checking
the extended file; it does not assume seek alone zero-initializes a gap.
The full-media probe requires positive progress and the specific root-full or
data-full DOS result, then demonstrates space reuse after deletion/truncation.

The programs report only a compact guest marker. Qualification also inspects
the saved raw/D88 bytes, both FAT copies, directory chains, and a fresh-boot
reread; a marker alone is not acceptance evidence.

`m14_block_boot.asm` is a separate pre-DOS MZ probe, not a COM program. Build
it inside the pinned container using `tools/m14/build_block_probe.sh`; it links
the exported component's actual platform, resident disk and machine-service
objects. It never starts DOS, mounts a filesystem, or returns after mutation.
Use only disposable boot media and package it with the established MZ carrier.
The leave-pattern and restoration variants each read, write, verify, reread
and check guards at geometry-derived first/last and track/head boundaries.
After the emulator exits, `tools/m14/check_block_probe.py` independently checks
the exact payload changes and unchanged D88 structure. Negative checker tests
reject corrupted targets, unrelated changes and metadata drift. These tests
alone do not qualify DOS filesystem writes or the complete block matrix.

The protected and missing-medium variants pause at named debugger boundaries
for normal media replacement, then observe retrace edges before retrying.
They require the expected adapter error, zero completion and successful later
write/verify/readback/restoration. The partial variant ejects at the second
production callback of a two-sector request and requires exactly one sector
completed. It deliberately leaves that prefix changed for host inspection;
its separate recovery target must be restored. Never boot DOS on the mutated
partial fixture or infer common DOS error/cache behavior from these raw probes.

`tools/m14/append_files.py` can add nonempty original probes and marker files
to a canonical flat input without moving existing file chains or boot payloads.
It requires an exact base hash and new persistent Git-excluded outputs, and
rejects collisions or invalid input allocation. This is input preparation only;
all claimed filesystem operations must subsequently execute through DOS.

`M14IO.COM` opens an old read handle and a new write handle, pauses for a key,
then requests a 4096-byte DOS write. Its error/count and close/read observations
come from the actual DOS returns. Use normal device replacement at a selected
production callback or recovery boundary to interrupt it. Independently check
the completed prefix, replacement-media preservation and subsequent recovery;
the fixture never prints PASS or patches the kernel, device state or returns.

`M14READ.COM` is placed on the input before the data-full workload. On a fresh
boot of the saved result, it reads every byte of DATAFULL.BIN using DOS, checks
the expected byte pattern, requires a real EOF and successful close, and prints
the measured 32-bit byte count. The independent saved-media check must bind that
count to the expected length. It is not appended to a full disk after testing.
