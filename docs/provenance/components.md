# Component Provenance

The parent pins the exact checked-out commit of each component with a gitlink
and repeats that SHA in `manifests/components.lock.json`. Branches are retained
as tracking metadata, while the gitlink is the reproducibility boundary.

| Component | Lineage | Role | Stability |
| --- | --- | --- | --- |
| `components/fdkernel` | `FDOS/kernel` -> `lpproj/fdkernel:nec98test_cherry-picked` -> `nakatamaho/fdkernel:nec88va` | Editable experimental PC-88VA kernel fork | experimental |
| `components/freecom` | `FDOS/freecom` -> `lpproj/freecom_dbcs2:dbcs` -> `nakatamaho/freecom_dbcs2:nec88va` | Editable DBCS/Japanese command processor fork | experimental-fork |
| `components/country` | `FDOS/country:master` | Read-only NLS/DBCS data baseline | upstream |

The fdkernel child branch has the explicit base
`lpproj/fdkernel:nec98test_cherry-picked`. Its PC-98-oriented code is an
experimental starting point and is not PC-88VA operating evidence. FreeCOM is
based on `lpproj/freecom_dbcs2:dbcs`.

The new child branch tips may equal their upstream base commit immediately
after branch creation. Branch identity and future history are nevertheless
separate from the upstream branch. The parent lock and gitlinks pin the exact
commit used here.

Historical note only: at the 2026-08-27 review point, the old
`nakatamaho/fdkernel` branches `nec98-current`, `nec98test_cherry-picked`, and
`necpc88va` all pointed to `c9ce245e0447003645adce47bd34960ae276d4bd`. Those
old names are not part of the current layout and are not recreated by M00.
