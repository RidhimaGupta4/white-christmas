#!/usr/bin/env python3
"""
White Christmas: how the answer depends on the definition and on the network.

Input : station_year_records.csv written by white_christmas_replication.py
        (one row per station per year, 25 December; already cleaned:
         version 1 only, one value per station, conflicts excluded)
Output: analysis/ folder with CSV tables and a printed report.

Everything below was specified BEFORE looking at the 1960-2025 results.
No parameter is tuned to the data. Nothing is fitted, so there is nothing
to overfit; all numbers are counts, exact probabilities or descriptive rates.

DEFINITIONS (per year, 25 December)
  D1  official   : snow/sleet fell (code 1 or 5) at ANY station
  D2  5 percent  : snow/sleet fell at >= 5% of full-day stations (codes 0/1/5)
  D3  widespread : >= 40% of stations with a valid 09:00 depth had >= 1 cm
                   lying (Met Office "widespread covering" threshold)
  D4  direct-only: D1 using only directly observed values
                   (quality flag E digit = 0, i.e. not program/manual estimates)
  D5  snow-only  : D1 counting code 5 (snow) only, not code 1 (sleet)

REPLICATION CHECKS against published Met Office statements (pass/fail fixed
in advance):
  D3 years must be exactly {1981, 1995, 2009, 2010} for 1960-2025
     ("four times since 1960")
  D2 share of years 1960-2025 must lie in 40%-60% ("around half")

NETWORK-SIZE EFFECT (no randomness; exact formula)
  For a year with N full-day stations of which m had snow/sleet, the chance
  that a network of k stations drawn at random from those N contains at
  least one snowy station is  1 - C(N-m, k) / C(N, k)  (hypergeometric).
  Averaged over years with N >= k, this gives the share of Christmases that
  would be "white" under D1 if the network had only k stations.
  Assumption (stated, not hidden): stations are treated as exchangeable within
  a year, i.e. geography is ignored. Real networks are not random samples,
  so this isolates the pure counting effect of network size.

UNCERTAINTY
  Shares of years get Wilson 95% intervals. Years are treated as independent
  trials; weather in consecutive Decembers is close to independent but this is
  an approximation and is stated as one. No trend test is run: with one binary
  outcome per year, the data cannot support trend claims, and the network
  changed over time (a trend in D1 could be a network artefact).

Usage:
  python3 -I white_christmas_analysis.py results/station_year_records.csv analysis
"""

import csv
import math
import os
import sys
from collections import defaultdict

WIDESPREAD_THRESHOLD = 40.0   # percent of stations with lying snow
FIVE_PCT = 5.0
NETWORK_SIZES = [5, 10, 25, 50, 100, 150, 200, 250]
PUBLISHED_WIDESPREAD = {1981, 1995, 2009, 2010}


def is_estimate(q):
    for x in (q or "").split("|"):
        if x.isdigit() and int(x.zfill(5)[1]) in (1, 2):
            return True
    return False


def is_suspect(q):
    for x in (q or "").split("|"):
        if x.isdigit() and int(x.zfill(5)[2]) in (1, 4, 5):
            return True
    return False


def wilson(k, n, z=1.96):
    if n == 0:
        return ("", "")
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (round(100 * (centre - half), 1), round(100 * (centre + half), 1))


