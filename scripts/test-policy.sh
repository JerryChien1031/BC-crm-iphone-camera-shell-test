#!/bin/bash
set -euo pipefail
shell_root="$(cd "$(dirname "$0")/.." && pwd)"
if [[ "$(uname -s)" != Darwin ]]; then
    echo "Native Swift policy tests require macOS with Xcode." >&2
    exit 1
fi
test_dir="$(mktemp -d "$shell_root/build-policy-tests.XXXXXX")"
trap 'rm -f "$test_dir/policy-tests"; rmdir "$test_dir"' EXIT
xcrun swiftc -swift-version 5 \
    "$shell_root/CameraShell/SitePolicy.swift" \
    "$shell_root/CameraShell/SiteSettings.swift" \
    "$shell_root/tests/main.swift" \
    -o "$test_dir/policy-tests"
"$test_dir/policy-tests"
