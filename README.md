# Crack Spread Risk Monitor

A live dashboard tracking refining margins — the **3:2:1**, **gasoline**, and **distillate**
crack spreads — built from daily WTI, RBOB gasoline, and heating oil futures settlements.
Refreshes automatically every trading day via GitHub Actions and publishes to GitHub Pages.

 https://psaurav-01.github.io/Crack-spread-monitor/

## What it does

Refiners buy crude oil and sell refined products (gasoline, diesel/heating oil). The
**crack spread** approximates that margin per barrel of crude processed. It's a standard
proxy for refining profitability and a common hedge instrument on NYMEX. This project pulls
the three underlying futures contracts, computes the spreads, and layers on basic
market-risk metrics so the spread level can be read in the context of its own recent history —
not just in isolation.

- **3:2:1 crack** — the standard refinery yield ratio: 3 barrels of crude in, ~2 barrels of
  gasoline and 1 barrel of distillate out.
  `[(2 × RBOB + 1 × HO) × 42 − 3 × WTI] / 3`, in $/bbl
- **Gasoline crack (1:1)** — `RBOB($/bbl) − WTI`
- **Distillate crack (1:1)** — `HO($/bbl) − WTI`

For each spread, the dashboard computes:

| Metric | What it tells you |
|---|---|
| Z-score / percentile rank vs trailing 1Y | Is the current margin rich or cheap relative to its own recent regime |
| 1-day historical VaR (95% / 99%) | Plausible next-day downside move in the spread, from the trailing-year empirical distribution |
| 20D / 60D annualized volatility | How turbulent the spread has been recently vs longer-run |
| Cross-spread correlation | How much the gasoline and distillate cracks move together vs independently |

### Position & P&L

Enter a refining throughput (bbl/day) and a holding period, and the dashboard converts each
spread from $/bbl into:
- **Daily margin** — current spread × throughput
- **Period P&L swing** — last observed 1-day move × throughput × period (a rough read on realized turbulence)
- **VaR 95% / 99% in dollars** — 1-day VaR scaled to the holding period via √t, × throughput

This is intentionally simple but a  real refinery risk also accounts for actual hedge ratios,
correlation between legs when combining VaR (this dashboard sums them, which is
conservative/undiversified, not a true portfolio VaR), and basis risk between paper and
physical. Treat it as a way to translate price-level signals into dollar terms, not as a
production risk model.

## Project structure

```
.
├── docs/
│   ├── index.html       # the dashboard (GitHub Pages serves this)
│   └── data.json         # generated data — do not hand-edit
├── scripts/
│   └── build_data.py     # fetches futures data, computes spreads + risk metrics
├── .github/workflows/
│   └── refresh-data.yml  # runs build_data.py daily after settlement, commits data.json
└── requirements.txt
```

## Running locally

```bash
pip install -r requirements.txt
python scripts/build_data.py     # writes docs/data.json
open docs/index.html             # or just double-click it
```

## Hosting on GitHub Pages

1. Push this repo to GitHub.
2. **Settings → Pages → Source** → deploy from branch `main`, folder `/docs`.
3. The Actions workflow keeps `docs/data.json` current on its own — no server needed, since
   the dashboard is a static page that fetches `data.json` client-side.

## Data & limitations

- Source: NYMEX continuous front-month futures (`CL=F`, `RB=F`, `HO=F`) via Yahoo Finance,
  daily settlement.
- Continuous contracts splice consecutive expiries and can show roll-related noise around
  expiry dates — worth being aware of if you extend this toward real trading decisions.
- VaR is a simple 1-day historical simulation on the spread level, not position- or
  volume-weighted. It's a monitoring signal, not a hedging or trading recommendation.

## Possible extensions

- Position-weighted P&L (spread × hedged volume) instead of price-only signal
- Seasonality overlay (driving season vs. heating season effects)
- Swap out the static Yahoo pull for a live/intraday feed
- Alerting (Slack/email) when a spread crosses a z-score threshold

