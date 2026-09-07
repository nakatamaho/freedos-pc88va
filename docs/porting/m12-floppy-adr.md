# M12 resident read-only floppy path

M12 keeps the accepted M08 parameterized `pc88va_disk_read_core` as the only
range, capacity, geometry, retry and partial-completion state machine. The
new `pc88va_kernel_disk_read` entry is linked in the kernel carrier and is
called after the normal M10 initialization and M11 input diagnostic. Its
request record and 4 KiB destination are resident kernel-owned storage, so
the service does not depend on loader scratch or the loader stack.

The callback is the accepted M08 firmware read route. It receives the core's
validated CHS and destination and returns success only with the declared
sector byte count. It cannot issue a write or format operation. The drive
context and incoming call flags are captured opaquely at kernel entry; no
ROM bytes, disk filenames or expected fixture data are embedded in the
driver. The M12 qualification caller is selected by a private test control
and is not a DOS request-packet interface.

The public profile is one 1024-byte logical sector, eight sectors per track,
two heads, and 1280 sectors. Requests are bounded to 4096 bytes and three
retries. Zero count, invalid ranges, capacity overflow, unsafe segmented
addresses, short transfers and retry exhaustion fail closed while preserving
the honest completed byte count. Existing completed sectors remain valid;
the sector in a failing transfer is not reported as complete.

This is a kernel-resident block primitive, not proof of INT 21h, FAT handles,
memory allocation, PSP/EXEC, console devices, COMMAND.COM or a complete DOS
core. Those interfaces are inventoried for M13 and are deliberately not
implemented here.
