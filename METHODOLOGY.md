# Methodology

## What gets published, and when

A run of the live engine rates every fixture kicking off that day, writes its probabilities,
then a builder selects which legs to back. That run finishes before the day's fixtures start.

**Predictions are committed before kickoff and released after the matches.** At the end of the
run only one thing is published: `commitments/<date>.<batch>.sha256`, holding the SHA-256 of
each of the four prediction files' rows for that run date, with the row count and the moment
it was committed. The rows themselves are held back until every fixture on that day's board is
final, and released by a later run.

The engine runs more than once on some days, as fixtures are added. A published hash is never
restated, so a later run writes the *next* batch, covering only the rows the earlier batches did
not. Every row of a batch carries the moment it was committed (`published_utc`), so
`tools/verify.py` rebuilds each batch from the rows of its run date with that `published_utc`,
in file order, with the same columns, and compares the hash. If a row had been edited, added or
dropped, the hash would not match.

A cryptographic hash reveals nothing about its input and cannot be recomputed to match different
content, so the commitment fixes exactly what was predicted while giving none of it away. It is
anchored in `stamps/` like everything else, so the timing does not rest on GitHub's word or ours.

The four committed files, released together once the day is played:

- **`board.csv`**: one row per fixture, with the probability for each core market, and in
  `backed` the markets the system picked.
- **`picks.csv`**: one row per backed leg.
- **`goals.csv`**: the total-goals distribution for every fixture, and **`scores.csv`**: the
  most likely scorelines. Both are described below.

Two files describe matches already over, so they are not committed and are appended as soon as
grading lands:

- **`results.csv`**: the final score of every fixture on the board. Published so that any market
  on the board can be graded by the reader; nothing about which legs were backed enters it.
- **`settled.csv`**: the backed legs graded.

`published_utc` always precedes `kickoff_utc`, and `tools/verify.py` checks it for every row.

## Carried over from the pre-launch ledger

