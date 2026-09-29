"""每日收盤市值存檔 v1.0.0（GitHub Actions 每個交易日 16:45 台北時間執行）

用法：
  python src/fetch_daily.py               # 抓今天收盤，寫入 history.csv 與每日檔
  python src/fetch_daily.py --backfill 365  # 先回補過去 N 天（估算），再抓今天

輸出：
  data/history.csv                     累加式歷史（同一天重跑會以最新一次取代該日）
  data/daily/marketcap_YYYYMMDD.csv    每日快照（同日重跑另存 _HHMM，不覆蓋）
  docs/data/latest.json                給 Dashboard 的最新一筆
  docs/data/history.json               給 Dashboard 的趨勢資料
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import marketcap as mc  # noqa: E402

DATA = mc.ROOT / "data"
DAILY = DATA / "daily"
HIST = DATA / "history.csv"
DOCS_DATA = mc.ROOT / "docs" / "data"
FIELDS = ["date", "timestamp", "code", "name", "ticker", "currency", "price_date",
          "close", "prev_close", "chg_pct", "shares", "shares_source", "mcap_local",
          "fx", "fx_source", "mcap_twd", "prev_mcap_twd", "method"]


def read_history() -> list[dict]:
    if not HIST.exists():
        return []
    with HIST.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def backfill(days: int, cfg: dict) -> list[dict]:
    """用日收盤價 × 目前股數 × 當日 Yahoo 匯率，估算過去 N 天的市值。"""
    import yfinance as yf
    start = (mc.now_tpe() - mc.timedelta(days=max(days, 5))).strftime("%Y-%m-%d")
    closes = {}
    for u in cfg["units"]:
        h = yf.Ticker(u["ticker"]).history(start=start, interval="1d", auto_adjust=False)
        closes[u["code"]] = {i.strftime("%Y-%m-%d"): float(c) for i, c in h["Close"].items()}
    fxs = {"TWD": None}
    for cur, tk in cfg["fx"]["fallback_yahoo"].items():
        h = yf.Ticker(tk).history(start=start, interval="1d", auto_adjust=False)
        fxs[cur] = {i.strftime("%Y-%m-%d"): float(c) for i, c in h["Close"].items()}
    shares = {}
    for u in cfg["units"]:
        try:
            shares[u["code"]] = mc.fetch_quote(u)["shares"]
        except Exception:  # noqa: BLE001
            shares[u["code"]] = float(u["fallback_shares"])

    all_dates = sorted({d for s in closes.values() for d in s})
    last_px, last_fx, prev_px = {}, {}, {}
    rows = []
    for d in all_dates:
        for cur, series in fxs.items():
            if series and d in series:
                last_fx[cur] = series[d]
        for u in cfg["units"]:
            c = u["code"]
            if d in closes[c]:
                if c in last_px:
                    prev_px[c] = last_px[c]
                last_px[c] = closes[c][d]
        if len(last_px) < len(cfg["units"]):
            continue
        for u in cfg["units"]:
            c, cur = u["code"], u["currency"]
            rate = 1.0 if cur == "TWD" else last_fx.get(cur)
            if not rate:
                continue
            px, pv = last_px[c], prev_px.get(c)
            loc = px * shares[c]
            rows.append({
                "date": d, "timestamp": f"{d} 16:45:00", "code": c, "name": u["name"],
                "ticker": u["ticker"], "currency": cur, "price_date": d,
                "close": round(px, 4), "prev_close": round(pv, 4) if pv else "",
                "chg_pct": round((px / pv - 1) * 100, 3) if pv else "",
                "shares": int(shares[c]), "shares_source": "current",
                "mcap_local": round(loc), "fx": round(rate, 4),
                "fx_source": "—" if cur == "TWD" else "Yahoo 歷史匯率（回補）",
                "mcap_twd": round(loc * rate),
                "prev_mcap_twd": round(pv * shares[c] * rate) if pv else "",
                "method": "backfill_est",
            })
    return rows


def merge(history: list[dict], new_rows: list[dict]) -> list[dict]:
    key = lambda r: (r["date"], r["code"])  # noqa: E731
    table = {key(r): r for r in history}
    for r in new_rows:
        old = table.get(key(r))
        # 正式收盤資料優先於回補估算
        if old and old.get("method") == "close" and r.get("method") == "backfill_est":
            continue
        table[key(r)] = {k: str(v) for k, v in r.items()}
    return sorted(table.values(), key=lambda r: (r["date"], r["code"]))


def export_json(history: list[dict], snap: dict, cfg: dict) -> None:
    DOCS_DATA.mkdir(parents=True, exist_ok=True)
    units = [{k: u[k] for k in ("code", "name", "ticker", "currency", "color")} for u in cfg["units"]]
    dates = sorted({r["date"] for r in history})
    idx = {d: i for i, d in enumerate(dates)}
    series = {u["code"]: [None] * len(dates) for u in units}
    method = ["backfill_est"] * len(dates)
    for r in history:
        if r["code"] in series:
            series[r["code"]][idx[r["date"]]] = int(float(r["mcap_twd"]))
            if r.get("method") == "close":
                method[idx[r["date"]]] = "close"
    (DOCS_DATA / "history.json").write_text(json.dumps({
        "generated": snap["timestamp"], "units": units, "dates": dates,
        "mcap_twd": series, "method": method,
    }, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (DOCS_DATA / "latest.json").write_text(json.dumps({
        "generated": snap["timestamp"], "mode": "close", "units": units,
        "fx": {k: v for k, v in snap["fx"].items() if k != "TWD"},
        "rows": snap["rows"], "errors": snap["errors"],
    }, ensure_ascii=False, indent=1), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backfill", type=int, default=0, help="回補天數（0 = 不回補）")
    args = ap.parse_args()
    cfg = mc.load_config()
    history = read_history()

    if args.backfill:
        bf = backfill(args.backfill, cfg)
        print(f"[backfill] {len(bf)} rows")
        history = merge(history, bf)

    snap = mc.snapshot(method="close")
    print(f"[today] {len(snap['rows'])} rows, errors={snap['errors']}")
    if not snap["rows"]:
        print("今天沒有抓到任何資料，保留原檔不變")
        return 1
    history = merge(history, snap["rows"])
    write_csv(HIST, history)

    ymd = snap["timestamp"][:10].replace("-", "")
    daily = DAILY / f"marketcap_{ymd}.csv"
    if daily.exists():
        daily = DAILY / f"marketcap_{ymd}_{snap['timestamp'][11:16].replace(':', '')}.csv"
    write_csv(daily, snap["rows"])

    export_json(history, snap, cfg)
    total = sum(r["mcap_twd"] for r in snap["rows"])
    print(f"[done] 集團合計 {total/1e8:,.0f} 億新台幣 → {daily.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
