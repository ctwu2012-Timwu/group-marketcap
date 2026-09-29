# CHANGELOG

## v1.0.5 — 2026-09-29
- 修正：回補時某市場當天休市或缺資料，改沿用前值並記漲跌 0%（原本會重複前一天的漲跌幅）

## v1.0.4 — 2026-09-29
- 修正：FII 歷史回補缺漏（Yahoo 的 CNYTWD=X 無歷史資料，導致 FII 走勢只有 1 天、相對表現恆為 0%）；匯率資料不足時改用美元交叉匯率（TWD=X ÷ CNY=X）
- 即時匯率備援同樣加入美元交叉匯率

## v1.0.3 — 2026-09-29
- 即時模式：Tailscale 網址連不到時，自動改試本機 http://127.0.0.1:8765（在 Mac Studio 本機開網頁也能看到即時資料）
- 已設定即時網址 https://timmac-studio.tailbb45a9.ts.net

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
