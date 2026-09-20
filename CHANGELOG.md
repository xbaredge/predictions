# Changelog

Model and format changes, newest first. Published rows are never rewritten, so this file is how
a change in meaning is announced.

## 2026-09-20 — data sources withheld; a second reference price added

**This release rewrote published history.** Every commit was rebuilt to drop `odds_source`, the
column naming the bookmaker, exchange or feed behind each price. Odds feeds are licensed and
their terms on redistribution and attribution differ, so no file here names a venue any more.
Commit hashes before this date have changed. See `ERRATA.md` for exactly what moved and what
did not.

No probability, price or result was altered. The rewrite removed one column, renamed three and
added seven.

- **Removed** from `picks.csv`: `odds_source`.
- **Renamed**: the three fair-price columns, and their `_utc` partners, are now `fair_open`,
  `fair_at_publish` and `fair_close`. Their former names carried an abbreviation of the
  reference book's name in the prefix.
- **Added** to `picks.csv`: `open_median`, `open_median_utc`, `open_books` — the cross-book
  median price at the earliest capture taken, and how many books stood behind it.
- **Added** to `settled.csv`: `close_median`, `close_median_utc`, `close_books`,
  `clv_median_pct` — the same median at the last capture before kickoff, and CLV against it.
  It covers 30 of 34 settled legs where the de-vigged `clv_pct` covers 16, but it is the
  weaker measure and reads about 7 percentage points kinder. `METHODOLOGY.md` says why.
- `tools/verify.py` now reports both CLV bases and states which one to judge on.

## 2026-09-18 — first publication
- Ledger opens. Board, picks and settled files, one folder per ISO week.
- Probabilities served by `v3/binary`: one gradient-boosted model per market, plus the serving
  layer described in `METHODOLOGY.md`.
