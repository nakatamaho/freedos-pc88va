# M07R2 positive-control boot diagnosis

M07R2 tested the prerequisite for comparing the public M07 probe media with a
known local PC-Engine control. It did not implement or modify a boot sector,
loader, kernel, media geometry, probe, or VAEG source.

## Recovery and observation boundary

The observation tool is public VAEG commit
`16ad2e0619bf4ed82a739325f7291eba4a6ed8ad`. Its accepted CI run is
`33455847870`, attempt 2. Two clean local P1 builds reproduced the accepted
production-memory binary identity. Trace was enabled with tests disabled, and
the flat test-memory seam was absent. The pre-existing VAEG worktrees were
left unchanged; a separate detached, clean checkout supplied the fixed source
identity.

The local positive control is named only `CONTROL` in public records. Its
firmware and disk identities, bytes, paths, hashes, traces, addresses, and
derived values remain in ignored local evidence. Public CI does not have or
inspect those inputs.

## Result

Two fresh bounded CONTROL runs used the same PC-88VA model, drive selection,
firmware input, instruction limit, production CPU trace, and FDD correlation
settings. Their canonical abstract projections were byte-identical and all
inputs were unchanged. Neither run reached the first firmware FDD-request
boundary. The positive-control prerequisite therefore failed before a valid
CONTROL-versus-V00--V04 comparison could begin.

The result is Class A:

```text
M07R2 BLOCKED — POSITIVE CONTROL FAILED
```

The last common boundary is recorded as not applicable before media
comparison. The first missing boundary is the firmware FDD request from the
CONTROL configuration. In accordance with the experiment plan, M07R2 ran no
fresh probe-variant trial and created no adaptive variant. This result points
to the ROM/model/drive-selection or emulator launch assumptions; it does not
establish a defect in the M05 container or any boot-record profile.

All eight M08 entry-contract fields remain unresolved: firmware handling of
the M05 geometry, accepted signature profile, initial sector reads, loaded
extent, physical load address, first `CS:IP`, initial register state, and boot
drive identity. M08 remains NO-GO.

## Public verification

`tools/m07r2/d88.py` is a content-agnostic structural D88 parser. It exposes no
sector payload and is tested only with newly authored synthetic bytes.
`tools/m07r2/trace_boundaries.py` classifies abstract A--E boundary sequences.
The committed status and schema contain only the class, boundary names,
trial/count state, unresolved field names, fixed public identities, and the
nonpromotion policy.

Run the ROM-free gate with:

```sh
make m07r2-public
```

The explicit local-only evidence gate is:

```sh
make m07r2-private-evidence
```

That local gate checks ignored evidence, two-run equality, and tracked-file
leakage without printing private values. It is never invoked by CI.

Public promotion remains `prohibited_pending_user_approval`. VAEG observation
is emulator evidence, not real-hardware verification.
