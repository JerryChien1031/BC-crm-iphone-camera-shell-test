import SwiftUI
import UIKit

struct ContentView: View {
    @Environment(\.scenePhase) private var scenePhase
    @State private var site = SiteSettings().load()
    @State private var isEditing = false
    @State private var isBackgrounded = false
    @State private var pageID = UUID()
    @State private var statusMessage: String?

    var body: some View {
        NavigationStack {
            Group {
                if isEditing || site == nil {
                    URLSettingsView(currentURL: site?.startURL.absoluteString, canCancel: site != nil) { policy in
                        SiteSettings().save(policy)
                        site = policy
                        statusMessage = nil
                        pageID = UUID()
                        isEditing = false
                    } onCancel: {
                        isEditing = false
                    } onClear: {
                        SiteSettings().clear()
                        site = nil
                        statusMessage = nil
                    }
                } else if let site {
                    VStack(spacing: 0) {
                        Text(site.origin.displayName)
                            .font(.caption).textSelection(.enabled)
                            .padding(8).frame(maxWidth: .infinity)
                            .background(Color(uiColor: .secondarySystemBackground))
                        if let statusMessage {
                            Text(statusMessage).font(.callout).foregroundStyle(.red)
                                .padding().accessibilityLabel("網站狀態：\(statusMessage)")
                        }
                        if !isBackgrounded {
                            CameraWebView(policy: site) { statusMessage = $0 }
                                .id(pageID)
                        } else {
                            Color.clear
                        }
                    }
                }
            }
            .navigationTitle("相機測試")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                if site != nil && !isEditing {
                    ToolbarItem(placement: .navigationBarLeading) {
                        Button("設定網址") { statusMessage = nil; isEditing = true }
                    }
                    ToolbarItem(placement: .navigationBarTrailing) {
                        Button("重新載入") { statusMessage = nil; pageID = UUID() }
                    }
                }
            }
        }
        .onChange(of: scenePhase) { phase in
            // Permission dialogs may briefly make the scene inactive. Only tear down on background.
            if phase == .background { isBackgrounded = true }
            if phase == .active { isBackgrounded = false }
        }
    }
}

private struct URLSettingsView: View {
    let currentURL: String?
    let canCancel: Bool
    let onSave: (SitePolicy) -> Void
    let onCancel: () -> Void
    let onClear: () -> Void
    @State private var text = ""
    @State private var error: String?

    var body: some View {
        Form {
            Section("HTTPS 測試網址") {
                TextField("https://…", text: $text, axis: .vertical)
                    .keyboardType(.URL).textContentType(.URL)
                    .textInputAutocapitalization(.never).autocorrectionDisabled()
                    .accessibilityLabel("HTTPS 測試網址")
                Text("請先確認這是你信任的測試網站。網址會保存在此 App；Cloudflare 網址改變時可回來重新設定。")
                    .font(.footnote)
                if let error { Text(error).foregroundStyle(.red) }
                Button("確認並載入網站") {
                    do { onSave(try SitePolicy.parse(text)) }
                    catch { self.error = error.localizedDescription }
                }
            }
            Section("相機使用") {
                Text("確認網址不代表授予相機權限。網站要求相機時仍須同意 WebKit／iOS 權限提示；僅允許此 HTTPS 來源的主頁面提出相機請求。")
                Text("不開放麥克風。設定網址、重新載入或進入背景時，會關閉目前網頁與相機；返回後重新載入首頁。")
                Text("若已拒絕系統相機權限，可到 iPhone「設定」中的此 App 檢查相機權限。")
                Button("開啟此 App 的系統設定") {
                    if let url = URL(string: UIApplication.openSettingsURLString) {
                        UIApplication.shared.open(url)
                    }
                }
            }
            if canCancel {
                Section {
                    Button("取消並返回網站", action: onCancel)
                    Button("清除已保存網址", role: .destructive, action: onClear)
                }
            }
        }
        .onAppear { text = currentURL ?? SitePolicy.exampleURL }
    }
}
