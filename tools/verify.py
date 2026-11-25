#!/usr/bin/env python3
"""Recompute this ledger's record from the files in this repository alone.

    python3 tools/verify.py [--repo .] [--market OVER_2_5] [--from 2026-11-20]

No dependencies, no network. It checks the promises this repo makes, then prints the record:

  1. every commitment matches the rows released for it. Picks first published in the pre-launch
     ledger and re-issued here at the website's price are reported as re-issued: their original
     rows check against the same commitments in that repository (see README.md)
  2. every published row pre-dates its own kickoff, and no fixture, leg or early pick appears twice
  3. every settled row points at a pick that was published first

Whether the timestamps are honest is a separate question, and not one this script can answer:
check the OpenTimestamps proofs in stamps/ with `ots verify`. This script only shows that the
files are internally consistent.
"""
import argparse, csv, datetime, glob, hashlib, io, os, re, sys
from collections import defaultdict

UNCOMMITTED = "uncommitted"
SHOWN = ("mean", "min")                 # a price somebody could have taken; 'estimate' never is
# How an early pick counts towards the hit rate, as the website counts it: a half result is half
# a leg, a void is left out.
EARLY_SCORE = {"Landed": (1.0, 1.0), "Half landed": (0.5, 0.5), "Missed": (0.0, 1.0),
               "Half missed": (0.0, 0.5), "Void": (0.0, 0.0)}
# The picks header of the pre-launch ledger. Only an EMPTY picks slice of a carried commitment is
# rebuilt with it (a header and nothing else); carried picks with rows are re-issued, see above.
PICKS_PRELAUNCH = ["published_utc", "run_date", "comp", "match_id", "kickoff_utc", "league", "home",
                   "away", "market", "gradable", "model_p", "model_fair_odds", "odds", "odds_basis",
                   "edge_pct", "open_median", "open_median_utc", "open_books", "fair_open",
                   "fair_open_utc", "fair_at_publish", "fair_at_publish_utc", "combinations", "model"]
PICKS_V2 = ["published_utc", "run_date", "comp", "match_id", "kickoff_utc", "league", "home", "away",
            "market", "gradable", "model_p", "model_fair_odds", "price", "price_basis", "edge_pct",
            "open_mean", "open_mean_utc", "open_books", "combinations", "model"]
COMMITTED_AT = re.compile(r"committed (\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ)")


def weekly(repo, name):
    """(path, header, rows) of every weekly file called `name`, in path order."""
    out = []
    for p in sorted(glob.glob(os.path.join(repo, "[0-9]" * 4, "W[0-9][0-9]", name))):
        with open(p, newline="") as f:
            rd = csv.DictReader(f)
            out.append((p, rd.fieldnames, list(rd)))
    return out


def rows(repo, name):
    return [r for _p, _c, rs in weekly(repo, name) for r in rs]


def blob(cols, rs):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, lineterminator="\n", extrasaction="ignore")
    w.writeheader()
    for r in rs:
        w.writerow(r)
    return hashlib.sha256(buf.getvalue().encode()).hexdigest()


def week_header(repo, name, date):
    iy, iw, _ = datetime.date.fromisoformat(date).isocalendar()
    p = os.path.join(repo, str(iy), f"W{iw:02d}", name + ".csv")
    if not os.path.exists(p):
        return None
    with open(p, newline="") as f:
        return csv.DictReader(f).fieldnames


