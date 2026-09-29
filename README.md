# 集團市值監控 Dashboard

五大次集團（FII、FHH、FIT、FVT、FIH）上市公司市值，統一換算新台幣。
**一個網址、一個畫面**：平常顯示每日收盤存檔；能連到 Mac Studio 時自動切換成盤中即時。

**網址：https://ctwu2012-timwu.github.io/group-marketcap/**

## Why
- 隨時掌握各單位市值與排名，會議上可即時引用。
- 每日自動存檔，累積可追溯的歷史趨勢。

## What
| 代號 | 公司 | 代碼 | 幣別 |
|---|---|---|---|
| FII | 工業富聯 | 601138.SS | CNY |
| FHH | 鴻海精密 | 2317.TW | TWD |
| FIT | 鴻騰精密 | 6088.HK | HKD |
| FVT | 鴻華先進 | 2258.TW | TWD |
| FIH | 富智康 | 2038.HK | HKD |

- 市值 = 股價 × 流通股數（Yahoo Finance）× 匯率
- 匯率 = 臺灣銀行牌告即期「買入／賣出中價」；取不到時改用 Yahoo 匯率並標註
- 增減單位：只改 `config/units.json`

## How
| 元件 | 位置 | 時間 |
|---|---|---|
| 每日收盤存檔 | GitHub Actions `.github/workflows/daily.yml` | 週一至週五 16:45（台北） |
| Dashboard | GitHub Pages（`docs/`） | 每次存檔後自動部署 |
| 盤中即時服務 | Mac Studio `src/live_server.py`（launchd 常駐） | 每 60 秒 |
| 跨裝置安全存取 | Tailscale HTTPS（只有自己的 tailnet 可連） | — |
| iCloud 備份 | Mac Studio `mac/sync_to_icloud.sh` | 週一至週五 17:00 |

### 資料檔
- `data/history.csv`：全部歷史（`method` = `close` 正式收盤／`backfill_est` 回補估算）
- `data/daily/marketcap_YYYYMMDD.csv`：每日快照，不覆蓋
- `docs/data/latest.json`、`docs/data/history.json`：Dashboard 讀取用

### 即時服務設定
Mac Studio 雙擊 `mac/install.command` 一次。完成後把 `install_status.txt` 裡的 `live_url` 填進 `docs/config.json` 的 `liveUrl`。
臨時指定：網址加 `?live=https://<mac>.<tailnet>.ts.net`（會記在該裝置）。

### 注意
- 回補的歷史市值以「當日收盤價 × 目前股數」估算，未反映期間的股數變動。
- 漲跌配色依台股慣例：紅漲綠跌。

版本紀錄見 `CHANGELOG.md`。
