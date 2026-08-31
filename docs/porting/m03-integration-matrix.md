# M03 Platform Integration Boundary Matrix

`pc88va` below is a proposed platform name only. M03 creates no such source
directory or build target. The IBM-PC and NEC98 columns describe current
source structure at the pinned commits; the VA column is a boundary decision
or an unresolved question, not an implementation claim.

| surface | IBMPC current | NEC98 current | proposed pc88va boundary | dependency | disposition | evidence / citation | blocker | contract candidates | implementation candidates |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| build | IBM-PC compiler/configuration path | `nec98/makefile` and NEC98 assembly dependencies | independent platform selection and target | WMake, compiler defines, object graph | adapt | `SOURCE_FACT`, fdkernel `6523acdb87f4665e6068ea331859885267242005`, `nec98/makefile`, `nec98/kernel/makefile.wc` | target naming and exact source set | — | M06; M05 only for explicit image-layout evidence |
| boot | shared boot/FAT shape with IBM-PC conditions | `nec98/boot/boot.asm`, `NEC98FDD`/`NEC98HDD` paths | separate VA IPL and boot contract | load state, BPB, firmware/FDC | replace | `SOURCE_FACT`, fdkernel `6523acdb87f4665e6068ea331859885267242005`, `nec98/boot/boot.asm`, `real_start` | all M04 boot questions | M04 | qualified M05 image layout, M07 IPL entry, M08 loader transfer |
| disk | BIOS/block-I/O assumptions in shared code | NEC98 floppy/controller and physical-sector branches | explicit block-I/O adapter | BIOS or direct controller, media change | adapt | `SOURCE_FACT`, fdkernel `6523acdb87f4665e6068ea331859885267242005`, `nec98/drivers/floppy.asm` | disk-service and geometry contract | M04 | qualified M08 loader, M12 read, M14 write/change; M18 only explicit HDD |
| dma | shared abstractions plus hardware-dependent paths | FDC/DMA signals in NEC98 driver | explicit DMA/FDC interface if required | DMA channels, controller protocol | investigate | `OBSERVATION`, scanner rules `DMA-FDC-SIGNAL` and `ASM-IO-OPERATION` | VA FDC/DMA/IRQ facts | M04 | qualified M12/M14 |
| console_output | shared console API with low-level branches | NEC98 INT/console assembly and `int29` path | early diagnostic interface, then console driver | firmware, video, character path | adapt | `SOURCE_FACT`, fdkernel `6523acdb87f4665e6068ea331859885267242005`, `nec98/kernel/int29dc.c` | pre-kernel diagnostic route | M04 only for identified early firmware route | M09; M16 for Japanese output |
| console_input | DOS console/input abstractions | NEC98 keyboard table and input assembly | explicit keyboard/input adapter | keyboard protocol and encoding | adapt | `SOURCE_FACT`, fdkernel `6523acdb87f4665e6068ea331859885267242005`, `nec98/kernel/conkey60.asm` | VA keyboard contract | — | M11; M17 for Japanese input/filenames |
| timer_clock | shared timer services with platform startup assumptions | NEC98 `sysclk`/interrupt-related object path | timer and clock interface | timer source, rate, vector ownership | replace | `OBSERVATION`, scanner `TIMER-CLOCK-SIGNAL` | VA timer/IRQ contract | M04 only for identified entry-state fact | M10; M15 only for writable clock behavior |
| interrupts | IBM-PC vector/PIC conventions remain in shared paths | NEC98 vector and firmware conditions | explicit vector/exception ownership | PIC, vectors, entry ABI | replace | `OBSERVATION`, scanner `INTERRUPT-VECTOR-SIGNAL` | initial vector map | M04 for boot-entry state | M10 |
| memory | DOS segments, stack, and startup model | NEC98 loader/kernel segment constants | explicit load, segment, stack contract | memory map and entry registers | investigate | `SOURCE_FACT`, fdkernel `6523acdb87f4665e6068ea331859885267242005`, `nec98/boot/boot.asm`, `kernel/kernel.asm` | IPL/kernel load state | M04 for boot/load state | M06 compile/startup, M08 handoff, M10 runtime |
| firmware | IBM-PC BIOS paths are selected where shared code uses them | NEC98 BIOS/controller paths and INT references | documented firmware boundary or replacement | BIOS calls, ports, firmware ownership | investigate | `OBSERVATION`, scanner `FIRMWARE-BIOS-SIGNAL` | VA firmware source | M04 | only the specifically coupled subsystem |
| nls_dbcs | shared NLS code and optional DBCS build | NEC98 build plus Country/DBCS data | platform-neutral NLS with explicit keyboard/file policy | codepage, DBCS, filename rules | reuse | `SOURCE_FACT`, FreeCOM `855281a3114b43ad4b8d9a320f2aca39be046bba` `config.std`, Country `23f189cca3420606eae8723884fa92ccd65eb307` `country.asm` | VA Japanese/runtime policy | — | M06 build matrix, M16 output/NLS, M17 input/filenames |
| device_init | DOS device initialization abstractions | NEC98 device and startup-specific paths | explicit device initialization boundary | device names and order | adapt | `OBSERVATION`, scanner `DEVICE-INIT-SIGNAL` | device contract | M04 when storage contract is implicated | M09/M10/M11/M12/M14 by subsystem |
| exec_runtime | FreeCOM command and low-level exec path | target defines can alter runtime assembly | shared command/runtime interface with VA-specific low-level hooks | loader, console, DOS API | reuse | `SOURCE_FACT`, FreeCOM `855281a3114b43ad4b8d9a320f2aca39be046bba`, `shell/command.c`, `lib/lowexec.asm` | reach-command-prompt proof | — | M13 read-only, M15 writable, M16/M17 Japanese behavior |

## Boundary rules

1. Platform-neutral DOS code is selected through explicit interfaces and build
   inputs. A VA implementation must not inherit NEC98 hardware behavior merely
   because it shares an 8086-class CPU model.
2. Hardware-facing services are isolated behind small interfaces before broad
   call-site conversion. The exact interface shape is a later implementation
   decision, not an M03 source change.
3. The scanner records `OBSERVATION`; prose conclusions identify when they are
   `INFERENCE` and cite their source facts. Absence of a hit is not proof of
   absence.
4. M04 owns boot/media facts, M05 owns host image construction, M06 owns the
   first compile target and DBCS build matrix, and later milestones consume
   observations according to the qualified routes above.
5. Milestone arrays are overlapping candidates. They are not exclusive work
   owners, issue counts, effort estimates, or completion percentages.
