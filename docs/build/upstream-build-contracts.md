# Upstream build contracts

M01 builds the exact parent-pinned commits. The parent gitlinks and source
archive SHA-256 values are checked before each pair of builds.

## fdkernel NEC98 baseline

The build input is the child fork commit
`29085311a47c8fcceb7902b64b0b5ebc170b8de5` on
`nakatamaho/fdkernel:nec98-current`, based directly on
`lpproj/fdkernel:nec98test_cherry-picked` commit
`c9ce245e0447003645adce47bd34960ae276d4bd`. The pinned [NEC98
README](https://github.com/lpproj/fdkernel/blob/c9ce245e0447003645adce47bd34960ae276d4bd/nec98/README.md)
states the Open Watcom, NASM, UPX, and GNU Make prerequisites. The inspected
[NEC98 makefile](https://github.com/lpproj/fdkernel/blob/c9ce245e0447003645adce47bd34960ae276d4bd/nec98/makefile)
selects the Linux `owlinux` path and uses GNU Make to invoke the Open Watcom
tools. Its [configuration](https://github.com/lpproj/fdkernel/blob/c9ce245e0447003645adce47bd34960ae276d4bd/nec98/config.m)
documents disabling UPX by leaving the compressor variable unexported. M01
uses the project-owned `config/m01/fdkernel-nec98.mak` template and explicitly
removes `XUPX` and `UPXOPT` from each make environment.

The child [patched WMake file](https://github.com/nakatamaho/fdkernel/blob/29085311a47c8fcceb7902b64b0b5ebc170b8de5/nec98/sys/makefile.wc)
contains the only M01F source change: the two conditional directives around
`XUPXSYS` are `!ifdef` and `!endif`, as required by WMake. The parent applies
no export-time source patch and no macro workaround.

The exact command contract, run in exported `fdkernel/nec98`, is:

```sh
cp /input/fdkernel-nec98.mak config.mak
env -u XUPX -u UPXOPT make clobber COMPILER=owlinux
env -u XUPX -u UPXOPT make all COMPILER=owlinux
```

Required outputs are `nec98/bin/kernel.sys`, `nec98/bin/KWC8616.sys`,
`nec98/bin/sys.com`, `nec98/bin/country.sys`, and
`nec98/boot/b_fat12f.bin`, `b_fat12.bin`, `b_fat16.bin`, and `b_fat32.bin`.
The upstream CI also shows an additional
GCC-IA16 path in its [build workflow](https://github.com/lpproj/fdkernel/blob/c9ce245e0447003645adce47bd34960ae276d4bd/.github/workflows/ci-build.yml);
that matrix is observed but deferred and is not evidence for this Open Watcom
baseline.

The previous attempted invocation, `make all COMPILER=owlinux XUPX=`, is a
rejected M01 invocation against the base source. An empty command-line
variable remains defined under GNU Make, so the uncorrected WMake file expands
its empty post-link command to `sys.com`. Linux then attempts to execute that
DOS output as a host command and exits with status 2 after linking it. This was
a build-contract/source build-system defect, not a compiler or linker failure.
The child repair corrects only the WMake directives; no export-time patch, shim,
error suppression, or fake UPX command is used.

## FreeCOM DBCS baseline

The source is the parent-pinned child commit
`855281a3114b43ad4b8d9a320f2aca39be046bba` on
`nakatamaho/freecom_dbcs2:deterministic-build-timestamp`, with parent
`c059aafe857f005b0d7d8295e3be67c0dba2aafd` from the lineage
`FDOS/freecom -> lpproj/freecom_dbcs2:dbcs`. The pinned [README](https://github.com/lpproj/freecom_dbcs2/blob/c059aafe857f005b0d7d8295e3be67c0dba2aafd/README.md)
documents the DBCS/NEC98/Japanese mode. Its [build script](https://github.com/lpproj/freecom_dbcs2/blob/c059aafe857f005b0d7d8295e3be67c0dba2aafd/build.sh)
accepts the `watcom` mode on Linux and does not enable UPX unless the `upx`
option is supplied. The child [timestamp implementation](https://github.com/nakatamaho/freecom_dbcs2/blob/855281a3114b43ad4b8d9a320f2aca39be046bba/shell/ver.c)
provides the generic opt-in macros described below. The README emphasizes
Windows for Open Watcom, while the script exposes the Linux Watcom path; this
platform/documentation discrepancy is recorded and tested without changing
the build command.

Route A was tested and rejected for the locked Open Watcom 1.9 compiler:
command-line redefinition of `__DATE__` and `__TIME__` through the FreeCOM
response-file syntax returned WCC E1100 because the predefined macros are not
identical. Route B is the minimal generic child repair in the pinned commit:
`shell/ver.c` defines opt-in `FREECOM_BUILD_DATE` and `FREECOM_BUILD_TIME`
macros with the original macros as fallbacks, and uses the date macro in both
visible version strings. The parent generates a read-only `config.mak` from
the pinned `config.std`, adds one `CFLAGS2` line, and feeds the canonical UTC
values from `config/m01/freecom-build-timestamp.json` into `watcomc.cfg`. No
export-time source patch or macro workaround is used.

The exact command contract, run in exported `freecom`, is:

```sh
./build.sh -r dbcs nec98 watcom japanese
```

The required output is `command.com`. The documented GCC-IA16 route remains a
later matrix expansion, not a substitute for the required Open Watcom build.

## COUNTRY.SYS baseline

The source is `FDOS/country` commit
`23f189cca3420606eae8723884fa92ccd65eb307`. Its [Makefile](https://github.com/FDOS/country/blob/23f189cca3420606eae8723884fa92ccd65eb307/Makefile)
assembles `country.asm` with NASM, and its [validator](https://github.com/FDOS/country/blob/23f189cca3420606eae8723884fa92ccd65eb307/ci_validate.py)
uses the pinned `iso3166` and `phonenumbers` Python modules. The upstream CI
records the same [build and validation sequence](https://github.com/FDOS/country/blob/23f189cca3420606eae8723884fa92ccd65eb307/.github/workflows/ci.yml).

The exact commands, run in exported `country`, are:

```sh
make clean all
python3 ./ci_validate.py
```

The required output is `country.sys`.

There are two intentionally distinct producers: the kernel build produces
`fdkernel/nec98/bin/country.sys`, stored under the `fdkernel-country`
namespace, while `FDOS/country` produces `country/country.sys`, stored under
`fdos-country`. Their equality is an informational observation only.
