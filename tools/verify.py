#!/usr/bin/env python3
"""Recompute this ledger's record from the files in this repository alone.

    python3 tools/verify.py [--repo .] [--market OVER_2_5] [--from 2026-09-18]

No dependencies, no network. It checks the promises this repo makes, then prints the record:

  1. every published row pre-dates its own kickoff
  2. no fixture or leg is published twice
  3. every settled row points at a leg that was published first

Whether the timestamps are honest is a separate question, and not one this script can answer:
check the commit dates with `git log`, and the OpenTimestamps proofs in stamps/ with
`ots verify`. This script only shows that the files are internally consistent.
"""
import argparse, csv, glob, hashlib, io, os, sys
from collections import defaultdict


def rows(repo, name):
    for path in sorted(glob.glob(os.path.join(repo, "[0-9]" * 4, "W[0-9][0-9]", name))):
        with open(path, newline="") as f:
            for r in csv.DictReader(f):
                r["_file"] = os.path.relpath(path, repo)
                yield r


def commitments(repo):
    """Check every released prediction against the hash published before its kickoff.

    Each `commitments/<date>.<batch>.sha256` was published on the morning of <date>, before the
    fixtures it covers kicked off, and anchored in `stamps/`. The rows are released after the
    day is played. A date can have several batches because the engine runs more than once a
    day; they are released in order and cover consecutive rows.

    This rebuilds the exact bytes each commitment covered - that batch's slice of the rows for
    that run date, in file order, written back with the same header and columns - and compares.
    A `released` line means those predictions provably existed, unchanged, before kickoff."""
    out, mans = [], {}
    for man in glob.glob(os.path.join(repo, "commitments", "*.sha256")):
        base = os.path.basename(man)[:-len(".sha256")]
        date, _, b = base.rpartition(".")
        if not date:
            date, b = base, "1"
        mans.setdefault(date, []).append((int(b) if b.isdigit() else 1, man))
    for date in sorted(mans):
        pub, pos = {}, {}
        for name in ("board", "picks", "goals", "scores"):
            sel, cols = [], None
            for p in sorted(glob.glob(os.path.join(repo, "[0-9]" * 4, "W[0-9][0-9]",
                                                  name + ".csv"))):
                with open(p, newline="") as f:
                    rd = csv.DictReader(f)
                    hit = [r for r in rd if r["run_date"] == date]
                    fields = rd.fieldnames
                # Keep the header even when this date has no rows here: a batch can legitimately
                # commit ZERO rows for a file (a board with no backed legs), and its slice is
                # then the header alone. Without this the empty slice can never be rebuilt and
                # the date would sit as "embargoed" for ever.
                if cols is None:
                    cols = fields
                if hit:
                    sel, cols = hit, fields
                    break
            pub[name], pos[name] = (sel, cols), 0
        for b, man in sorted(mans[date]):
            for line in open(man):
                if line.startswith("#") or not line.strip():
                    continue
                want, name, n = line.split()
                n = int(n)
                sel, cols = pub.get(name, ([], None))
                if cols is None:      # nothing of this file published yet — still embargoed
                    out.append((date, b, name, "embargoed", n, 0))
                    continue
                take = sel[pos[name]:pos[name] + n]
                if len(take) < n:
                    out.append((date, b, name, "embargoed", n, len(take)))
                    continue
                pos[name] += n
                buf = io.StringIO()
                w = csv.DictWriter(buf, fieldnames=cols, lineterminator="\n")
                w.writeheader()
                for r in take:
                    w.writerow(r)
                got = hashlib.sha256(buf.getvalue().encode()).hexdigest()
                out.append((date, b, name, "released" if got == want else "MISMATCH",
                            n, len(take)))
    return out


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def net_return(odds, frac):
    """Net return on a one-unit stake, from the settlement fraction.

    `settle_frac` is the fraction WON: 1.0 clean win, 0.75 quarter-line half-win, 0.5 push
    (stake refunded), 0.25 quarter half-loss, 0.0 loss. With m = 2*frac - 1 (so +1 win, 0 push,
    -1 loss), the winning part is paid at the price and the losing part costs its stake:

        m >= 0  ->  m * (odds - 1)
        m <  0  ->  m

    This is computed here rather than read from the files on purpose. Settled rows published
    before 2026-09-21 carry a `profit_1u` column that booked every loss as zero; see ERRATA.md.
    Recomputing from `odds`, `result` and `settle_frac` gives the right answer for every row,
    old or new, and needs nothing stored."""
    if odds is None or frac is None:
        return None
    m = 2.0 * frac - 1.0
    return m * (odds - 1.0) if m >= 0 else m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--market", help="only this market")
    ap.add_argument("--from", dest="since", default="", help="only kickoffs on/after YYYY-MM-DD")
    a = ap.parse_args()

    board = list(rows(a.repo, "board.csv"))
    picks = list(rows(a.repo, "picks.csv"))
    settled = list(rows(a.repo, "settled.csv"))
    problems = []

    for r in board + picks:
        if not (r["published_utc"] < r["kickoff_utc"]):
            problems.append(f"published after kickoff: {r['_file']} {r['home']} v {r['away']} "
                            f"{r.get('market', '')} published {r['published_utc']} ko {r['kickoff_utc']}")
    for label, rs, key in (("board", board, ("run_date", "fixture_id")),
                           ("picks", picks, ("run_date", "fixture_id", "market"))):
        seen = set()
        for r in rs:
            k = tuple(r[c] for c in key)
            if k in seen:
                problems.append(f"duplicate {label} row: {k}")
            seen.add(k)
    commits = commitments(a.repo)
    for date, b, name, state, n_want, n_got in commits:
        if state == "MISMATCH":
            problems.append(f"commitment broken: {date} batch {b} / {name} — the {n_got} "
                            f"released rows do not hash to the commitment published before "
                            f"kickoff ({n_want} rows)")

    published = {(r["run_date"], r["fixture_id"], r["market"]): r for r in picks}
    for r in settled:
        k = (r["run_date"], r["fixture_id"], r["market"])
        if k not in published:
            problems.append(f"settled row with no published pick: {k}")

    keep = [r for r in settled
            if (not a.market or r["market"] == a.market) and r["kickoff_utc"] >= a.since]
    n = len(keep)
    wins = sum(1 for r in keep if r["result"] == "1")
    # One unit per settled leg, and the return recomputed from the grade — never read from a
    # stored money column. `settle_frac` defaults to 1 only when it is absent, not when it is 0:
    # 0 means the leg LOST, and treating that as missing is how the old bug read.
    priced = [r for r in keep if num(r["odds"]) is not None]
    def frac_of(r):
        f = num(r.get("settle_frac"))
        return f if f is not None else (1.0 if r["result"] == "1" else 0.0)
    staked = float(len(priced))
    pnl = sum(net_return(num(r["odds"]), frac_of(r)) or 0.0 for r in priced)
    clvs = [num(r["clv_pct"]) for r in keep if num(r["clv_pct"]) is not None]
    clvm = [num(r.get("clv_median_pct")) for r in keep
            if num(r.get("clv_median_pct")) is not None]

    # `odds_basis` since 2026-09-21; `odds_estimated` was the 0/1 flag before it.
    est = sum(1 for r in picks
              if r.get("odds_basis") == "estimated" or r.get("odds_estimated") == "1")
    gradable = [r for r in picks if r.get("gradable", "1") == "1"]
    done = {(r["run_date"], r["fixture_id"], r["market"]) for r in settled}
    waiting = [r for r in gradable if (r["run_date"], r["fixture_id"], r["market"]) not in done]
    print(f"board:   {len(board):>6} fixtures")
    print(f"picks:   {len(picks):>6} legs published"
          + (f"  ({est} at an ESTIMATED price, not a quoted one — see METHODOLOGY.md)"
             if est else ""))
    print(f"settled: {n:>6} legs" + (f"  (filtered: market={a.market or 'all'}, from={a.since or 'start'})"
                                     if a.market or a.since else ""))
    print(f"pending: {len(waiting):>6} gradable legs not yet settled"
          f"  ({len(picks) - len(gradable)} legs are marked not gradable — see METHODOLOGY.md)")
    if commits:
        rel = sum(1 for c in commits if c[3] == "released")
        emb = sum(1 for c in commits if c[3] == "embargoed")
        dates = sorted({c[0] for c in commits})
        print(f"\ncommitments: {len(dates)} run date(s); {rel} file(s) released and matching "
              f"their pre-kickoff hash, {emb} still embargoed")
        for d in dates:
            states = [c[3] for c in commits if c[0] == d]
            nb = len({c[1] for c in commits if c[0] == d})
            mark = ("MISMATCH" if "MISMATCH" in states
                    else "embargoed" if "embargoed" in states else "released")
            n_picks = sum(c[4] for c in commits if c[0] == d and c[2] == "picks")
            print(f"  {d}  {mark:<10} {nb} batch(es), {n_picks} picks")
    if n:
        print(f"\nhit rate:  {wins}/{n} = {wins / n * 100:.1f}%")
        if staked:
            print(f"net:       {pnl:+.2f} units on {staked:.0f} settled legs, one unit each"
                  f"  →  {pnl / staked * 100:+.2f}%")
        if clvs:
            print(f"CLV fair:  mean {sum(clvs) / len(clvs):+.2f}% over {len(clvs)} legs "
                  f"({sum(1 for c in clvs if c > 0) / len(clvs) * 100:.1f}% positive)")
        if clvm:
            print(f"CLV panel: mean {sum(clvm) / len(clvm):+.2f}% over {len(clvm)} legs "
                  f"({sum(1 for c in clvm if c > 0) / len(clvm) * 100:.1f}% positive)")
        if clvs and clvm:
            print("  Judge on CLV fair — margin is removed from both sides. CLV panel compares\n"
                  "  the taken price with a median that still carries the books' margin, so it\n"
                  "  reads positive whether or not the prediction was any good. See "
                  "METHODOLOGY.md.")
        by = defaultdict(lambda: [0, 0, 0.0])
        for r in keep:
            b = by[r["market"]]
            b[0] += 1
            b[1] += r["result"] == "1"
            b[2] += net_return(num(r["odds"]), frac_of(r)) or 0.0
        print("\n  market            n   won      net")
        for m, (c, w, p) in sorted(by.items(), key=lambda kv: -kv[1][0]):
            print(f"  {m:<16} {c:>3} {w:>5} {p:>+8.2f}")
        print("\nA few dozen settled legs is a very small sample: a short-run result is "
              "mostly variance.\nOdds are the price seen at upload; exchange prices exclude "
              "commission. Estimated\nprices were never quoted by anyone — see METHODOLOGY.md.")
    if problems:
        print(f"\n❌ {len(problems)} problem(s):")
        for p in problems[:20]:
            print("  ·", p)
        return 1
    print("\n✅ every pick pre-dates its kickoff; no duplicates; every result maps to a published pick")
    return 0


if __name__ == "__main__":
    sys.exit(main())