def p_any(N, m, k):
    """P(at least one of m snowy stations is in a random k-subset of N)."""
    if k > N:
        return None
    if m == 0:
        return 0.0
    if N - m < k:
        return 1.0
    return 1.0 - math.comb(N - m, k) / math.comb(N, k)


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    src, outdir = sys.argv[1], sys.argv[2]
    os.makedirs(outdir, exist_ok=True)

    by_year = defaultdict(list)
    n_suspect_dropped = 0
    with open(src, newline="") as fh:
        for r in csv.DictReader(fh):
            if is_suspect(r.get("snow_day_id_q", "")):
                n_suspect_dropped += 1      # suspect values excluded
                r = dict(r, snow_day_id="")  # keep depth, drop snow-day value
            by_year[int(r["year"])].append(r)

    years = sorted(by_year)
    table = []
    for y in years:
        rows = by_year[y]
        full = [r for r in rows if r["snow_day_id"] in ("0", "1", "5")]
        fell = [r for r in rows if r["snow_day_id"] in ("1", "5")]
        code9 = [r for r in rows if r["snow_day_id"] == "9"]
        snow_only = [r for r in rows if r["snow_day_id"] == "5"]
        direct_full = [r for r in full if not is_estimate(r.get("snow_day_id_q", ""))]
        direct_fell = [r for r in direct_full if r["snow_day_id"] in ("1", "5")]
        depth = []
        for r in rows:
            d = r.get("snow_depth_0900", "")
            if d != "" and float(d) != 999.0:
                depth.append(float(d))
        lying = [d for d in depth if 1 <= d <= 996]
        pct_fell_full = 100 * len(fell) / len(full) if full else None
        pct_lying = 100 * len(lying) / len(depth) if depth else None
        # Code 9 counted as snow-free (Met Office NCIC: code 9 is assigned only
        # when no snow is reported; snow in any hour overrides it).
        n_all = len(full) + len(code9)
        pct_fell_all = 100 * len(fell) / n_all if n_all else None
        table.append({
            "year": y,
            "n_fullday": len(full),
            "n_fell": len(fell),
            "pct_fell_fullday": round(pct_fell_full, 2) if pct_fell_full is not None else "",
            "n_code9": len(code9),
            "pct_fell_code9_as_snow_free": round(pct_fell_all, 2) if pct_fell_all is not None else "",
            "gap_points": round(pct_fell_full - pct_fell_all, 2) if (pct_fell_full is not None and pct_fell_all is not None) else "",
            "n_valid_depth": len(depth),
            "n_lying": len(lying),
            "pct_lying": round(pct_lying, 2) if pct_lying is not None else "",
            "n_direct_fullday": len(direct_full),
            "n_direct_fell": len(direct_fell),
            "D1_official_any_station": len(fell) > 0,
            "D2_5pct_fullday": pct_fell_full is not None and pct_fell_full >= FIVE_PCT,
            "D2b_5pct_code9_as_snow_free": pct_fell_all is not None and pct_fell_all >= FIVE_PCT,
            "D3_widespread_lying": pct_lying is not None and pct_lying >= WIDESPREAD_THRESHOLD,
            "D4_direct_only_any": len(direct_fell) > 0,
            "D5_snow_only_any": len(snow_only) > 0,
            "D1_has_data": len(full) + len([r for r in rows if r["snow_day_id"] == "9"]) > 0,
            "D3_has_data": len(depth) > 0,
        })

    with open(os.path.join(outdir, "white_christmas_by_year.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(table[0].keys()))
        w.writeheader()
        w.writerows(table)

    # Share of years under each definition, 1960 onwards (and all years)
    def share(col, has, lo=None, hi=None):
        sel = [t for t in table if t[has] and (lo is None or t["year"] >= lo) and (hi is None or t["year"] <= hi)]
        k = sum(1 for t in sel if t[col])
        n = len(sel)
        ci = wilson(k, n)
        return k, n, (round(100 * k / n, 1) if n else ""), ci

    defs = [
        ("D1_official_any_station", "D1_has_data", "Official: a flake at any station"),
        ("D2_5pct_fullday", "D1_has_data", ">= 5% of full-day stations"),
        ("D3_widespread_lying", "D3_has_data", "Widespread lying snow (>= 40%)"),
        ("D2b_5pct_code9_as_snow_free", "D1_has_data", "Same 5% rule, code 9 counted as snow-free"),
        ("D4_direct_only_any", "D1_has_data", "Any station, excluding automatic/corrected values"),
        ("D5_snow_only_any", "D1_has_data", "Any station, snow only (no sleet)"),
    ]
    summary = []
    for col, has, label in defs:
        k, n, p, ci = share(col, has, lo=1960)
        summary.append({"definition": label, "white_years": k, "years_with_data": n,
                        "pct_of_years": p, "ci95_low": ci[0], "ci95_high": ci[1]})
    with open(os.path.join(outdir, "definition_summary_1960_onwards.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(summary[0].keys()))
        w.writeheader()
        w.writerows(summary)

    # Replication checks fixed in advance
    d3_years = {t["year"] for t in table if t["year"] >= 1960 and t["D3_widespread_lying"]}
    d3_ok = d3_years == PUBLISHED_WIDESPREAD
    d2 = [s for s in summary if s["definition"] == ">= 5% of full-day stations"][0]
    d2_ok = d2["pct_of_years"] != "" and 40 <= d2["pct_of_years"] <= 60

    # Network-size effect (exact). EVERY k is averaged over the SAME years, so
    # differences between k values reflect network size only, not a change
    # in which years are included. k is limited to the smallest network among
    # those years; the actual full networks are reported alongside.
    net_years = [t for t in table if t["year"] >= 1960 and t["n_fullday"] > 0]
    min_n = min(t["n_fullday"] for t in net_years) if net_years else 0
    ks = [k for k in NETWORK_SIZES if k <= min_n]
    if min_n and min_n not in ks:
        ks.append(min_n)
    net = []
    for k in ks:
        probs = [p_any(t["n_fullday"], t["n_fell"], k) for t in net_years]
        net.append({"network_size_k": k, "years_used": len(probs),
                    "expected_pct_white_christmases": round(100 * sum(probs) / len(probs), 1)})
    actual = sum(1 for t in net_years if t["n_fell"] > 0)
    net.append({"network_size_k": "actual network (varies by year)", "years_used": len(net_years),
                "expected_pct_white_christmases": round(100 * actual / len(net_years), 1) if net_years else ""})
    with open(os.path.join(outdir, "network_size_effect.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["network_size_k", "years_used", "expected_pct_white_christmases"])
        w.writeheader()
        w.writerows(net)

    # Report
    span = [t["year"] for t in table if t["D1_has_data"]]
    print(f"years with snow-day data: {min(span)}-{max(span)} ({len(span)} years)")
    print(f"suspect snow-day values excluded: {n_suspect_dropped}")
    print()
    print("SHARE OF CHRISTMASES THAT WERE 'WHITE', 1960 onwards (Wilson 95% CI)")
    for s in summary:
        print(f"  {s['definition']:<50} {s['white_years']:>3}/{s['years_with_data']:<3} "
              f"= {s['pct_of_years']:>5}%  [{s['ci95_low']}, {s['ci95_high']}]")
    print()
    print("REPLICATION CHECKS (fixed in advance)")
    print(f"  widespread years found: {sorted(d3_years)}")
    print(f"  Met Office: {sorted(PUBLISHED_WIDESPREAD)} -> {'PASS' if d3_ok else 'FAIL'}")
    print(f"  >=5% share {d2['pct_of_years']}% (Met Office 'around half', 40-60%) -> {'PASS' if d2_ok else 'FAIL'}")
    print()
    print("NETWORK-SIZE EFFECT: share of Christmases that would count as white")
    print("if the official 'any station' rule used a network of k stations")
    print(f"  (same {len(net_years)} years for every k; k capped at the smallest network, {min_n})")
    for n_ in net:
        print(f"  k = {str(n_['network_size_k']):>3}: {n_['expected_pct_white_christmases']:>5}%  ({n_['years_used']} years)")
    print()
    print("NETWORK SIZE AND DIRECT OBSERVATION BY DECADE (mean stations per year)")
    dec = defaultdict(list)
    for t in table:
        if t["year"] >= 1960 and t["D1_has_data"]:
            dec[10 * (t["year"] // 10)].append(t)
    for d in sorted(dec):
        ts = dec[d]
        mf = sum(t["n_fullday"] for t in ts) / len(ts)
        md = sum(t["n_direct_fullday"] for t in ts) / len(ts)
        print(f"  {d}s: full-day {mf:6.1f}   not automatic/corrected {md:6.1f}   ({len(ts)} years)")
    print()
    # Extra facts used in the article, all computed here so none is hand-made.
    s60 = [t for t in table if t["year"] >= 1960 and t["D1_has_data"]]
    sleet_only = [t["year"] for t in s60 if t["D1_official_any_station"] and not t["D5_snow_only_any"]]
    print("WHITE ONLY BECAUSE OF SLEET:", sleet_only)
    by_y = {t["year"]: t for t in s60}
    wins = []
    for a in range(min(by_y), max(by_y) - 53 + 1):
        ys_ = [y for y in range(a, a + 54) if y in by_y]
        if len(ys_) == 54:
            wins.append((a, a + 53, sum(by_y[y]["D1_official_any_station"] for y in ys_),
                         sum(by_y[y]["D5_snow_only_any"] for y in ys_)))
    if wins:
        print(f"54-YEAR WINDOWS ({len(wins)}): snow or sleet {min(w[2] for w in wins)}-{max(w[2] for w in wins)} of 54; "
              f"snow only {min(w[3] for w in wins)}-{max(w[3] for w in wins)} of 54")
        print("  windows giving snow-only = 38:", [f"{w[0]}-{w[1]}" for w in wins if w[3] == 38])
    gaps = [(t["year"], t["gap_points"], t["n_code9"]) for t in s60 if t["n_code9"] > 0 and t["gap_points"] != ""]
    if gaps:
        pre = [g for g in gaps if g[0] < 2010]
        print("CODE 9: first year", min(g[0] for g in gaps), "| station-days", sum(g[2] for g in gaps))
        if pre:
            mx = max(pre, key=lambda g: g[1])
            print(f"  largest gap before 2010: {mx[1]} points ({mx[0]})")
        print("  gaps from 2010:", [(g[0], g[1]) for g in gaps if g[0] >= 2010])
        only = [t["year"] for t in s60 if t["D2_5pct_fullday"] and not t["D2b_5pct_code9_as_snow_free"]]
        print("  years reaching 5% only because code 9 is excluded:", only)
    with open(os.path.join(outdir, "extra_facts.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["fact", "value"])
        w.writerow(["white_only_because_of_sleet", " ".join(map(str, sleet_only))])
        for a, b, c1, c5 in wins:
            w.writerow([f"window_{a}_{b}_snow_or_sleet", c1])
            w.writerow([f"window_{a}_{b}_snow_only", c5])
    print()
    print("Caveats: years treated as independent; no trend test (network changed);")
    print("network-size effect assumes stations exchangeable within a year.")


if __name__ == "__main__":
    main()
