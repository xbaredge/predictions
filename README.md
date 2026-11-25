# X̄BAR EDGE — public prediction ledger

Every football prediction this system makes, fixed **before kickoff** and published once the
matches are over, with the price the website showed for it. Nothing already published is ever
edited.

The point is timing. A prediction is only worth anything if it was fixed before the match, so
before any fixture starts this repository receives the **SHA-256 of the predictions**
(`commitments/`). The predictions themselves follow once the day's fixtures are final. A hash
cannot be reversed, so the commitment gives nothing away while the matches are still to be
played, and it cannot be altered afterwards without every reader noticing.

Each commitment is anchored with [OpenTimestamps](https://opentimestamps.org) (`stamps/`), which
proves the content existed at that time independently of GitHub and of us. When the rows are
released, `tools/verify.py` re-derives the hash from them and checks it against the commitment
published before kickoff.

An anchor takes two steps and about a day. A stamp starts as a *pending* attestation, a receipt
from the timestamp calendars, and becomes a Bitcoin block header once the calendars' transaction
confirms; the next upload completes it. So the newest file in `stamps/` reads as pending for
roughly a day, and every older one names a Bitcoin block you can check yourself:

```bash
ots info stamps/2026/<file>.sha256.ots     # BitcoinBlockHeaderAttestation(<block height>)
```

## Where this record starts

This ledger starts with the website's track record, on **20 November 2026**.

The system's earlier predictions, from before launch, are in a separate public repository,
[`predictions-prelaunch-v1-2026`](https://github.com/xbaredge/predictions-prelaunch-v1-2026),
which ran from 18 September 2026 until this one opened and stays online.

Predictions from 20 November until this repository opened were first committed there. Those
commitments, and the timestamp proofs that anchor them, are copied here byte for byte, and so are
the board, goals and scores rows they cover: those check against the same commitments here.

The picks of those days are in `picks_reissued.csv` instead of `picks.csv`. The pre-launch ledger
published each pick with the price of a single bookmaker or exchange; here every price is the one
the website showed (see below), so those rows were re-issued with it, and `reissued_utc` says when.
Changing a price changes the hash, so their picks commitments do not check in this repository.
They do check in the pre-launch repository, against the rows as first published. Which markets
were picked on those days is also fixed in this repository, in the committed `board.csv`: its
`backed` column names them, beside every probability.

## Prices

Every price in this repository is the one the website showed:

- `mean`: the average of at least three bookmakers' prices for that market. A betting exchange
  never enters it.
- `min`: a pick shown at its minimum price, the lowest price at which it was published as worth
  taking.
- `estimate`: the model's own price for a market no bookmaker quoted. Nobody could have bet it,
  so it never counts towards a return.

No file names a bookmaker, and no price is one bookmaker's or one exchange's quote. The reference
prices before kickoff are averages of at least three bookmakers in the same way.

## What is here

```
commitments/                  the SHA-256 of each day's predictions, published before kickoff
commitments/early/            the SHA-256 of each day's early picks, published before kickoff
2026/W48/board.csv            every fixture the model rated, with its probability for each market
2026/W48/goals.csv            the total-goals distribution implied by those probabilities
2026/W48/scores.csv           the most likely scorelines, as far as the engine records them
2026/W48/picks.csv            the legs the system backed, at the website's price
2026/W48/picks_reissued.csv   20 November onwards, until this repository opened: picks re-issued at the website's price
2026/W48/results.csv          the final score of every fixture on the board, added after the match
2026/W48/settled.csv          backed legs graded, with the average price before kickoff and CLV
2026/W48/early.csv            early picks, published ahead of the main board †
2026/W48/early_settled.csv    early picks graded, with the market around them
stamps/                       timestamp proofs, one per upload
tools/verify.py               recomputes the record from the files in this repo alone
```

One folder per ISO week. Each upload appends; a published line never changes.

† Rows marked `uncommitted` in the `batch` column of `early.csv` were published on the website
but never committed before kickoff: early picks were added to the ledger on 25 November 2026, and
the ones published from 20 November until then are included so the record is complete.

## Early picks

The website also publishes early picks, ahead of the day's main board. They have their own files
and their own commitments (`commitments/early/`, one per kickoff date) and work the same way: a
hash before kickoff, the rows once the matches are over. An early pick is the pick as the website
showed it, with the **minimum** price it was published at. `early_settled.csv` adds the average of
three or more bookmakers on the same line when the pick was posted and before kickoff.
`tools/verify.py` reports early picks separately from the main picks.

## Verify it yourself

```bash
git clone https://github.com/xbaredge/predictions.git && cd predictions
python3 tools/verify.py            # checks every commitment, then hit rate, net return, CLV
```

The commitment check is the important one. For every released batch it rebuilds the exact bytes
covered by the hash and compares, so `released` on a line means those predictions provably
existed, unchanged, before a ball was kicked.

Check that nothing was rewritten:
```bash
git log --patch -- '2026/*/picks.csv' | grep '^-[^-]'     # expect no output
```

Check a timestamp proof (needs `pip install opentimestamps-client`):
```bash
ots verify stamps/2026/<file>.sha256.ots
```

## The board matters as much as the picks

`board.csv` holds every fixture the model rated, not only the ones it backed, and `results.csv`
gives the final score of each one. Between them you can grade **any** market on the board
yourself, rather than taking our word for the legs we chose to settle. A record of winning bets
alone can always be assembled after the fact; a full board with scores cannot.

## What these numbers are not

- They are **not** a claim that the system beats the market. Judge that from `settled.csv`.
- A price is what the website showed, not a price that was certainly available at every
  bookmaker. An average of several bookmakers is not any one of them.
- **No money column is published.** The net return follows from the price and the grade;
  `tools/verify.py` computes it.
- Nothing here is betting advice.

See `METHODOLOGY.md` for definitions and `CHANGELOG.md` for changes.

## Licence

You may read, clone and verify this ledger, publish what you find, and quote limited extracts
with a credit. You may not republish it as a dataset, use it in a product or service, or use it
to train, test or reconstruct a model. The full terms are in [`LICENSE.md`](LICENSE.md); the
code in `tools/` is MIT-licensed.
