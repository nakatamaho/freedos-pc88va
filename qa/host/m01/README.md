# M01 host QA

M01 host QA validates the exact component gitlinks, source-export archives,
locked Linux/amd64 image, unmodified source trees, build contracts, required
artifact inventory, two-run byte comparison, and committed golden manifest.

Use `make m01-preflight`, `make m01-image`, `make m01-build`,
`make m01-compare`, and `make m01-verify` from the repository root. Generated
archives, binaries, logs, container IDs, and host-adapter diagnostics remain
under ignored `qa/results/m01/`. VAEG and hardware are `NOT RUN` for M01.