def commitments(repo):
    """Check every released prediction against the hash published before its kickoff.

    `commitments/<date>.<batch>.sha256` holds the SHA-256 of each of four files' rows for that run
    date and batch, with the row count, and the moment it was committed. Every row of a batch was
    published at that same moment (`published_utc`), so a batch is rebuilt as the rows of its run
    date with that `published_utc`, in file order, under the file's header — and hashed."""
    files = {n: weekly(repo, n + ".csv") for n in ("board", "goals", "scores", "picks", "picks_reissued")}
    out = []
    for man in sorted(glob.glob(os.path.join(repo, "commitments", "*.sha256"))):
        base = os.path.basename(man)[:-len(".sha256")]
        date, _, b = base.rpartition(".")
        text = open(man).read()
        m = COMMITTED_AT.search(text)
        if not date or not m:
            out.append((base, "?", "UNREADABLE", 0, 0))
            continue
        at = m.group(1)
        for line in text.splitlines():
            if line.startswith("#") or not line.strip():
                continue
            want, name, n = line.split()
            n = int(n)
            take, cols = [], None
            for _p, c, rs in files.get(name, []):
                hit = [r for r in rs if r["run_date"] == date and r["published_utc"] == at]
                if hit:
                    take, cols = take + hit, c
            if name == "picks" and not take:
                re_ = [r for _p, _c, rs in files["picks_reissued"] for r in rs
                       if r["run_date"] == date and r["published_utc"] == at]
                if re_:
                    out.append((base, name, "re-issued" if len(re_) == n else "MISMATCH", n, len(re_)))
                    continue
            if not take and n:
                out.append((base, name, "embargoed", n, 0))
                continue
            if not take:                                    # an empty slice: the header alone
                heads = [week_header(repo, name, date)] + [c for _p, c, _r in files.get(name, [])][:1]
                if name == "picks":
                    heads += [PICKS_V2, PICKS_PRELAUNCH]
                heads = [h for h in heads if h]
                if not heads:                               # no file of this kind released anywhere yet
                    out.append((base, name, "embargoed", 0, 0))
                    continue
                ok = any(blob(h, []) == want for h in heads)
                out.append((base, name, "released" if ok else "MISMATCH", 0, 0))
                continue
            got = blob(cols, take)
            out.append((base, name, "released" if got == want and len(take) == n else "MISMATCH", n, len(take)))
    return out


def early_commitments(repo):
    """Each `commitments/early/<date>.<batch>.sha256` covers the early picks kicking off on <date>
    (UTC) that no earlier batch covered, published before the first of them kicked off. Released
    rows carry their batch and a random salt; a batch is rebuilt from the rows carrying its
    `batch` value, in file order, under the file's header."""
    rel, head, problems = defaultdict(list), {}, []
    for _p, cols, rs in weekly(repo, "early.csv"):
        for r in rs:
            if r["batch"] != UNCOMMITTED:
                rel[r["batch"]].append(r)
                head[r["batch"]] = cols
    out, seen = [], set()
    for man in sorted(glob.glob(os.path.join(repo, "commitments", "early", "*.sha256"))):
        batch = os.path.basename(man)[:-len(".sha256")]
        seen.add(batch)
        lines = [ln.split() for ln in open(man) if ln.strip() and not ln.startswith("#")]
        if len(lines) != 1 or len(lines[0]) != 3:
            problems.append(f"early commitment {batch}: unreadable")
            continue
        want, n = lines[0][0], int(lines[0][2])
        take = rel.get(batch, [])
        if not take:
            out.append((batch, "embargoed", n, 0))
            continue
        ok = len(take) == n and blob(head[batch], take) == want
        out.append((batch, "released" if ok else "MISMATCH", n, len(take)))
    for batch in sorted(set(rel) - seen):
        problems.append(f"early rows released under batch {batch}, which has no commitment")
    return out, problems


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def net_return(price, frac):
    """Net return on a one-unit stake. `settle_frac` is the fraction WON: 1.0 won, 0.75 quarter
    line half won, 0.5 push (stake back), 0.25 quarter line half lost, 0.0 lost. With
    m = 2*frac - 1: the winning part is paid at the price, the losing part costs its stake."""
    if price is None or frac is None:
        return None
    m = 2.0 * frac - 1.0
    return m * (price - 1.0) if m >= 0 else m


