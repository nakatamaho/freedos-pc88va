# Components

The parent repository contains exactly three foundational git submodules. The
parent pins their checked-out commits; branch names are tracking metadata, not
the reproducibility boundary.

| Path | Repository and branch | Role |
| --- | --- | --- |
| `components/fdkernel` | `nakatamaho/fdkernel`, `nec88va` | Editable experimental PC-88VA kernel fork |
| `components/freecom` | `nakatamaho/freecom_dbcs2`, `nec88va` | Editable DBCS/Japanese command processor fork |
| `components/country` | `FDOS/country`, `master` | Read-only NLS/DBCS data baseline |

Do not vendor component source into the parent. Component licenses and history
remain governed by each component repository.
