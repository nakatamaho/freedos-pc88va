# M15 source-built distribution

`media.d88.xz` contains the normal FreeDOS PC-88VA system disk generated from
the source commits in `manifest.json`. It contains KERNEL.SYS, LOADER.BIN,
COMMAND.COM, COUNTRY.SYS, SYSVA.EXE and SYS.ID, plus COMPROBE.COM, MZPROBE.EXE,
TYPEA.TXT, TYPEB.TXT and COMDATA.TXT required by the existing SYSVA transfer
contract. All are source-generated; there are no ROMs or old QA results.

Extract a working copy from the repository root:

```sh
mkdir -p build/m15-distribution
xz -dc images/milestones/m15/media.d88.xz > build/m15-distribution/media.d88
shasum -a 256 build/m15-distribution/media.d88
```

Compare the digest with `manifest.json`'s `media.d88.sha256`. The compressed
archive has its own separately recorded digest. Two independent source builds
produced the same disk. A byte-identical disk reached FreeCOM's `A:\>` prompt
in a VA2 VAEG boot smoke check; this is not a new full-QA or hardware result.

To rebuild, check out `sources.parent` from the manifest, initialize its
submodules, and follow [the source-build instructions](../../../docs/porting/m15-source-build.md).
The startup `build:` line identifies `sources.fdkernel`; the parent identifies
the complete recipe and public platform settings.

The project license and scope are [COPYING](../../../COPYING) and
[LICENSE.md](../../../LICENSE.md). The corresponding component sources and
notices are retained at the exact pinned gitlinks:

- [Kernel and SYSVA](../../../components/fdkernel), including `COPYING`.
- [FreeCOM](../../../components/freecom), including `license` and the SUPPL notices.
- [COUNTRY.SYS](../../../components/country), including `LICENSE`.

Keep these notices and access to the corresponding source when redistributing.
The source-build instructions also describe the pinned compiler and build
configuration needed to reproduce the disk.
