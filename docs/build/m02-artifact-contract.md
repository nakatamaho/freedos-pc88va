# M02 baseline artifact contract

M02 packages the verified M01 NEC98 baseline as a deterministic reference
bundle. It does not create a PC-88VA runtime. The bundle metadata declares
`platform` as `nec98-baseline`, `purpose` as `build-reference-only`, and
`pc88va_bootable`, `hardware_validated`, and `vaeg_validated` as `false`.

## Inputs and authority

`make m02-preflight` first runs the existing offline M01 verifier. The
committed files `manifests/components.lock.json`,
`manifests/toolchains.lock.json`, `manifests/m01-build-contract.json`, and
`qa/golden/m01-baseline.json` must have the accepted M01 snapshot digests.
The M01 golden manifest is the sole authority for individual artifact sizes,
SHA-256 values, and source-archive SHA-256 values. M02 does not duplicate
those values in source, documentation, or configuration.

The four kernel-produced files, four boot files, FreeCOM command processor,
and standalone COUNTRY.SYS are copied from the real paths recorded by the M01
contract and golden manifest. Symlinks, hard-linked inputs, special files,
missing files, unexpected files, path traversal, and stale M01 manifests are
rejected before copying.

## Namespaces and roles

| Logical role | Bundle namespace | Bundle path |
| --- | --- | --- |
| `kernel` | `fdkernel` | `payload/fdkernel/KERNEL.SYS` |
| `kernel-alias` | `fdkernel` | `payload/fdkernel/KWC8616.SYS` |
| `system-transfer-tool` | `fdkernel` | `payload/fdkernel/SYS.COM` |
| `kernel-country-driver` | `fdkernel` | `payload/fdkernel/COUNTRY.SYS` |
| `boot-fat12` | `fdkernel` | `payload/fdkernel/boot/B_FAT12.BIN` |
| `boot-fat12-fallback` | `fdkernel` | `payload/fdkernel/boot/B_FAT12F.BIN` |
| `boot-fat16` | `fdkernel` | `payload/fdkernel/boot/B_FAT16.BIN` |
| `boot-fat32` | `fdkernel` | `payload/fdkernel/boot/B_FAT32.BIN` |
| `command-interpreter` | `freecom` | `payload/freecom/COMMAND.COM` |
| `standalone-country-driver` | `fdos-country` | `payload/fdos-country/COUNTRY.SYS` |

The two `COUNTRY.SYS` files remain distinct. A future consumer selects by
logical role and namespace, never by basename alone. M02 does not select
either country driver as the VA runtime driver. The four boot binaries are
NEC98 baseline evidence, not VA IPLs.

## Canonical JSON and tar

Generated JSON is UTF-8 without BOM, sorted by object key, two-space indented,
deterministically array-ordered, and terminated by exactly one newline. It
contains no floating-point values, wall-clock timestamps, absolute paths, or
host/container identity. The four committed M01 evidence files are copied
byte-for-byte and treated as opaque evidence; they are not reformatted.

The archive is an uncompressed USTAR archive created by the repository-owned
Python standard-library implementation. Entries are sorted by canonical path,
have empty owner names, UID/GID zero, regular-file mode `0644`, and directory
mode `0755`. M01 records a source epoch per component. Payload entries retain
their producer's committed M01 epoch. Directories and metadata use the
deterministic minimum of the three committed component epochs; that derived
rule is recorded in `artifact-manifest.json` and `provenance.json`. If the
component epoch set is incomplete, duplicated, or invalid, assembly fails
closed.

The tar sidecar is the canonical ASCII line containing the archive SHA-256,
two spaces, the archive basename, and one final newline. Payload bytes are
never normalized, patched, timestamped, or recompressed.

## Commands and golden enrollment

The ordinary sequence is:

```sh
make m02-preflight
make m02-clean
make m02-bundle
make m02-compare
make m02-verify
```

For the first implementation only, run `make m02-enroll-golden` after
`make m02-compare` passes, then clean and repeat the sequence. Enrollment is
separate and refuses to overwrite an existing golden. Ordinary verification
never rewrites it. Generated payloads, archives, sidecars, and comparison
evidence remain ignored under `qa/results/m02/`; only the canonical M02 golden
metadata is committed.

M02 host code supports macOS and Linux using Python standard-library file,
JSON, hashing, and tar APIs. VAEG, PC-88VA hardware, VA bootability, disk
geometry, and root-license selection are outside this milestone.
