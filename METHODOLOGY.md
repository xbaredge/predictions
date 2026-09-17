# Methodology

## What gets published, and when

A run of the live engine rates every fixture kicking off that day, writes its probabilities,
then a builder selects which legs to back. The upload happens at the end of that run, typically
07:00 UTC, and publishes:

- **`board.csv`** — one row per fixture, with the probability for each core market.
- **`picks.csv`** — one row per backed leg.
- **`settled.csv`** — appended once results are graded, usually the next day.

Every row carries `published_utc` and `kickoff_utc`. A fixture that has already kicked off is
never published: `tools/verify.py` checks this for every row.

## The probability

`p_*` is the probability the system serves — the same number shown on the website and used to
select bets. It comes from gradient-boosted models, one per market, plus a serving layer that
adjusts for team form and, where lineups are known, for absences. The `model` column names the
version and the producer that generated it (`v3/binary`). Any change is dated in
`CHANGELOG.md`.

Markets published on the board: match result (`HOME_WIN`, `DRAW`, `AWAY_WIN`), goal totals
(`OVER_1_5`, `OVER_2_5`, `UNDER_2_5`, `UNDER_3_5`), both teams to score (`BTTS`), goal bands
(`GOALS_1_3`, `GOALS_2_3`), and `UPSET` (the underdog wins). Correct scores and count markets
(corners, cards, shots) are rated internally but not served, so they are not published.

## The odds

`odds` is the price the run had for that leg at upload, and `odds_source` names where it came
from: an exchange (`betfair`, before commission), a bookmaker feed (`apifootball`), or
`derived` where the price was inferred rather than quoted. `odds_estimated` marks the latter.
Unpriced legs are published with blank odds; they are still predictions.

`edge_pct` is `model_p × odds − 1`. It is the system's own view, not a measured return.

## Fair prices

Bookmaker odds include a margin. To compare like with like, Pinnacle's quotes are de-vigged
with Shin's method over the complete market group (the three match-result prices together, or
an over/under pair). The result is a fair price: the odds implied with the margin removed.

- **`pin_fair_first`** — the earliest capture we hold, up to about 72 hours before kickoff.
  This is *the first price we saw*, not the bookmaker's opening price.
- **`pin_fair_at_publish`** — the last capture before upload.
- **`pin_fair_last`** — the last capture before kickoff. Prices are captured on a schedule, so
  this can be hours old at kickoff. It is *not* a closing price.

`clv_pct` in `settled.csv` is `odds ÷ pin_fair_last − 1`: how the taken price compares with the
fair price nearest kickoff. Where Pinnacle's feed carries only one side of a market (both teams
to score, over 1.5, goal bands), no complete book exists, so the fair columns are blank rather
than guessed.

## Results

`result` is 1 for a winning leg and 0 for a loser. `settle_frac` is the fraction of the stake
that settled, for markets that can settle in part. `profit_1u` is the profit on a one-unit
stake at the published price. Grading uses final scores from the fixture feed.

## Limits worth stating

- Exchange prices are shown before commission, and the available stake at that price may have
  been small.
- The fixtures covered are those the model has trained leagues for; the board is not every
  match played that day.
- A sample of bets is small for a long time. Short-run profit or loss here is mostly variance.
