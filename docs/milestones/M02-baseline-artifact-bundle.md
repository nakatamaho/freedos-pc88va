# M02 — Baseline Artifact Bundle

## Scope

M02 converts the accepted, reproducible M01 NEC98 baseline outputs into a
namespaced artifact contract. It is packaging and provenance work only. No
PC-88VA kernel, IPL, disk image, HAL, driver, emulator, or hardware work is
included.

## Required evidence

The parent and all component worktrees must remain clean at the accepted M01
identity. The existing M01 verifier must pass before any payload is copied.
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

M01 binaries retain their NEC98 baseline identity. They are not PC-88VA
binaries and no VA bootability or runtime claim is made. Real hardware and
VAEG are not required for M02 and remain unrun. Root license selection remains
deferred.