def early(repo, since=""):
    problems = []
    all_ = rows(repo, "early.csv")
    committed = [r for r in all_ if r["batch"] != UNCOMMITTED]
    late = [r for r in all_ if r["batch"] == UNCOMMITTED]
    settled = rows(repo, "early_settled.csv")
    if not (all_ or settled or glob.glob(os.path.join(repo, "commitments", "early", "*.sha256"))):
        return problems
    for r in committed:
        if not (r["posted_utc"] <= r["committed_utc"] < r["kickoff_utc"]):
            problems.append(f"early pick committed after kickoff: {r['batch']} {r['home']} v {r['away']} {r['pick']}")
    for r in late:
        if r["committed_utc"] or r["salt"]:
            problems.append(f"uncommitted early pick carries a commitment time or salt: {r['home']} v {r['away']} {r['pick']}")
    seen = set()
    for r in all_:
        k = (r["match_id"], r["pick"])
        if k in seen:
            problems.append(f"duplicate early pick: {k}")
        seen.add(k)
    known = {(r["batch"], r["match_id"], r["pick"]) for r in all_}
    done = set()
    for r in settled:
        k = (r["batch"], r["match_id"], r["pick"])
        if k not in known:
            problems.append(f"early settled row with no published pick: {k}")
        if k in done:
            problems.append(f"early pick settled twice: {k}")
        done.add(k)
    commits, cp = early_commitments(repo)
    problems += cp
    for batch, state, n_want, n_got in commits:
        if state == "MISMATCH":
            problems.append(f"early commitment broken: {batch} - the {n_got} released rows do not hash to the "
                            f"commitment published before kickoff ({n_want} rows)")
    rel = sum(1 for c in commits if c[1] == "released")
    emb = [c for c in commits if c[1] == "embargoed"]
    print("\nearly picks (published ahead of the main board - see METHODOLOGY.md)")
    print(f"  released: {len(all_):>5} early picks, of which")
    print(f"    committed before kickoff: {len(committed):>5}  from {rel} batch(es) matching their hash; "
          f"{sum(c[2] for c in emb)} more in {len(emb)} batch(es) still embargoed")
    if late:
        print(f"    uncommitted:              {len(late):>5}  published on the website, never committed here "
              f"before kickoff; no proof of timing - see README.md")
    for label, pick_ in (("all", lambda b: True), ("committed", lambda b: b != UNCOMMITTED),
                         ("uncommitted", lambda b: b == UNCOMMITTED)):
        if label == "all" and not late:
            continue
        keep = [r for r in settled if pick_(r["batch"]) and r["kickoff_utc"] >= since]
        if not keep:
            continue
        hit = weight = implied = 0.0
        voids = 0
        for r in keep:
            h, w = EARLY_SCORE.get(r["result"], (0.0, 0.0))
            hit, weight = hit + h, weight + w
            voids += r["result"] == "Void"
            price = num(r["min_odds"])
            implied += w / price if price else 0.0
        clv = [num(r.get("clv_mean_pct")) for r in keep if num(r.get("clv_mean_pct")) is not None]
        line = f"  {label:<11} settled {len(keep):>4}"
        if weight:
            line += f"  hit rate {hit / weight * 100:.1f}%  - the minimum prices imply {implied / weight * 100:.1f}%"
        if clv:
            line += f"  CLV {sum(clv) / len(clv):+.2f}% ({len(clv)})"
        print(line + (f"  ({voids} void)" if voids else ""))
    print("  A half result counts as half a leg and a void is left out, as on the website. `min_odds` is the\n"
          "  MINIMUM a pick was published at. CLV compares the average of 3+ bookmakers when the pick was\n"
          "  posted with the same average at the last capture before kickoff.")
    return problems


