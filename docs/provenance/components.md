# Component Provenance

The parent pins the exact checked-out commit of each component with a gitlink
and repeats that SHA in `manifests/components.lock.json`. Branches are retained
as tracking metadata, while the gitlink is the reproducibility boundary.

| Component | Lineage | Role | Stability |
| --- | --- | --- | --- |
| `components/fdkernel` | `FDOS/kernel` -> `lpproj/fdkernel:nec98test_cherry-picked` (`c9ce245e...`) -> `nakatamaho/fdkernel:nec98-current` (`29085311...`) | Editable experimental NEC98 kernel build-fix fork | experimental |
| `components/freecom` | `FDOS/freecom` -> `lpproj/freecom_dbcs2:dbcs` -> `nakatamaho/freecom_dbcs2:deterministic-build-timestamp` (`855281a...`) | Editable DBCS/Japanese command processor reproducibility fork | experimental-fork |
| `components/country` | `FDOS/country:master` | Read-only NLS/DBCS data baseline | upstream |

The fdkernel child branch has the explicit base
`lpproj/fdkernel:nec98test_cherry-picked` at
`c9ce245e0447003645adce47bd34960ae276d4bd`. Its sole child commit,
`29085311a47c8fcceb7902b64b0b5ebc170b8de5`, changes the two WMake conditional
directives around `XUPXSYS` from `ifdef`/`endif` to `!ifdef`/`!endif`. This is a
build-system repair; its PC-98-oriented code is not PC-88VA operating evidence.
FreeCOM is based on `lpproj/freecom_dbcs2:dbcs`. Its sole M01 timestamp commit,
`855281a3114b43ad4b8d9a320f2aca39be046bba`, adds opt-in generic build-date and
build-time macros in `shell/ver.c`; it is a reproducible-build facility, not a
PC-88VA port.

The parent lock and gitlinks pin the exact child repair commit used here;
branch names remain tracking metadata and are not the reproducibility input.

Historical note only: before M01F, the old `nakatamaho/fdkernel` refs
`nec98-current`, `nec98test_cherry-picked`, and `necpc88va` were observed at
the base SHA. M01F now uses the new `nec98-current` child repair ref.
`necpc88va` was not created.
