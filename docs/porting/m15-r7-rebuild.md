# M15 r7 candidate rebuild recipe

This is the historical r6 comparison procedure, not the source-build entry
point. To generate a new disk without old media or saved binaries, use
[M15 build from source](m15-source-build.md). The private paths below are
example inputs for the historical procedure and are not supplied by a clone.

The r7 candidate is a reproducible rebuild of the recovered r6 media, not a
claim that the unavailable original r6 build directory was recovered. The
recipe consumes the immutable r6 D88 seed and a Git-excluded private input
profile. The profile locks the parent and component revisions, the carrier
builder, the seed image identity, and the rebuilt major system and QA binaries.
Unchanged seed-only support files are explicitly labeled as preserved inputs.

The rebuild tool parses the seed D88 and FAT12 filesystem, checks every
source-built binary against its live file, reconstructs the D88 twice from
independent reads, and compares the complete logical-sector contents and live
file set. The output is created only when both passes agree. Exact D88 hash
identity is recorded but is not required; equivalence requires identical
logical sectors, FAT12 structure, directory contents, and file bytes.

The private profile must list every live file exactly once. It must classify
each one as `source_build` with a regular artifact under `.private-evidence`,
or as `r6_seed` with a reason. The following major artifacts are mandatory
source builds: `KERNEL.SYS`, `LOADER.BIN`, `COMMAND.COM`, `COUNTRY.SYS`,
`SYSVA.EXE`, `SYSQA.COM`, `ALIASQA.COM`, `NLSTABLE.COM`, `NLSQA.COM`,
`SYSMISC.COM`, `CONSOLE.COM`, and `FCBQA.COM`.

Use a new, empty Git-excluded output directory:

```sh
make m15-r7-rebuild \
  M15_R7_SEED=.private-evidence/m15/runs/normal-qa-current-20260925-r6/va/media.d88 \
  M15_R7_PROFILE=.private-evidence/m15/r7-profile/input.json \
  M15_R7_OUTPUT=.private-evidence/m15/r7-rebuild
```

The command emits `media.d88` and `reproduction.json`. QA must use that exact
`media.d88` only after `reproduction.json` records two equal builds, the
complete source-built payload set, and unchanged logical sectors. The source
profile, media, generated records, and their concrete identities remain
private and are not committed.
