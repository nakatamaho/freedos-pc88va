# FreeDOS PC-88VA Integration

This is an experimental FreeDOS integration project for NEC PC-88VA. M15 is
owner-accepted with the deferred work listed in its
[acceptance report](docs/porting/m15-report.md).

For a complete build from public source and configuration, see
[M15 build from source](docs/porting/m15-source-build.md):

```sh
make m01-image   # Prepare the pinned toolchain once.
make m15-image
```

This produces `build/m15-image/media.d88` without an old candidate D88 or
saved DOS binaries. Initialize the pinned submodules first as shown below.

Kernel-only is not a complete distribution. The three foundational components
are:

- `components/fdkernel`: the `nakatamaho/fdkernel` fork with PC-88VA adapters.
- `components/freecom`: the `nakatamaho/freecom_dbcs2` command processor fork.
- `components/country`: the read-only upstream NLS/DBCS data component,
  `FDOS/country:master`.

The parent gitlinks pin the exact M15 component commits. The M01 manifests
retain their historical baseline identities. The kernel and FreeCOM forks
are experimental; branch names do not imply PC-88VA boot success.

Clone the repository with its components:

```sh
git clone --branch topic/m15-dos-api-writable-session --recurse-submodules https://github.com/nakatamaho/freedos-pc88va.git
```

For an existing clone, initialize the components with:

```sh
git submodule update --init --recursive
```

The host scaffold check is:

```sh
make verify-scaffold
```

M01 uses a pinned Linux/amd64 container and does not modify the component
sources. Its host checks are:

```sh
make m01-preflight
make m01-image
make m01-build
make m01-compare
make m01-verify
```

M01 proves only that the exact pinned upstream baselines build reproducibly in
the canonical host environment. It does not prove PC-88VA compatibility or a
successful boot.

VAEG and private documentation are sibling checkouts and are not included in
this repository. A possible workspace layout is:

```text
work/
├── freedos-pc88va/          public writable integration repository
├── vaeg/                    separate emulator checkout
└── pc88va-private-docs/     non-public local material
```

Project status must not be read as evidence of a successful PC-88VA boot.
