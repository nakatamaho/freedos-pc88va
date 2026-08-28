# Agent Rules

This repository integrates and pins components; component source remains in
its component repository. If component source must change, work in that
component's own repository and branch, commit there, and then update the
parent gitlink. Never vendor a submodule file as a copy in the parent.

The `origin` remote for the kernel and FreeCOM components is the
`nakatamaho` fork. Their `upstream` remote is the corresponding `lpproj`
repository. Do not push directly to an upstream branch. Preserve provenance
and exact source SHAs in the parent metadata.

Do not commit private artifacts or facts derived from private artifacts. Do not
change the separate VAEG checkout. PC-98 behavior is a structural precedent,
not PC-88VA evidence.

Use these evidence labels precisely: `HOST PASS`, `VAEG PASS`, `HARDWARE PASS`,
and `DEFERRED HARDWARE VALIDATION`. Real hardware is optional and non-blocking,
but only an actual hardware result can receive `HARDWARE PASS`.

Do not commit generated files, build products, images, or logs. Use English for
code, comments, and file names. Fail closed: an unrun test is not a success.
M00 permits scaffold and provenance work only. M01 permits the parent
repository build harness and reproducibility evidence for pinned component
exports. The approved M01F exception is one fdkernel child commit that changes
only WMake conditional syntax; it must not add PC-88VA source changes,
packages, images, emulator tests, or hardware tests.

M01 builds must run in the pinned Linux/amd64 container, never in a component
submodule or a host bind-mounted source tree. The kernel, FreeCOM, and
COUNTRY.SYS sources are exported with deterministic git archives. The two
kernel/FreeCOM fork remotes remain `origin=https://github.com/nakatamaho/...`
and `upstream=https://github.com/lpproj/...`; component source changes belong
in the component repository and branch before the parent gitlink is updated.
The parent must preserve exact component, source-archive, contract, and
toolchain identities.

The canonical Open Watcom binaries used by M01 are the official final 1.9
Linux i386 tools in `/opt/openwatcom-1.9/binl`, executed inside the pinned
Linux/amd64 container. They are not run directly on macOS. On Apple Silicon,
the complete x86_64 QEMU Colima profile is only a host adapter: the actual
container must report `x86_64` and `amd64`, while daemon and adapter details
remain diagnostic evidence.

M01 required builds disable UPX. Do not commit toolchain archives, generated
binaries, results, logs, ROMs, BIOS files, disk images, private artifacts, or
private-derived facts. Do not report skipped VAEG or hardware work as a pass.
The exact evidence labels remain `HOST PASS`, `VAEG PASS`, `HARDWARE PASS`, and
`DEFERRED HARDWARE VALIDATION`; M01 can use only `HOST PASS` after its local
gates and native x64 GitHub Actions gate pass. VAEG and hardware are `NOT RUN`.
