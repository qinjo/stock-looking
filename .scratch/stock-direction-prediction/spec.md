# Spec: A-share next-day direction prediction

Status: ready-for-agent

## Problem Statement

I want a small-scale A-share stock prediction tool for my own investment reference. I care about whether a stock I follow is likely to close higher or lower on the next trading day (or the day after), so I have a data-driven reference signal rather than a guess. I don't want to build elaborate infrastructure or hunt for proprietary data — I want something cheap, free, and runnable with minimal effort, and I'm happy to stand on existing open-source work instead of writing everything from scratch.

## Solution

A minimal, configurable demo that:

1. Fetches A-share daily price/volume history for a configurable pool of stocks via `akshare` (free, MIT, no token, supports `前复权`).
2. Engineers price/volume/technical features (moving averages, RSI, MACD, volume ratio, position, lagged returns, turnover, amplitude, pct change).
3. Trains a **LightGBM** binary classifier to predict the **direction** (up vs down) of the next trading day's close.
4. Evaluates honestly with a chronological **walk-forward** backtest (expanding window, no look-ahead bias) and reports accuracy / AUC / confusion matrix / win rate against the baseline `up_rate`.
5. Is delivered both as a **Jupyter notebook** (explore + verify) and a **CLI** (`python -m stocklook`, daily use).
6. Keeps the stock pool and prediction horizon as parameters so I can swap in stocks I actually follow and choose next-day (`T+1`) or day-after (`T+2`).

The signal is framed as a **probabilistic reference signal with interpretable features**, not a guarantee: an individual stock's next-day direction is close to random (~50% over the long run), so realistic value comes from the probability, the feature importance, and honest backtest numbers — not from chasing high accuracy.

## User Stories

1. As a personal investor, I want to see whether a stock I follow is likely to close up or down on the next trading day, so that I have a quantitative reference signal for my own decisions.
2. As a personal investor, I want the tool to fetch real A-share daily history automatically, so that I don't have to manually gather price data.
3. As a personal investor, I want to use a free, no-token data source, so that I can start cheaply without signing up for anything.
4. As a personal investor, I want the stock pool to be configurable, so that I can model the stocks I actually care about rather than a fixed hard-coded set.
5. As a personal investor, I want a sensible default stock pool out of the box, so that I can run the demo immediately without additional configuration.
6. As a personal investor, I want to configure the prediction horizon (next day or day-after), so that I can look at the signal that matches my intended holding/decision window.
7. As a personal investor, I want the model to output a next-day up/down probability rather than just a hard call, so that I can gauge my confidence.
8. As a personal investor, I want to see per-stock evaluation metrics (accuracy, AUC, win rate, baseline up rate), so that I can judge whether the signal is worth trusting for a given stock.
9. As a personal investor, I want the backtest to be chronological and avoid look-ahead bias, so that the reported performance is honest and not over-optimistic.
10. As a personal investor, I want to see feature importance, so that I can understand what drives a given prediction and remain skeptical of black-box outputs.
11. As a personal investor, I want to run the tool from the command line on demand, so that I can use it as a quick daily check.
12. As a personal investor, I want to explore the steps interactively in a notebook, so that I can verify each stage (data, features, training, evaluation) and build familiarity before trusting it.
13. As a personal investor, I want to reuse existing open-source libraries (akshare, LightGBM, scikit-learn) rather than build everything from scratch, so that I stay minimal and maintainable.
14. As a personal investor, I want to start small with a handful of blue-chip stocks and expand later, so that I can validate the approach cheaply before scaling.
15. As a personal investor, I want to distinguish "up/down" at a configurable threshold sensitivity later (e.g., ignore tiny moves), so that I can reduce noisy near-zero predictions if needed.
16. As a maintainer, I want a clear module structure (data / features / model / config) with pure function boundaries, so that the demo is easy to extend and test.
17. As a maintainer, I want the prediction horizon and stock pool exposed as parameters, so that future iterations can sweep or configure them without rewriting logic.
18. As a maintainer, I want the core prediction logic decoupled from network I/O, so that it can be tested offline with synthetic or prepared data.

## Implementation Decisions

