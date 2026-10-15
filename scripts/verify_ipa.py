"""Check a built unsigned device IPA. Works on macOS and Windows, stdlib only."""
import argparse
from pathlib import PurePosixPath
import plistlib
import struct
import zipfile


def verify(path):
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if archive.testzip() is not None:
            raise ValueError("ZIP CRC failure")
        if len(names) != len(set(names)):
            raise ValueError("Duplicate ZIP entries")
        for name in names:
            item = PurePosixPath(name)
            if item.is_absolute() or ".." in item.parts or "\\" in name:
                raise ValueError("Unsafe ZIP entry")
        app = "Payload/CameraShell.app/"
        if any(not name.startswith("Payload/") for name in names):
            raise ValueError("Unexpected IPA root")
        bundles = {PurePosixPath(n).parts[1] for n in names if len(PurePosixPath(n).parts) > 1}
        if bundles != {"CameraShell.app"}:
            raise ValueError("Expected exactly one CameraShell app")
        info = plistlib.loads(archive.read(app + "Info.plist"))
        assert info["CFBundlePackageType"] == "APPL"
        assert info["CFBundleExecutable"] == "CameraShell"
        assert info["NSCameraUsageDescription"]
        assert info["UIDeviceFamily"] == [1]
        assert float(info["MinimumOSVersion"]) >= 16
        assert "iPhoneOS" in info["CFBundleSupportedPlatforms"]
        assert "$" not in info["CFBundleIdentifier"]
        assert "NSMicrophoneUsageDescription" not in info
        assert "NSPhotoLibraryAddUsageDescription" not in info
        assert "NSAppTransportSecurity" not in info
        assert not any("_CodeSignature" in n or n.endswith("embedded.mobileprovision") for n in names)
        privacy = plistlib.loads(archive.read(app + "PrivacyInfo.xcprivacy"))
        assert privacy["NSPrivacyTracking"] is False
        binary = archive.read(app + info["CFBundleExecutable"])
        # This project builds a thin arm64 device executable, not a simulator or macOS app.
        assert binary[:4] == b"\xcf\xfa\xed\xfe", "Expected little-endian Mach-O 64"
        _, cpu, _, filetype, commands, _, _, _ = struct.unpack_from("<8I", binary)
        assert cpu == 0x0100000c and filetype == 2, "Expected arm64 executable"
        offset, platform = 32, None
        for _ in range(commands):
            command, length = struct.unpack_from("<II", binary, offset)
            assert length >= 8 and offset + length <= len(binary)
            assert command != 0x1d, "LC_CODE_SIGNATURE present in unsigned executable"
            if command == 0x32:  # LC_BUILD_VERSION
                platform = struct.unpack_from("<I", binary, offset + 8)[0]
            if command == 0x25:  # LC_VERSION_MIN_IPHONEOS on older toolchains
                platform = 2
            offset += length
        assert platform == 2, "Expected device iOS Mach-O platform (2), not iOS Simulator (7)"
    print("PASS: unsigned IPA structure, Info.plist, privacy manifest and arm64 iOS executable")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ipa")
    verify(parser.parse_args().ipa)
