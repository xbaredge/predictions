# Changelog

Model and format changes, newest first. Published rows are never rewritten, so this file is how
a change in meaning is announced.

## 2026-11-25 — the ledger opens

- The record starts on 20 November 2026, with the website's track record. The predictions from
  20 November until today were first committed in the pre-launch ledger,
  [`predictions-prelaunch-v1-2026`](https://github.com/xbaredge/predictions-prelaunch-v1-2026),
  and are carried over as `METHODOLOGY.md` describes: commitments and timestamp proofs byte for
  byte, picks re-issued at the website's price in `picks_reissued.csv`.
- Every price is the one the website showed: the average of at least three bookmakers (`mean`),
  a pick's minimum price (`min`), or the model's own estimate where no bookmaker quoted the market
  (`estimate`). Reference prices are averages of at least three bookmakers. No price is one
  bookmaker's or exchange's quote, and no fair price is derived from a single bookmaker.
- Early picks are included from the start, with their own commitments (`commitments/early/`) and
  files (`early.csv`, `early_settled.csv`).
- Probabilities are served by `v3/binary`: one gradient-boosted model per market, plus the serving
  layer described in `METHODOLOGY.md`. The `model` column reads `v3/binary/published`: the
  probability is the one the website shows.
