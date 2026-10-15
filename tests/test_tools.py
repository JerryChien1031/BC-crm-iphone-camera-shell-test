"""Tool tests use synthetic fixtures; they do not build or validate a real iOS app."""
import contextlib
import importlib.util
import io
from pathlib import Path
import plistlib
import struct
import tempfile
import unittest
import warnings
import zipfile


ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / (name + ".py"))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


checker = module("check_project")
ipa = module("verify_ipa")


class ProjectParserTests(unittest.TestCase):
    def test_nested_plist(self):
        value = checker.OpenStepParser('// comment\n{ paths = (CameraShell/Info.plist, "a b",); child = { enabled = YES; }; }').parse()
        self.assertEqual(value, {"paths": ["CameraShell/Info.plist", "a b"], "child": {"enabled": "YES"}})

    def test_malformed_plist_rejected(self):
        for value in ("{ a = YES }", "{ a = 1; a = 2; }", "{ a = (b c); }", "{} {}"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                checker.OpenStepParser(value).parse()


class IPAInspectorTests(unittest.TestCase):
    def fixture(self, path, *, platform=2, cpu=0x0100000c, signed=False, extra=None):
        info = {
            "CFBundlePackageType": "APPL", "CFBundleExecutable": "CameraShell",
            "CFBundleIdentifier": "com.example.CameraShell", "NSCameraUsageDescription": "Test fixture",
            "UIDeviceFamily": [1], "MinimumOSVersion": "16.0", "CFBundleSupportedPlatforms": ["iPhoneOS"],
        }
        command = struct.pack("<6I", 0x32, 24, platform, 0x100000, 0x100000, 0)
        if signed:
            command += struct.pack("<4I", 0x1d, 16, 0, 0)
        binary = struct.pack("<8I", 0xfeedfacf, cpu, 0, 2, 2 if signed else 1, len(command), 0, 0) + command
        prefix = "Payload/CameraShell.app/"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr(prefix + "Info.plist", plistlib.dumps(info))
            archive.writestr(prefix + "PrivacyInfo.xcprivacy", plistlib.dumps({"NSPrivacyTracking": False}))
            archive.writestr(prefix + "CameraShell", binary)
            if extra:
                archive.writestr(*extra)

    def test_synthetic_device_fixture_passes(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory, contextlib.redirect_stdout(io.StringIO()):
            path = Path(directory) / "fixture.ipa"
            self.fixture(path)
            ipa.verify(path)

    def test_invalid_artifacts_rejected(self):
        cases = [
            {"platform": 7},  # Simulator arm64 is not a device build.
            {"cpu": 0x01000007},  # Intel simulator.
            {"signed": True},
            {"extra": ("Payload/CameraShell.app/embedded.mobileprovision", "profile")},
            {"extra": ("Payload/CameraShell.app/_CodeSignature/CodeResources", "signature")},
            {"extra": ("../outside", "path traversal")},
            {"extra": ("Payload/Other.app/Info.plist", "second app")},
            {"extra": ("Payload/CameraShell.app/Info.plist", "duplicate")},
        ]
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            for index, kwargs in enumerate(cases):
                with self.subTest(kwargs=kwargs), warnings.catch_warnings():
                    warnings.simplefilter("ignore", UserWarning)
                    path = Path(directory) / f"fixture-{index}.ipa"
                    self.fixture(path, **kwargs)
                    with self.assertRaises((AssertionError, ValueError)):
                        ipa.verify(path)


if __name__ == "__main__":
    unittest.main()