This ledger starts on 20 November 2026, with the website's track record. From that date until
this repository opened, predictions were committed in the pre-launch ledger,
[`predictions-prelaunch-v1-2026`](https://github.com/xbaredge/predictions-prelaunch-v1-2026).
Here is what was carried over, and how:

- **Byte for byte:** those commitments, the stamp manifests and timestamp proofs that anchor them,
  and the `board.csv`, `goals.csv`, `scores.csv` and `results.csv` rows of those days. The board,
  goals and scores rows check against their commitments here. A carried stamp manifest also lists
  files of the pre-launch repository as they stood that day; here, only its `commitments/` lines
  apply.
- **Re-issued:** the picks of those days, in `picks_reissued.csv`. The pre-launch ledger published
  each pick with the price one venue offered. Here every price is the website's, so those picks
  were re-issued with it: every column but the prices is copied from the original row, and
  `reissued_utc` says when the re-issue was made. A changed price changes the hash, so these
  picks commitments are reported by `tools/verify.py` as *re-issued*. They check in the
  pre-launch repository, against the rows as first published. Which markets were picked is also
  fixed here, in each committed board row's `backed` column.
- **Rebuilt here:** `settled.csv` for those picks, graded at the website's price.

## The probability

`p_*` is the probability the system serves, the same number shown on the website and used to
select bets. It comes from gradient-boosted models, one per market, plus a serving layer that
adjusts for team form and, where lineups are known, for absences. The `model` column names the
version and the producer that generated it (`v3/binary/published`, where `/published` means the
probability is the one the website shows). Any change is dated in `CHANGELOG.md`.

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
can therefore disagree slightly: in rare rows a bucket comes out negative. Those rows carry
`coherent=0` and are published unchanged rather than quietly adjusted. `p_over_2_5` and
`p_under_2_5` are separate model outputs and do not sum to exactly 1.

## Scorelines

`scores.csv` holds the individual scorelines the engine records for a fixture, most likely
first, as `scoreline` ("1-1") and its probability `p`. It is a thin file: a few scorelines per
fixture, covering part of the probability. `p_covered` is the total probability of the
scorelines published for that fixture, so what is missing is visible rather than implied.

It can be graded. `results.csv` gives the final score of every fixture on the board, so a reader
can join on `match_id` and ask how often the actual score was among the scorelines published
before kickoff, and compare that with `p_covered`, which is what the model claimed the chance of
exactly that was.

## Prices

`price` is the price the website showed for that leg, and `price_basis` says what kind it is:

| `price_basis` | meaning |
|---|---|
| `mean` | the average of at least three bookmakers' prices for that market. A betting exchange never enters it. Below three bookmakers there is no average, because two quotes may be one bookmaker counted twice. |
| `min` | a pick shown at its minimum price, the lowest price at which it was published as worth taking. |
| `estimate` | the model's own price for a market no bookmaker quoted. Nobody could have bet it. |
| blank | the website showed no price for that leg. It is still a prediction. |

No file names a bookmaker, an exchange or a data feed, and no price is one venue's quote: an
average of several bookmakers is not any one of them, and a minimum price is a threshold, not a
quote. `edge_pct` is `model_p × price − 1`, the system's own view rather than a measured return,
and is blank on an estimate.

## Reference prices

`open_mean` is the average of the bookmakers' prices at the first capture at which at least
three of them quoted the market, never one later than the row's own `published_utc`.
`close_mean` in `settled.csv` is the same average at the last such capture before kickoff.
`open_books` and `close_books` give how many bookmakers stood behind each. A betting exchange
never enters either. Where no capture had three bookmakers, the price is withheld and only the
count is published.

Prices are captured on a schedule, so `close_mean` can be hours old at kickoff: it is not a
closing price. Equally, `open_mean` is from the first capture we hold, not a bookmaker's opening
price.

## Closing-line value

`clv_mean_pct` = `price ÷ close_mean − 1`: how the price the pick was published at compares with
the market just before kickoff. Both are averages of several bookmakers, so both carry the
bookmakers' margin and it largely cancels; a positive number means the market moved towards the
pick after it was published. It is blank on an estimate.

## Results

`gradable` in a picks file is 0 for a leg this ledger cannot settle. Such legs are published
anyway, since a pick that quietly never settles would be a hidden loser, and they are excluded
from the record `tools/verify.py` reports.

`result` is 1 for a winning leg and 0 for a loser. Grading uses final scores from the fixture
feed. `settle_frac` is the fraction of the stake that **won**:

| `settle_frac` | meaning |
|---|---|
| 1.0 | won outright |
| 0.75 | quarter line, half won and half refunded |
| 0.5 | push: the stake is returned and nothing is won or lost |
| 0.25 | quarter line, half lost and half refunded |
| 0.0 | lost outright |

**No money column is published.** The net return on a one unit stake follows from `price` and
`settle_frac`: with `m = 2 × settle_frac − 1`, it is `m × (price − 1)` when `m` is positive and
`m` when it is negative. `tools/verify.py` computes it, at `mean` and `min` prices only.

## Early picks

The website publishes a second list of picks ahead of the day's main board: the early picks.
They are committed in the same way as the board, on files of their own.

Several times a day, after the list is updated, the early picks that no commitment covers yet and
whose kickoff is more than ten minutes away are hashed, one batch per kickoff date (UTC):
`commitments/early/<date>.<batch>.sha256`. Once every match kicking off on that date is final,
the rows are released to `early.csv` in the date's week folder. `tools/verify.py` rebuilds each
batch from the rows carrying its `batch` value, in file order, and compares the hash.

The columns of `early.csv`:

| column | meaning |
|---|---|
| `batch` | the commitment the row belongs to, `<date>.<batch>`, or `uncommitted` (below) |
| `committed_utc` | when the hash was published. The proof covers this time: the row existed, unchanged, by then |
| `posted_utc` | when the website first listed the pick, from our own clock. Nothing here proves it |
| `pick` | the pick as the website showed it: a team and a handicap line (`Derby +0.5`), or a goals line (`Under 3.5`) |
| `min_odds` | the lowest price the pick was published at. Anyone who took it was paid this or more |
| `star` | 1 where the website marked the pick ✦ |
| `salt` | 32 random hex characters. An early pick has only a few fields, so without a salt a small batch could be found by hashing every likely pick and price until one matched |

`comp`, `match_id`, `kickoff_utc`, `league`, `home` and `away` mean what they mean in the other
files.

**Rows marked `uncommitted`.** A row whose `batch` reads `uncommitted` is an early pick the
website published that was never committed before kickoff. Early picks were added to the ledger
on 25 November 2026; the ones the website published from 20 November until then are included so
the record is complete, winners and losers alike. Their `committed_utc` and `salt` are blank and
their timing cannot be checked. `tools/verify.py` shows the early record with them and without
them. If an early pick is ever listed too close to kickoff to be committed in time, it is added
the same way once its match is over.

`early_settled.csv` grades each pick once the match is over, under the same `batch`. `result` is
the website's wording: `Landed`, `Half landed`, `Half missed`, `Missed` or `Void`, and
`settle_frac` is on the scale above. It also gives the market around the pick, on the pick's own
line and side:

| column | meaning |
|---|---|
| `post_mean`, `post_books`, `post_mean_utc` | the average of the bookmakers' prices at the last capture, at or before the pick was posted, at which at least three of them quoted that line; how many, and when |
| `last_mean`, `last_books`, `last_mean_utc` | the same at the last such capture before kickoff |
| `clv_mean_pct` | `post_mean ÷ last_mean − 1`: how the market's price when the pick was posted compares with the market before kickoff |

A betting exchange never enters these averages, and below three bookmakers they are withheld.
`tools/verify.py` gives the early hit rate the way the website counts it, where a half result is
half a leg and a void is left out, beside the rate the minimum prices imply. It gives no return
figure for early picks: the minimum is a threshold, not the price anyone took.

## Limits worth stating

- The fixtures covered are those the model has trained leagues for; the board is not every match
  played that day.
- An average of several bookmakers is not a price any one of them offered, and the money
  available at a price may have been small.
- A sample this size says very little. A short-run result here is mostly variance.
