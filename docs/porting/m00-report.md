# M00 — MS-DOS 2.11 VA memory-compatibility baseline

Status: COMPLETE for the corrected M0 scope (`VAEG PASS`; physical PC-88VA
validation is `DEFERRED HARDWARE VALIDATION`).

## Selected milestone and identity

M0 was the first eligible milestone in the corrected memory-compatibility
specification. Work was performed in an isolated parent worktree whose
required downstream base was `1ec3101ec5ffcd9babf306f2e553125a604934d9`.
The original dirty M13 worktree and the VAEG checkout were not modified.

The detailed report is
`docs/msdos211-memory-compat/reports/M0-remove-bios-shims-and-rebaseline.md`.
It records the exact source/artifact identities, build command, launch
configuration, MCB walk, named probes, and private evidence paths.

## Result

The selected current PC-88VA source and linked path contain no installation of
the superseded PC-88VA INT 12h/INT 15h BIOS shim. The superseded commit
`49335bb547348e5e899285f0535e26284c388834` was inspected and was not treated
as a current conformance implementation. No source inverse patch was needed.

The fresh 640-KiB native MCB probe found first MCB header `219Fh`, first data
segment `21A0h`, a valid non-overlapping chain, and final exclusive physical
end `A0000h`. The fresh candidate's largest-block observation is kept
separate from the formal recorded FreeDOS comparison value of 423008 bytes;
the detailed report explains the candidate/configuration difference rather
than replacing the baseline.

The retained MZ relocation, allocator, MCB-lifetime and current source-family
probes are recorded in the detailed report. No allocator, BIOS, native
capacity, or memory-reclamation behavior was changed by M0.

## Verification and non-claims

The pinned Open Watcom Linux/amd64 build completed, and the fresh VAEG probe
and named regressions are labelled `VAEG PASS` for this M0 evidence scope.
The IBM-style INT 12h/INT 15h observations are characterization only, not
acceptance criteria. Physical hardware was not run and remains `DEFERRED
HARDWARE VALIDATION`. M1 native decoder fixtures, M2 arena wiring, and later
memory targets were not run.

## Next eligible milestone

M1 only: establish and test the VA-native capacity decoder backed by the
mapped common/backup-memory state. The VAEG `vabkupmem.dat` load path is
documented in `docs/msdos211-memory-compat/handoff.md`; no decoder was
implemented in M0.

No implementation commit identifier is claimed by this report; parent
documentation publication is the only tracked M0 change in this worktree.
