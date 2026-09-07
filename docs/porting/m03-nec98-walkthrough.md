# M03 NEC98 Baseline Walkthrough

This document describes the pinned NEC98 source tree as a source walkthrough.
It is not a PC-88VA compatibility statement. Every source citation below is
at the component commit recorded by M03.

## Build selection and assembly

`fdkernel`'s NEC98 makefile selects the Linux/Windows build environment and
the `all` graph, then enters `utils`, `lib`, `drivers`, `boot`, `sys`, and
`kernel` in that order. The NEC98 kernel makefile enumerates the object groups
`OBJS1` through `OBJS8`, creates `kernel.rsp`, links `kernel.exe`, and runs
`exeflat.exe` to create `kernel.sys`. It also copies the target alias and
builds the kernel Country driver. These are source facts from fdkernel commit
`6523acdb87f4665e6068ea331859885267242005`, paths
`nec98/makefile` target `all` and `nec98/kernel/makefile.wc` symbols
`OBJS`, `TARGET_LNK`, `kernel.exe`, and `kernel.sys`.

The shared `kernel/makefile` and the IBM-PC `ibmpc/kernel/makefile.wc` show
that much of the DOS object graph is shared or follows the same build shape.
The NEC98 makefile explicitly adds `nec98cfg.inc`, `conseg60.asm`, and
`conkey60.asm` to relevant assembly dependencies. Source fact:
fdkernel commit `6523acdb87f4665e6068ea331859885267242005`, paths
`kernel/kernel.asm`, `kernel/makefile`, and `ibmpc/kernel/makefile.wc`.

Reusable structure includes the object-list/link/flatten pipeline, DOS data
structures, FAT routines, process and file services, and the separation of
assembly entry points from C services. The exact low-level implementation is
not automatically reusable: the source selects platform assembly and BIOS or
controller behavior through build inputs and file layout.

## Boot and disk path

The NEC98 boot source defines `LOADSEG`, `DISK_BOOT`, a BPB-shaped header, the
temporary FAT and stack layout, and the `real_start` entry. It reads the root
directory, searches for `KERNEL.SYS`, and has `NEC98FDD`/`NEC98HDD` conditional
paths. The source also contains NEC98 DOS5+ physical-sector fields. Source
fact: fdkernel commit `6523acdb87f4665e6068ea331859885267242005`, path
`nec98/boot/boot.asm`, symbols `LOADSEG`, `DISK_BOOT`, BPB fields, and
`real_start`.

The NEC98 floppy driver has `NEC98` conditional regions and named operations
such as `FL_SENSE`, `FL_READID`, `FL_RESET`, and `FL_DISKCHANGED`; the other
branch uses shared BIOS-style paths including INT 13h. Source fact: fdkernel
commit `6523acdb87f4665e6068ea331859885267242005`, path
`nec98/drivers/floppy.asm`, those symbols and `%ifdef NEC98` sections.

The reusable part is the abstract sequence of reading sectors, interpreting a
FAT, finding a system file, and transferring control. NEC98-specific parts
include the controller access, physical-sector handling, conditional boot
layout, and firmware assumptions. None of these sources establish a VA load
address, entry register state, floppy geometry, or accepted boot signature.

## Kernel initialization and device I/O

The shared kernel assembly marks the kernel entry and performs the DOS startup
and high-memory movement work. The NEC98 object graph includes `int29dc.obj`,
and `nec98/kernel/int29dc.c` defines the NEC98 console/interrupt-related C
entry points `int29_main` and `intdc_main`. The assembly console and keyboard
support expose `nec98_fetch_key_table` and
`NEC98_PROGRAMMABLE_KEY_TABLE_FAR`, with constants in `nec98cfg.inc`.
Source fact: fdkernel commit `6523acdb87f4665e6068ea331859885267242005`, paths
`kernel/kernel.asm`, `nec98/kernel/int29dc.c`,
`nec98/kernel/conkey60.asm`, and `nec98/kernel/nec98cfg.inc`.

The DOS-level device, block-I/O, FAT, memory-manager, process, and NLS
interfaces are candidates for extraction or reuse. Direct ports, interrupt
vectors, segment constants, keyboard tables, and early console paths require
an explicit VA interface. The scanner's `OBSERVATION` entries locate these
surfaces; they do not prove a complete call graph.

## FreeCOM runtime

FreeCOM's `config.std` maps `NEC98` and `IBMPC` to target defines and maps
`DBCS` to `DBCS` plus `JAPANESE`. `shell/command.c` is the command runtime;
`lib/lowexec.asm` and `lib/nls.c` are low-level execution and NLS-related
surfaces. Source fact: FreeCOM commit
`855281a3114b43ad4b8d9a320f2aca39be046bba`, paths
`config.std`, `shell/command.c`, `lib/lowexec.asm`, and `lib/nls.c`.

The command parser and DOS API-facing structure are potential shared code.
Process loading, low-level execution, console input/output, and target build
defines remain integration boundaries. This source does not establish that
`COMMAND.COM`, or the NEC98 build of it, executes on a VA.

## Country and NLS

Country has a small make graph: target `country.sys` assembles `country.asm`
and `production` copies it to the component binary directory. The assembly
contains the Country format and entry data, case and filename tables, collating
tables, and DBCS table data in the documented `.data1` through `.data7`
sections. Source fact: Country commit
`23f189cca3420606eae8723884fa92ccd65eb307`, paths `Makefile` and
`country.asm`, target `country.sys`, sections `.data1` through `.data7`, and
the `COUNTRY_DBCS` data.

The table format and DOS NLS service boundary are candidates for reuse. The
availability and semantics of a VA Japanese runtime, firmware code page,
keyboard encoding, and filename behavior are unknown and are not inferred
from this artifact.

## Classification of assumptions

* Reusable structure: build graph shape, DOS service boundaries, FAT
  algorithms, process/file abstractions, and data-table interfaces. These are
  `SOURCE_FACT` observations of structure plus an `INFERENCE` for reuse.
* NEC98-specific behavior: the NEC98 boot layout, FDC/controller operations,
  platform assembly, keyboard table, interrupt and BIOS paths. These are
  `SOURCE_FACT` locations and `OBSERVATION` scanner hits, not VA facts.
* IBM-PC assumptions: shared code and the IBM-PC build branch retain BIOS/INT
  13h and related conventional paths where the source selects them. This is a
  source-level observation, not a promise that either IBM-PC or NEC98 paths
  apply to VA.
* Japanese/DBCS behavior: Country tables and FreeCOM's DBCS/Japanese build
  switches are separable from hardware services. The runtime matrix begins in
  M06.
* VA unknowns: IPL layout, load/entry state, disk geometry and services, FDC,
  DMA, interrupts, early console, and timing. These remain `UNKNOWN` in the
  M04 blocker ledger until a registered VA source supplies accepted evidence.
