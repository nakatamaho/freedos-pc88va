# macOS and Apple Silicon host adapter

The canonical M01 environment is still Linux/amd64. A macOS host, Docker
daemon, image, and running container have different architecture identities:
the host and daemon may be arm64, while the requested image and the observed
container must be amd64. The gate is the running container reporting
`uname -m=x86_64` and `dpkg --print-architecture=amd64`.

## Project-local Colima storage

Use `tools/host/colima.sh` for future Colima commands in this checkout.
It sets `COLIMA_HOME` to the repository's `.colima/`, `LIMA_HOME` to
`.colima/_lima/`, and `COLIMA_CACHE_HOME` to `.colima/cache/`. VM disks and
the Docker images stored inside them belong to that location. The default
profile is `freedos-pc88va`, with Docker context `colima-freedos-pc88va`.
The storage directory is Git-excluded. Docker client context metadata remains
in its normal client configuration directory.

This follows the official [Colima storage configuration](https://github.com/abiosoft/colima/blob/main/docs/FAQ.md#how-do-i-change-where-colima-files-are-stored).
Use the wrapper for subsequent start, status and stop operations so that they
address the same storage. For example, `tools/host/colima.sh status`.

Prepare the new profile after completing the active M15 session. Before
removing an old Colima home, retain any required image exports and evidence
outside that home. A new profile needs its build images loaded or rebuilt;
changing the storage directory alone does not migrate an existing VM.

## Runtime profiles

The documented Colima installation and configuration references are the
[Colima installation guide](https://colima.run/docs/installation/) and
[Colima configuration guide](https://colima.run/docs/configuration/). The
recommended user-managed profile on Apple Silicon is:

```sh
brew install colima docker
tools/host/colima.sh start \
  --runtime docker \
  --arch aarch64 \
  --vm-type vz \
  --vz-rosetta \
  --mount-type virtiofs \
  --cpus 4 \
  --memory 8 \
  --disk 30
docker context use colima-freedos-pc88va
```

If Rosetta execution is unavailable, use a separate user-selected QEMU
profile; do not mutate an existing VZ profile's immutable settings:

```sh
tools/host/colima.sh start freedos-pc88va-qemu \
  --runtime docker \
  --arch x86_64 \
  --vm-type qemu \
  --cpus 4 \
  --memory 8 \
  --disk 30
docker context use colima-freedos-pc88va-qemu
```

Keep the selected runtime running until its active milestone work is complete.
VM lifecycle changes follow the owner's instructions. These read-only checks
confirm the selected runtime and actual execution path:

```sh
docker context show
docker info
docker buildx imagetools inspect ubuntu:22.04
docker run --rm --platform linux/amd64 --network=none \
  ubuntu:22.04@sha256:79676deb51ebb02885b0b9d33788e78a37cf1045ad79d1bb04c6a222c3556b3d \
  sh -c 'uname -m; dpkg --print-architecture'
```

The expected last two lines are `x86_64` and `amd64`. An arm64 daemon is not
itself a failure when this probe succeeds. The Docker multi-platform model is
described in the [Docker documentation](https://docs.docker.com/build/building/multi-platform/).
The M01 workflow additionally runs on the explicit native x64
`ubuntu-22.04` GitHub-hosted runner; see the [GitHub-hosted runner
reference](https://docs.github.com/en/actions/reference/runners/github-hosted-runners).

Open Watcom 1.9 is the final stable 1.x release used by M01. Its Linux host
tools are 32-bit i386 executables, so the recommended fallback for this
attempt is a user-managed full x86_64 QEMU profile, for example
`vaeg-x86-qemu` with context `colima-vaeg-x86-qemu`. The exact profile name is
host-local and must be recorded only as diagnostic evidence.

All compilation occurs in container-local Linux `/work` storage. The parent
repository, source archives, extracted sources, and build outputs are never
bind-mounted into a build container. Do not install or execute Open Watcom
directly on macOS; the official release's Darwin snapshot is not the M01
compiler. The selected adapter is recorded as `native`, `Rosetta`, `QEMU`, or
`unknown` only when the runtime provides evidence; it is never inferred from
daemon architecture and never enters the golden manifest.

Troubleshooting: select the intended Docker context; confirm Rosetta is
available for a VZ profile; use the distinct x86_64 QEMU profile if the
required binaries cannot execute; provide at least 8 GiB to both the host
filesystem and Docker VM; and avoid reusing a profile with incompatible
immutable architecture or VM settings. If no amd64 container can report the
expected values, stop before changing the repository. Native x64 GitHub
Actions must reproduce the committed golden manifest before M01 receives
`HOST PASS`.

Primary source access date for the links above and the official
[Open Watcom 1.9 release](https://github.com/open-watcom/open-watcom-1.9/releases/tag/ow1.9): 2026-08-28.
