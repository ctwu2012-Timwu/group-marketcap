# src

| 檔案 | 用途 |
|---|---|
| `marketcap.py` | 共用核心：抓股價、股數、臺銀匯率，計算台幣市值 |
| `fetch_daily.py` | 每日收盤存檔（GitHub Actions 執行），可 `--backfill N` 回補 |
| `live_server.py` | 盤中即時服務（Mac Studio 常駐，127.0.0.1:8765） |
