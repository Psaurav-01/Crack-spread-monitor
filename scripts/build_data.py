"""
build_data.py
Pulls WTI, RBOB, and Heating Oil futures, computes the 3:2:1, gasoline, and
distillate crack spreads, derives risk metrics, and writes docs/data.json —
the single data file the dashboard reads at load time.

Run manually:
    python scripts/build_data.py

Runs automatically once a day via .github/workflows/refresh-data.yml
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

TICKERS = {"WTI": "CL=F", "RBOB": "RB=F", "HO": "HO=F"}
LOOKBACK = "2y"
GAL_PER_BBL = 42
OUT_PATH = Path(__file__).resolve().parent.parent / "docs" / "data.json"


def fetch_prices() -> pd.DataFrame:
    raw = {}
    for name, ticker in TICKERS.items():
        df = yf.download(ticker, period=LOOKBACK, interval="1d",
                          progress=False, auto_adjust=True)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        raw[name] = df["Close"]
    prices = pd.DataFrame(raw).dropna()
    if prices.empty:
        raise RuntimeError("No price data returned — check tickers / network access.")
    return prices


def compute_spreads(prices: pd.DataFrame) -> pd.DataFrame:
    df = prices.copy()
    df["RBOB_bbl"] = df["RBOB"] * GAL_PER_BBL
    df["HO_bbl"] = df["HO"] * GAL_PER_BBL
    df["Crack_321"] = (2 * df["RBOB_bbl"] + df["HO_bbl"] - 3 * df["WTI"]) / 3
    df["Crack_Gasoline"] = df["RBOB_bbl"] - df["WTI"]
    df["Crack_Distillate"] = df["HO_bbl"] - df["WTI"]
    return df


def build_metrics(df: pd.DataFrame, spreads: list[str]) -> dict:
    metrics = {}
    for s in spreads:
        ser = df[s]
        chg = ser.diff().dropna()
        window = ser[-252:]
        current = ser.iloc[-1]
        mean_1y, std_1y = window.mean(), window.std()
        metrics[s] = {
            "current": round(current, 2),
            "mean1y": round(mean_1y, 2),
            "std1y": round(std_1y, 2),
            "min1y": round(window.min(), 2),
            "max1y": round(window.max(), 2),
            "zscore": round((current - mean_1y) / std_1y, 2),
            "percentileRank": round((window < current).mean() * 100, 1),
            "vol20dAnnualized": round(chg[-20:].std() * np.sqrt(252), 2),
            "vol60dAnnualized": round(chg[-60:].std() * np.sqrt(252), 2),
            "var95_1d": round(np.percentile(chg[-252:], 5), 2),
            "var99_1d": round(np.percentile(chg[-252:], 1), 2),
            "chg1d": round(ser.iloc[-1] - ser.iloc[-2], 2),
            "chg5d": round(ser.iloc[-1] - ser.iloc[-6], 2),
            "chg1m": round(ser.iloc[-1] - ser.iloc[-22], 2),
        }
    return metrics


def build_payload(df: pd.DataFrame) -> dict:
    spreads = ["Crack_321", "Crack_Gasoline", "Crack_Distillate"]
    legs = ["WTI", "RBOB", "HO"]

    series = {}
    for col in spreads:
        series[col] = [{"d": d.strftime("%Y-%m-%d"), "v": round(v, 2)} for d, v in df[col].items()]
    for col in legs:
        series[col] = [{"d": d.strftime("%Y-%m-%d"), "v": round(v, 3)} for d, v in df[col].items()]

    corr = df[spreads].diff().dropna().corr().round(2).to_dict()

    return {
        "asOf": df.index[-1].strftime("%Y-%m-%d"),
        "series": series,
        "metrics": build_metrics(df, spreads),
        "correlations": corr,
    }


def main():
    prices = fetch_prices()
    df = compute_spreads(prices)
    payload = build_payload(df)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload))
    print(f"Wrote {OUT_PATH} — as of {payload['asOf']}, "
          f"3:2:1 = ${payload['metrics']['Crack_321']['current']}/bbl")


if __name__ == "__main__":
    main()
