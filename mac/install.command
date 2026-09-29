#!/bin/bash
# ============================================================
#  集團市值 Dashboard — Mac Studio 一鍵安裝 v1.0.0
#  在 Mac Studio 上雙擊執行一次即可（可重複執行，不會重複安裝）
#  會做的事：
#   1. 從 GitHub 下載程式到 ~/Developer/group-marketcap
#   2. 建立 Python 環境並安裝 yfinance
#   3. 設定兩個背景服務（launchd）：
#        - 即時市值服務（開機自動啟動，常駐）
#        - 每日 17:00 同步資料到 iCloud
#   4. 用 Tailscale 以 HTTPS 分享即時服務（只有你的 Tailscale 裝置看得到）
#  不會修改任何系統設定、不需要 GitHub 密碼。
# ============================================================
set -u
REPO_URL="https://github.com/ctwu2012-Timwu/group-marketcap.git"
DEST="$HOME/Developer/group-marketcap"
ICLOUD="$HOME/Library/Mobile Documents/com~apple~CloudDocs/1_Foxconn/0_2025/2025輪值CEO會議/AI Generated/MarketCap Dashboard"
LA="$HOME/Library/LaunchAgents"
TS="/Applications/Tailscale.app/Contents/MacOS/Tailscale"
LIVE_LABEL="com.ctwu.marketcap.live"
SYNC_LABEL="com.ctwu.marketcap.sync"

step() { printf "\n\033[1;34m▶ %s\033[0m\n" "$1"; }
ok()   { printf "  \033[32m✓ %s\033[0m\n" "$1"; }
warn() { printf "  \033[33m! %s\033[0m\n" "$1"; }
die()  { printf "  \033[31m✗ %s\033[0m\n" "$1"; read -r -p "按 Enter 關閉視窗…" _; exit 1; }

echo "集團市值 Dashboard — Mac Studio 安裝 v1.0.0"
echo "電腦名稱：$(scutil --get ComputerName 2>/dev/null)"

step "1/6 檢查必要工具"
PY=""
for c in /opt/homebrew/bin/python3 /usr/local/bin/python3 /usr/bin/python3; do [ -x "$c" ] && PY="$c" && break; done
[ -n "$PY" ] || die "找不到 python3"
ok "Python：$($PY --version 2>&1)（$PY）"
command -v git >/dev/null || die "找不到 git（請先安裝 Xcode Command Line Tools：xcode-select --install）"
ok "git：$(git --version)"
[ -x "$TS" ] && ok "Tailscale 已安裝" || warn "找不到 Tailscale.app，即時服務只能在本機使用"

step "2/6 下載 / 更新程式"
mkdir -p "$(dirname "$DEST")"
if [ -d "$DEST/.git" ]; then
  git -C "$DEST" pull --ff-only --quiet origin main && ok "已更新到最新版" || warn "更新失敗，沿用現有版本"
else
  git clone --quiet "$REPO_URL" "$DEST" || die "無法從 GitHub 下載 $REPO_URL"
  ok "已下載到 $DEST"
fi
ok "版本：$(cat "$DEST/VERSION" 2>/dev/null)"

step "3/6 建立 Python 環境"
[ -x "$DEST/.venv/bin/python" ] || "$PY" -m venv "$DEST/.venv" || die "venv 建立失敗"
"$DEST/.venv/bin/pip" install --quiet --upgrade pip >/dev/null 2>&1
"$DEST/.venv/bin/pip" install --quiet yfinance || die "安裝 yfinance 失敗（請確認網路）"
ok "yfinance 已安裝"
echo "  測試抓取一次即時市值…"
"$DEST/.venv/bin/python" - <<'PYEOF' || warn "測試抓取失敗，稍後服務會自動重試"
import sys; sys.path.insert(0, "src")
import os; os.chdir(os.path.expanduser("~/Developer/group-marketcap")); sys.path.insert(0, "src")
import marketcap as mc
s = mc.snapshot("live")
for r in sorted(s["rows"], key=lambda r: -r["mcap_twd"]):
    print(f"   {r['code']:<4}{r['name']:<6} {r['mcap_twd']/1e8:>10,.0f} 億")
print(f"   合計 {sum(r['mcap_twd'] for r in s['rows'])/1e12:.2f} 兆新台幣　錯誤：{s['errors'] or '無'}")
PYEOF

