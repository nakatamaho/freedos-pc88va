# M15 build from source

The complete build uses only this repository, its pinned component gitlinks,
the public `config/m15/loader.json`, and the pinned toolchain. It does not read
an old D88, ROM, private evidence directory, or a saved DOS executable.

## Build

Clone `topic/m15-dos-api-writable-session` with `--recurse-submodules` and
check out the desired parent commit. A Docker-compatible Linux/amd64 runtime and Python with pip are
required. On macOS the default Python command is `/opt/local/bin/python3.12`;
on Linux pass `M15_PYTHON=python3`. For new Colima profiles use
`tools/host/colima.sh` as described in the host setup documentation.

```sh
make m01-image   # Once, unless the pinned toolchain image is already installed.
make m15-image
```

Use a new output directory for another build:

```sh
make m15-image M15_IMAGE_OUTPUT=build/m15-image-next
```

The driver exports the committed parent and exact component gitlinks with
`git archive`. Tracked edits and mismatched component checkouts are rejected.
It builds twice in fresh, network-disabled containers without source mounts.
Open Watcom executable identities are checked against the toolchain lock.
The map's `Created on:` header is normalized to the fixed source epoch and
its `Link time:` duration to zero;
all linker section and symbol records are retained.
The pinned Unicorn wheel for placement verification is fetched before the
offline builds; it is not a guest input. No new Colima VM is created.

The stages are:

1. Build the common FreeDOS kernel with `makefile.m13.wc` and SYSVA with
   `sys/makefile.pc88va` using Open Watcom 1.9.
2. Build the pinned generic English FreeCOM without XMS swapping, retaining
   the fixed build date/time, and assemble COUNTRY.SYS.
3. Generate the compact in-place kernel carrier and both loader stages from
   source, checking the linked placement and the 256-KiB early layout bound.
4. Allocate a new FAT12 filesystem and derive the stage-1 loader extent from
   its actual allocation. Generate the BPB and D88 headers from public media
   configuration; insert the two declared boot-signature slots.
5. Read every file back, check FAT copies, run focused placement/loader tests,
   and compare both builds before publishing `media.d88` in the output folder.

The normal disk contains KERNEL.SYS, LOADER.BIN, COMMAND.COM, COUNTRY.SYS,
SYSVA.EXE and SYS.ID. It intentionally contains no previous QA results or
diagnostic fixture programs. `build.json` records the source commits, archive
digests, toolchain image, verifier dependency and output identities.

The source-built D88 is a public distribution artifact. It contains no ROM or
private disk input. Distribute it with the exact source/build identities and
the applicable component license notices. The designated milestone D88 is stored as an xz archive under
`images/milestones/m15/` with its source identities and hashes. Intermediate
build products remain outside Git.

To archive a newly completed build (the destination must not already contain
a distribution):

```sh
python3 tools/m15/archive_image.py --build build/m15-image
```

The archive command checks both build outputs, creates `media.d88.xz` and
`manifest.json`, and verifies decompression. Review and commit those files
together with the milestone's distribution README.

## Public platform configuration

The owner clarified that ROM/private media must remain uncommitted but the
port's build settings and project-authored BIOS adapter code belong in source
control. `loader.json` exposes those settings. The low-staging memory layout
is the existing M13 loader/carrier contract, and the disk callback uses the
same request ABI and BIOS read operation as the kernel resident disk adapter.
`public_platform_profile` distinguishes it from synthetic test callbacks and
private observation records; ownership and instruction validation still apply.

The startup banner identifies the exported kernel component commit. The
parent commit in `build.json` additionally identifies the recipe and profile.
Byte-identical clean builds establish reproducibility, not guest boot or
hardware acceptance. M15's existing owner acceptance is unchanged; a newly
generated disk has no guest boot claim until that disk is tested.
