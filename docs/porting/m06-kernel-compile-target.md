# M06 PC-88VA kernel compile target

M06 introduces the first source change for the PC-88VA port.  It is a
compile-only boundary, not a boot or runtime result.  The target is maintained
on fdkernel branch `necpc88va`, whose first M06 source commit descends from the
accepted M01R1 fdkernel commit.  FreeCOM and Country remain unchanged.

## Independent platform boundary

The target lives below `pc88va/` and defines `PC88VA`, `JAPAN`, and `DBCS`.
It does not define `NEC98` or `IBMPC`, and its explicit link response contains
no source or object from those platform directories.  The initial object set
is intentionally small:

| Source | Classification | Purpose |
| --- | --- | --- |
| `pc88va/kernel/startup.asm` | `pc88va-owned` | DOS MZ entry and local fail-closed halt |
| `pc88va/kernel/stubs.c` | `temporary-fail-closed-stub` | unresolved platform interface returns |

This is a linked kernel scaffold that establishes the platform selector,
toolchain path, object graph, and loader-facing container.  It is not yet the
complete shared FreeDOS DOS-C core.  Later milestones may add reviewed
`common-core` and `shared-portable` objects only when their machine
dependencies are explicit.

## Reproducible build contract

The exact child build command is:

```sh
cd pc88va && wmake -ms -h -f makefile.wc clean all
```

It runs inside the accepted Linux/amd64 M01 container with the official Open
Watcom 1.9 tools under `/opt/openwatcom-1.9/binl`.  NASM creates the startup
OMF object, WCC creates the small-model C object, WLIB creates the platform
library, and WLINK emits the DOS MZ container.  `SOURCE_DATE_EPOCH` fixes the
object mtime consumed by WLIB.  The link input order is exactly:

1. `pc88va/build/startup.obj`
2. `pc88va/build/platform.lib`

Two builds use separate containers and source exports.  Objects, library,
linked aliases, compile manifest, canonical symbol evidence, interface record,
derived raw/D88 media, and extracted files must all be byte-identical.  The
raw Open Watcom map is retained only as ignored bounded diagnostics because it
contains a creation line; canonical symbol evidence is parsed during the
build from stable entry, stack, memory, library, and symbol rows.

## Temporary fail-closed interfaces

Every unresolved service returns a failure value and performs no firmware
interrupt, I/O-port, DMA, IRQ, or undocumented memory operation.

| Interface | Service | Removal milestone |
| --- | --- | --- |
| `pc88va_machine_init` | earliest machine initialization | M10 |
| `pc88va_disk_read` | firmware or loader disk input | M08 |
| `pc88va_console_putc` | console output | M09 |
| `pc88va_console_getc` | keyboard and console input | M11 |
| `pc88va_clock_read` | timer and clock | M10 |
| `pc88va_interrupts_init` | interrupts and vectors | M10 |
| `pc88va_memory_query` | memory discovery and reservations | M10 |
| `pc88va_fatal_stop_request` | reboot, termination, and fatal stop | M10 |
| `pc88va_loader_handoff` | loader/system transfer | M08 |
| `pc88va_nls_hook` | machine-coupled DBCS/NLS hook | M17 |

The C status value is signed `-1`; the assembly probe returns `0xffff` and
then enters a local `CLI`/`HLT` loop.  These interfaces are detectable in the
canonical symbol evidence and are not runtime implementations.

## Kernel interface

`KERNEL.SYS` and `KVA8616.SYS` are identical DOS MZ files.  The linked entry
symbol is `_pc88va_compile_only_entry`; its MZ-relative entry is recorded from
the header and map.  The interface manifest records header/body sizes,
relocations, initial MZ stack requirement, memory model, symbols, and loader
responsibilities.

The physical load address, firmware entry state, boot-drive convention, and
incoming general/segment register state remain unknown.  The MZ container
must not be treated as a flat binary.  M08 must either load the complete MZ
contract correctly or define a reviewed deterministic transformation.

## NEC98 regression and M05 media

The child source archive is a new M06 identity.  Historical M01R1 locks,
contracts, and goldens remain unchanged.  The current M06 component lock
records the child lineage while the M06 gate rebuilds the historical NEC98
target from the child commit and requires all eight fdkernel artifacts to
remain byte-identical.

The derived M06 media retains the accepted M05 geometry, BPB, placeholder
boot record, no-signature policy, FAT timestamp policy, `COMMAND.COM`, and
standalone `COUNTRY.SYS`.  It replaces only `KERNEL.SYS` and the FAT/root/data
bytes required by that payload.  The generated raw and D88 images are ignored
and never committed; only the canonical textual manifest is tracked.

## Deferred evidence

M07 must establish firmware acceptance, initial load extent, entry address and
state, and a trace-only or documented early diagnostic path.  M08 must define
the disk-read ABI, physical kernel placement, DOS MZ loading or transformation,
stack/memory ownership, boot-drive transfer, and final handoff state.

M06 makes no claim that firmware accepts the M05 placeholder, that the M06
kernel executes, or that disk, console, keyboard, timer, interrupt, memory,
NLS, `COMMAND.COM`, VAEG, or hardware works.
