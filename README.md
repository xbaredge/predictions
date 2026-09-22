# X̄BAR EDGE — public prediction ledger

Every football prediction this system makes, recorded **before kickoff** and published once the
matches are over, with the price that was available at the time. Nothing already published is
ever edited.

The point is timing. A prediction is only worth anything if it was fixed before the match — so
on the morning of each matchday, before any fixture starts, this repository receives the
**SHA-256 of that day's predictions** (`commitments/`). The predictions themselves follow once
the day's fixtures are final. A hash cannot be reversed, so the commitment gives nothing away
while the matches are still to be played, and it cannot be altered afterwards without every
reader noticing.

Each commitment is anchored with [OpenTimestamps](https://opentimestamps.org) (`stamps/`),
which proves the content existed at that time independently of GitHub and of us. When the rows
are released, `tools/verify.py` re-derives the hash from them and checks it against the
commitment published before kickoff.

An anchor takes two steps and about a day. A stamp is created the moment its files are
published, but it starts as a *pending* attestation — a receipt from the timestamp calendars —
and only becomes a Bitcoin block header once the calendars' transaction confirms. The next
day's upload completes it. So the newest file in `stamps/` will read as pending for roughly
24 hours; every older one carries a block height you can check against the chain yourself:

```bash
ots info stamps/2026/2026-09-21T070307Z.sha256.ots   # BitcoinBlockHeaderAttestation(967964)
```

Full `ots verify` compares that block header against Bitcoin itself, so it needs a local node
or a block explorer — `ots info` alone shows you which block the proof names.

## What is here

```
commitments/           the SHA-256 of each day's predictions, published before kickoff
2026/W38/board.csv     every fixture the model looked at, with its probability for each market
2026/W38/goals.csv     the total-goals distribution implied by those probabilities
2026/W38/scores.csv    the most likely scorelines, as far as the engine records them
2026/W38/picks.csv     the legs the system backed, with the odds taken and two reference prices
2026/W38/results.csv   the final score of every fixture on the board, added after the match
2026/W38/settled.csv   backed legs graded, with the reference prices near kickoff and CLV
stamps/                timestamp proofs, one per upload
tools/verify.py        recomputes the record from the files in this repo alone
```

One folder per ISO week. Each upload appends; a published line never changes.

## Verify it yourself

```bash
git clone https://github.com/xbaredge/predictions.git && cd predictions
python3 tools/verify.py            # checks every commitment, then hit rate, net return, CLV
```

The commitment check is the important one. For every released day it rebuilds the exact bytes
covered by the hash and compares, so `released` on a line means those predictions provably
existed, unchanged, before a ball was kicked.

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
- Odds are the best price the system saw at upload time. Some are exchange prices, before
  commission. **Where a price came from is not published** — odds feeds are licensed, so no file
  here names a bookmaker, an exchange or a data feed.
- **Some prices are estimated, not quoted** (50 of 203 legs so far, where `odds_basis` reads
  `estimated` rather than `-`). An estimated price was inferred from the rest of the market, not
  taken from anyone's board, so no one could have bet it. Some fixtures are unpriced entirely.
- **No money column is published.** The net return follows from the odds and the grade;
  `tools/verify.py` computes it. A stored one was wrong once — see `ERRATA.md`.
- Two reference prices are given, and they are not interchangeable. The **panel median** is a
  cross-book median that still contains the bookmakers' margin; the **fair price** has that
  margin removed. CLV against the first reads about 7 percentage points kinder than CLV against
  the second. `METHODOLOGY.md` gives both, and says which one to judge on.
- Nothing here is betting advice.

See `METHODOLOGY.md` for definitions, `CHANGELOG.md` for model changes, `ERRATA.md` for
corrections.
