#!/bin/bash
set -euo pipefail
shell_root="$(cd "$(dirname "$0")/.." && pwd)"
if [[ "$(uname -s)" != Darwin ]]; then
    echo "An iOS build requires macOS and full Xcode; Windows cannot produce this IPA." >&2
    exit 1
fi
cd "$shell_root"
mkdir -p build
run_dir="$(mktemp -d "$shell_root/build/unsigned.XXXXXX")"
archive="$run_dir/CameraShell.xcarchive"
xcodebuild -version | tee "$run_dir/xcode-version.txt"
xcrun swift --version | tee "$run_dir/swift-version.txt"
python3 scripts/check_project.py
python3 -B -m unittest discover -s tests -p 'test_*.py' -v 2>&1 | tee "$run_dir/tool-tests.log"
plutil -lint CameraShell/Info.plist CameraShell/PrivacyInfo.xcprivacy CameraShell.xcodeproj/project.pbxproj
bash scripts/test-policy.sh | tee "$run_dir/policy-tests.log"
xcodebuild -project CameraShell.xcodeproj -scheme CameraShell \
    -configuration Release -sdk iphoneos -destination 'generic/platform=iOS' \
    -derivedDataPath "$run_dir/DerivedData" -archivePath "$archive" \
    CODE_SIGNING_ALLOWED=NO CODE_SIGNING_REQUIRED=NO CODE_SIGN_IDENTITY= DEVELOPMENT_TEAM= \
    archive 2>&1 | tee "$run_dir/xcodebuild.log"
app="$archive/Products/Applications/CameraShell.app"
test -d "$app"
plutil -lint "$app/Info.plist"
lipo "$app/CameraShell" -verify_arch arm64
if [[ -e "$app/_CodeSignature" || -e "$app/embedded.mobileprovision" ]]; then
    echo "Unexpected signature or provisioning profile in unsigned product." >&2
    exit 1
fi
if codesign -dv "$app" 2>/dev/null; then
    echo "Unexpected signed app; this flow must produce an unsigned IPA." >&2
    exit 1
fi
mkdir -p "$run_dir/package/Payload"
ditto "$app" "$run_dir/package/Payload/CameraShell.app"
(cd "$run_dir/package" && /usr/bin/zip -qry "$run_dir/CameraShell-unsigned.ipa" Payload)
python3 scripts/verify_ipa.py "$run_dir/CameraShell-unsigned.ipa"
(cd "$run_dir" && shasum -a 256 CameraShell-unsigned.ipa > CameraShell-unsigned.ipa.sha256)
echo "Unsigned IPA: $run_dir/CameraShell-unsigned.ipa"
echo "This file must be signed with a valid device provisioning profile before sideloading."