- **Data source**: `akshare`, interface `stock_zh_a_hist` (daily, `period="daily"`), with `前复权` (`adjust="qfq"`). It is free, MIT-licensed, and requires no token or registration.
- **Stock pool**: configurable list, default `600519`, `000001`, `300750`, `600036`, `601318`. Easily replaced by the user with the stocks they actually follow.
- **Prediction horizon**: a single integer parameter (`1` = next trading day, `2` = the day after). Implemented by shifting the label forward by the horizon; the default is `1`.
- **Target variable**: binary up/down classification. Label = `1` when the `前复权` close at `today + horizon` is strictly greater than today's close, else `0`. No threshold applied initially (a threshold to ignore tiny moves is a possible later tweak).
- **Model**: tabular **LightGBM** classifier (not LSTM/deep models) — suited to limited per-stock history, fast to train, interpretable feature importance. Engineered features include: simple returns and lagged returns (1/2/3/5), moving averages (5/10/20) and close-over-MA ratios, RSI(14), MACD (12/26/9 including signal line and histogram), volume ratio (volume / 5-day mean), 20-day position, plus the raw `振幅` (amplitude), `换手率` (turnover), and `涨跌幅` (pct change).
- **Evaluation**: chronological expanding-window **walk-forward** backtest (a minimum train window, then rolling test steps), to avoid look-ahead bias. Metrics reported: `n`, `up_rate` (baseline), `accuracy`, `auc`, `win_rate` (precision on the "up" class), and the confusion-matrix cells.
- **Delivery**: a Jupyter notebook for exploration/verification plus a CLI entry point (`python -m stocklook`) for on-demand daily use. Both read the same config/params.
- **Reuse strategy**: build a minimal demo from scratch, borrowing ideas from existing open-source stock-prediction repos but pulling only what's needed (data via akshare, model via LightGBM). Not a fork of a large repo.
- **Expectation-setting**: individual-stock direction is near-random; the output is a probability-weighted reference signal with interpretation, not a guarantee of accuracy.

## Testing Decisions

- **What makes a good test**: assert external behavior — the returned predictions and metrics are correct and well-formed — rather than internal implementation details.
- **Primary seam** (highest, the single integration seam): `walk_forward_eval(df, feature_cols, label_col, min_train, step) -> (y_true, y_pred, y_prob)`. Feed a prepared feature DataFrame (synthetic or fixture), assert the output shapes match the test rows, that probabilities lie in `[0, 1]`, and that predictions are produced chronologically (no future data in training). This exercises the whole "features → LightGBM → walk-forward" path without touching the network.
- **Pure unit seams**: `evaluate(y_true, y_pred, y_prob) -> metrics dict` (verify accuracy / AUC / win-rate / confusion-cell math against known small inputs); `build_label(df, horizon)` (verify the up/down label definition for both `horizon=1` and `horizon=2`, including the `NaN` tail at the end of the series).
- **Explicitly not a seam / excluded**: `fetch_history` (network I/O) — the data boundary; it is skipped or mocked in unit tests.
- **Prior art**: the repo currently has no tests; this spec establishes the initial lightweight test pattern (pytest) over the pure seams plus one integration test at `walk_forward_eval`.

## Out of Scope

- Actual trading, order execution, or portfolio construction.
- Position sizing, transaction costs, or slippage-aware backtesting.
- Chasing high prediction accuracy for individual stocks (near-random by nature).
- Non-tabular models (LSTM / transformers / attention) — deferred to a later expansion.
- News / social sentiment data integration (possible later; not in this minimal demo).
- Live streaming or intraday signals; daily-close scope only.
- Real-time scheduled automation (e.g., a cron job) — the CLI runs on demand.
- Multi-context repo layout or domain-doc content (`CONTEXT.md`/ADRs); not introduced here.
- Publising anything to GitHub Issues (the tracker is local-markdown in this repo).

## Further Notes

- akshare imports and the full pipeline were verified correct end-to-end on **synthetic data** during development (`auc ≈ 0.53`, `win_rate ≈ 0.52` > baseline `up_rate ≈ 0.52`). 
- A live data fetch could not be completed on the development machine: the eastmoney host's anti-bot reset the machine's outgoing connections (Python `requests` and, after repeated attempts, even `curl`), an IP/network-level block rather than a code issue. On a normal network (e.g., direct/China routing as configured in the user's proxy), `akshare` should fetch fine; if `RemoteDisconnected`/`ProxyError` is hit, route eastmoney directly in the proxy.
- On macOS, LightGBM requires OpenMP (`brew install libomp`).
- A minimal demo already exists in the repo (`stocklook/` package + `notebooks/demo.ipynb`) described and validated by this spec; future tickets extend it. The domain vocabulary (A-share, 前复权, T+1/T+2, walk-forward) is taken from the design conversation, as no `CONTEXT.md` glossary exists yet.
