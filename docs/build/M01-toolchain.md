# M01 canonical toolchain

M01 uses a Linux/amd64 container so the legacy Open Watcom build is independent
of the macOS host. The Ubuntu 22.04 multi-platform index was inspected on
2026-08-27 at digest
`sha256:2edbbc5dc405e9612ba3584ce95480277e3eb374407b5505fe26f17df77c7dbc`.
The exact amd64 manifest used by `FROM` is
`sha256:79676deb51ebb02885b0b9d33788e78a37cf1045ad79d1bb04c6a222c3556b3d`.
The Dockerfile is called with `--platform linux/amd64` and contains no
`FROM --platform` override.

The apt source is the immutable dated snapshot
`https://snapshot.ubuntu.com/ubuntu/20260827T000000Z/`, using the jammy,
jammy-updates, and jammy-security suites with `main` and `universe`. Exact
direct package versions are in `manifests/toolchains.lock.json`, including
NASM, GNU Make, Python, the required C development headers, `python3-iso3166`,
and `python3-phonenumbers`.

The required compiler is the stable final Open Watcom 1.x release, Open Watcom
1.9, GitHub release tag `ow1.9`, release ID `49559960`, and tag commit
`81d626f24e07bdee89300c90ab93717964fbab3a`. The exact official Linux package
is `open-watcom-c-linux-1.9`, asset ID `44807673`, size `83959748`, publisher
MD5 `960fe6b5cf88769a42949f5fedf62827`, and archive SHA-256
`f7484be27eb70028010303fc16bb2acc5a785679567a568b940c28190ddbf3f3`.
It is the official
[GitHub release asset](https://github.com/open-watcom/open-watcom-1.9/releases/tag/ow1.9)
and is also downloaded from the official FTP URL
`https://openwatcom.org/ftp/install/open-watcom-c-linux-1.9`. The two copies
must match size, MD5, SHA-256, and bytes; the first is then deleted by its
exact pathname and only the second is used for the image.

The package is a self-extracting ZIP and is extracted with `unzip`, never
executed, at `/opt/openwatcom-1.9`. M01 uses only its `/opt/openwatcom-1.9/binl`
Linux i386 tools. Each of `wcc`, `wcl`, `wmake`, `wlink`, `wasm`, and `wlib`
is checked as a statically linked ELF Intel 80386 executable with its locked
size, SHA-256, and Version 1.9 banner.

The host image builder downloads the exact official asset once, verifies its
size and SHA-256, deletes that first copy, downloads it again, verifies it
again, and passes only the verified second copy to Docker as a named build
context. The verification method is
`tofu-from-official-github-release` because the release does not publish a
separate checksum file.

Before each component build, the entrypoint records `WATCOM`, `PATH`, POSIX
`command -v` resolved paths, ELF file types, sizes, SHA-256 values, and tool
banners. It runs a valid `wcc -bt=dos` probe and a real WMake makefile probe;
both must exit zero, produce the required evidence, and remain diagnostic
only. It fails unless all six tools resolve under `/opt/openwatcom-1.9/binl`.

The fixed environment is `LC_ALL=C`, `LANG=C`, `TZ=UTC`, and process umask
022. `SOURCE_DATE_EPOCH` is set to the author timestamp of each pinned source
commit. UPX is deliberately excluded from every required build. The image ID
and Docker/Colima host adapter details are runtime diagnostics under ignored
`qa/results/m01/runtime/`; they are not golden-manifest inputs.

Image construction uses the exact locked apt snapshot and the official
release URL, with the locked asset SHA-256 verified before extraction. Each
baseline build uses no network namespace and no host bind mount. The required
artifacts are copied from the container only after the command and output
checks complete.
