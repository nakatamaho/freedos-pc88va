# M09 early console mechanism

Status: accepted after final-artifact two-run qualification and native public CI.

The mechanism is the preserved PC-88VA Text BIOS string-output service, called
with a one-byte NUL-terminated string. No direct text-plane or controller
implementation is added. Two bounded private exploratory runs returned from
this service and produced the project-authored diagnostic in the existing
text display backing, with identical projections. These experiments select
the mechanism; they are not the final C0-C9 qualification.

## Evidence-supported alternatives

| Route | Evidence and decision |
| --- | --- |
| Preserved Text BIOS | Public VAEG documentation specifies INT 83h/AH=02h, DS:SI and DX=8000h. Bounded experiments establish availability after the retained M08 handoff. Selected. |
| Direct text plane | Public VAEG memory and renderer source defines banked text memory and descriptors. It would add mapping, attribute and cursor ownership that the working firmware service already provides. Not implemented. |
| Hybrid | No evidence that two mechanisms are required. Not implemented. |

The public service identity is independently documented at VAEG commit
`7463f9501d84701f50f3243d5067b6a9dfd0c2e7`,
`docs/modernization/openwatcom-build-environment.md`, section
"Building SQEMM98 for PC-88VA". The existing observer is
`sdl2/g75_screen.c:g75_screen_capture_to`; text-cell consumption is
`vram/maketextva.c`. Source locators refer to that exact public commit.
No VAEG implementation is copied into the kernel.

The service vector, function, pointer convention and attribute selector are
PUBLIC_SOURCE facts. Inherited vector target, cursor location, descriptor
state, ownership ranges and observation addresses are PRIVATE_OBSERVATION
fields retained only in the local overlay. Runtime evidence is emulator
evidence, not hardware verification or permission to publish those values.

## Preconditions and ownership

M08 must have completed its MZ transformation and entered the kernel with its
declared stack. The inherited Text BIOS and its display state must remain
valid. A zero vector is rejected. The caller supplies a single ASCII byte in
AX and a valid near-call stack; the wrapper owns only its bounded stack frame.
The firmware owns the display, cursor and scrolling. No M10 machine-init,
keyboard-input, timer, interrupt-controller initialization or new disk/DMA
operation is introduced by the wrapper. The existing BIOS does perform ROM
bank switching and PIC operational reads/writes. Those bindings are public in
`io/memctrlva.c` and `io/pic.c` at the same pinned VAEG commit. The private
dependency audit verifies per-call restoration of ROM bank and interrupt mask,
no PIC initialization command, and no disk, keyboard, clock-query or DMA path.
This is an inherited firmware-state dependency, not a claim of zero device IO.
The diagnostic validates its service precondition before the first putc; each
standalone putc also validates its own vector. Stack headroom and dependencies
were checked in both final-artifact runs; see the qualification report.

Unsupported bytes fail before invoking firmware. A successful return means
the firmware call returned, not an invented hardware-ready result. Guest
display mutation is independently required by C3-C9. The wrapper cannot
recover from a firmware handler that never returns; private trials have an
external deterministic bound and do not turn a timeout into success.

The development control probe independently exercised CR, LF and bottom-row
scrolling in two clean runs. CR retains the row and returns to its first
logical column; LF retains the logical column while advancing the row. At the
bottom, the firmware scrolls the previous row upward and clears the new row.
The exact clearing representation and display layout stay in the local-only
overlay. The renderer raster extent is not used as the logical wrapping width.
These selection experiments did not replace final-artifact C0-C9 qualification.
The final kernel completed C0-C9 twice with equal complete causal projections;
the same final source also passed a fresh two-run bottom-row control test.
The public ABI contract distinguishes return from independent output evidence.
M10 still owns general machine initialization, M11 input,
and M17 Japanese/NLS. No full DOS character-device or shell is implemented.
