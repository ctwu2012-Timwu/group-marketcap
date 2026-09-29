#!/bin/bash
# 集團市值 Dashboard v1.0.2 — 每日同步（launchd 週一至週五 17:00 執行）
# 1) 從 GitHub 拉最新每日資料  2) 複製一份到 iCloud「AI Generated/MarketCap Dashboard」
set -u
REPO="${HOME}/Developer/group-marketcap"
ICLOUD="${HOME}/Library/Mobile Documents/com~apple~CloudDocs/1_Foxconn/0_2025/2025輪值CEO會議/AI Generated/MarketCap Dashboard"
LOG="${HOME}/Library/Logs/marketcap-sync.log"
ts() { date '+%Y-%m-%d %H:%M:%S'; }

{
  echo "[$(ts)] sync start"
  cd "${REPO}" || { echo "repo not found"; exit 1; }
  git pull --ff-only --quiet origin main || echo "[$(ts)] git pull 失敗（網路或衝突），沿用本機現有資料"
  mkdir -p "${ICLOUD}/data/daily" "${ICLOUD}/dashboard/data"
  rsync -a "${REPO}/data/daily/" "${ICLOUD}/data/daily/"          # 每日檔：只增不刪
  cp -f "${REPO}/data/history.csv" "${ICLOUD}/data/history.csv"
  rsync -a "${REPO}/docs/" "${ICLOUD}/dashboard/"                 # 可離線開啟的 Dashboard 副本
  echo "[$(ts)] sync done: $(ls "${ICLOUD}/data/daily" | wc -l | tr -d ' ') 份每日檔"
} >> "${LOG}" 2>&1
