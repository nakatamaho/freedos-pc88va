# M11 early console input mechanism

Status: qualified direct-poll implementation; final publication and handoff
remain pending. See [the report](m11-report.md). Private runtime qualification
is retained separately; public tests and emulator evidence are not hardware
validation.

## Mechanism and provenance

Use read-only keyboard-matrix polling with the inherited M10 interrupt policy.
The driver calls no firmware, writes no controller, and leaves existing
firmware queues and IVT entries untouched. This avoids adopting a broader
firmware execution environment merely to obtain early input.

The exact public source authority is the M11 VAEG descendant
`7dd453cbd36014ba453a26765b00cd0cc9a99655` (from accepted
`7463f9501d84701f50f3243d5067b6a9dfd0c2e7`):

- [io/serial.c](https://github.com/nakatamaho/vaeg/blob/7dd453cbd36014ba453a26765b00cd0cc9a99655/io/serial.c):
  `keyboard_bind` installs read-only matrix ports 0 through 14;
  `keyboardva_i000` returns existing matrix state without clearing it;
  `scantomap` and `updatekeymap` define active-low coordinates, physical Shift,
  Return/Space aliases, and unsupported modifier/mode positions.
- [sdl2/kbdpaste.c](https://github.com/nakatamaho/vaeg/blob/7dd453cbd36014ba453a26765b00cd0cc9a99655/sdl2/kbdpaste.c):
  `map_ascii` defines the public printable ASCII/Shift correspondence used by
  the independently written lookup table. No firmware table is copied.
- [sdl2/kbdinject.c](https://github.com/nakatamaho/vaeg/blob/7dd453cbd36014ba453a26765b00cd0cc9a99655/sdl2/kbdinject.c):
  normal make/break events pass through `keystat_senddata` and `keyboard_send`.
  Runtime tests use this boundary, not decoded-byte or register injection.

Public VA demos also demonstrate `INT 82h` AH=0Ah (CF indicates empty) and
AH=09h (consume). That smaller firmware adapter was tested as an unqualified
candidate, but its private ownership gate did not pass. Its exploratory
evidence remains retained; no exception or masked projection accepts it.
The selected matrix adapter independently passed all runtime gates.
Neither the source mapping nor emulator observation establishes hardware
validation or complete keyboard compatibility.

## Version-one early ABI

Keep the M06 near Watcom C signature:
`int pc88va_console_getc(unsigned short *character)`.
AX contains the near pointer on entry and the signed 16-bit status on return.
The pointer must designate `pc88va_m11_character` in DS=CS, following the
accepted M10 exported-record ownership restriction. M10 must be ready;
IF, DF and TF must be clear. Non-reentrant, single-threaded polling only.

| AX | Meaning | Output word |
| --- | --- | --- |
| 0 | One supported new make edge | Zero-extended ASCII byte |
| 1 | No new non-modifier input, or first-call baseline adoption | Unchanged |
| 2 | Unsupported key/mode or ambiguous simultaneous make edges | Unchanged |
| 65535 | Invalid pointer, segment, readiness or entry FLAGS | Unchanged; no I/O |

BX, CX, DX, SI, DI, BP, DS, ES, SS, SP and architectural FLAGS are preserved.
The wrapper saves 18 bytes, in addition to the caller's two-byte near return
address; it has no nested calls or interrupt frames. The accepted M10 stack
ownership and guard remain mandatory. FLAGS comparison uses the existing
uPD9002 architectural pushf/popf materialization contract, retaining raw flags
in private evidence rather than silently discarding a meaningful difference.

## State and limited key policy

Each poll reads exactly fifteen bytes into owned snapshot storage. The first
poll adopts held keys without returning them. Later polls compare the old and
new active-low matrices. Releases update the baseline; they never return a
character. A held key does not repeat. A distinct release followed by a new
press returns the same character again when both transitions are observed.

There is no queue, buffering or typematic implementation. Two non-modifier
make edges in one snapshot return status 2 and adopt that snapshot; neither is
returned later as a stale success. Press and release entirely between polls
cannot be recovered. These are explicit single-key polling limits, not queue
overflow behavior. Actual qualification schedules each transition across
multiple guest frames and proves intervening polls.

Support printable ASCII, Space, Enter as CR, and Backspace as byte 8. Physical
left/right Shift selects uppercase and punctuation. Derived Return, Shift and
INSDEL aliases are not counted as additional presses. Unsupported control,
mode, Kana, Caps, conversion and extended-key combinations are rejected;
Shift+0 has no character mapping. They cannot turn into a successful NUL.
No Japanese/NLS, ANSI, function-key expansion or full keyboard coverage is
claimed. The driver never echoes. Its qualification caller alone echoes
printable input and CR/LF through unchanged M09 output, and does not implement
Backspace editing.

## Qualification boundaries

The finite polling loop must pass ROM-free instruction, ownership, all-printable
mapping, unsupported/ambiguous input, release/repeated-press, modifier,
no-input, and invalid-state tests. Runtime qualification must additionally
establish K0-K9 and N0-N4 in two clean pairs, unchanged M08-M10 services,
no post-entry disk commands/transfers/rearm/reset, production memory,
actual normal device reads, ABI preservation and exact input preservation.
No interrupt is installed or suppressed by this driver; existing device
delivery continues and M10's inherited CPU IF policy is preserved.
