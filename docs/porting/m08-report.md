# M08 acceptance evidence closure report

Status: M08R1 PASS — M08 PUBLIC ACCEPTANCE EVIDENCE CLOSED.

This report closes the public M08 evidence record from the fixed parent
commit `3b2b203fd04765d2236594b2c39a03bf4c31a68f`. The current parent branch
is `topic/m08r1-acceptance-evidence-closure`. The fdkernel child remains the
accepted `105d49a72ec41afe07fc1e7b080bdbd1b3026ae2` export on
`topic/m08-pc88va-disk-loader-handoff`; FreeCOM and Country remain unchanged.
The qualified public VAEG identity is `7463f9501d84701f50f3243d5067b6a9dfd0c2e7`,
with successful VAEG CI run `33937050536`.
The public evidence-closure commit is `0bbefb97e6233283053ecb301c84a7688fb39101`.

## Accepted identities

- M08 contract: `config/m08/loader-contract.json`, SHA-256
  `f383a4f4e71b00fd0bcf5e69a00aeef5068f0c55c788b610fcd431f3e29db54c`
  (accepted status).
- Artifact manifest: `qa/golden/m08-artifact-manifest.json`, SHA-256
  `2210a590a7d705f3936a9053e197d05eb94888254b708f4435a1e7c89d3ef5e0`.
- Artifact-manifest schema: `schema/m08-artifact-manifest.schema.json`,
  SHA-256 `9e81fef8a5668525e521df9ae322c8dc3029cc336edd34a62b8455f141c7d682`.
- M08 golden: `qa/golden/m08-golden.json`, SHA-256
  `b7661bcfddd9ab45748a530dac3d8fe07b86eb16254f075ea24c346bd57bad60`.
- VAEG qualification record: `config/m08/vaeg-qualification.json`, SHA-256
  `3ebbf58e18ea2acf0f92ba755cca99c3082b5ed419e6bfa51a5bd2d2fd8dbe47`.
- Current M08 component lock: `manifests/m08-components.lock.json`, SHA-256
  `c3e736596ce63ce006ba0363682259260f30a1792e59a04e3250ac9821544f07`.
  It preserves the historical component lock identity
  `440e481b28c740875489a6953a246ce5370c44074053c7aad3f80e79ec40c19c` and
  pins fdkernel, FreeCOM and Country to the accepted gitlinks.

## Public artifact closure

Two independent clean builds from the fixed source archive and Open Watcom
1.9 Linux/i386 tools in the pinned Linux/amd64 container were byte-identical,
including objects, link/map evidence, generated inputs and final artifacts.

| Artifact | Size | SHA-256 |
| --- | ---: | --- |
| loader stage 1 | 1,024 | `20efd8a66dde7feac3f48df4bd6e8c4564d70e80a5a8871a8293e735c1585f24` |
| loader stage 2 | 4,304 | `db324cbdae11fd1e6085a7957ef171ccf9d6a9be6ea05f3df0eedf83d8f594f7` |
| `KERNEL.SYS` | 5,771 | `461e55d6983a944d35749eb658a5e11ba0316ff0bcd7da65982228aefce17253` |
| raw M05-derived media | 1,310,720 | `d19ec41d30973229df0d4e91b0344159b284f17243989a5e712eb40de5fe5724` |
| D88 media | 1,331,888 | `7ff2169271f4f101a8b53bb36be0343f3272d50051c2616b05d0ed4e10fa1260` |
| extracted `KERNEL.SYS` | 5,771 | `461e55d6983a944d35749eb658a5e11ba0316ff0bcd7da65982228aefce17253` |
| extracted `COMMAND.COM` | 91,143 | `fabe7744cc7c51c6f72519cc39d89bf77beaf908f994675a97a1e34c93549da1` |
| extracted `COUNTRY.SYS` | 42,614 | `04b2d2bc8df382090686f00e547d718d6706d22fb34c34dd77cd55083d5c34d5` |

The loader preserves the accepted M05 geometry and FAT12 layout, locates the
exact `KERNEL.SYS` root entry and chain, applies the zero-relocation DOS MZ
policy, validates body-relative placement and stack ownership, and performs a
one-way entry handoff. The D88-to-raw projection is byte-identical. FreeCOM
and Country payloads are unchanged.

The verifier now requires the accepted contract to reference and digest the
artifact manifest, M08 golden, and VAEG qualification record. Negative tests
prove that removing any of those identities is rejected; an accepted-status
string alone cannot pass.

## Private qualification summary

The retained private qualification used two clean VAEG runs under the same
launch contract. Both runs observed L0–L9 twice, produced byte-identical
canonical projections, preserved inputs, and reached the M06 kernel-entry
marker. Private values remain in persistent ignored local evidence and are not
represented in this report. Temporary raw traces and intermediate build
products are disposable; manifests, projections, input-preservation records,
qualification identity and cleanup records are retained.

M07 established firmware boot acceptance. M08 consumed and regression-checked
that accepted handoff contract; it did not newly claim hardware validation.
The two successful public workflow runs are `33947694791` and `33947807789`;
the latter is recorded as the second clean workflow result rather than being
collapsed into an unsupported single-run claim. The accepted VAEG workflow is
`33937050536`.

## Verification and boundaries

- Public synthetic fdkernel tests: 164 passed.
- Parent public media and acceptance tests: 10 passed.
- M08 public verifier: PASS, including artifact/golden/VAEG identity checks.
- Historical M01–M07 regression workflow: PASS in the successful M08 workflow
  runs listed above.
- M08R1 closure workflow `33953289513`: success; both `public-loader` and
  `historical-regression` jobs passed.
- Local public artifact builds: two-build byte equality PASS.
- Evidence labels: HOST PASS for deterministic public build/tests; VAEG PASS
  for the retained two-run qualification; HARDWARE PASS: not claimed.
- Private evidence and generated artifacts: not committed, uploaded, or put in
  public CI.

Full DOS startup, COMMAND.COM execution, console/keyboard/timer/interrupt
services, unrestricted firmware use, and hardware validation remain outside
M08. M09 has not started.

M08R1 PASS — M08 PUBLIC ACCEPTANCE EVIDENCE CLOSED.
