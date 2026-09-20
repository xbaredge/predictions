# Changelog

Model and format changes, newest first. Published rows are never rewritten, so this file is how
a change in meaning is announced.

## 2026-09-20 — predictions are committed before kickoff, released after

From this date the day's predictions are no longer published on the morning they are made.
Instead `commitments/<date>.<batch>.sha256` is published before the fixtures it covers kick
off, holding the SHA-256 and row count of each of the four prediction files. The rows follow
once every fixture on that day's board is final, normally on the next morning's run. A date can
carry several batches, because the engine runs again as fixtures are added; a published hash is
never restated, so each later run commits only what the earlier ones did not.

A hash cannot be reversed and cannot be made to match different content, so this fixes exactly
what was predicted without revealing it while the matches are still to be played. It makes the
timing claim stronger rather than weaker: previously the commit timestamp was the only witness,
and now an anchored hash pins the exact bytes.

- `tools/verify.py` checks every commitment against the released rows and reports each run date
  as `released` or `embargoed`. A `MISMATCH` is a hard failure.
- `results.csv` and `settled.csv` are not embargoed — they describe matches already over.
- 2026-09-18 and 2026-09-19 were published in full on the day, under the previous scheme, and
  carry no commitment.

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
