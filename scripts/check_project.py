"""Portable structural checks, not a Swift compiler or an iOS runtime test.

Python 3.10+, standard library only. Writes validation-report.json inside ios-shell.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import plistlib
import re
import struct
import sys
import xml.etree.ElementTree as ET
import zlib

ROOT = Path(__file__).resolve().parents[1]


class OpenStepParser:
    """Parse the OpenStep plist subset used by this checked-in Xcode project."""
    def __init__(self, text):
        pattern = re.compile(r'\s+|//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|[{}()=;,]|[^\s{}()=;,"]+', re.S)
        self.tokens = []
        end = 0
        for match in pattern.finditer(text):
            if match.start() != end:
                raise ValueError(f"Invalid OpenStep token at {end}")
            token = match.group()
            end = match.end()
            if token.isspace() or token.startswith(("//", "/*")):
                continue
            self.tokens.append(token)
        if end != len(text):
            raise ValueError("Unparsed OpenStep input")
        self.index = 0

    def pop(self, expected=None):
        if self.index >= len(self.tokens):
            raise ValueError("Unexpected end of OpenStep plist")
        token = self.tokens[self.index]
        self.index += 1
        if expected is not None and token != expected:
            raise ValueError(f"Expected {expected}, got {token}")
        return token

    def value(self):
        token = self.pop()
        if token == "{":
            result = {}
            while self.tokens[self.index] != "}":
                key = self.value()
                if not isinstance(key, str) or key in result:
                    raise ValueError(f"Invalid or duplicate key: {key}")
                self.pop("=")
                result[key] = self.value()
                self.pop(";")
            self.pop("}")
            return result
        if token == "(":
            result = []
            while self.tokens[self.index] != ")":
                result.append(self.value())
                if self.tokens[self.index] == ",":
                    self.pop(",")
                elif self.tokens[self.index] != ")":
                    raise ValueError("Expected comma in array")
            self.pop(")")
            return result
        if token in "})=;,":
            raise ValueError(f"Unexpected token: {token}")
        return json.loads(token) if token.startswith('"') else token

    def parse(self):
        result = self.value()
        if self.index != len(self.tokens):
            raise ValueError("Trailing OpenStep input")
        return result


def load_plist(path):
    return plistlib.loads((ROOT / path).read_bytes())


def main():
    results = []

    def check(name, condition, detail=""):
        results.append({"name": name, "status": "PASS" if condition else "FAIL", "detail": detail})
        if not condition:
            raise AssertionError(f"{name}: {detail}")

    try:
        project = OpenStepParser((ROOT / "CameraShell.xcodeproj/project.pbxproj").read_text(encoding="utf-8-sig")).parse()
        objects = project["objects"]
        check("OpenStep project parses", bool(objects))
        check("Project root object", objects[project["rootObject"]]["isa"] == "PBXProject")

        def references(value):
            if isinstance(value, dict):
                for item in value.values():
                    yield from references(item)
            elif isinstance(value, list):
                for item in value:
                    yield from references(item)
            elif isinstance(value, str) and re.fullmatch(r"[A-F0-9]{24}", value):
                yield value

        check("All project object references resolve", all(ref in objects for ref in references(project)))
        source_files = {p.name for p in (ROOT / "CameraShell").glob("*.swift")}
        source_phase = next(o for o in objects.values() if o["isa"] == "PBXSourcesBuildPhase")
        compiled = {objects[objects[ref]["fileRef"]]["path"] for ref in source_phase["files"]}
        check("Every Swift app source is in Compile Sources", compiled == source_files and len(compiled) == 5)
        for obj in objects.values():
            if obj["isa"] == "PBXFileReference" and obj.get("sourceTree") == "<group>":
                check("Referenced file exists: " + obj["path"], (ROOT / "CameraShell" / obj["path"]).exists())
        resource_phase = next(o for o in objects.values() if o["isa"] == "PBXResourcesBuildPhase")
        resources = {objects[objects[ref]["fileRef"]]["path"] for ref in resource_phase["files"]}
        check("App resources included, Info.plist not copied", resources == {"Assets.xcassets", "PrivacyInfo.xcprivacy"})
        for obj in objects.values():
            if obj["isa"] == "XCBuildConfiguration":
                settings = obj["buildSettings"]
                if "INFOPLIST_FILE" in settings:
                    check(obj["name"] + " iPhone Swift target settings", settings["SWIFT_VERSION"] == "5.0"
                          and settings["TARGETED_DEVICE_FAMILY"] == "1"
                          and settings["INFOPLIST_FILE"] == "CameraShell/Info.plist"
                          and settings["DEVELOPMENT_TEAM"] == "")
                else:
                    check(obj["name"] + " deployment target", settings["IPHONEOS_DEPLOYMENT_TARGET"] == "16.0")
        scheme = ET.parse(ROOT / "CameraShell.xcodeproj/xcshareddata/xcschemes/CameraShell.xcscheme")
        check("Shared scheme resolves target", all(objects[n.attrib["BlueprintIdentifier"]]["isa"] == "PBXNativeTarget"
              for n in scheme.findall(".//BuildableReference")))
        check("Release archive configured", scheme.find("ArchiveAction").attrib["buildConfiguration"] == "Release")
        info = load_plist("CameraShell/Info.plist")
        check("Camera usage description present", bool(info.get("NSCameraUsageDescription")))
        check("No microphone, photo saving, ATS bypass or background modes", not any(key in info for key in (
            "NSMicrophoneUsageDescription", "NSPhotoLibraryUsageDescription", "NSPhotoLibraryAddUsageDescription",
            "NSAppTransportSecurity", "UIBackgroundModes")))
        privacy = load_plist("CameraShell/PrivacyInfo.xcprivacy")
        check("App-only UserDefaults reason declared", privacy["NSPrivacyAccessedAPITypes"] == [{
            "NSPrivacyAccessedAPIType": "NSPrivacyAccessedAPICategoryUserDefaults", "NSPrivacyAccessedAPITypeReasons": ["CA92.1"]}])
        check("Shell privacy declarations", privacy["NSPrivacyTracking"] is False and privacy["NSPrivacyCollectedDataTypes"] == [])
        catalog = ROOT / "CameraShell/Assets.xcassets/AppIcon.appiconset"
        asset = json.loads((catalog / "Contents.json").read_text())
        png = (catalog / asset["images"][0]["filename"]).read_bytes()
        check("1024 RGB app icon", png.startswith(b"\x89PNG\r\n\x1a\n")
              and struct.unpack(">IIBB", png[16:26]) == (1024, 1024, 8, 2))
        offset, image_data = 8, bytearray()
        while offset < len(png):
            length = struct.unpack_from(">I", png, offset)[0]
            kind = png[offset + 4:offset + 8]
            data = png[offset + 8:offset + 8 + length]
            crc = struct.unpack_from(">I", png, offset + 8 + length)[0]
            check("PNG chunk CRC: " + kind.decode(), crc == zlib.crc32(kind + data) & 0xffffffff)
            if kind == b"IDAT":
                image_data.extend(data)
            offset += 12 + length
        check("PNG pixel data decodes", len(zlib.decompress(image_data)) == 1024 * (1 + 1024 * 3))
        web = (ROOT / "CameraShell/CameraWebView.swift").read_text(encoding="utf-8")
        check("Permission source review guards", "allowed ? .prompt : .deny" in web
              and ".grant" not in web and "type == .camera" in web
              and "frame.isMainFrame" in web and "pageURL: webView.url" in web
              and "frameURL: frame.request.url" in web)
        check("Ephemeral WebView and inline preview configuration", ".nonPersistent()" in web
              and "allowsInlineMediaPlayback = true" in web
              and "mediaTypesRequiringUserActionForPlayback = []" in web)
        check("No TLS trust override, script bridge or camera script injection",
              "didReceive challenge" not in web and "evaluateJavaScript(" not in web
              and "WKScriptMessageHandler" not in web)
        check("Teardown stops native capture", "setCameraCaptureState(.none" in web
              and "setMicrophoneCaptureState(.none" in web and "coordinator.isValid = false" in web)
        for path in ROOT.rglob("*"):
            if path.is_file() and path.suffix in {".swift", ".sh", ".yml", ".pbxproj", ".plist", ".xcprivacy"} and "build" not in path.parts:
                check("UTF-8/LF: " + str(path.relative_to(ROOT)), b"\r" not in path.read_bytes()
                      and not path.read_bytes().startswith(b"\xef\xbb\xbf"))
        # Workflow is stored as JSON, a YAML 1.2 subset, so validation needs no pip dependencies.
        workflow = json.loads((ROOT / ".github/workflows/ios-unsigned.yml").read_text(encoding="utf-8"))
        job = workflow["jobs"]["unsigned-ipa"]
        check("Workflow manual trigger and least permissions", workflow["on"] == {"workflow_dispatch": {}}
              and workflow["permissions"] == {"contents": "read"})
        check("Workflow macOS runner", job["runs-on"] == "macos-15")
        check("Workflow invokes build script", any(step.get("run") == "bash scripts/build-unsigned.sh" for step in job["steps"]))
        check("Workflow retains IPA and evidence", sum(step.get("uses") == "actions/upload-artifact@v4" for step in job["steps"]) == 2)
        build_script = (ROOT / "scripts/build-unsigned.sh").read_text()
        check("Build disables signing and targets iOS devices", "CODE_SIGNING_ALLOWED=NO" in build_script
              and "CODE_SIGNING_REQUIRED=NO" in build_script and "generic/platform=iOS" in build_script
              and "-sdk iphoneos" in build_script and "scripts/verify_ipa.py" in build_script)
        check("Build runs native policy tests", "bash scripts/test-policy.sh" in build_script)
        for path in (ROOT / "scripts").glob("*.py"):
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
        check("Python tooling syntax", True)
        website = ROOT.parent
        baseline = json.loads((ROOT / "website-baseline.json").read_text(encoding="utf-8-sig"))
        if (website / "app.py").is_file():
            for item in baseline:
                target = website / item["path"]
                check("Website unchanged: " + item["path"], target.is_file()
                      and hashlib.sha256(target.read_bytes()).hexdigest() == item["sha256"])
        else:
            results.append({"name": "Website integrity", "status": "SKIP", "detail": "Standalone shell; parent website not included"})
    except Exception as error:
        results.append({"name": "Check failure", "status": "FAIL", "detail": str(error)})
    report = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(), "python": platform.python_version(),
        "scope": "Structural/source checks only. Not Swift typechecking, Xcode compilation or iPhone validation.",
        "results": results,
        "not_verified": ["Swift compilation and SDK compatibility", "Native policy test execution",
                         "Xcode archive and real IPA output", "iOS camera consent, preview and photos",
                         "Windows signing and iPhone sideloading"],
    }
    (ROOT / "validation-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    failures = [result for result in results if result["status"] == "FAIL"]
    print(f"Structural checks: {sum(r['status'] == 'PASS' for r in results)} passed, {len(failures)} failed")
    for failure in failures:
        print("FAIL: " + failure["name"] + ": " + failure["detail"])
    print("Report: " + str(ROOT / "validation-report.json"))
    return bool(failures)


if __name__ == "__main__":
    sys.exit(main())
