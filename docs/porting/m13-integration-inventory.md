# M13 integration inventory (source-backed)

This inventory records the checked source and link state at M13 Phase A. It is
an implementation map, not an acceptance claim. The starting parent is
`66138e6539e4220ae7b6d3ffee24581e0d674267` and the starting fdkernel gitlink is
`21d9f3450276d42e5fedd1ddb9e80485b888cc07`.

## Current target and required transition

`components/fdkernel/pc88va/makefile.wc` currently links only
`startup.obj`, `loader_services.obj`, `console.obj`, `machine_services.obj`,
`console_input.obj`, `resident_disk.obj`, and `platform.lib`. Its
`config/link.rsp` has the same seven inputs. `kernel/startup.asm` enters the
M10/M11/M12 diagnostics and then executes the local fatal-stop loop; it does
not call `FreeDOSmain`, install DOS vectors, or transfer control to FreeCOM.
The target explicitly rejects `NEC98` and `IBMPC` and no source below either
platform directory is a link input.

The M13 transition must add the existing common FreeDOS objects through a
PC-88VA adapter boundary. It must not add a second FAT, allocator, request
dispatcher, or command interpreter. The production path must retain the M12
resident callback and its ownership rules while making it reachable from the
common DOS block layer.

## Source-backed matrix

| Area | Current source/link finding | M13 connection and proof required |
| --- | --- | --- |
| Kernel startup | `pc88va/kernel/startup.asm` is the only target entry and stops after M12 diagnostics. The common `kernel/main.c` entry is `FreeDOSmain`; common startup/interrupt objects are `kernel/kernel.asm`, `entry.asm`, `io.asm`, `intr.asm`, `irqstack.asm`, `procsupt.asm` and `execrh.asm`. None is linked by the PC-88VA carrier. | Add a PC-88VA startup that establishes the common kernel data/stack contract and calls the real `FreeDOSmain`, with a map showing every common-core object and a target-side initialization probe. |
| Resident storage | `pc88va/kernel/resident_disk.asm` exposes the M12 kernel-owned request and 4 KiB buffer, calls the M08 `pc88va_disk_read_core`, and receives the firmware callback/context through the resident entry. `loader_services.asm` and `boot/disk_read.inc` contain the callback ABI. | Keep request, callback state, stack and scratch resident for all DOS reads. Show intervals and lifetime in the M13 contract; chunk larger file reads and never give the M12 scratch buffer to a process. |
| Block device | Common `kernel/dsk.c` calls `fl_read`, `fl_write`, `fl_reset`, `fl_diskchanged` and `fl_readkey`. `kernel/blockio.c` consumes request packets and device headers; `hdr/device.h`, `hdr/dcb.h`, `hdr/fat.h` define the DOS block/DPB types. The generic `drivers/floppy.asm` uses IBM BIOS INT 13h and is not a PC-88VA adapter. | Provide PC-88VA implementations of the block entry points that translate drive/CHS/count/status to the M12 resident service. Writes must return a documented DOS error before any media operation. |
| Filesystem | Common `kernel/initdisk.c`, `dsk.c`, `blockio.c`, `fatdir.c`, `fatfs.c`, `fattab.c` and `fcbfns.c` implement BPB/DPB setup, FAT12 traversal, directories and FCB/file operations. `kernel/inthndlr.c` contains the INT 21h open/read/seek/close/DTA cases. These objects are absent from the PC-88VA link. | Link the existing FAT12 and handle implementation through the PC-88VA block adapter. Verify multi-cluster/EOF/DTA and an alternate layout through actual target calls; no fixture LBA or host extraction may enter the kernel. |
| Memory/process | Common `kernel/memmgr.c` owns MCB allocation; `kernel/task.c` owns process/task state; `kernel/dyninit.c` describes the initial PSP; `kernel/entry.asm`, `procsupt.asm` and `execrh.asm` preserve parent state and termination. No allocator, PSP or EXEC object is currently linked. | Reserve kernel/M12 areas before creating MCBs. Prove PSP/environment/handle ownership, child cleanup and resident callback reachability after EXEC. |
| Interrupt/API | Common `kernel/entry.asm` and `intr.asm` provide INT 21h entry/return glue; `kernel/inthndlr.c` dispatches services and maintains DTA/error state. `kernel/main.c` calls `setup_int_vectors` during `FreeDOSmain`. No DOS vector is installed by the current PC-88VA entry. | Install only the common DOS vectors required by the read-only session, preserving firmware ownership for the M12 adapter and keyboard path. Record stack/segment and restoration rules, then probe general INT 21h calls. |
| Console | M09/M11 raw services are `pc88va/kernel/console.asm` and `console_input.asm`; they are currently diagnostic-only link inputs. Common `kernel/console.asm`, `chario.c` and `inthndlr.c` provide DOS CON requests, status, read and write, but are not linked. | Adapt common CON requests to M09/M11 output/getc without turning raw getc into a shell. Reuse common ASCII line editing for Enter/Backspace and prove output, input, and handle semantics. |
| EXEC | Common `kernel/inthndlr.c` dispatches `DosExec`; `kernel/procsupt.asm` enters a child and restores the parent; `kernel/execrh.asm`, `kernel/entry.asm`, `kernel/memmgr.c` and `kernel/task.c` implement load, relocation, PSP and termination. The current M08 MZ transform is a loader-only KERNEL.SYS operation and is not an application EXEC path. | Use common DOS EXEC for an independently built COM and a genuine relocated MZ EXE. Verify relocation, arguments, return codes and repeated parent resource integrity. |
| FreeCOM | `components/freecom` contains the actual `command.c`, `cmd/dir.c`, `cmd/type.c`, `lib/exec.c` and `lowexec.asm` sources and its documented build variants. The PC-88VA target has no shell image or shell startup path. | Build/select a documented ASCII FreeCOM variant without changing parser or EXEC semantics, place the resulting COMMAND.COM on the generated FAT image, and start it through DOS file/EXEC services. |

## M12 callback and buffer lifetime

The M12 source keeps its request record and 4 KiB destination in the resident
kernel data area. The firmware callback is invoked by the M08 read core from
the M12 resident entry; it is not a loader scratch callback and is not copied
into application memory. The current target has no DOS caller, so reads larger
than 4 KiB are not yet chunked. M13 must implement bounded chunk/copy logic in
the DOS block adapter and demonstrate that a process allocation cannot overlap
the callback, request record, destination, or active stack.

## Phase-A conclusion

The prerequisite identities and existing M12 records are verified separately.
The missing common-core wiring is an in-scope B-D implementation task, not a
reason to claim a shell or DOS session today. The first implementation change
is therefore the PC-88VA common-core adapter and link map, followed by focused
build/link and target-side probes before adding the filesystem and shell
session evidence.
