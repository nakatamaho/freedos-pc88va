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
M00 permits scaffold and provenance work only; source changes, builds, image
creation, emulator tests, and hardware tests are prohibited.
