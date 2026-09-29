# mac（Mac Studio 端）

| 檔案 | 用途 |
|---|---|
| `install.command` | 一鍵安裝：下載程式、Python 環境、launchd 服務、Tailscale HTTPS |
| `sync_to_icloud.sh` | 每日 17:00 由 launchd 執行：git pull 後同步資料到 iCloud |

服務記錄檔：`~/Library/Logs/marketcap-live.log`、`~/Library/Logs/marketcap-sync.log`
