# M02 — Baseline Artifact Bundle

## Scope

M02 converts the accepted, reproducible M01R1 NEC98 baseline outputs into a
namespaced artifact contract. It is packaging and provenance work only. No
PC-88VA kernel, IPL, disk image, HAL, driver, emulator, or hardware work is
included.

## Required evidence

The parent and all component worktrees must remain clean at the accepted M01R1
identity. The existing M01 verifier and M01R1 reproducibility regression must
pass before any payload is copied.
Two independently assembled M02 runs must have identical path sets, file
sizes, file SHA-256 values, canonical JSON bytes, USTAR bytes, and sidecar
bytes. Negative tests cover missing, extra, modified, symlinked, unsafe, and
malformed inputs as well as archive attribute failures.

## Status

The M02 implementation is complete only after local preflight, clean assembly,
comparison, explicit initial golden enrollment, clean regeneration, golden
verification, portability and negative tests, and native x86-64 GitHub Actions
success. The workflow uploads bounded metadata and comparison evidence only;
it does not publish a release.

M01R1 binaries retain their NEC98 baseline identity. They are not PC-88VA
binaries and no VA bootability or runtime claim is made. Real hardware and
VAEG are not required for M02 and remain unrun. Root license selection remains
deferred.

## M02R1 supersession

M01R1 replaced an ambient `__DATE__` input and generated FAT-header mtime
drift. Therefore the original M02 tar (399360 bytes,
`feb4a1f8199bcb4dcdc4885d63944ab5eafb146b900ef61042a7094485110762`) and
M02 golden (`76fff7b3602e716e9fb9fdc99d782281913a1d4d60166cbc9f1c0fa0c9e7401f`)
are superseded historical evidence. M02R1 enrolls a new golden only after
fresh M01R1 verification and an identical two-run bundle comparison.
