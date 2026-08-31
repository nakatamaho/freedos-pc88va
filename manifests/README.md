# Manifests

Manifests describe reproducible component pins and future package choices.
FreeDOS userland consists of many independent packages, so M00 and M01 do not
select package repositories or turn unselected packages into submodules.
Package licenses must be checked before any future distribution.

`m01-build-contract.json` records the exact baseline commands and artifacts.
`toolchains.lock.json` records the canonical container inputs. Generated
results and required binaries remain ignored; only the deterministic golden
manifest is committed after two matching runs.

`m06-components.lock.json` records the current M06 fdkernel child commit and
its accepted M01R1 parent.  It does not replace or rewrite the historical
`components.lock.json`; descendants use the M06 lock for the current gitlink
and retain artifact-level NEC98 regression against the historical lock.
