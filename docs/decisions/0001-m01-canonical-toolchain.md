# Decision 0001: M01 canonical toolchain

M01 uses the stable final Open Watcom 1.9 release as the common required
compiler for the kernel and FreeCOM. The archived official package is locked
by release metadata, byte size, publisher MD5, SHA-256, and tool identities;
no V2 beta snapshot is active in the M01 contract.

Linux/amd64 in a pinned Ubuntu container is canonical. Open Watcom 1.9 uses
i386 Linux host tools, so Apple Silicon uses a separately selected full
x86_64 QEMU Colima profile as a non-canonical host adapter. Container-local
Linux storage is required so macOS filesystem semantics and bind mounts do not
affect the baseline. An ARM64 daemon is not used for this final 1.9 attempt.

UPX is disabled for required M01 artifacts to remove compressor-version
effects. The observed GCC-IA16 cross-build paths are deferred to a later
matrix and are not evidence for the required Open Watcom build. Containers are
appropriate because the legacy toolchain is otherwise difficult to reproduce
across macOS/Linux hosts. If a real fdkernel or FreeCOM build fails after the
1.9 probes, this Open Watcom path is abandoned; no further Open Watcom
version, flag, source, or shim retry is permitted by M01.
