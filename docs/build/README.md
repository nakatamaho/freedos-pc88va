# Build

M01 adds a pinned Linux/amd64 host baseline. It exports the exact parent
gitlinks and builds the pinned kernel (with the approved M01F WMake
build-system repair), FreeCOM, and COUNTRY.SYS sources twice in container-local
storage. It does not select packages or generate a boot image. See
`M01-toolchain.md`, `macos-apple-silicon.md`, and
`upstream-build-contracts.md`.
