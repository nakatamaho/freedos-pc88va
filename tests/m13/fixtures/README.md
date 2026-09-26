# M13 public guest probes

These sources are independent DOS programs, not host transcript markers. The
COM probe uses the inherited command tail, opens and reads `COMDATA.TXT`,
writes the bytes through handle 1, and exits with status `11h`. The MZ probe
contains data/stack references that require a genuine relocation entry, uses
INT 21h for output, and exits with status `13h`. The build harness assembles
them with the pinned Open Watcom/NASM toolchain and checks the MZ relocation
table before placing them in the generated fixture.