def key(r):
    return r.get("match_id") or r.get("fixture_id", "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--market", help="only this market")
    ap.add_argument("--from", dest="since", default="", help="only kickoffs on/after YYYY-MM-DD")
    a = ap.parse_args()

    board = rows(a.repo, "board.csv")
    picks = rows(a.repo, "picks.csv")
    reissued = rows(a.repo, "picks_reissued.csv")
    settled = rows(a.repo, "settled.csv")
    problems = []

    for r in board + picks + reissued:
        if not (r["published_utc"] < r["kickoff_utc"]):
            problems.append(f"published after kickoff: {r['home']} v {r['away']} {r.get('market', '')} "
                            f"published {r['published_utc']} ko {r['kickoff_utc']}")
    for label, rs, extra in (("board", board, ()), ("picks", picks + reissued, ("market",))):
        seen = set()
        for r in rs:
            k = (r["run_date"], key(r)) + tuple(r[c] for c in extra)
            if k in seen:
                problems.append(f"duplicate {label} row: {k}")
            seen.add(k)
    commits = commitments(a.repo)
    for base, name, state, n_want, n_got in commits:
        if state in ("MISMATCH", "UNREADABLE"):
            problems.append(f"commitment broken: {base} / {name} - {n_got} released rows against {n_want} committed")
    published = {(r["run_date"], key(r), r["market"]) for r in picks + reissued}
    for r in settled:
        if (r["run_date"], key(r), r["market"]) not in published:
            problems.append(f"settled row with no published pick: {(r['run_date'], key(r), r['market'])}")

    keep = [r for r in settled if (not a.market or r["market"] == a.market) and r["kickoff_utc"] >= a.since]
    n = len(keep)
    wins = sum(1 for r in keep if r["result"] == "1")
    priced = [r for r in keep if r.get("price_basis") in SHOWN and num(r.get("price")) is not None]
    pnl = sum(net_return(num(r["price"]), num(r["settle_frac"])) or 0.0 for r in priced)
    clv = [num(r["clv_mean_pct"]) for r in keep if num(r.get("clv_mean_pct")) is not None]
    re_keys = {(r["run_date"], key(r), r["market"]) for r in reissued}
    gradable = [r for r in picks + reissued if r.get("gradable", "1") == "1"]
    done = {(r["run_date"], key(r), r["market"]) for r in settled}
    waiting = [r for r in gradable if (r["run_date"], key(r), r["market"]) not in done]

    print(f"board:    {len(board):>6} fixtures")
    print(f"picks:    {len(picks) + len(reissued):>6} legs published"
          + (f"  ({len(reissued)} re-issued at the website's price - see README.md)" if reissued else ""))
    print(f"settled:  {n:>6} legs" + (f"  (filtered: market={a.market or 'all'}, from={a.since or 'start'})"
                                      if a.market or a.since else ""))
    print(f"pending:  {len(waiting):>6} gradable legs not yet settled")
    states = defaultdict(int)
    for c in commits:
        states[c[2]] += 1
    if commits:
        print("\ncommitments: " + ", ".join(f"{v} file(s) {k}" for k, v in sorted(states.items())))
        for base in sorted({c[0] for c in commits}):
            st = {c[1]: c[2] for c in commits if c[0] == base}
            mark = ("MISMATCH" if "MISMATCH" in st.values() else "embargoed" if "embargoed" in st.values()
                    else "re-issued picks" if "re-issued" in st.values() else "released")
            n_p = sum(c[3] for c in commits if c[0] == base and c[1] == "picks")
            print(f"  {base:<14} {mark:<16} {n_p} picks")
    if n:
        print(f"\nhit rate:  {wins}/{n} = {wins / n * 100:.1f}%"
              + (f"  ({sum(1 for r in keep if (r['run_date'], key(r), r['market']) in re_keys)} re-issued)" if re_keys else ""))
        if priced:
            print(f"net:       {pnl:+.2f} units on {len(priced)} legs at the website's price, one unit each"
                  f"  ->  {pnl / len(priced) * 100:+.2f}%")
        if clv:
            print(f"CLV:       mean {sum(clv) / len(clv):+.2f}% over {len(clv)} legs "
                  f"({sum(1 for c in clv if c > 0) / len(clv) * 100:.1f}% positive)")
        by = defaultdict(lambda: [0, 0, 0.0])
        for r in keep:
            b = by[r["market"]]
            b[0] += 1
            b[1] += r["result"] == "1"
            if r.get("price_basis") in SHOWN:
                b[2] += net_return(num(r["price"]), num(r["settle_frac"])) or 0.0
        print("\n  market            n   won      net")
        for m, (c, w, p) in sorted(by.items(), key=lambda kv: -kv[1][0]):
            print(f"  {m:<16} {c:>3} {w:>5} {p:>+8.2f}")
        print("\nA few dozen settled legs is a very small sample: a short-run result is mostly variance.\n"
              "Prices are the website's: the average of 3+ bookmakers, or a pick's minimum. A leg priced\n"
              "at the model's own estimate never counts towards the return.")
    if not a.market:
        problems += early(a.repo, a.since)
    if problems:
        print(f"\n❌ {len(problems)} problem(s):")
        for p in problems[:20]:
            print("  ·", p)
        return 1
    print("\n✅ every commitment checks or is accounted for; every pick pre-dates its kickoff; no duplicates;\n"
          "   every result maps to a published pick")
    return 0


if __name__ == "__main__":
    sys.exit(main())
