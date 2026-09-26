# ADR 0013: PC-88VA read-only FreeDOS/FreeCOM integration

## Status

M13 implementation in progress from M12 downstream base
`66138e6539e4220ae7b6d3ffee24581e0d674267`.

## Decision

The PC-88VA target links the existing FreeDOS common DOS core and uses
PC-88VA-owned adapters only at the machine boundary:

- `kernel/m13_platform.asm` translates common floppy calls to the resident
  M12 `pc88va_kernel_disk_read` entry and rejects writes, formatting and
  unsupported mutation before the firmware callback.
- `kernel/console.asm` retains M09 output and M11 keyboard services while
  exposing the common CON request table and ASCII line input boundary.
- `kernel/kernel.asm` keeps FreeDOS segment groups and startup ownership but
  avoids IBM-PC BIOS probes; the M10 machine service is invoked before
  `FreeDOSmain`.
- Existing common `main.c`, `config.c`, `initdisk.c`, `dsk.c`, FAT, SFT/JFT,
  memory, interrupt and EXEC modules remain the semantic implementation.

The first supported volume is one 1024-byte-sector FAT12 floppy with eight
sectors per track, two heads and 1280 logical sectors, matching the accepted
M12 public contract. The production path is read-only for disk contents;
console output and in-memory process/handle/MCB changes remain allowed.

## Ownership and limits

The M12 request record, callback context, callback code and 4 KiB transfer
area remain resident kernel-owned storage. DOS reads are one-sector bounded
copies through this area and reject segmented destination wrap. The allocator
must establish its first MCB after this interval and EXEC must preserve it.
No IBM-PC or NEC98 firmware selector is enabled, and no private ROM/D88 value
is present in source or public records. Japanese/NLS, ANSI, HDD, writable DOS,
TSRs, networking and broad application compatibility are outside M13.

## Qualification boundary

M13 acceptance requires real common-core startup, FAT/DTA/handle reads,
interactive FreeCOM DIR/TYPE, one COM and one relocated MZ EXEC, truthful
read-only errors, post-error recovery, two deterministic clean build pairs,
two main and two negative private runtime pairs, schema-instance validation,
historical regressions, and exact-tip CI. A source name, shell banner,
host-side model, or direct test-harness jump is not sufficient evidence.
