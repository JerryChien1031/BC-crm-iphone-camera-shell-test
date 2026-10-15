# 相機與網站信任範圍

## 使用者與來源

- 首次沒有已確認網址時，App 不載入網頁。範例 HTTPS 網址只填在原生表單內，必須按「確認並載入網站」。
- UserDefaults 只保存一個經驗證的網址。讀回無效值會返回設定畫面；沒有保存 Shell 自行授予的相機同意旗標。
- 僅接受完整 HTTPS URL，拒絕帳密、空白、控制字元、反斜線與無效連接埠。預設連接埠視為 443。
- 導覽限制為使用者確認的精確 HTTPS origin：scheme + host + port。相同來源的不同路徑／query／fragment 可載入；子網域、其他連接埠、HTTP、file、data、blob 頂層導覽均不允許。
- 新視窗、所有子框架導覽與跨來源重新導向均取消，不自動跳到 Safari 或其他 App。切換網站須返回原生設定重新確認。
- 原生頂端持續顯示設定的來源；網頁內容不能修改此原生標籤。

## getUserMedia 相機請求

`WKUIDelegate` 的 `requestMediaCapturePermissionFor` 先檢查：

1. WebView 尚未被銷毀、可見，且 App 處於 active。
2. 僅要求 `.camera`；`.microphone` 與 `.cameraAndMicrophone` 都拒絕。
3. 發出請求的 frame 是主框架。
4. `WKSecurityOrigin` 的 HTTPS、主機與連接埠符合已確認來源。
5. frame URL 與目前 WebView URL 也都符合該來源。

任一不符便回傳 `.deny`。全部符合時回傳 **`.prompt`**，從不回傳 `.grant`。網站來源的同意由 WebKit 提示，App 層級的相機同意由 iOS 依 `NSCameraUsageDescription` 處理；網站確認和相機同意是獨立動作。實際提示次序、重複頻率與 OS 權限快取由 WebKit／iOS 控制，必須實機驗證。[Apple API 說明](https://developer.apple.com/documentation/webkit/wkuidelegate/webview(_:requestmediacapturepermissionfor:initiatedbyframe:type:decisionhandler:))

使用 `WKWebsiteDataStore.nonPersistent()`，每次重新載入、切換設定或從背景返回均重建 WebView，不把網站 cookie／工作階段持久保存。iOS 的 App 相機權限可能持續存在，清除網址不會重設系統權限，可到 App 系統設定調整。

## 擷取生命週期與網站邊界

- 設定網址、重新載入、進入背景時銷毀 WebView，先停止載入並呼叫 `setCameraCaptureState(.none)`、`setMicrophoneCaptureState(.none)` 與媒體關閉 API。
- 不在短暫 inactive 狀態銷毀，以免系統權限視窗出現時中斷自己的請求；真正進入 background 才重建。切換／鎖屏的相機停止時機仍須在 iPhone 驗證。
- 不注入相機 JavaScript、不建立 JS 原生橋接、不使用私有 API，不改寫既有 `getUserMedia`、預覽或 canvas 拍照。
- `allowsInlineMediaPlayback` 與免播放手勢設定用來允許已同意後的即時 video 預覽；它們不等於相機授權。
- 保留系統預設 TLS 驗證；沒有 ATS 例外、自簽憑證略過或 server-trust override。
- Shell 不宣告麥克風、相簿讀寫、背景相機、App Groups 或額外 entitlements。

導覽來源檢查是來源信任邊界，**不是對網站所有網路請求的內容防火牆**。使用者確認的網站及其同來源程式碼仍必須可信。WKNavigationDelegate 不會逐一攔截所有 script、fetch、圖片等子資源；Shell 不對任意新網站承諾「不會上傳照片」。現有 Flask 測試網站具備自己的 CSP、Permissions-Policy 與不上傳設計，這些均未更改。

現有網站的 HTML file input 備援由 WebKit／iOS 系統選圖或拍照 UI 處理，並非本 delegate 的 getUserMedia 流程。使用者仍須操作系統 UI；OS 是否保存原生備援相機照片取決於平台行為。本 Shell 沒有實作照片保存 API，也未宣稱能控制 OS 備援相機的儲存行為。

`PrivacyInfo.xcprivacy` 申報 Shell 使用 App 自身 UserDefaults 的 `CA92.1` 理由；不代表對使用者自行輸入網站的資料處理作出保證。[Apple UserDefaults 理由說明](https://developer.apple.com/documentation/bundleresources/app-privacy-configuration/nsprivacyaccessedapitypes/nsprivacyaccessedapitype)
