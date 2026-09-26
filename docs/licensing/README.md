# Licensing

Root license: GPL-2.0-or-later

Decision milestone: M04R1

M04R1 supersedes the earlier deferred root-license status. Original material
owned by the `freedos-pc88va` project is licensed under GNU General Public
License version 2 or, at the recipient's option, any later version. The full
GPL version 2 terms are in [`COPYING`](../../COPYING), and the scope and
third-party boundaries are in [`LICENSE.md`](../../LICENSE.md).

This default applies only where project contributors have the right to grant
the license. File-specific notices take precedence for their files. Git
submodules and other third-party material retain their own upstream licenses
and copyright notices. Generated bundles may contain independently licensed
component outputs, so their provenance and applicable notices must be
preserved.

Private manuals, Tekumani material, ROM images, PC-Engine D88 images, and
local analysis outputs are outside the public repository and public license
grant. The root policy grants no trademark permission.

## SPDX policy for new files

New project-owned source files and nontrivial scripts should use this
identifier with the file type's normal comment syntax:

```text
SPDX-License-Identifier: GPL-2.0-or-later
```

Do not add SPDX comments to JSON, generated files, the canonical `COPYING`
text, vendored or imported upstream files, submodules, private evidence, or
formats that do not support comments. Preserve existing copyright and license
headers. A compatible file-specific notice governs that file instead of the
repository default. M04R1 does not mechanically rewrite existing headers.
