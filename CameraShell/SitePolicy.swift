import Foundation

/// The only origin trusted by this WebView. A subdomain or a different port is a different origin.
struct HTTPSOrigin: Equatable {
    let host: String
    let port: Int

    init?(scheme: String, host: String, port: Int?) {
        guard scheme.lowercased() == "https", !host.isEmpty,
              (1...65535).contains(port ?? 443) else { return nil }
        self.host = host.lowercased()
        self.port = port ?? 443
    }

    init?(_ url: URL) {
        guard let parts = URLComponents(url: url, resolvingAgainstBaseURL: false),
              parts.user == nil, parts.password == nil,
              let scheme = parts.scheme, let host = parts.host else { return nil }
        self.init(scheme: scheme, host: host, port: parts.port)
    }

    var displayName: String { "https://\(host)\(port == 443 ? "" : ":\(port)")" }
}

struct SitePolicy: Equatable {
    static let exampleURL = "https://premises-ripe-build-offset.trycloudflare.com/"
    let startURL: URL
    let origin: HTTPSOrigin

    enum ValidationError: LocalizedError {
        case invalidHTTPSURL
        var errorDescription: String? {
            "請輸入完整有效的 HTTPS 網址；不可包含帳號、密碼、空白或無效連接埠。"
        }
    }

    static func parse(_ input: String) throws -> SitePolicy {
        let text = input.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty,
              !text.contains(where: { $0.isWhitespace || $0.isNewline }),
              !text.unicodeScalars.contains(where: { CharacterSet.controlCharacters.contains($0) }),
              !text.contains("\\"),
              var parts = URLComponents(string: text),
              parts.scheme?.lowercased() == "https",
              let host = parts.host, !host.isEmpty,
              parts.user == nil, parts.password == nil,
              let origin = HTTPSOrigin(scheme: "https", host: host, port: parts.port) else {
            throw ValidationError.invalidHTTPSURL
        }
        parts.scheme = "https"
        parts.host = host.lowercased()
        if parts.path.isEmpty { parts.path = "/" }
        guard let url = parts.url else { throw ValidationError.invalidHTTPSURL }
        return SitePolicy(startURL: url, origin: origin)
    }

    func allowsNavigation(to url: URL?) -> Bool {
        guard let url else { return false }
        return HTTPSOrigin(url) == origin
    }

    /// Shared, testable permission gate; WebKit must still ask for consent after it passes.
    func allowsCameraRequest(
        scheme: String, host: String, port: Int, isMainFrame: Bool,
        frameURL: URL?, pageURL: URL?, cameraOnly: Bool, isActive: Bool
    ) -> Bool {
        isActive && cameraOnly && isMainFrame
            && HTTPSOrigin(scheme: scheme, host: host, port: port == 0 ? nil : port) == origin
            && allowsNavigation(to: frameURL)
            && allowsNavigation(to: pageURL)
    }
}
