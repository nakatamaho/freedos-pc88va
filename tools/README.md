# Tools

The M00 scaffold verifier is offline and read-only. M01 tools export exact
parent-pinned component commits, build them in disposable Linux/amd64
containers, collect bounded evidence, compare required binaries, and verify
the committed golden manifest.

M01 build results, source archives, container identifiers, and logs are
ignored. The tools never modify component repositories, access the network
during a build, or use the parent working tree as a container mount.
