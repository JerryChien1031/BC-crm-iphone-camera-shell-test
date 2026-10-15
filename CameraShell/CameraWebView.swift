import SwiftUI
import UIKit
import WebKit

struct CameraWebView: UIViewRepresentable {
    let policy: SitePolicy
    let onStatus: (String?) -> Void

    func makeCoordinator() -> Coordinator { Coordinator(policy: policy, onStatus: onStatus) }

    func makeUIView(context: Context) -> WKWebView {
        let configuration = WKWebViewConfiguration()
        // Per-view ephemeral storage prevents old website sessions/permissions following URL changes.
        configuration.websiteDataStore = .nonPersistent()
        configuration.allowsInlineMediaPlayback = true
        configuration.mediaTypesRequiringUserActionForPlayback = []
        configuration.preferences.javaScriptCanOpenWindowsAutomatically = false
        let view = WKWebView(frame: .zero, configuration: configuration)
        view.navigationDelegate = context.coordinator
        view.uiDelegate = context.coordinator
        view.allowsBackForwardNavigationGestures = false
        view.load(URLRequest(url: policy.startURL))
        return view
    }

    func updateUIView(_ uiView: WKWebView, context: Context) {}

    static func dismantleUIView(_ view: WKWebView, coordinator: Coordinator) {
        coordinator.isValid = false
        view.stopLoading()
        view.setCameraCaptureState(.none, completionHandler: nil)
        view.setMicrophoneCaptureState(.none, completionHandler: nil)
        view.closeAllMediaPresentations(completionHandler: nil)
        view.navigationDelegate = nil
        view.uiDelegate = nil
        // No script injection into the existing camera implementation.
        view.loadHTMLString("", baseURL: nil)
    }

    final class Coordinator: NSObject, WKNavigationDelegate, WKUIDelegate {
        let policy: SitePolicy
        let onStatus: (String?) -> Void
        var isValid = true

        init(policy: SitePolicy, onStatus: @escaping (String?) -> Void) {
            self.policy = policy
            self.onStatus = onStatus
        }

        func webView(
            _ webView: WKWebView, decidePolicyFor navigationAction: WKNavigationAction,
            decisionHandler: @escaping (WKNavigationActionPolicy) -> Void
        ) {
            guard isValid, navigationAction.targetFrame?.isMainFrame == true,
                  policy.allowsNavigation(to: navigationAction.request.url) else {
                decisionHandler(.cancel)
                if isValid { onStatus("已阻擋非目前 HTTPS 來源的導覽、子框架或新視窗。請從「設定網址」確認新來源。") }
                return
            }
            decisionHandler(.allow)
        }

        func webView(
            _ webView: WKWebView, decidePolicyFor navigationResponse: WKNavigationResponse,
            decisionHandler: @escaping (WKNavigationResponsePolicy) -> Void
        ) {
            guard isValid, navigationResponse.isForMainFrame,
                  navigationResponse.canShowMIMEType,
                  policy.allowsNavigation(to: navigationResponse.response.url) else {
                decisionHandler(.cancel)
                if isValid { onStatus("已阻擋來源不符或無法在 App 內顯示的回應。") }
                return
            }
            decisionHandler(.allow)
        }

        func webView(
            _ webView: WKWebView, requestMediaCapturePermissionFor origin: WKSecurityOrigin,
            initiatedByFrame frame: WKFrameInfo, type: WKMediaCaptureType,
            decisionHandler: @escaping (WKPermissionDecision) -> Void
        ) {
            let allowed = policy.allowsCameraRequest(
                scheme: origin.protocol, host: origin.host, port: origin.port,
                isMainFrame: frame.isMainFrame, frameURL: frame.request.url,
                pageURL: webView.url, cameraOnly: type == .camera,
                isActive: isValid && webView.window != nil
                    && UIApplication.shared.applicationState == .active
            )
            // Never silently grant. WebKit presents origin consent; iOS manages the OS permission.
            decisionHandler(allowed ? .prompt : .deny)
        }

        func webView(
            _ webView: WKWebView, createWebViewWith configuration: WKWebViewConfiguration,
            for navigationAction: WKNavigationAction, windowFeatures: WKWindowFeatures
        ) -> WKWebView? {
            if isValid { onStatus("此測試 App 不開啟新視窗；可透過「設定網址」切換網站。") }
            return nil
        }

        func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
            if isValid { onStatus(nil) }
        }

        func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
            show(error)
        }

        func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) {
            show(error)
        }

        func webViewWebContentProcessDidTerminate(_ webView: WKWebView) {
            if isValid { onStatus("網頁程序已結束，請按「重新載入」。") }
        }

        private func show(_ error: Error) {
            guard isValid, (error as NSError).code != NSURLErrorCancelled else { return }
            onStatus("網站載入失敗：\(error.localizedDescription)。請確認 Windows 伺服器、HTTPS 網址與連線，或重新設定網址。")
        }
        // No TLS challenge override: invalid certificates fail using the system's default handling.
    }
}
