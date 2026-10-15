# 驗證範圍與待辦

2026-10-15 在 Windows 執行。這份文件記錄已完成的檢查，不代表通過 Xcode 編譯或 iPhone 實機驗收。

## 已驗證

| 項目 | 結果與範圍 |
| --- | --- |
| 結構檢查 | `python -B scripts/check_project.py`：67 項通過，0 失敗。詳細項目與時間記錄在 `validation-report.json`。 |
| Xcode 專案結構 | 自訂 OpenStep 解析、物件引用、所有 5 個 Swift 來源的 Compile Sources membership、資源與 Info.plist、共享 scheme、iOS 16.0／Swift 5 設定。不是 Xcode 解析驗證。 |
| 權限設定 | plist／privacy manifest 可解析，存在相機用途說明；沒有麥克風、相簿儲存、ATS 放寬或背景模式。相機 gate 僅作來源碼靜態檢查。 |
| 圖示 | 1024×1024 不透明 RGB PNG，CRC 與像素資料可解碼，Asset Catalog 引用存在。 |
| Actions 定義 | JSON 語法（有效 YAML 子集）可解析，手動觸發、macOS Runner、唯讀權限、建置與 artifacts 步驟存在。尚未由 GitHub 執行。 |
| Bash 腳本 | Git for Windows Bash 對兩支 `.sh` 分別執行 `-n`，語法通過。未在 Windows 執行 Xcode 建置腳本。 |
| 工具測試 | `python -B -m unittest discover -s tests -p 'test_*.py' -v`：4 個測試通過；涵蓋 OpenStep 正反案例與 IPA 檢查器的合成案例。 |
| IPA 檢查器反例 | 合成的 simulator／Intel／含簽章／含 profile／多 App／重複 ZIP entry／路徑穿越等案例均被拒絕；合成合法案例通過。這不是實際 IPA 編譯。 |
| 原網站完整性 | `website-baseline.json` 所列原有檔案 SHA-256 均一致，包括 Python、相機 JS、HTML、樣式、圖示、啟動檔與原測試。 |
| 原網站回歸 | 在父目錄執行 `.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v`：原有 13 個 Flask／PWA 測試通過。 |

Git Bash 初次在程序沙箱內啟動遭 Windows namespace 存取限制；經授權在沙箱外執行唯讀語法檢查後成功，沒有更改 ACL 或系統設定。

未安裝 Swift／Apple SDK／Xcode；本機也未提供 Node.js 命令，因此沒有執行原網站的可選 Node DOM 相機測試。現有 JavaScript 內容完全未改動。

## 必須等 macOS／Actions

- Xcode 是否接受完整專案、共享 scheme、Asset Catalog 及 privacy manifest。
- SwiftUI／WebKit API 與實際 SDK 的型別檢查、連結與建置警告。
- `scripts/test-policy.sh` 編譯並執行真實 `SitePolicy.swift`／`SiteSettings.swift` 的 51 項 Swift assertions，涵蓋 HTTPS URL、精確來源、相機 frame／頁面／媒體類型、UserDefaults 保存、取代與清除。
- `xcodebuild archive` 是否成功，`.xcarchive` 是否包含正確 `.app`。
- 真實未簽署 IPA 的 `Payload`、編譯後 Info.plist、arm64 iOS device Mach-O、無簽章及雜湊檢查。
- GitHub Runner、artifact 產生及下載流程。此工作區目前沒有 Git repository／遠端設定，尚未發送任何原始碼或執行 CI。

`test-policy.sh` 是獨立命令列測試，不是 XCTest target；共享 scheme 不包含 XCTest。請執行腳本或完整 `build-unsigned.sh`，不要把 Xcode 的空 Test action 當成已跑過權限測試。

## 後續 iPhone 實機驗收

本階段不安裝至 iPhone。後續先完成免費簽署／側載，再記錄型號、iOS 版本、簽署方式與測試日期：

1. 首次啟動停在原生表單，尚未確認前沒有網頁請求或相機提示；確認 HTTPS 網址後載入原網站。
2. 結束 App 再啟動，恢復保存網址。修改與清除網址後再啟動，驗證保存值正確。
3. 點網站「開啟相機」，同意 WebKit／iOS 提示；確認後置鏡頭、內嵌即時預覽與完整照片，重複返回／拍照。
4. 拒絕權限、關閉 App 層權限後重試、從系統設定恢復，再確認網站錯誤提示及備援 UI。勿把 OS 的拒絕與 Shell URL 錯誤混為一談。
5. 預覽時切換設定、重新載入、背景切換或鎖屏，確認擷取與綠色相機指示停止；返回後從首頁重新操作。權限提示顯示中也測試離開 App 與切換網址，確認舊頁面不恢復相機。
6. 使用自有、受控 HTTPS 測試頁驗證跨來源 redirect／連結、新視窗、同來源與跨來源 iframe 的相機請求、音訊以及音訊＋視訊請求均被阻擋。原網站不需為此新增測試功能。
7. 測試 HTTP、帳密 URL、錯誤憑證與不同連接埠；設定或載入應拒絕／失敗，不略過 TLS。
8. 停止 Windows 伺服器、網路中斷或換 tunnel；確認錯誤提示、重新載入與重新設定網址能恢復。
9. 直向／橫向、瀏海與底部 safe area、網站 file input 備援與取消操作均可用。備援拍照的 OS 儲存行為另行記錄。

尚未驗證 Windows 簽署工具、免費 profile 續期、iPhone 側載、Developer Mode 或任何硬體相機行為。未簽署 IPA 無法直接安裝；成功 archive 也不等同上述實機驗收通過。
