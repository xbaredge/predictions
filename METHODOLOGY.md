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

`odds` is the price the run had for that leg at upload. Some are exchange prices, quoted before
commission.

**Not every leg has a quoted price.** Where none was available the run works from an *estimated
price* — inferred from the rest of the market rather than taken from anyone's board — and those
rows carry `odds_estimated = 1`. 50 of the 203 legs published so far are estimated.
An estimated price is not a price that could have been taken, so `edge_pct`, `profit_1u` and the
CLV columns on those rows describe a price that never existed on a screen. Read them as
indicative and judge the record on the quoted rows. Legs with no price at all are published with
blank odds; they are still predictions.

Which venue a price came from is not published. Odds feeds are licensed, and the terms covering
redistribution and attribution are not the same everywhere, so no file here names a bookmaker,
an exchange or a data feed. That limit is worth stating plainly rather than dressing up: `odds`
is still the price actually taken at one venue, and `profit_1u`, `edge_pct` and both CLV columns
are computed from it. What is withheld is the venue's identity, not its number.

`edge_pct` is `model_p × odds − 1`. It is the system's own view, not a measured return.

## The reference line

Each leg carries two reference prices, on two different bases. They are not interchangeable,
and the gap between them is wider than anything either one measures.

**The panel median.** `open_median` is the median quote across every book holding that line at
the earliest capture taken, and `close_median` is the same median at the last capture before
kickoff. `open_books` and `close_books` give how many books stood behind each. This is a
derived statistic rather than any one house's price — and below three books it would be one or
two quotes wearing an average's clothes, so there the price is withheld and only the depth is
published. The panel mixes bookmaker and exchange quotes; the exchange moves the median by
+0.098% on average and 0.000% at the median, so it is left in rather than curated out.

**The fair price.** `fair_open`, `fair_at_publish` and `fair_close` take a single sharp
reference book and remove its margin, de-vigging with Shin's method over a complete market
group — the three match-result prices together, or an over/under pair. An incomplete book has
no defined overround to remove, so where that book carries only one side of a market (over 1.5,
both teams to score, the goal bands) these columns are blank rather than guessed. That is why
they are sparser than the panel columns: 59 of 203 legs in W38, against 95.

Prices are captured on a schedule, so `close_median` and `fair_close` can be hours old at
kickoff. Neither is a closing price. Equally, `open_median` and `fair_open` are the first
capture *taken*, not a bookmaker's opening price — and neither is ever read from a capture
later than the row's own `published_utc`. A price ledger keeps growing, so "the first capture we
hold" would otherwise drift: for one W38 leg the only capture ever taken landed 53 minutes
after publication, and reading that as the leg's opening price would import hindsight into a
file whose entire point is that none was available.

## Closing-line value

`settled.csv` carries CLV on both bases:

- **`clv_pct`** = `odds ÷ fair_close − 1`. Margin removed from both sides. This is the one to
  judge the system on.
- **`clv_median_pct`** = `odds ÷ close_median − 1`. The panel median still carries the books'
  margin, so clearing it is largely expected: taking the best available price against a vigged
  consensus scores positive whether or not the prediction was any good.

On the 16 W38 legs where both are defined, `clv_median_pct` averages **+4.71%** while `clv_pct`
averages **−2.27%** — seven percentage points apart, and essentially all of it margin. The
better-covered number is the flattering one. Quoting it as evidence of an edge would be wrong.
It is published anyway, because withholding it while publishing `close_median` would leave the
same mistake one subtraction away.

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
