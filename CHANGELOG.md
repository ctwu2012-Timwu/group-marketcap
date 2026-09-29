# CHANGELOG

## v1.0.2 — 2026-09-29
- 修正：一鍵安裝在 macOS 內建 bash 3.2 + 中文環境下，變數後接全形字元會被誤判（PY?: unbound variable），所有 shell 變數改為 ${VAR} 寫法

## v1.0.1 — 2026-09-29
- 修正：前一交易日收盤改由日K判定（Yahoo previous_close 收盤後會等於當日收盤，導致漲跌顯示 0%）
- 說明：GitHub Actions 雲端主機無法連線臺銀匯率，每日存檔改用 Yahoo 匯率備援並標註來源；Mac Studio 即時服務在台灣可正常使用臺銀匯率

## v1.0.0 — 2026-09-29
- 首版上線：五大次集團市值 Dashboard（桌面／手機自適應）
- 每日收盤存檔（GitHub Actions 16:45）＋ 首次自動回補 1 年
- 整合即時模式：自動偵測 Mac Studio 即時服務（Tailscale HTTPS），連不到時顯示收盤資料
- 匯率採臺灣銀行牌告即期中價，Yahoo 匯率備援
- Mac Studio 一鍵安裝：launchd 即時服務、每日 iCloud 同步
