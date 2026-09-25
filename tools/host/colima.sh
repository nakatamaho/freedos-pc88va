#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Keep this project's VM disks, configuration and downloads in its checkout.
set -eu

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
export COLIMA_HOME="$PROJECT_ROOT/.colima"
export COLIMA_CACHE_HOME="$COLIMA_HOME/cache"
export LIMA_HOME="$COLIMA_HOME/_lima"
export COLIMA_PROFILE=freedos-pc88va
umask 077
mkdir -p "$COLIMA_HOME" "$COLIMA_CACHE_HOME" "$LIMA_HOME"

exec colima "$@"
