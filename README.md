# X̄BAR EDGE — public prediction ledger

Every football prediction this system makes, published **before kickoff**, with the price that
was available at the time. Results are added afterwards. Nothing already published is ever
edited.

The point is timing. A prediction is only worth anything if it was recorded before the match,
so each upload is committed to this repository minutes after the model runs and hours before
the fixtures start, and each commit is anchored with [OpenTimestamps](https://opentimestamps.org)
(`stamps/`), which proves the content existed at that time independently of GitHub and of us.

## What is here

```
2026/W38/board.csv     every fixture the model looked at, with its probability for each market
2026/W38/picks.csv     the legs the system backed, with the odds and fair price at upload
2026/W38/results.csv   the final score of every fixture on the board, added after the match
2026/W38/settled.csv   backed legs graded, with the fair price near kickoff and CLV
stamps/                timestamp proofs, one per upload
tools/verify.py        recomputes the record from the files in this repo alone
```

One folder per ISO week. Each upload appends; a published line never changes.

## Verify it yourself

```bash
git clone https://github.com/xbaredge/predictions.git && cd predictions
python3 tools/verify.py            # every pick pre-dates its kickoff; hit rate, P&L, CLV
```

Check that nothing was rewritten:
```bash
git log --patch -- 2026/W38/picks.csv | grep '^-[^-]'     # expect no output
```

Check a timestamp proof (needs `pip install opentimestamps-client`):
```bash
ots verify stamps/2026/2026-09-18T070500Z.sha256.ots
```

## The board matters as much as the picks

`board.csv` holds every fixture the model rated, not only the ones it backed, and `results.csv`
gives the final score of each one. Between them you can grade **any** market on the board
yourself, rather than taking our word for the legs we chose to settle. A record of winning bets
alone can always be assembled after the fact; a full board with scores cannot.

## What these numbers are not

- They are **not** a claim that the system beats the market. Judge that from `settled.csv`.
- Odds are the best price the system saw at upload time, at the source named in the row. Some
  are exchange prices, before commission. Some fixtures are unpriced.
- Fair prices are Pinnacle's, with the bookmaker margin removed. See `METHODOLOGY.md` for what
  "first seen" and "last seen" mean, and what they do not.
- Nothing here is betting advice.

See `METHODOLOGY.md` for definitions, `CHANGELOG.md` for model changes, `ERRATA.md` for
corrections.
