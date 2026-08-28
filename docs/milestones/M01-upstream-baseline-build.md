# M01: upstream baseline buildability

## Purpose

M01 establishes a trustworthy host-side build baseline for the three exact
parent-pinned component commits. It proves only buildability and byte
reproducibility in the canonical Linux/amd64 environment. It does not claim a
bootable system or PC-88VA compatibility.

## Inputs and non-goals

Inputs are the three pinned component gitlinks, including the approved M01F
fdkernel build-system repair and the generic FreeCOM reproducible-build child
commit, deterministic source archives, the locked Ubuntu snapshot, and the
dated official Open Watcom release. The M01F child changes only WMake
conditional syntax, while the FreeCOM child adds opt-in timestamp macros; no
PC-88VA source change is made.

M01 does not select userland packages, add PC-88VA code, create disk images,
run VAEG, run another emulator, or use real hardware. Hardware is optional and
not applicable to this host milestone. VAEG is `NOT RUN`; hardware is
`NOT RUN`.

## Commands and artifact contract

The harness runs the following in fresh exports and separate no-network,
no-mount containers:

```sh
cp /input/fdkernel-nec98.mak config.mak
env -u XUPX -u UPXOPT make clobber COMPILER=owlinux
env -u XUPX -u UPXOPT make all COMPILER=owlinux
./build.sh -r dbcs nec98 watcom japanese
make clean all
python3 ./ci_validate.py
```

The fdkernel template is copied only inside each disposable source export.
The prior `make all COMPILER=owlinux XUPX=` attempt is a rejected M01
invocation: its empty command-line variable remained defined under GNU Make
and caused the nested post-link command to expand to `sys.com`. The resulting
status 2 was a build-contract error, not a compiler or linker failure.
The current required fdkernel binaries come from child commit
`29085311a47c8fcceb7902b64b0b5ebc170b8de5`, whose base is
`c9ce245e0447003645adce47bd34960ae276d4bd`; the parent performs no source
patch during export.

The required artifacts and namespaces are declared in
`manifests/m01-build-contract.json`. Both COUNTRY.SYS producers are retained
under different names. `qa/golden/m01-baseline.json` contains only metadata,
sizes, hashes, and deterministic identities; binaries remain ignored.

FreeCOM uses Route B after the bounded Route A probe showed Open Watcom 1.9
E1100 failures for direct redefinition of predefined date/time macros. The
parent supplies the UTC date `Feb 22 2025` and time `14:17:52` through the
generated `CFLAGS2` response-file line before `shell/ver.c` is compiled. The
entrypoint verifies `ver.obj`, `command.exe`, and `command.com` contain only
that canonical stamp and that the live wall-clock stamp is absent.

## QA gates and evidence labels

The gates are: exact gitlinks, clean component worktrees, locked image and
toolchain, two fresh source exports, successful required commands, complete
artifact inventories, byte-identical run 1/run 2 output, offline verification,
and a successful native x64 `ubuntu-22.04` GitHub Actions rebuild matching the
golden manifest. The only M01 success label is `HOST PASS`, and it is allowed
only after every gate including native x64 CI passes. `VAEG PASS` and
`HARDWARE PASS` are not applicable. `DEFERRED HARDWARE VALIDATION` is not a
substitute for this host gate.

## Limitations and failure semantics

The legacy tools may not honor `SOURCE_DATE_EPOCH`; it remains a controlled
input. Text diagnostics are retained only in ignored bounded results. Any
required byte mismatch fails closed with both hashes, sizes, first differing
offset, and bounded ranges. Local ARM-adapter success that differs from native
x64 is `LOCAL HOST BUILD PASS; M01 GATE FAIL — CROSS-HOST REPRODUCIBILITY`.
Queued or running native CI is `M01 PENDING — NATIVE X64 CI`, not a pass.
Stale current component identity in the parent harness is `M01 PARENT
HARNESS FAIL — STALE IDENTITY`; it is a parent validation failure, not a
component build failure.

The local adapter classification is diagnostic evidence only. The current
Colima preflight is recorded as `unknown` when status does not explicitly
declare Rosetta or QEMU, even if the amd64 container executes successfully.
It is excluded from the deterministic contract and golden manifest.

## Completion record

Status: pending until the local two-run gates and the native x64 GitHub Actions
gate complete. No PC-88VA porting work is part of M01.
