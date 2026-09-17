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
import argparse, csv, glob, os, sys
from collections import defaultdict


def rows(repo, name):
    for path in sorted(glob.glob(os.path.join(repo, "[0-9]" * 4, "W[0-9][0-9]", name))):
        with open(path, newline="") as f:
            for r in csv.DictReader(f):
                r["_file"] = os.path.relpath(path, repo)
                yield r


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


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
    published = {(r["run_date"], r["fixture_id"], r["market"]): r for r in picks}
    for r in settled:
        k = (r["run_date"], r["fixture_id"], r["market"])
        if k not in published:
            problems.append(f"settled row with no published pick: {k}")

    keep = [r for r in settled
            if (not a.market or r["market"] == a.market) and r["kickoff_utc"] >= a.since]
    n = len(keep)
    wins = sum(1 for r in keep if r["result"] == "1")
    staked = sum(num(r["settle_frac"]) or 1 for r in keep if num(r["odds"]))
    pnl = sum(num(r["profit_1u"]) or 0 for r in keep if num(r["odds"]))
    clvs = [num(r["clv_pct"]) for r in keep if num(r["clv_pct"]) is not None]

    print(f"board:   {len(board):>6} fixtures")
    print(f"picks:   {len(picks):>6} legs published")
    print(f"settled: {n:>6} legs" + (f"  (filtered: market={a.market or 'all'}, from={a.since or 'start'})"
                                     if a.market or a.since else ""))
    if n:
        print(f"\nhit rate:  {wins}/{n} = {wins / n * 100:.1f}%")
        if staked:
            print(f"P&L:       {pnl:+.2f} units on {staked:.2f} staked  →  {pnl / staked * 100:+.2f}%")
        if clvs:
            print(f"CLV:       mean {sum(clvs) / len(clvs):+.2f}% over {len(clvs)} legs "
                  f"({sum(1 for c in clvs if c > 0) / len(clvs) * 100:.1f}% positive)")
        by = defaultdict(lambda: [0, 0, 0.0])
        for r in keep:
            b = by[r["market"]]
            b[0] += 1
            b[1] += r["result"] == "1"
            b[2] += num(r["profit_1u"]) or 0
        print("\n  market            n   won      P&L")
        for m, (c, w, p) in sorted(by.items(), key=lambda kv: -kv[1][0]):
            print(f"  {m:<16} {c:>3} {w:>5} {p:>+8.2f}")
        print("\nA few hundred bets is a small sample: short-run profit or loss is mostly "
              "variance.\nOdds are the price seen at upload; "
              "exchange prices exclude commission.")
    if problems:
        print(f"\n❌ {len(problems)} problem(s):")
        for p in problems[:20]:
            print("  ·", p)
        return 1
    print("\n✅ every pick pre-dates its kickoff; no duplicates; every result maps to a published pick")
    return 0


if __name__ == "__main__":
    sys.exit(main())