step "4/6 設定背景服務（launchd）"
mkdir -p "$LA" "$HOME/Library/Logs"
chmod +x "$DEST/mac/sync_to_icloud.sh"
cat > "$LA/$LIVE_LABEL.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$LIVE_LABEL</string>
  <key>ProgramArguments</key><array><string>$DEST/.venv/bin/python</string><string>$DEST/src/live_server.py</string></array>
  <key>WorkingDirectory</key><string>$DEST</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>$HOME/Library/Logs/marketcap-live.log</string>
  <key>StandardErrorPath</key><string>$HOME/Library/Logs/marketcap-live.log</string>
</dict></plist>
EOF
cat > "$LA/$SYNC_LABEL.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$SYNC_LABEL</string>
  <key>ProgramArguments</key><array><string>/bin/bash</string><string>$DEST/mac/sync_to_icloud.sh</string></array>
  <key>StartCalendarInterval</key><array>
    <dict><key>Weekday</key><integer>1</integer><key>Hour</key><integer>17</integer><key>Minute</key><integer>0</integer></dict>
    <dict><key>Weekday</key><integer>2</integer><key>Hour</key><integer>17</integer><key>Minute</key><integer>0</integer></dict>
    <dict><key>Weekday</key><integer>3</integer><key>Hour</key><integer>17</integer><key>Minute</key><integer>0</integer></dict>
    <dict><key>Weekday</key><integer>4</integer><key>Hour</key><integer>17</integer><key>Minute</key><integer>0</integer></dict>
    <dict><key>Weekday</key><integer>5</integer><key>Hour</key><integer>17</integer><key>Minute</key><integer>0</integer></dict>
  </array>
</dict></plist>
EOF
for L in "$LIVE_LABEL" "$SYNC_LABEL"; do
  launchctl bootout "gui/$(id -u)/$L" >/dev/null 2>&1
  launchctl bootstrap "gui/$(id -u)" "$LA/$L.plist" && ok "$L 已啟用" || warn "$L 啟用失敗"
done
sleep 3
curl -fsS http://127.0.0.1:8765/api/health >/dev/null && ok "即時服務運作中（本機 127.0.0.1:8765）" || warn "即時服務尚未回應，請看 ~/Library/Logs/marketcap-live.log"

step "5/6 Tailscale HTTPS 分享"
LIVE_URL=""
if [ -x "$TS" ]; then
  if "$TS" serve --bg --https=443 http://127.0.0.1:8765 >/tmp/ts_serve.log 2>&1; then
    NAME=$("$TS" status --json 2>/dev/null | "$PY" -c 'import json,sys;print(json.load(sys.stdin)["Self"]["DNSName"].rstrip("."))' 2>/dev/null)
    LIVE_URL="https://$NAME"
    ok "已分享：$LIVE_URL"
    sleep 2
    curl -fsS "$LIVE_URL/api/health" >/dev/null && ok "HTTPS 連線測試成功" || warn "第一次申請 HTTPS 憑證可能需 1 分鐘，稍後會自動生效"
  else
    warn "Tailscale serve 失敗，通常是尚未開啟 HTTPS 憑證："
    sed 's/^/     /' /tmp/ts_serve.log | head -8
    echo "     → 請到 https://login.tailscale.com/admin/dns 開啟「MagicDNS」與「HTTPS Certificates」，再重新雙擊本檔。"
  fi
fi

step "6/6 同步資料到 iCloud 並記錄設定"
bash "$DEST/mac/sync_to_icloud.sh"
mkdir -p "$ICLOUD"
{
  echo "installed_at=$(date '+%Y-%m-%d %H:%M:%S')"
  echo "computer=$(scutil --get ComputerName 2>/dev/null)"
  echo "version=$(cat "$DEST/VERSION" 2>/dev/null)"
  echo "live_url=$LIVE_URL"
} > "$ICLOUD/install_status.txt"
ls "$ICLOUD/data/daily" >/dev/null 2>&1 && ok "iCloud 同步完成" || warn "iCloud 寫入失敗：請到「系統設定 › 隱私權與安全性 › 完整磁碟取用權限」加入「/bin/bash」後重跑"

echo
echo "================ 安裝完成 ================"
echo " 網址（所有裝置）：https://ctwu2012-timwu.github.io/group-marketcap/"
[ -n "$LIVE_URL" ] && echo " 即時服務：$LIVE_URL （已記錄到 iCloud install_status.txt）"
echo " 提醒：請在「系統設定 › 能源」開啟「防止在顯示器關閉時自動進入睡眠」，即時服務才能全天可用。"
echo " 手機 / iPad 需登入同一個 Tailscale 帳號才看得到即時資料。"
echo "=========================================="
read -r -p "按 Enter 關閉視窗…" _
