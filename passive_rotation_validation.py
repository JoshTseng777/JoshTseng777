#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
passive_rotation_validation.py
================================================================================
被動元件跨市場輪動 Pilot 驗證 (JP / KR / TW / US)
Cross-market passive-components rotation validation — event study + lead-lag.

WHAT THIS DOES
--------------
1. Downloads daily adjusted closes via yfinance for the passive-components
   universe across Japan / Korea / Taiwan / US, plus local benchmarks.
   (auto_adjust=True -> split/dividend adjusted; a splits report is written so
   corporate actions -- e.g. Yageo 2327 splits -- can be verified by eye.)
2. Builds per-market equal-weight "purity Tier-A" baskets and RS lines
   (basket / local benchmark) -> currency-neutral by construction.
3. Detects mechanical "族群啟動" (group ignition) events per market:
       C1: RS line at a 60-trading-day high
       C2: basket index above its 60-day MA
       C3: breadth -- >= 2/3 of members above their own 20-day MA
       fresh trigger + 40-trading-day per-market cooldown
4. Detects "國際確認" (international confirmation): two DISTINCT external
   markets (JP/KR/US) fire within 14 calendar days of each other.
   Confirmation date = the later fire. 60-calendar-day cooldown.
   Classes (from Taiwan's perspective):
       C1_predictive : TW has NOT fired in the prior 28 calendar days
                       -> the tradeable claim ("外部先動、台灣還沒動")
       C2_confirm    : TW already fired -> does confirmation extend the move?
   Also logged: A_tw_alone = TW fires with no external fire in prior 28 days.
5. Event study: TW basket forward returns (raw + excess vs TAIEX) at
   5/10/20/60 trading-day horizons for each event class, benchmarked against
   a bootstrap of random dates (n=10,000, seed=42).
6. Lead-lag descriptives:
       - propagation matrix: P(Y fires within 14 cal days | X fired), all pairs
       - weekly RS log-change cross-correlations at lags -4..+4 weeks
       - leadership ratio: RS(Yageo vs TWII) / RS(Murata vs N225);
         60-day slope > 0  -> "TW-led / pricing cycle" (漲價型, 台系領先)
         60-day slope <= 0 -> "JP-led / spec cycle"   (規格型, 日系領先)
7. Prints PASS/FAIL against PRE-REGISTERED criteria (edit BEFORE running,
   never after) and a current-status dashboard for the latest data date.

USAGE
-----
    pip install yfinance pandas numpy matplotlib
    python passive_rotation_validation.py              # real run (downloads)
    python passive_rotation_validation.py --refresh    # force re-download
    python passive_rotation_validation.py --selftest   # synthetic-data check
                                                       # (no network needed)

OUTPUTS (./output/)
-------------------
    summary.json            all metrics (send this back)
    events.csv              per-market fires + confirmations + fwd returns
    propagation_matrix.csv  P(Y within 14d | X fired) + median gap days
    xcorr.csv               weekly RS cross-correlations by lag
    splits_report.csv       every split event per ticker (verify 2327 here)
    charts/*.png            RS lines, event paths, xcorr, leadership ratio
Raw downloads are cached append-style in ./data_raw/ (one CSV per ticker).

KNOWN LIMITATIONS (pilot)
-------------------------
    - Few independent sector cycles in 2016+ sample -> small N is expected;
      criteria below refuse to "pass" on insufficient N rather than pretend.
    - Survivorship: basket uses currently-listed names (Chilisin, KEMET etc.
      left mid-sample via M&A).
    - Purity: VSH (~half discrete semis) and SEMCO (camera/substrate mix) are
      their markets' only members -> treated as low-purity nodes; US/KR are
      confirmation inputs, never standalone conclusions.
================================================================================
"""

import argparse
import json
import os
import sys
import warnings
from datetime import timedelta

import numpy as np
import pandas as pd

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore", category=FutureWarning)

# ------------------------------------------------------------------------------
# CONFIG -- edit thresholds BEFORE running; do not tune after seeing results.
# ------------------------------------------------------------------------------
CONFIG = {
    "start": "2016-01-01",
    "rs_high_lookback": 60,       # RS line must be at a high of this many bars
    "ma_long": 60,                # basket above this MA
    "breadth_ma": 20,             # members above their own N-day MA
    "breadth_frac": 2.0 / 3.0,    # fraction of members required
    "market_cooldown_bars": 40,   # min trading days between fires, per market
    "intl_window_days": 14,       # calendar-day window pairing external fires
    "conf_cooldown_days": 60,     # calendar days between confirmations
    "tw_recent_days": 28,         # "TW already fired" lookback (calendar days)
    "horizons": [5, 10, 20, 60],  # forward-return horizons (TW trading days)
    "bootstrap_n": 10000,
    "seed": 42,
    "min_member_obs": 400,        # drop members with less usable history
}

# Pre-registered pass criteria for the C1_predictive class (20d horizon).
PASS_CRITERIA = {
    "min_events_C1": 6,           # below this: verdict = INSUFFICIENT N
    "hit_rate_min": 0.60,         # share of events with 20d excess > 0
    "median_excess_min": 0.0,     # median 20d excess return
    "bootstrap_pctile_min": 80.0, # mean 20d excess vs random-date baseline
}

# Universe. TW bare codes are resolved .TW -> .TWO automatically.
# tier_b members are downloaded (splits report / reference) but excluded from
# signal baskets unless noted.
UNIVERSE = {
    "JP": {
        "bench": ["^N225", "1321.T"],
        "members": {"6981.T": "Murata", "6976.T": "TaiyoYuden",
                    "6997.T": "NipponChemiCon", "6996.T": "Nichicon"},
        "tier_b": {"6762.T": "TDK"},  # battery-heavy -> excluded from basket
    },
    "KR": {
        "bench": ["^KS11", "069500.KS"],
        "members": {"009150.KS": "SEMCO"},  # purity caveat, sole KR node
        "tier_b": {},
    },
    "TW": {
        "bench": ["^TWII", "0050.TW"],
        "members": {"2327": "Yageo", "2492": "WalsinTech",
                    "3026": "HolyStone", "2472": "Lelon"},
        "tier_b": {"8042": "Chinsan", "6173": "PDC"},
    },
    "US": {
        "bench": ["^GSPC", "SPY"],
        "members": {"VSH": "Vishay"},  # purity caveat, sole US node
        "tier_b": {},
    },
}

EXTERNAL_MARKETS = ["JP", "KR", "US"]
TARGET_MARKET = "TW"

RAW_DIR = "data_raw"
OUT_DIR = "output"
CHART_DIR = os.path.join(OUT_DIR, "charts")


# ------------------------------------------------------------------------------
# Data layer
# ------------------------------------------------------------------------------
def _safe_name(ticker: str) -> str:
    return ticker.replace("^", "IDX_").replace(".", "_")


def _cache_path(ticker: str) -> str:
    return os.path.join(RAW_DIR, _safe_name(ticker) + ".csv")


def fetch_one(ticker: str, start: str, refresh: bool):
    """Return (close: Series, splits: Series) or (None, None) on failure."""
    path = _cache_path(ticker)
    if os.path.exists(path) and not refresh:
        df = pd.read_csv(path, parse_dates=["Date"], index_col="Date")
    else:
        try:
            import yfinance as yf
        except ImportError:
            sys.exit("yfinance not installed. Run: pip install yfinance")
        try:
            hist = yf.Ticker(ticker).history(start=start, auto_adjust=True)
        except Exception as exc:  # network / ticker errors
            print(f"    [warn] download failed for {ticker}: {exc}")
            return None, None
        if hist is None or hist.empty:
            return None, None
        idx = pd.to_datetime(hist.index)
        try:
            idx = idx.tz_localize(None)
        except TypeError:
            pass
        hist.index = idx.normalize()
        cols = {"Close": hist["Close"]}
        cols["StockSplits"] = (hist["Stock Splits"]
                               if "Stock Splits" in hist.columns
                               else pd.Series(0.0, index=hist.index))
        df = pd.DataFrame(cols)
        df.index.name = "Date"
        os.makedirs(RAW_DIR, exist_ok=True)
        df.to_csv(path)
    close = df["Close"].dropna()
    splits = df["StockSplits"]
    splits = splits[splits != 0.0]
    return close, splits


def resolve_tw(code: str, start: str, refresh: bool):
    """Try 2327 -> 2327.TW -> 2327.TWO. Returns (ticker, close, splits)."""
    if "." in code or not code.isdigit():
        c, s = fetch_one(code, start, refresh)
        return code, c, s
    for suffix in (".TW", ".TWO"):
        t = code + suffix
        c, s = fetch_one(t, start, refresh)
        if c is not None and len(c) > 0:
            return t, c, s
    return code, None, None


def load_real_data(refresh: bool):
    """Build {market: {"bench": Series, "members": DataFrame}} from yfinance."""
    data, splits_rows = {}, []
    for mkt, cfg in UNIVERSE.items():
        print(f"  [{mkt}] downloading ...")
        bench = None
        for bt in cfg["bench"]:
            bench, _ = fetch_one(bt, CONFIG["start"], refresh)
            if bench is not None and len(bench) > 500:
                print(f"    benchmark: {bt} ({len(bench)} bars)")
                break
        if bench is None:
            sys.exit(f"no benchmark available for {mkt}")
        members = {}
        for code, name in {**cfg["members"], **cfg["tier_b"]}.items():
            ticker, close, splits = (resolve_tw(code, CONFIG["start"], refresh)
                                     if mkt == "TW"
                                     else (code, *fetch_one(code, CONFIG["start"], refresh)))
            if close is None or len(close) < CONFIG["min_member_obs"]:
                print(f"    [warn] skipping {name} ({code}): insufficient data")
                continue
            in_basket = code in cfg["members"]
            print(f"    {name:<15} {ticker:<12} {len(close)} bars"
                  f"{'' if in_basket else '   [tier-B, excluded from basket]'}")
            if in_basket:
                members[name] = close
            if splits is not None:
                for d, ratio in splits.items():
                    splits_rows.append({"market": mkt, "name": name,
                                        "ticker": ticker,
                                        "date": d.strftime("%Y-%m-%d"),
                                        "split_ratio": ratio})
        if len(members) == 0:
            sys.exit(f"no usable members for {mkt}")
        data[mkt] = {"bench": bench, "members": pd.DataFrame(members)}
    os.makedirs(OUT_DIR, exist_ok=True)
    pd.DataFrame(splits_rows).to_csv(
        os.path.join(OUT_DIR, "splits_report.csv"), index=False)
    print(f"  splits_report.csv written ({len(splits_rows)} split events)"
          f" -- check Yageo/2327 rows to verify the Jul-2026 question.")
    return data


# ------------------------------------------------------------------------------
# Signal layer
# ------------------------------------------------------------------------------
def build_market_frame(bench: pd.Series, members: pd.DataFrame):
    """Align members to the benchmark calendar; build basket + conditions."""
    dates = bench.index
    m = members.reindex(dates).ffill(limit=3)
    rets = m.pct_change()
    basket_ret = rets.mean(axis=1)
    basket = (1.0 + basket_ret.fillna(0.0)).cumprod()
    rs = (basket / basket.iloc[0]) / (bench / bench.iloc[0])

    lookback = CONFIG["rs_high_lookback"]
    rs_max = rs.rolling(lookback, min_periods=lookback).max()
    c1 = rs >= rs_max * (1 - 1e-12)
    c2 = basket > basket.rolling(CONFIG["ma_long"],
                                 min_periods=CONFIG["ma_long"]).mean()
    above20 = m > m.rolling(CONFIG["breadth_ma"],
                            min_periods=CONFIG["breadth_ma"]).mean()
    breadth = above20.mean(axis=1)
    c3 = breadth >= CONFIG["breadth_frac"]
    cond_all = (c1 & c2 & c3).fillna(False)

    fresh = cond_all & ~cond_all.shift(1, fill_value=False)
    fires, last_pos = [], -10 ** 9
    idx = cond_all.index
    for pos in np.flatnonzero(fresh.to_numpy()):
        if pos - last_pos >= CONFIG["market_cooldown_bars"]:
            fires.append(idx[pos])
            last_pos = pos
    return {"bench": bench, "members": m, "basket": basket, "rs": rs,
            "cond": pd.DataFrame({"rs_high": c1, "above_ma": c2,
                                  "breadth_ok": c3, "all": cond_all,
                                  "breadth": breadth}),
            "fires": fires}


def find_confirmations(frames):
    """Pair fires from two distinct external markets within the window."""
    ext = []
    for mkt in EXTERNAL_MARKETS:
        ext += [(d, mkt) for d in frames[mkt]["fires"]]
    ext.sort(key=lambda x: x[0])
    win = timedelta(days=CONFIG["intl_window_days"])
    confs, last_conf = [], None
    for i in range(len(ext)):
        for j in range(i + 1, len(ext)):
            d1, m1 = ext[i]
            d2, m2 = ext[j]
            if d2 - d1 > win:
                break
            if m1 == m2:
                continue
            conf_date = d2
            if last_conf is not None and \
               (conf_date - last_conf).days < CONFIG["conf_cooldown_days"]:
                continue
            confs.append({"date": conf_date, "pair": f"{m1}+{m2}",
                          "first_fire": d1, "gap_days": (d2 - d1).days})
            last_conf = conf_date
            break
    tw_fires = frames[TARGET_MARKET]["fires"]
    recent = timedelta(days=CONFIG["tw_recent_days"])
    for c in confs:
        prior_tw = [d for d in tw_fires if c["date"] - recent <= d <= c["date"]]
        c["klass"] = "C2_confirm" if prior_tw else "C1_predictive"
    return confs


def tw_alone_events(frames):
    """TW fires with no external fire in the prior window."""
    win = timedelta(days=CONFIG["tw_recent_days"])
    ext_dates = [d for m in EXTERNAL_MARKETS for d in frames[m]["fires"]]
    out = []
    for d in frames[TARGET_MARKET]["fires"]:
        if not any(d - win <= e <= d for e in ext_dates):
            out.append(d)
    return out


# ------------------------------------------------------------------------------
# Event study layer
# ------------------------------------------------------------------------------
def forward_returns(frames, date):
    tw = frames[TARGET_MARKET]
    idx = tw["basket"].index
    pos = idx.searchsorted(pd.Timestamp(date))
    out = {}
    if pos >= len(idx):
        return out
    b0 = tw["basket"].iloc[pos]
    x0 = tw["bench"].iloc[pos]
    for h in CONFIG["horizons"]:
        if pos + h < len(idx):
            raw = tw["basket"].iloc[pos + h] / b0 - 1.0
            mkt = tw["bench"].iloc[pos + h] / x0 - 1.0
            out[h] = {"raw": raw, "excess": raw - mkt}
    return out


def bootstrap_baseline(frames):
    rng = np.random.default_rng(CONFIG["seed"])
    tw = frames[TARGET_MARKET]
    idx = tw["basket"].index
    h = 20
    lo, hi = CONFIG["rs_high_lookback"] + 5, len(idx) - h - 1
    if hi <= lo:
        return None
    picks = rng.integers(lo, hi, size=CONFIG["bootstrap_n"])
    b = tw["basket"].to_numpy()
    x = tw["bench"].to_numpy()
    exc = (b[picks + h] / b[picks] - 1.0) - (x[picks + h] / x[picks] - 1.0)
    return exc


def summarize_class(events_fwd, label):
    """events_fwd: list of dicts {horizon: {raw, excess}}."""
    out = {"class": label, "n": len(events_fwd)}
    for h in CONFIG["horizons"]:
        vals = [e[h]["excess"] for e in events_fwd if h in e]
        raws = [e[h]["raw"] for e in events_fwd if h in e]
        if vals:
            out[f"excess_{h}d_mean"] = float(np.mean(vals))
            out[f"excess_{h}d_median"] = float(np.median(vals))
            out[f"excess_{h}d_hit"] = float(np.mean([v > 0 for v in vals]))
            out[f"raw_{h}d_mean"] = float(np.mean(raws))
    return out


# ------------------------------------------------------------------------------
# Lead-lag descriptives
# ------------------------------------------------------------------------------
def propagation_matrix(frames):
    win = timedelta(days=CONFIG["intl_window_days"])
    mkts = list(UNIVERSE.keys())
    rows = []
    for x in mkts:
        for y in mkts:
            if x == y:
                continue
            xf, yf = frames[x]["fires"], frames[y]["fires"]
            hits, gaps = 0, []
            for d in xf:
                follow = [e for e in yf if d < e <= d + win]
                if follow:
                    hits += 1
                    gaps.append((min(follow) - d).days)
            rows.append({"from": x, "to": y, "n_from_fires": len(xf),
                         "p_follow_14d": hits / len(xf) if xf else np.nan,
                         "median_gap_days": float(np.median(gaps)) if gaps else np.nan})
    return pd.DataFrame(rows)


def weekly_xcorr(frames):
    weekly = {}
    for mkt in UNIVERSE:
        w = frames[mkt]["rs"].resample("W-FRI").last()
        weekly[mkt] = np.log(w).diff()
    rows = []
    tw = weekly[TARGET_MARKET]
    for mkt in EXTERNAL_MARKETS:
        pair = pd.concat({"tw": tw, "x": weekly[mkt]}, axis=1).dropna()
        for k in range(-4, 5):
            c = pair["tw"].corr(pair["x"].shift(k))
            rows.append({"external": mkt, "lag_weeks": k, "corr": c,
                         "note": "k>0: external leads TW by k weeks"})
    return pd.DataFrame(rows)


def leadership_ratio(frames):
    """RS(Yageo)/RS(Murata), each vs its own local index."""
    try:
        tw = frames["TW"]
        jp = frames["JP"]
        yageo = tw["members"]["Yageo"]
        murata = jp["members"]["Murata"]
    except KeyError:
        return None, None
    rs_y = (yageo / yageo.dropna().iloc[0]) / (tw["bench"] / tw["bench"].iloc[0])
    rs_m = (murata / murata.dropna().iloc[0]) / (jp["bench"] / jp["bench"].iloc[0])
    joined = pd.concat({"y": rs_y, "m": rs_m}, axis=1).ffill(limit=5).dropna()
    ratio = joined["y"] / joined["m"]
    slope = np.log(ratio).diff(60)
    return ratio, slope


def cycle_tag(slope, date):
    if slope is None:
        return "n/a"
    s = slope.reindex([pd.Timestamp(date)], method="ffill").iloc[0]
    if pd.isna(s):
        return "n/a"
    return "TW-led_pricing" if s > 0 else "JP-led_spec"


# ------------------------------------------------------------------------------
# Charts
# ------------------------------------------------------------------------------
def make_charts(frames, confs, ratio, slope, baseline):
    os.makedirs(CHART_DIR, exist_ok=True)
    # 1. RS lines with fires
    fig, ax = plt.subplots(figsize=(12, 6))
    for mkt in UNIVERSE:
        rs = frames[mkt]["rs"]
        ax.plot(rs.index, rs / rs.dropna().iloc[0], label=f"{mkt} RS", lw=1.2)
        for d in frames[mkt]["fires"]:
            ax.axvline(d, color="grey", alpha=0.12, lw=0.8)
    for c in confs:
        ax.axvline(c["date"], color="red", alpha=0.55, lw=1.0)
    ax.set_title("Passive-components RS vs local benchmark "
                 "(grey=market fires, red=international confirmations)")
    ax.legend()
    ax.set_yscale("log")
    fig.tight_layout()
    fig.savefig(os.path.join(CHART_DIR, "rs_lines.png"), dpi=130)
    plt.close(fig)

    # 2. Event paths: TW basket cumulative excess around C1 events
    tw = frames[TARGET_MARKET]
    idx = tw["basket"].index
    fig, ax = plt.subplots(figsize=(10, 6))
    paths = []
    for c in confs:
        if c["klass"] != "C1_predictive":
            continue
        pos = idx.searchsorted(pd.Timestamp(c["date"]))
        lo, hi = pos - 10, pos + 60
        if lo < 0 or hi >= len(idx):
            continue
        b = tw["basket"].iloc[lo:hi + 1].to_numpy()
        x = tw["bench"].iloc[lo:hi + 1].to_numpy()
        exc = (b / b[10]) / (x / x[10]) - 1.0
        ax.plot(range(-10, 61), exc, color="steelblue", alpha=0.45, lw=1)
        paths.append(exc)
    if paths:
        ax.plot(range(-10, 61), np.mean(paths, axis=0),
                color="navy", lw=2.5, label=f"mean (n={len(paths)})")
    if baseline is not None:
        q = np.percentile(baseline, [5, 95])
        ax.axhspan(q[0], q[1], color="orange", alpha=0.12,
                   label="random-date 20d 5-95% band")
    ax.axvline(0, color="red", lw=1)
    ax.axhline(0, color="black", lw=0.6)
    ax.set_title("TW basket cumulative excess return around C1_predictive events")
    ax.set_xlabel("trading days from international confirmation")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(CHART_DIR, "event_paths.png"), dpi=130)
    plt.close(fig)

    # 3. Weekly cross-correlation
    xc = weekly_xcorr(frames)
    fig, ax = plt.subplots(figsize=(9, 5))
    for mkt in EXTERNAL_MARKETS:
        sub = xc[xc["external"] == mkt]
        ax.plot(sub["lag_weeks"], sub["corr"], marker="o", label=mkt)
    ax.axvline(0, color="black", lw=0.6)
    ax.set_title("corr( TW weekly RS chg , external shifted by k )  "
                 "k>0 = external leads")
    ax.set_xlabel("lag k (weeks)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(CHART_DIR, "xcorr.png"), dpi=130)
    plt.close(fig)

    # 4. Leadership ratio
    if ratio is not None:
        fig, ax = plt.subplots(figsize=(12, 5))
        ax.plot(ratio.index, ratio, lw=1.2, color="darkgreen")
        ax.set_yscale("log")
        ax2 = ax.twinx()
        ax2.plot(slope.index, slope, lw=0.8, color="purple", alpha=0.5)
        ax2.axhline(0, color="purple", lw=0.5, ls="--")
        ax.set_title("Leadership ratio  RS(Yageo)/RS(Murata)  "
                     "(purple: 60d log slope; >0 = TW-led pricing cycle)")
        fig.tight_layout()
        fig.savefig(os.path.join(CHART_DIR, "leadership_ratio.png"), dpi=130)
        plt.close(fig)


# ------------------------------------------------------------------------------
# Orchestration
# ------------------------------------------------------------------------------
def run_pipeline(data):
    os.makedirs(OUT_DIR, exist_ok=True)
    frames = {mkt: build_market_frame(d["bench"], d["members"])
              for mkt, d in data.items()}

    confs = find_confirmations(frames)
    alone = tw_alone_events(frames)
    ratio, slope = leadership_ratio(frames)
    baseline = bootstrap_baseline(frames)

    # forward returns per class
    ev_rows = []
    for mkt in UNIVERSE:
        for d in frames[mkt]["fires"]:
            ev_rows.append({"type": "fire", "market": mkt,
                            "date": d.strftime("%Y-%m-%d")})
    class_fwd = {"C1_predictive": [], "C2_confirm": [], "A_tw_alone": []}
    for c in confs:
        fwd = forward_returns(frames, c["date"])
        class_fwd[c["klass"]].append(fwd)
        row = {"type": "confirmation", "market": c["pair"],
               "date": c["date"].strftime("%Y-%m-%d"),
               "class": c["klass"], "gap_days": c["gap_days"],
               "cycle_tag": cycle_tag(slope, c["date"])}
        for h, v in fwd.items():
            row[f"tw_excess_{h}d"] = round(v["excess"], 4)
            row[f"tw_raw_{h}d"] = round(v["raw"], 4)
        ev_rows.append(row)
    for d in alone:
        fwd = forward_returns(frames, d)
        class_fwd["A_tw_alone"].append(fwd)
        row = {"type": "tw_alone_fire", "market": "TW",
               "date": d.strftime("%Y-%m-%d"), "class": "A_tw_alone",
               "cycle_tag": cycle_tag(slope, d)}
        for h, v in fwd.items():
            row[f"tw_excess_{h}d"] = round(v["excess"], 4)
            row[f"tw_raw_{h}d"] = round(v["raw"], 4)
        ev_rows.append(row)

    pd.DataFrame(ev_rows).to_csv(os.path.join(OUT_DIR, "events.csv"),
                                 index=False)

    prop = propagation_matrix(frames)
    prop.to_csv(os.path.join(OUT_DIR, "propagation_matrix.csv"), index=False)
    xc = weekly_xcorr(frames)
    xc.to_csv(os.path.join(OUT_DIR, "xcorr.csv"), index=False)

    make_charts(frames, confs, ratio, slope, baseline)

    # ---- summary + verdict ----
    stats = {k: summarize_class(v, k) for k, v in class_fwd.items()}
    c1 = stats["C1_predictive"]
    verdict = {"criteria": PASS_CRITERIA}
    if c1["n"] < PASS_CRITERIA["min_events_C1"]:
        verdict["result"] = f"INSUFFICIENT_N (C1 events = {c1['n']})"
    else:
        mean20 = c1.get("excess_20d_mean", np.nan)
        pct = (float(np.mean(baseline < mean20)) * 100
               if baseline is not None else np.nan)
        checks = {
            "hit_rate": c1.get("excess_20d_hit", 0) >= PASS_CRITERIA["hit_rate_min"],
            "median": c1.get("excess_20d_median", -1) > PASS_CRITERIA["median_excess_min"],
            "vs_bootstrap": pct >= PASS_CRITERIA["bootstrap_pctile_min"],
        }
        verdict["checks"] = checks
        verdict["bootstrap_percentile_of_mean"] = pct
        verdict["result"] = "PASS" if all(checks.values()) else "FAIL"

    latest = {}
    for mkt in UNIVERSE:
        cond = frames[mkt]["cond"].iloc[-1]
        f = frames[mkt]["fires"]
        latest[mkt] = {
            "as_of": frames[mkt]["cond"].index[-1].strftime("%Y-%m-%d"),
            "rs_60d_high": bool(cond["rs_high"]),
            "basket_above_60ma": bool(cond["above_ma"]),
            "breadth": round(float(cond["breadth"]), 3),
            "all_conditions": bool(cond["all"]),
            "last_fire": f[-1].strftime("%Y-%m-%d") if f else None,
        }
    if slope is not None and len(slope.dropna()):
        latest["leadership_60d_slope"] = round(float(slope.dropna().iloc[-1]), 4)
        latest["cycle_tag_now"] = ("TW-led_pricing"
                                   if slope.dropna().iloc[-1] > 0
                                   else "JP-led_spec")

    summary = {
        "config": CONFIG, "pass_criteria": PASS_CRITERIA,
        "n_fires": {m: len(frames[m]["fires"]) for m in UNIVERSE},
        "n_confirmations": len(confs),
        "class_stats": stats,
        "verdict": verdict,
        "propagation_matrix": prop.to_dict(orient="records"),
        "current_status": latest,
    }
    with open(os.path.join(OUT_DIR, "summary.json"), "w") as fh:
        json.dump(summary, fh, indent=2, default=str)

    # ---- console report ----
    print("\n" + "=" * 70)
    print("FIRES PER MARKET :", summary["n_fires"])
    print("INTL CONFIRMATIONS:", len(confs),
          "| C1_predictive:", stats["C1_predictive"]["n"],
          "| C2_confirm:", stats["C2_confirm"]["n"],
          "| A_tw_alone:", stats["A_tw_alone"]["n"])
    for k in ("C1_predictive", "C2_confirm", "A_tw_alone"):
        s = stats[k]
        if s["n"]:
            print(f"  {k:<14} n={s['n']:<3} 20d excess: "
                  f"mean={s.get('excess_20d_mean', float('nan')):+.3%} "
                  f"median={s.get('excess_20d_median', float('nan')):+.3%} "
                  f"hit={s.get('excess_20d_hit', float('nan')):.0%}")
    print("VERDICT:", verdict["result"])
    print("-" * 70)
    print("CURRENT STATUS (latest bar):")
    for mkt in UNIVERSE:
        s = latest[mkt]
        print(f"  {mkt}: as_of={s['as_of']} all={s['all_conditions']} "
              f"rs_high={s['rs_60d_high']} >60MA={s['basket_above_60ma']} "
              f"breadth={s['breadth']} last_fire={s['last_fire']}")
    if "cycle_tag_now" in latest:
        print(f"  cycle tag now: {latest['cycle_tag_now']} "
              f"(leadership 60d slope={latest['leadership_60d_slope']})")
    print("=" * 70)
    print(f"outputs -> ./{OUT_DIR}/  (send back summary.json + events.csv"
          f" + splits_report.csv)")
    return summary


# ------------------------------------------------------------------------------
# Self-test with synthetic data (validates pipeline logic, no network)
# ------------------------------------------------------------------------------
def make_synthetic():
    rng = np.random.default_rng(7)
    dates = pd.bdate_range("2016-01-04", "2025-12-31")
    n = len(dates)

    def bench_series():
        r = rng.normal(0.0003, 0.010, n)
        return pd.Series(np.cumprod(1 + r), index=dates)

    # two sector-cycle episodes; JP leads, KR/US shortly after, TW last
    episodes = [int(n * 0.30), int(n * 0.65)]
    lead = {"JP": 0, "KR": 2, "US": 3, "TW": 5}  # business-day offsets

    def factor(offset):
        f = rng.normal(0.0, 0.004, n)
        for e in episodes:
            s = e + offset
            f[s: s + 45] += 0.006  # sustained sector impulse
        return f

    data = {}
    for mkt, cfg in UNIVERSE.items():
        bench = bench_series()
        fac = factor(lead[mkt])
        members = {}
        n_members = max(3, len(cfg["members"]))
        for i in range(n_members):
            idio = rng.normal(0.0, 0.006, n)
            r = 0.6 * bench.pct_change().fillna(0).to_numpy() + fac + idio
            name = (list(cfg["members"].values()) + [f"M{i}"])[i] \
                if i < len(cfg["members"]) else f"M{i}"
            members[name] = pd.Series(np.cumprod(1 + r) * 100, index=dates)
        data[mkt] = {"bench": bench, "members": pd.DataFrame(members)}
    return data


def selftest():
    print("SELFTEST: synthetic data, embedded lead-lag JP -> KR/US -> TW")
    summary = run_pipeline(make_synthetic())
    ok = True
    fires = summary["n_fires"]
    if not all(fires[m] >= 1 for m in ("JP", "TW")):
        print("  [FAIL] expected fires in JP and TW"); ok = False
    if summary["n_confirmations"] < 1:
        print("  [FAIL] expected >= 1 international confirmation"); ok = False
    c1 = summary["class_stats"]["C1_predictive"]
    if c1["n"] >= 1 and c1.get("excess_20d_mean", -1) <= 0:
        print("  [warn] C1 mean 20d excess not positive on synthetic data")
    for f in ("summary.json", "events.csv", "propagation_matrix.csv",
              "xcorr.csv"):
        if not os.path.exists(os.path.join(OUT_DIR, f)):
            print(f"  [FAIL] missing output {f}"); ok = False
    print("SELFTEST", "PASS" if ok else "FAIL")
    return 0 if ok else 1


# ------------------------------------------------------------------------------
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true",
                    help="force re-download of all tickers")
    ap.add_argument("--selftest", action="store_true",
                    help="run synthetic-data pipeline check (no network)")
    args = ap.parse_args()
    if args.selftest:
        sys.exit(selftest())
    print("Loading data via yfinance ...")
    real = load_real_data(refresh=args.refresh)
    run_pipeline(real)
