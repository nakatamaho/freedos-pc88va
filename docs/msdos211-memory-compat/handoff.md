# Handoff: M2 blocked; resident-placement evidence required

## M1 complete; M2 executed and blocked

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

## M1 implementation and evidence

Read-only inspection of the matching VAEG source established that the VA
emulator loads a fixed-size 0x4000-byte backup image, selects `vabkupmem.dat`
for VA and the VA2 file for VA2/VA3, and seeds a missing image from the
supported 256/384/512/640 KiB setting. The documented field is at offset
`1fc4h` in backup RAM exposed at `B0000h`; the low three bits encode
`(capacity/128)-1`. The PC-88VA decoder is implemented in component commit
`a11c72dc9ce17cc2742d457b39d26629c1aca4df`. It selects bank 9 through the
evidenced word-port path, preserves the prior bank value, rejects zero and
codes above four, and returns a 16-bit KiB value. The kernel never opens a
host persistence file.

Relevant local VAEG source references are `io/bkupmemva.c`, `io/memctrlva.c`,
`io/memoryva.c`, and the VA memory-selection code in `machine/pccore.c`. The
matching private input and source hashes remain outside Git under the M0
evidence record.

## M1 completion and next action

The seven M1 decoder fixtures, 19 focused PC-88VA/M13 tests, pinned
Linux/amd64 Open Watcom build (two byte-identical runs), and guarded NEC98
`initoem.c` compile passed. The two linked maps differ only in volatile
creation/link-time fields and match after normalization. The M1 report records
all hashes, commands, and explicitly unrun VAEG/MCB gates. No second
milestone was mixed into the component commit.

The clean native-capacity matrix was executed in M2. The 640-KiB case has a
valid MCB chain ending at `A0000h`, while the 256/384/512-KiB cases fail the
existing resident-arena guard before MCB creation because the resident range
ends near `98A8h`. The detailed M2 report is:

`reports/M2-native-capacity-arena.md`

M2 is **BLOCKED**; no later milestone is eligible. M2 started from parent
`f7a41cc532d6d5bb08384a5e221541a7741774fc`; its documentation checkpoint is
`670cd75dd4353f64027bf56d767779fc5251296b`; no source change was retained
in M2 and the component remains at
`a11c72dc9ce17cc2742d457b39d26629c1aca4df`. There is no qualified M2
implementation SHA. Physical PC-88VA validation remains
`DEFERRED HARDWARE VALIDATION`.

The next action is to establish paragraph-exact ownership and a safe resident
placement for the lower native limits. Do not start M3/M4 work or reclaim
memory until that dependency is resolved and the M2 matrix can be rerun.
