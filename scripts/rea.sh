#!/bin/sh
# Pinned CLI/runtime; use an explicitly configured Ghidra or the local research install.
set -eu
repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
export GHIDRA_INSTALL_DIR="${GHIDRA_INSTALL_DIR:-$repo_root/../tools/ghidra_12.1.4_PUBLIC}"
export JAVA_HOME="${JAVA_HOME:-/opt/homebrew/opt/openjdk/libexec/openjdk.jdk/Contents/Home}"
export REA_GHIDRA_STARTUP_TIMEOUT_MS="${REA_GHIDRA_STARTUP_TIMEOUT_MS:-600000}"
exec npx --yes --package=node@24.22.1 --package=rea-agents@6.8.0 rea "$@"
