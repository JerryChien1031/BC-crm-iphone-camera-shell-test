# iPhone 原生 CameraShell

SwiftUI + WKWebView 的最小 iPhone 原生專案，目標 iOS 16.0 以上、Xcode 16 以上，Swift 5 語言模式。無第三方套件、專案產生器、AI、資料庫、登入或原生相簿儲存功能。

**目前已建立原始碼與完整 Xcode 專案，通過 Windows 結構檢查；尚未在 macOS 編譯，尚未產生真實 IPA，也未完成 iPhone 相機實測。** 詳細證據見 `VALIDATION.md` 與執行檢查後產生的 `validation-report.json`。

所有新檔案均位於 `C:\Project\iphone-camera-pwa\ios-shell`。原 Flask、HTML、JavaScript、樣式、啟動檔與原網站測試檔均保留；不更改 ACL、全域設定、Harness 治理檔案或系統信任憑證。

## 操作與網址變更

1. 首次啟動先顯示原生網址表單，預填本次提供的範例：
   `https://premises-ripe-build-offset.trycloudflare.com/`。
2. 使用者檢查或修改網址，按「確認並載入網站」後才保存至 UserDefaults 並載入。
3. 在網站按既有「開啟相機」，依 WebKit／iOS 提示同意後進行即時預覽與拍照。Shell 不改寫網頁相機程式。
4. 頂端「設定網址」可隨時變更或清除保存值。「重新載入」會建立新的 WebView 工作階段。
5. App 進入背景會關閉目前 WebView／相機；返回前景時重新載入網站首頁。系統權限視窗導致的短暫 inactive 狀態不會觸發這次重建。

Windows 測試伺服器仍使用原本的啟動檔：

```powershell
& 'C:\Project\iphone-camera-pwa\start-dev.cmd'
```

啟動檔會啟動 Flask（127.0.0.1:8000）及 Cloudflare 臨時 tunnel。網址更換後，在 App 的「設定網址」輸入當次完整 HTTPS 網址，不必重建或重新安裝 App。範例網址只用來填入首次表單，不會追蹤 tunnel 變更，也不代表網址一直有效。原啟動檔含可見的 `cmd /k` 視窗；本階段未自動執行或修改它。

手機必須能透過網路連到運行中的 Windows／Flask／tunnel。App 不提供離線網站或永久網域，也不設定正式部署。

## 專案檔案

```text
CameraShell.xcodeproj/
  project.pbxproj                         完整 Xcode 專案，不需 XcodeGen
  xcshareddata/xcschemes/CameraShell.xcscheme
CameraShell/
  CameraShellApp.swift                    SwiftUI 入口
  ContentView.swift                       原生表單、工具列、生命週期
  CameraWebView.swift                     WKWebView 與導覽／權限代理
  SitePolicy.swift                        HTTPS 驗證與來源／相機規則
  SiteSettings.swift                      UserDefaults 保存、還原與清除
  Info.plist                             NSCameraUsageDescription
  PrivacyInfo.xcprivacy                   App 自身 UserDefaults 使用理由
  Assets.xcassets/AppIcon.appiconset/      不透明 1024px 相機圖示
scripts/
  check_project.py                       Windows/macOS 結構檢查
  test-policy.sh                         macOS 編譯並執行 Swift 規則測試
  build-unsigned.sh                      macOS archive 與未簽署 IPA 封裝
  verify_ipa.py                          真實產物的結構、平台、架構檢查
  generate_app_icon.py                   純標準函式庫幾何圖示產生器
tests/
  main.swift                            原生網址、來源、權限與保存測試
  test_tools.py                         工具測試，使用合成 IPA fixture
.github/workflows/ios-unsigned.yml        macOS Runner 手動建置流程
website-baseline.json                    原網站檔案 SHA-256 基準
README.md / SECURITY.md / VALIDATION.md
```

`AppIcon.png` 已附上，不需先執行產生器。圖示延用網站的幾何相機造型，產生器只輸出 Shell 圖示。

## Windows 可執行的檢查

```powershell
Set-Location 'C:\Project\iphone-camera-pwa\ios-shell'
python -B scripts/check_project.py
python -B -m unittest discover -s tests -p 'test_*.py' -v
& 'C:\Program Files\Git\bin\bash.exe' -n scripts/build-unsigned.sh
& 'C:\Program Files\Git\bin\bash.exe' -n scripts/test-policy.sh
```

前兩項只需 Python 3.10 以上標準函式庫，不需 pip。Bash 語法檢查需既有 Git for Windows；不需 WSL。`check_project.py` 的 OpenStep 解析器只支援本專案使用的格式，無法替代 Xcode 專案解析器。Swift 來源檢查僅檢查關鍵規則的存在，無法證明 SDK 型別相容或權限在裝置上正常工作。

## macOS Xcode 建置

將整個 `ios-shell` 目錄複製到 Mac，使用完整 Xcode 16 以上的開發工具。以 Xcode 開啟 `CameraShell.xcodeproj`，選擇共享 scheme `CameraShell`。不需先執行套件還原或專案產生器。

