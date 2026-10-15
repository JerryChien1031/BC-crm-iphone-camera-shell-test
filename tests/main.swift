import Foundation

var assertions = 0
func check(_ condition: @autoclosure () -> Bool, _ message: String) {
    assertions += 1
    if !condition() { fatalError("FAIL: \(message)") }
}

let policy = try SitePolicy.parse("  https://Example.com/demo?mode=1#camera  ")
check(policy.origin == HTTPSOrigin(scheme: "https", host: "example.com", port: 443), "normalized origin")
check(policy.allowsNavigation(to: URL(string: "https://EXAMPLE.com:443/next")), "same origin and explicit default port")
check(policy.allowsNavigation(to: URL(string: "https://example.com/photo?a=1#result")), "same origin path/query/fragment")
let rootPolicy = try SitePolicy.parse("https://example.com")
check(rootPolicy.startURL.absoluteString == "https://example.com/", "root path")
let customPort = try SitePolicy.parse("https://example.com:8443/")
check(customPort.allowsNavigation(to: URL(string: "https://example.com:8443/next")), "custom port")
check(!customPort.allowsNavigation(to: URL(string: "https://example.com/")), "custom port is separate")

for text in ["", "http://example.com/", "file:///etc/passwd", "javascript:alert(1)",
             "data:text/html,test", "example.com", "https:///", "https://", "https://example.com:0/",
             "https://example.com:65536/", "https://example.com:abc/", "https://user@example.com/",
             "https://user:pass@example.com/", "https://example.com/a b", "https://example.com/\npath",
             "https://example.com/\\other", "https://example.com/\u{0000}"] {
    do {
        _ = try SitePolicy.parse(text)
        fatalError("FAIL: accepted invalid URL \(text)")
    } catch { assertions += 1 }
}
for text in ["http://example.com/", "https://evil.example/", "https://sub.example.com/",
             "https://example.com.evil.test/", "https://example.com:8443/", "https://user@example.com/",
             "blob:https://example.com/id", "about:blank", "file:///test", "data:text/html,test"] {
    check(!policy.allowsNavigation(to: URL(string: text)), "blocked navigation: \(text)")
}
check(!policy.allowsNavigation(to: nil), "nil navigation")

func camera(
    scheme: String = "https", host: String = "example.com", port: Int = 0,
    main: Bool = true, frame: String? = "https://example.com/",
    page: String? = "https://example.com/", cameraOnly: Bool = true, active: Bool = true
) -> Bool {
    policy.allowsCameraRequest(
        scheme: scheme, host: host, port: port, isMainFrame: main,
        frameURL: frame.flatMap(URL.init(string:)), pageURL: page.flatMap(URL.init(string:)),
        cameraOnly: cameraOnly, isActive: active
    )
}
check(camera(), "main-frame matching camera request is eligible for prompting")
check(camera(host: "EXAMPLE.com", port: 443), "case and default port")
check(!camera(scheme: "http"), "camera HTTPS gate")
check(!camera(host: "evil.example"), "camera origin host")
check(!camera(port: 8443), "camera origin port")
check(!camera(main: false), "all iframes denied, including same-origin")
check(!camera(frame: "https://evil.example/"), "frame URL must match")
check(!camera(page: "https://evil.example/"), "visible page must match")
check(!camera(frame: nil), "missing frame URL")
check(!camera(page: nil), "missing page URL")
check(!camera(cameraOnly: false), "microphone and camera+microphone denied")
check(!camera(active: false), "inactive or dismantled view denied")

let suite = "CameraShell.PolicyTests.\(UUID().uuidString)"
let defaults = UserDefaults(suiteName: suite)!
defer { defaults.removePersistentDomain(forName: suite) }
let settings = SiteSettings(defaults: defaults)
check(settings.load() == nil, "first launch has no confirmed URL")
settings.save(policy)
check(SiteSettings(defaults: defaults).load() == policy, "saved URL round-trip")
settings.save(customPort)
check(settings.load() == customPort, "replace URL")
settings.clear()
check(settings.load() == nil, "forget URL")
defaults.set("http://bad.example/", forKey: SiteSettings.urlKey)
check(settings.load() == nil, "invalid persisted URL returns to setup")
print("PASS: \(assertions) native policy and settings assertions")
