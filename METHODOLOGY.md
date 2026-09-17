# Methodology

## What gets published, and when

A run of the live engine rates every fixture kicking off that day, writes its probabilities,
then a builder selects which legs to back. The upload happens at the end of that run, typically
07:00 UTC, and publishes:

- **`board.csv`** — one row per fixture, with the probability for each core market.
- **`picks.csv`** — one row per backed leg.
- **`goals.csv`** — the total-goals distribution for every fixture, and **`scores.csv`** — the
  most likely scorelines. Both are described below.
- **`results.csv`** — the final score of every fixture on the board, appended once the match is
  graded, usually the next day. Published so that any market on the board can be graded by the
  reader; nothing about which legs were backed enters it.
- **`settled.csv`** — the backed legs graded, appended at the same time.

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

## The goals distribution

`goals.csv` turns the served totals markets into a distribution over the number of goals:
`p_0_1` = 1 − P(over 1.5), `p_2` = P(over 1.5) − P(over 2.5), `p_3` = P(over 2.5) − P(over 3.5),
`p_4plus` = P(over 3.5). The thresholds it is derived from are published in the same row, so the
arithmetic can be checked.

These come from separate models, one per market, rather than from a single model of goals. They
can therefore disagree slightly. Measured over 958 fixtures in September 2026: the thresholds
are in the right order for 99.0% of fixtures, and fewer than 1% produce a negative bucket. Rows
where that happens carry `coherent=0` and are published unchanged rather than quietly adjusted.
`p_over_2_5` and `p_under_2_5` are separate model outputs and do not sum to exactly 1; the mean
gap is 1.5 percentage points.

## Scorelines

`scores.csv` holds the individual scorelines the engine records for a fixture, most likely
first. It is a **partial** distribution: three scorelines per fixture, covering a median of 32%
of the probability, and only about 45% of fixtures have any at all. `p_covered` gives the total
for each fixture so the missing mass is visible. For a complete view of how many goals the model
expects, use `goals.csv`.

## The odds

`odds` is the price the run had for that leg at upload. Some are exchange prices, quoted
before commission. `odds_estimated` marks a price that was inferred rather than quoted. Where a
price came from is not published: odds feeds are licensed, so no file here names a bookmaker, an
exchange or a data feed. Unpriced legs are published with blank odds; they are still
predictions.

`edge_pct` is `model_p × odds − 1`. It is the system's own view, not a measured return.

## Fair prices

Bookmaker odds include a margin. To compare like with like, a single sharp reference book's
quotes are de-vigged with Shin's method over the complete market group (the three match-result prices together, or
an over/under pair). The result is a fair price: the odds implied with the margin removed.

- **`fair_open`** — the earliest capture we hold, up to about 72 hours before kickoff.
  This is *the first price we saw*, not the bookmaker's opening price.
- **`fair_at_publish`** — the last capture before upload.
- **`fair_close`** — the last capture before kickoff. Prices are captured on a schedule, so
  this can be hours old at kickoff. It is *not* a closing price.

`clv_pct` in `settled.csv` is `odds ÷ fair_close − 1`: how the taken price compares with the
fair price nearest kickoff. Where that book carries only one side of a market (both teams
to score, over 1.5, goal bands), no complete book exists, so the fair columns are blank rather
than guessed.

## Results

`gradable` in `picks.csv` is 0 for a leg this ledger cannot settle: Asian lines are priced and
backed by the builder but are not graded by the engine that produces these files. They are
published anyway — a pick that quietly never settles would be a hidden loser — and they are
excluded from the record `tools/verify.py` reports.

`result` is 1 for a winning leg and 0 for a loser. `settle_frac` is the fraction of the stake
that settled, for markets that can settle in part. `profit_1u` is the profit on a one-unit
stake at the published price. Grading uses final scores from the fixture feed.

## Limits worth stating

- Exchange prices are shown before commission, and the available stake at that price may have
  been small.
- The fixtures covered are those the model has trained leagues for; the board is not every
  match played that day.
- A sample of bets is small for a long time. Short-run profit or loss here is mostly variance.
