# Errata

Corrections, newest first. A published row is never edited or deleted; if something is wrong it
is stated here, and the corrected value is added as a new row.

## 2026-09-20 — published files rewritten to remove data-source names

Every commit in this repository was rebuilt on this date. `odds_source`, the column naming the
bookmaker, exchange or data feed behind each price, was removed from `picks.csv` for both days
already published (2026-09-18 and 2026-09-19), and three fair-price columns were renamed.

This repository promises that a published line is never rewritten. That promise was broken here
deliberately, once, and it is recorded rather than done quietly:

- **Commit hashes before 2026-09-20 have changed.** An older clone will not fast-forward.
- **No probability, price or result was changed.** One column was removed, three renamed, seven
  added. Every surviving value was carried across verbatim, and that was checked rather than
  assumed: the fair prices were recomputed from the price ledger and all 203 published legs and
  all 34 settled legs reproduced their published values exactly.
- **The timestamp proofs in `stamps/` are kept as they were, not regenerated.** The
  2026-09-19 manifest still matches `board.csv`, `goals.csv`, `results.csv` and `scores.csv`
  byte for byte, so the anchored proof that every probability and every score pre-dated its
  kickoff survives this rewrite untouched. Only `picks.csv` and `settled.csv` no longer match
  it, which is this change. A fresh manifest for the rewritten tree is added alongside.
- The 2026-09-18 manifest already did not match the current files before this rewrite: those
  files grew on 2026-09-19, and a manifest fixes a file as it stood at that run. That is how an
  append-only file and a point-in-time hash interact, and it is not a consequence of this
  change.

The reason is licensing rather than presentation. What it does *not* achieve is worth being
straight about: `odds` is still the price actually taken at one venue. The venue's identity is
withheld; its number is not.

