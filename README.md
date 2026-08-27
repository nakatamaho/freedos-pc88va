# FreeDOS PC-88VA Integration

This is an experimental FreeDOS integration project for NEC PC-88VA. The
current milestone is the M00 scaffold; no bootable release exists.

Kernel-only is not a complete distribution. The three foundational components
are:

- `components/fdkernel`: the editable experimental PC-88VA kernel fork,
  `nakatamaho/fdkernel:nec88va`.
- `components/freecom`: the editable DBCS/Japanese command processor fork,
  `nakatamaho/freecom_dbcs2:nec88va`.
- `components/country`: the read-only upstream NLS/DBCS data component,
  `FDOS/country:master`.

The parent repository pins exact component commits with gitlinks and
`manifests/components.lock.json`. The kernel and FreeCOM forks are experimental
and their branch names do not imply PC-88VA boot success.

Clone the repository with its components:

```sh
git clone --recurse-submodules https://github.com/nakatamaho/freedos-pc88va.git
```

For an existing clone, initialize the components with:

```sh
git submodule update --init --recursive
```

The host scaffold check is:

```sh
make verify-scaffold
```

VAEG and private documentation are sibling checkouts and are not included in
this repository. A possible workspace layout is:

```text
work/
├── freedos-pc88va/          public writable integration repository
├── vaeg/                    separate emulator checkout
└── pc88va-private-docs/     non-public local material
```

Project status must not be read as evidence of a successful PC-88VA boot.
