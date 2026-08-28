# Manifests

Manifests describe reproducible component pins and future package choices.
FreeDOS userland consists of many independent packages, so M00 and M01 do not
select package repositories or turn unselected packages into submodules.
Package licenses must be checked before any future distribution.

`m01-build-contract.json` records the exact baseline commands and artifacts.
`toolchains.lock.json` records the canonical container inputs. Generated
results and required binaries remain ignored; only the deterministic golden
manifest is committed after two matching runs.
