import Foundation

struct SiteSettings {
    static let urlKey = "CameraShell.testSiteURL"
    let defaults: UserDefaults

    init(defaults: UserDefaults = .standard) { self.defaults = defaults }

    func load() -> SitePolicy? {
        guard let text = defaults.string(forKey: Self.urlKey) else { return nil }
        return try? SitePolicy.parse(text)
    }

    func save(_ policy: SitePolicy) {
        defaults.set(policy.startURL.absoluteString, forKey: Self.urlKey)
    }

    func clear() { defaults.removeObject(forKey: Self.urlKey) }
}
