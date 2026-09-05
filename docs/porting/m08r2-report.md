# M08R2 artifact schema conformance closure

Status: validation complete locally; publication and native CI pending.

Parent start: `0bbefb97e6233283053ecb301c84a7688fb39101`.
Branch: `topic/m08r2-artifact-schema-conformance`.

## Correction and dependency order

The accepted artifact manifest carried three kernel provenance digests that
its bound schema rejected. The prior verifier checked the schema identity
but not instance conformance. A dedicated closed `kernel_artifact` definition
now requires format, size, artifact hash, compile-manifest hash,
kernel-interface hash, and symbol-evidence hash. Generic artifact definitions
remain unchanged and reject kernel provenance fields.

The verifier checks Draft 2020-12 schema validity and validates the actual
manifest before accepting its evidence. Validation failures do not print
instance values. Host QA uses jsonschema 4.25.1; the guest toolchain is unchanged.

Rebinding order is schema, then golden's schema reference, then contract's
golden reference. Verifier pins follow those identities. The artifact manifest
does not reference the schema, so its bytes do not change. The qualification
record has no dependency on the corrected schema and remains unchanged.

| Record | Previous SHA-256 | Current SHA-256 |
| --- | --- | --- |
| Schema | `9e81fef8a5668525e521df9ae322c8dc3029cc336edd34a62b8455f141c7d682` | `575086b668fb7f2439f17b63a33675978fef00861eb0b30f66a7b22d3279e7fe` |
| Artifact manifest | `2210a590a7d705f3936a9053e197d05eb94888254b708f4435a1e7c89d3ef5e0` | unchanged |
| Golden | `b7661bcfddd9ab45748a530dac3d8fe07b86eb16254f075ea24c346bd57bad60` | `bd611f5d6a0cb37c16114aec5b7382cb3bf7c18d340b762501d8bc2a574ad2a7` |
| Contract | `f383a4f4e71b00fd0bcf5e69a00aeef5068f0c55c788b610fcd431f3e29db54c` | `c163ab5a1f1d1a3c3ae76e93bd24da7535393ea923f1d891cdbc1ab4460dae19` |
| Qualification | `3ebbf58e18ea2acf0f92ba755cca99c3082b5ed419e6bfa51a5bd2d2fd8dbe47` | unchanged |
| Component lock | `c3e736596ce63ce006ba0363682259260f30a1792e59a04e3250ac9821544f07` | unchanged |

## Build and tests

Two separate network-disabled Linux/amd64 containers rebuilt the unchanged
child from its deterministic prefixed Git archive using Open Watcom 1.9 and
the pinned M01 tools. The public synthetic overlay, accepted M05 structure,
and per-component M01 timestamps were used. Existing accepted FreeCOM/Country
payloads were hash-checked before use. No private qualification was rerun.

Loader stages, KERNEL.SYS, raw/D88 media, independently extracted payloads,
objects, library, and canonical JSON compare byte-for-byte. Every public
artifact matches the unchanged M08 artifact manifest. The rebuilt composition
manifest in each run hashes to
`85988bf11900b0d4e75d7fce318ec51771bfc448ebc81cdd527c15d063ecec39`.
Raw WLink maps differ in their creation-time line; all other map lines and
canonical symbol evidence match. Raw map byte equality is not claimed.

The repeatable public command is `bash tools/m08/compare_public_builds.sh
COMMAND.COM COUNTRY.SYS`, with the accepted M01 container image selected by
`M08_BUILD_IMAGE` and the optional host adapter by `M08_DOCKER_CONTEXT`.
Generated results remain ignored under `build/`.

ROM-free child tests: 164 passed. Parent tests: 19 passed, including 14
acceptance/schema tests. Negative checks reject missing required kernel fields,
unknown fields, invalid hash types/patterns, kernel fields on generic artifacts,
invalid schema definitions, schema digest drift, manifest digest drift, and
incomplete acceptance references. An integration test proves acceptance calls
the instance validator rather than only checking digests.

Local M01/M02/M05/M06/M07 golden verifiers and M04/M07 completion checks passed
at the accepted historical checkout. The first M05 CI run (33956713641) rejected
the new report at its historical path gate. M04/M05 descendant path checks now
allow exactly the M08 artifact manifest, golden and M08R2 report; adjacent
unreviewed paths remain rejected by negative tests. Current-tree M04 validation
and all 39 M04 tests pass. No geometry, golden artifact, or historical contract
validation was weakened. Native M08 CI uses its existing accepted historical
checkout for M01 through M07 regression.
M08 source/schema gates and synthetic tests run on the current branch.

The standalone M05 workflow previously selected M06's fixed-child preflight
even with an M08 lock. For the M08 case it now uses the existing M05 descendant
validator and unchanged builder/inspector, rebuilds twice, and verifies the
original golden. This path passed locally using verified retained M01/M02
public inputs; 36 M05 tests passed. No component checkout is changed by it.

## Preservation and limitations

- fdkernel: `105d49a72ec41afe07fc1e7b080bdbd1b3026ae2`.
- FreeCOM: `855281a3114b43ad4b8d9a320f2aca39be046bba`.
- Country: `23f189cca3420606eae8723884fa92ccd65eb307`.

All component sources and gitlinks are unchanged. Existing M09 worktrees and
untracked reports are preserved. Private qualification values, projections,
inputs and identities are unchanged and not published. Generated build output
and logs are not committed. No public history was amended or force-pushed.

This is public evidence correction, not a new runtime qualification.
HARDWARE NOT RUN. M09 NOT STARTED.
