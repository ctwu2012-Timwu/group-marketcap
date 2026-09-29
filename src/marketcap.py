"""集團市值 Dashboard 核心模組 v1.0.0

共用於：
  - fetch_daily.py （GitHub Actions 每日收盤後存檔）
  - live_server.py （Mac Studio 盤中即時服務）

市值 = 最新股價 × 流通股數 × 匯率（換算新台幣）
匯率 = 臺灣銀行牌告「即期」買入/賣出中價；抓不到時改用 Yahoo 匯率並標註來源。
"""
from __future__ import annotations

import csv
import io
import json
import math
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "units.json"
TPE = timezone(timedelta(hours=8))
BOT_CSV_URL = "https://rate.bot.com.tw/xrt/flcsv/0/day"
UA = {"User-Agent": "Mozilla/5.0 (group-marketcap-dashboard)"}


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def now_tpe() -> datetime:
    return datetime.now(TPE)


# ---------------------------------------------------------------- 匯率
def fetch_bot_fx(currencies=("HKD", "CNY", "USD")) -> dict:
    """回傳 {'HKD': {'buy':..,'sell':..,'mid':..}, ..., '_time': '...'}；失敗丟例外。"""
    req = urllib.request.Request(BOT_CSV_URL, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        raw = r.read()
    text = raw.decode("utf-8-sig", errors="replace")
    out = {}
    for row in csv.reader(io.StringIO(text)):
        if not row or row[0].strip() not in currencies:
            continue
        cells = [c.strip() for c in row]
        try:
            bi = cells.index("本行買入")
            si = cells.index("本行賣出")
            buy = float(cells[bi + 2])   # 即期買入
            sell = float(cells[si + 2])  # 即期賣出
        except (ValueError, IndexError):
            continue
        if buy > 0 and sell > 0:
            out[cells[0]] = {"buy": buy, "sell": sell, "mid": round((buy + sell) / 2, 4)}
    if not out:
        raise RuntimeError("臺銀匯率 CSV 解析不到任何幣別")
    out["_source"] = "臺灣銀行即期中價"
    out["_time"] = now_tpe().strftime("%Y-%m-%d %H:%M")
    return out


def fetch_yahoo_fx(cfg: dict) -> dict:
    import yfinance as yf
    out = {}
    for cur, tk in cfg["fx"]["fallback_yahoo"].items():
        try:
            px = float(yf.Ticker(tk).fast_info["last_price"])
            out[cur] = {"buy": None, "sell": None, "mid": round(px, 4)}
        except Exception:
            pass
    out["_source"] = "Yahoo Finance 匯率（備援）"
    out["_time"] = now_tpe().strftime("%Y-%m-%d %H:%M")
    return out


def get_fx(cfg: dict) -> dict:
    try:
        fx = fetch_bot_fx()
    except Exception as e:  # noqa: BLE001
        print(f"[fx] 臺銀匯率失敗，改用 Yahoo：{e}")
        fx = fetch_yahoo_fx(cfg)
    fx["TWD"] = {"buy": 1.0, "sell": 1.0, "mid": 1.0}
    return fx


# ---------------------------------------------------------------- 股價
def _num(v):
    try:
        f = float(v)
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None


def fetch_quote(unit: dict) -> dict:
    """抓單一標的的最新價、前收、股數。"""
    import yfinance as yf
    t = yf.Ticker(unit["ticker"])
    fi = t.fast_info
    last = _num(fi.get("last_price"))
    prev = _num(fi.get("previous_close")) or _num(fi.get("regular_market_previous_close"))
    shares = _num(fi.get("shares"))
    shares_src = "yahoo"
    if not shares:
        try:
            shares = _num(t.info.get("sharesOutstanding"))
        except Exception:  # noqa: BLE001
            shares = None
    if not shares:
        shares, shares_src = float(unit["fallback_shares"]), "config"
    # 取最新一筆日K的日期，當作價格日期
    price_date = None
    try:
        h = t.history(period="5d", interval="1d", auto_adjust=False)
        if len(h):
            price_date = h.index[-1].strftime("%Y-%m-%d")
            if last is None:
                last = float(h["Close"].iloc[-1])
            if prev is None and len(h) > 1:
                prev = float(h["Close"].iloc[-2])
    except Exception:  # noqa: BLE001
        pass
    if last is None:
        raise RuntimeError(f"{unit['ticker']} 抓不到股價")
    return {"close": last, "prev_close": prev, "shares": shares,
            "shares_source": shares_src, "price_date": price_date}


def build_rows(cfg: dict, fx: dict, quotes: dict, stamp: str, method: str) -> list[dict]:
    rows = []
    for u in cfg["units"]:
        q = quotes.get(u["code"])
        if not q:
            continue
        rate = fx.get(u["currency"], {}).get("mid")
        if not rate:
            continue
        mcap_local = q["close"] * q["shares"]
        prev_local = q["prev_close"] * q["shares"] if q.get("prev_close") else None
        rows.append({
            "date": stamp[:10],
            "timestamp": stamp,
            "code": u["code"],
            "name": u["name"],
            "ticker": u["ticker"],
            "currency": u["currency"],
            "price_date": q.get("price_date") or stamp[:10],
            "close": round(q["close"], 4),
            "prev_close": round(q["prev_close"], 4) if q.get("prev_close") else "",
            "chg_pct": round((q["close"] / q["prev_close"] - 1) * 100, 3) if q.get("prev_close") else "",
            "shares": int(q["shares"]),
            "shares_source": q.get("shares_source", ""),
            "mcap_local": round(mcap_local),
            "fx": rate,
            "fx_source": fx.get("_source", "") if u["currency"] != "TWD" else "—",
            "mcap_twd": round(mcap_local * rate),
            "prev_mcap_twd": round(prev_local * rate) if prev_local else "",
            "method": method,
        })
    return rows


def snapshot(method: str = "close") -> dict:
    """抓全部標的，回傳 {'timestamp', 'fx', 'rows', 'errors'}。"""
    cfg = load_config()
    fx = get_fx(cfg)
    quotes, errors = {}, {}
    for u in cfg["units"]:
        try:
            quotes[u["code"]] = fetch_quote(u)
        except Exception as e:  # noqa: BLE001
            errors[u["code"]] = str(e)
    stamp = now_tpe().strftime("%Y-%m-%d %H:%M:%S")
    return {
        "timestamp": stamp,
        "fx": {k: v for k, v in fx.items()},
        "rows": build_rows(cfg, fx, quotes, stamp, method),
        "errors": errors,
    }