從該目錄執行：

```bash
bash scripts/build-unsigned.sh
```

腳本依序執行結構檢查、Python 工具測試、`plutil`、Swift 原生規則測試與 Release device archive。關鍵編譯設定如下：

```bash
xcodebuild -project CameraShell.xcodeproj -scheme CameraShell \
  -configuration Release -sdk iphoneos -destination 'generic/platform=iOS' \
  -archivePath build/CameraShell.xcarchive \
  CODE_SIGNING_ALLOWED=NO CODE_SIGNING_REQUIRED=NO CODE_SIGN_IDENTITY= DEVELOPMENT_TEAM= archive
```

完整腳本使用每次獨立的 `build/unsigned.XXXXXX/` 目錄，無需刪除既有建置結果。它將 archive 中的 `.app` 放入 `Payload/CameraShell.app` 並 ZIP 封裝，**不使用需要簽署資料的 `-exportArchive`**。

成功後會得到：

```text
build/unsigned.XXXXXX/CameraShell-unsigned.ipa
build/unsigned.XXXXXX/CameraShell-unsigned.ipa.sha256
build/unsigned.XXXXXX/CameraShell.xcarchive
build/unsigned.XXXXXX/xcodebuild.log
```

腳本記錄 Xcode／Swift 版本，檢查 Mach-O 是 arm64、iOS device 平台而非 Simulator，且沒有簽章或 provisioning profile。未簽署 IPA 是後續重新簽署的輸入檔，不能直接安裝。

本機若 Xcode 開發工具尚未被選取，可只為這次命令指定其路徑，例如 `DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer bash scripts/build-unsigned.sh`。本專案不執行全域 `xcode-select --switch`。

## GitHub Actions macOS Runner

GitHub 只會從**儲存庫根目錄的 `.github/workflows/`** 載入流程。本次所有產出受限於 `ios-shell`，因此沒有在其父目錄新增 workflow。[GitHub workflow 目錄規則](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)

最直接的配置方式是將 **`ios-shell` 的內容（包含 `.github`、`.gitattributes` 與 `.gitignore`）作為新 GitHub 儲存庫的根目錄**。這時 `.github/workflows/ios-unsigned.yml` 就能直接被辨識。原網站不必上傳。

如果未來把整個 Flask 專案上傳為儲存庫，則需要自行把這份 workflow 複製到儲存庫根目錄的 `.github/workflows/ios-unsigned.yml`。流程會辨識 Shell 在根目錄、`ios-shell/` 或 `iphone-camera-pwa/ios-shell/` 的情況；更深的自訂路徑需修改 locate 步驟。這次尚未複製到父目錄、建立遠端儲存庫、上傳或觸發 Actions。

流程檔使用 JSON 語法（YAML 的子集），副檔名仍為 `.yml`，方便 Windows 以標準函式庫解析檢查。

1. 將上述配置推送至 GitHub 預設分支。
2. 在 Actions 選擇 **Build unsigned iPhone CameraShell**，按 **Run workflow**。
3. Runner 使用 `macos-15` 上已選取的 Xcode，不需要 Apple ID、付費開發者會員或任何簽署 secrets。
4. 成功後下載 `CameraShell-unsigned-<run number>` artifact，解開外層 artifact ZIP，找到內層 `.ipa` 與 `.sha256`。另有 build evidence artifact，保留 7 天。
5. 如失敗，下載 evidence 並檢查 `xcodebuild.log`；Runner 的 Xcode 版本可能隨映像更新，實際版本會記錄在 artifact。

此流程只手動觸發，不會因 push 自動消耗 Runner。GitHub 使用額度／計費取決於儲存庫可見性與帳號方案；Apple 會員費與 GitHub Runner 額度是兩件事。[GitHub Runner 規則](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)

## 後續免費簽署與側載

本階段交付到原生專案與未簽署建置流程。未簽署建置不需要付費 Apple Developer Program，也不需要把 Apple 帳號交給 CI。

未來從 Windows 透過適用的簽署／側載工具，使用個人 Apple 帳號及對應裝置 profile 重新簽署；工具可能需要調整 `com.example.CameraShell` 為可用的唯一 Bundle ID。需確認 iPhone 與工具的 iOS 相容性、USB 配對／信任及 Developer Mode 等要求；本次沒有安裝、設定或驗證任何側載工具。

Apple 的免費 Personal Team provisioning profile 有 7 天期限，到期需重新簽署／安裝。Windows 工具如何實作簽署與續期，仍須在後續選定工具後驗證；此處不承諾已完成 Windows 簽署。[Apple 免費開發帳號與期限](https://developer.apple.com/help/account/basics/about-your-developer-account)

下一步是先跑一次 macOS Actions，確認原生編譯與真正 IPA 產物通過，再於後續階段驗證簽署、側載及 `VALIDATION.md` 的 iPhone 驗收清單。
