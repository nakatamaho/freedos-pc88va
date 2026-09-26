# M16 host tooling

The M13 carrier builder and linked-placement verifier in this directory are
maintained M16 copies of the algorithms from parent revision
`1af9974700cd4dd1164cc0df56cc062925376148`:

- `tools/m15/build_compressed_kernel.py`
- `tools/m15/verify_linked_placement.py`
- `tests/m15/test_memory_placement.py`
- `tests/m15/test_carrier_tail.py`
- `config/m15/legacy-placement-test.json`

Their M16 regression copies are under `tests/m16/`. They are retained because
the active M16 kernel still uses the M13 carrier and placement contract. The
M16 copies operate on the pinned component inputs and local fixture
`config/m16/va-fixed-loader-profile-test.json`; they do not import, execute,
or read any M15 runtime files. Generated test output belongs under `build/m16/`.

This provenance records algorithm lineage only. M15 acceptance results and
unrelated M15 tooling are not carried into M16.

The overlay loader builder and profile validator are M16-maintained copies in
`tools/m16/build_loader.py` and `tools/m16/loader_profile.py`. Their source
provenance is fdkernel commit
`d8dbbf7111f86ea4800daeac84ac53ba601aaf32`,
`components/fdkernel/pc88va/tools/{build_loader.py,loader_profile.py}`.
`tests/m16/test_loader_builder.py` exercises those local copies. M16 does not
import component helper tools or run the component's historical milestone
tests as part of its build.

## Build

The host needs Git, Python 3 with pip, Docker Buildx, and network access for the
first acquisition of pinned public dependencies. Build the locked Linux/amd64
Open Watcom 1.9 image, then build the complete disk twice from Git archives:

```sh
python3 tools/m16/toolchain.py
python3 tools/m16/build_image.py --output build/m16-image
```

`build_image.py` downloads the configured Unicorn 2.1.4 verifier wheel and
checks its filename and SHA-256 before starting network-disabled containers.
Both builds use the committed parent inputs, exact component gitlinks, and the
image produced by `toolchain.py`; their full artifact manifests must match.
The output directory must stay Git-excluded. `build/m16-image/media.d88` is a
freshly composed candidate and is not a milestone distribution until its guest
acceptance and publication checks are complete.
