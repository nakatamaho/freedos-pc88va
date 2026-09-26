# M01 build image

This image is the canonical Linux/amd64 host environment for M01. The caller
passes `--platform linux/amd64`; the Dockerfile deliberately does not select a
platform itself. Its base image, apt snapshot, package versions, and official
Open Watcom archive are locked in `manifests/toolchains.lock.json`.

Image assembly may access only the exact snapshot and the verified Open Watcom
release asset. Build containers are created with `--network=none`, have no
mounts, receive read-only source archives with `docker cp`, and compile in
container-local `/work` storage. The image contains no emulator, ROM, BIOS,
disk image, FreeDOS binary distribution, credentials, or private material.

The archive is the official Open Watcom 1.9 self-extracting ZIP package. M01
extracts it with `unzip` at `/opt/openwatcom-1.9` and uses only its `binl`
Linux i386 host tools inside the canonical Linux/amd64 container. The complete
x86_64 QEMU host adapter is required when the host cannot execute these 32-bit
Linux tools natively. No Darwin-hosted compiler is used.
