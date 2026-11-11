#!/usr/bin/env python3
"""
White Christmas replication from Met Office MIDAS Open daily weather observations.

What it does
------------
1. Walks a local copy of the MIDAS Open "uk-daily-weather-obs" dataset
   (only qc-version-1 files are used).
2. Pulls every station's 25 December records for every year:
     - snow_day_id  : 24-hour value (ob_hour_count == 24, ends 23:59 on 25 Dec)
                      0 = no snow/sleet (full day observed)
                      1 = sleet
                      5 = snow
                      9 = no snow/sleet observed, RESTRICTED observing period
     - lying_snow_flag : 09:00 spot value on 25 Dec (1 = >= half ground covered)
3. Applies the data-handling rules:
     - keep only rows with version_num == 1 (quality-checked)
     - de-duplicate to ONE value per station (src_id) per year; a station can
       carry several ids (e.g. two DCNN numbers) and would otherwise be
       double-counted
     - conflicting duplicate values are logged, never silently resolved
     - code 9 is NOT treated as missing. In real files it is the routine
       "no snow" entry at stations observed only part of the day (e.g. one
       test station: 355 of 365 days coded 9). Treating it as missing would
       drop most negative days and inflate the rates. The script reports both
       denominators so the effect is visible:
         main  : snow fell (1 or 5) / stations reporting any of 0,1,5,9
         sens. : snow fell (1 or 5) / stations reporting 0,1,5 only
4. Flags Northern Ireland stations (historic counties antrim, armagh, down,
   fermanagh, londonderry, tyrone) and reports the share of the network they
   form each year.
5. Compares results with the Met Office's published figures and prints a
   pass/fail replication table.

Usage
-----
  python3 -I white_christmas_replication.py /path/to/uk-daily-weather-obs/dataset-version-XXXXXX  OUTDIR

Outputs (in OUTDIR)
-------------------
  station_year_records.csv   one row per station per year (25 Dec)
  yearly_summary.csv         per-year counts and percentages
  replication_check.csv      computed vs Met Office published figures
  conflicts.csv              duplicate rows that disagreed (should be empty)
  named_stations_2022.csv    the five stations named in 2022 press reports
"""

import csv
import os
import sys
from collections import defaultdict

NI_COUNTIES = {"antrim", "armagh", "down", "fermanagh", "londonderry", "tyrone"}

# Met Office published figures (percent of stations), with sources.
# None = not published.
MET_OFFICE_PUBLISHED = {
    # year: (pct_falling, pct_lying, source)
    2004: (64, 34, "Met Office via PA (64% falling, 34% lying)"),
    2009: (13, 57, "Met Office white Christmas page"),
    2010: (19, 83, "Met Office white Christmas page"),
    2015: (10, None, "Met Office via press (10% falling)"),
    2016: (6, None, "Met Office via press (6% falling)"),
    2017: (11, 0, "Met Office via press (11% falling, none lying)"),
    2018: (0, None, "Met Office page: no station recorded snow falling"),
    2019: (0, None, "Met Office page: no station recorded snow falling"),
    2020: (6, 4, "Met Office white Christmas page"),
    2021: (6, 1, "Met Office page (<1% lying; checked as <=1)"),
    2022: (9, 0, "Met Office white Christmas page"),
    2023: (11, 0, "Met Office white Christmas page"),
}

# Confirmed corrections to published figures. The ORIGINAL published value is
# still graded above (the pre-specified test); the corrected value is graded
# separately and both are reported, so nothing is swapped silently.
PUBLISHED_CORRECTIONS = {
    2009: (20, "Met Office NCIC, email of 6 Nov 2026: published 13% is an error; should be 20% (snow or sleet)"),
}

# Absolute tolerance in percentage points. Published figures are rounded to
# whole percent, and Met Office may use a slightly different station set, so
# exact equality is not expected.
TOLERANCE_PP = 2.0


def qc_digits(q):
    """Decode a MIDAS _q flag (MESQL, right-aligned). Returns (E, S) digits or (None, None)."""
    if not q or not q.isdigit():
        return None, None
    d = q.zfill(5)
    return int(d[1]), int(d[2])


def is_estimate(q):
    # E digit 1 = estimate/correction derived automatically, 2 = set manually
    return any(qc_digits(x)[0] in (1, 2) for x in q.split("|") if x)


def is_suspect(q):
    # S digit 1 = observed and suspect, 4 = unreliable estimate,
    # 5 = correction (reported value assumed to be in error)
    return any(qc_digits(x)[1] in (1, 4, 5) for x in q.split("|") if x)


def read_badc_csv(path):
    """Parse a BADC-CSV file. Returns (global_metadata, list_of_row_dicts)."""
    meta = {}
    with open(path, newline="", encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines()
    try:
        start = lines.index("data")
    except ValueError:
        return meta, []
    for line in lines[:start]:
        parts = line.split(",")
        if len(parts) >= 3 and parts[1] == "G":
            meta[parts[0]] = ",".join(parts[2:])
    header = lines[start + 1].split(",")
    rows = []
    for line in lines[start + 2:]:
        if not line or line.strip() == "end data":
            continue
        rows.append(dict(zip(header, line.split(","))))
    return meta, rows


def find_files(root):
    """Yield paths of qc-version-1 CSV files under root."""
    for dirpath, _dirs, files in os.walk(root):
        if os.path.basename(dirpath) != "qc-version-1":
            continue
        for name in files:
            if name.endswith(".csv") and "_qcv-1_" in name:
                yield os.path.join(dirpath, name)


def county_from_path(path, meta):
    county = meta.get("historic_county_name")
    if county:
        return county.strip().lower()
    # .../<county>/<src_id_station>/qc-version-1/<file>
    parts = path.split(os.sep)
    return parts[-4].lower() if len(parts) >= 4 else ""


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    root, outdir = sys.argv[1], sys.argv[2]
    os.makedirs(outdir, exist_ok=True)

    # (year, src_id) -> {"snow": set(), "lying": set(), "county":..., "station":...}
    rec = defaultdict(lambda: {"snow": set(), "lying": set(), "depth": set(), "q": set(), "county": "", "station": ""})
    n_files = 0
    n_dropped_version = 0
    # Nothing is dropped silently: every 25/26-Dec row carrying a snow or
    # lying-snow value that does NOT match the standard timing is logged here,
    # as is every unexpected code value.
    nonstandard = []
    unexpected_codes = []
    qc_flags = defaultdict(int)  # snow_day_id_q values on rows that were used

    for path in find_files(root):
        meta, rows = read_badc_csv(path)
        n_files += 1
        county = county_from_path(path, meta)
        station = meta.get("observation_station", "")
        for r in rows:
            t = r.get("ob_end_time", "")
            md = t[5:10]
            if md not in ("12-25", "12-26"):
                continue
            sd = r.get("snow_day_id", "NA").strip()
            ly = r.get("lying_snow_flag", "NA").strip()
            dp = r.get("snow_depth", "NA").strip()
            has_sd = sd not in ("", "NA")
            has_ly = ly not in ("", "NA")
            has_dp = dp not in ("", "NA")
            if not (has_sd or has_ly or has_dp):
                continue
            hours = r.get("ob_hour_count", "")
            src = r.get("src_id", "").strip()
            std_sd = md == "12-25" and hours == "24" and t[11:16] == "23:59"
            std_ly = md == "12-25" and hours == "0" and t[11:16] == "09:00"
            # A 24-h snow-day row ending on 26 Dec (e.g. 00:00 or 09:00) could
            # cover 25 Dec under a different reporting convention. Log it so
            # its frequency can be judged; do not count it.
            # A normal 26-Dec day (ending 26 Dec 23:59) covers only Boxing Day
            # and is NOT logged.
            sd_could_cover_25 = (md == "12-25") or (hours == "24" and t[11:16] != "23:59")
            if (has_sd and not std_sd and sd_could_cover_25) or \
               ((has_ly or has_dp) and not std_ly and md == "12-25"):
                nonstandard.append((t, src, station, hours, sd, ly, r.get("met_domain_name", "")))
            if md != "12-25" or not src or not (std_sd or std_ly):
                continue
            if r.get("version_num") != "1":
                n_dropped_version += 1
                continue
            year = int(t[:4])
            key = (year, src)
            rec[key]["county"] = county
            rec[key]["station"] = station
            if std_sd and has_sd:
                if sd in ("0", "1", "5", "9"):
                    rec[key]["snow"].add(sd)
                    qv = r.get("snow_day_id_q", "column absent").strip() or "blank"
                    qc_flags[qv] += 1
                    rec[key]["q"].add(qv)
                else:
                    unexpected_codes.append((t, src, station, "snow_day_id", sd))
            if std_ly and has_ly:
                if ly in ("0", "1"):
                    rec[key]["lying"].add(ly)
                else:
                    unexpected_codes.append((t, src, station, "lying_snow_flag", ly))
            if std_ly and has_dp:
                try:
                    d = float(dp)
                except ValueError:
                    unexpected_codes.append((t, src, station, "snow_depth", dp))
                else:
                    if 0 <= d <= 999:
                        rec[key]["depth"].add(d)
                    else:
                        unexpected_codes.append((t, src, station, "snow_depth", dp))

    conflicts = []
    station_rows = []
    for (year, src), v in sorted(rec.items()):
        snow_vals, lying_vals = v["snow"], v["lying"]
        if len(snow_vals) > 1:
            conflicts.append((year, src, v["station"], "snow_day_id", "|".join(sorted(snow_vals))))
        if len(lying_vals) > 1:
            conflicts.append((year, src, v["station"], "lying_snow_flag", "|".join(sorted(lying_vals))))
        if len(v["depth"]) > 1:
            conflicts.append((year, src, v["station"], "snow_depth", "|".join(str(x) for x in sorted(v["depth"]))))
        # Conflicts are excluded from the counts (not silently resolved).
        snow = next(iter(snow_vals)) if len(snow_vals) == 1 else ""
        lying = next(iter(lying_vals)) if len(lying_vals) == 1 else ""
        depth = next(iter(v["depth"])) if len(v["depth"]) == 1 else ""
        station_rows.append({
            "year": year, "src_id": src, "station": v["station"], "county": v["county"],
            "is_NI": v["county"] in NI_COUNTIES, "snow_day_id": snow, "lying_snow_flag": lying,
            "snow_depth_0900": depth,
            "snow_day_id_q": "|".join(sorted(v["q"])),
        })

    with open(os.path.join(outdir, "station_year_records.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(station_rows[0].keys()) if station_rows else ["year"])
        w.writeheader()
        w.writerows(station_rows)

    with open(os.path.join(outdir, "conflicts.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["year", "src_id", "station", "field", "values"])
        w.writerows(conflicts)

    with open(os.path.join(outdir, "nonstandard_timing_rows.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["ob_end_time", "src_id", "station", "ob_hour_count", "snow_day_id",
                    "lying_snow_flag", "met_domain_name"])
        w.writerows(nonstandard)

    with open(os.path.join(outdir, "unexpected_codes.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["ob_end_time", "src_id", "station", "field", "value"])
        w.writerows(unexpected_codes)

    # Yearly summary
    by_year = defaultdict(list)
    for r in station_rows:
        by_year[r["year"]].append(r)

    summary = []
    for year in sorted(by_year):
        rows = by_year[year]
        snow_rep = [r for r in rows if r["snow_day_id"] in ("0", "1", "5", "9")]
        full_day = [r for r in snow_rep if r["snow_day_id"] in ("0", "1", "5")]
        fell = [r for r in snow_rep if r["snow_day_id"] in ("1", "5")]
        code9 = [r for r in snow_rep if r["snow_day_id"] == "9"]
        ly_rep = [r for r in rows if r["lying_snow_flag"] in ("0", "1")]
        ly_yes = [r for r in ly_rep if r["lying_snow_flag"] == "1"]
        ni_rep = [r for r in snow_rep if r["is_NI"]]
        ni_fell = [r for r in fell if r["is_NI"]]
        pct = lambda a, b: round(100 * len(a) / len(b), 2) if b else ""

        # LYING SNOW from 09:00 snow depth (modern files leave the lying flag
        # empty). Definitions fixed BEFORE looking at any lying-snow result:
        #   lying          = depth 1-996 cm
        #   997 (<0.5 cm), 998 (cover not continuous) = NOT lying in primary,
        #                    lying in the sensitivity version
        #   999 (measurement impossible) = invalid, excluded
        # Primary denominator (A): the same full-day network that replicated the
        #   falling-snow series; a full-day station with no valid depth reading
        #   is counted as no lying snow. (Assumption: stated, and tested by B.)
        # Sensitivity denominator (B): stations with a valid depth reading only.
        def lying(r, inclusive=False):
            d = r["snow_depth_0900"]
            if d == "":
                return False
            d = float(d)
            if 1 <= d <= 996:
                return True
            return inclusive and d in (997.0, 998.0)

        valid_depth = [r for r in rows if r["snow_depth_0900"] != "" and float(r["snow_depth_0900"]) != 999.0]
        depth_zero = [r for r in valid_depth if float(r["snow_depth_0900"]) == 0.0]
        lyA = [r for r in full_day if lying(r)]
        lyB = [r for r in valid_depth if lying(r)]
        lyB_incl = [r for r in valid_depth if lying(r, inclusive=True)]
        fullday_with_depth = [r for r in full_day if r["snow_depth_0900"] != ""]
        snow_only = [r for r in full_day if r["snow_day_id"] == "5"]

        summary.append({
            "year": year,
            "n_stations_snow_reported": len(snow_rep),
            "n_snow_or_sleet_fell": len(fell),
            "n_code9_restricted_no_snow": len(code9),
            "pct_fell_main_(0159_denom)": pct(fell, snow_rep),
            "pct_fell_sensitivity_(015_denom)": pct(fell, full_day),
            "EXPLORATORY_pct_snow_only_code5_fullday": pct(snow_only, full_day),
            "n_stations_lying_reported": len(ly_rep),
            "n_lying_snow": len(ly_yes),
            "pct_lying": pct(ly_yes, ly_rep),
            "n_valid_depth_readings": len(valid_depth),
            "n_depth_zero": len(depth_zero),
            "n_fullday_with_depth": len(fullday_with_depth),
            "n_lying_A": len(lyA),
            "pct_lying_A_fullday": pct(lyA, full_day),
            "pct_lying_B_validdepth": pct(lyB, valid_depth),
            "pct_lying_B_incl_997_998": pct(lyB_incl, valid_depth),
            "n_NI_stations_snow_reported": len(ni_rep),
            "n_NI_snow_fell": len(ni_fell),
            "n_fullday_estimated_values": sum(1 for r in full_day if is_estimate(r["snow_day_id_q"])),
            "n_fell_estimated_values": sum(1 for r in fell if is_estimate(r["snow_day_id_q"])),
            "n_suspect_values": sum(1 for r in snow_rep if is_suspect(r["snow_day_id_q"])),
            "white_christmas_any_station": bool(fell),
        })

    with open(os.path.join(outdir, "yearly_summary.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(summary[0].keys()) if summary else ["year"])
        w.writeheader()
        w.writerows(summary)

    # Replication check
    s_by_year = {s["year"]: s for s in summary}
    # The Met Office does not publish which stations form the denominator, so
    # BOTH candidate denominators are tested. Whichever (if either) matches the
    # published series tells us which network the Met Office uses.
    def verdict(calc, pub, n_fell):
        if pub is None:
            return "n/a"
        if calc == "":
            return "NO DATA"
        if pub == 0:
            return "PASS" if n_fell == 0 else "FAIL"
        return "PASS" if abs(calc - pub) <= TOLERANCE_PP else "FAIL"

    check = []
    for year, (pf, pl, src) in sorted(MET_OFFICE_PUBLISHED.items()):
        s = s_by_year.get(year)
        if not s:
            check.append({"year": year, "published_pct_falling": pf, "published_pct_lying": pl,
                          "fall_main_ok": "NO DATA", "fall_fullday_ok": "NO DATA",
                          "fall_fullday_vs_corrected_ok": "NO DATA",
                          "lying_A_ok": "NO DATA", "lying_B_ok": "NO DATA", "source": src})
            continue
        cm = s["pct_fell_main_(0159_denom)"]
        cs = s["pct_fell_sensitivity_(015_denom)"]
        clA = s["pct_lying_A_fullday"]
        clB = s["pct_lying_B_validdepth"]
        nf = s["n_snow_or_sleet_fell"]
        # For a published 0%, a PASS needs zero stations, not just a small %.
        nA = s["n_lying_A"]
        nB = round(clB * s["n_valid_depth_readings"] / 100) if clB != "" else 0
        check.append({
            "year": year,
            "published_pct_falling": pf,
            "calc_fall_main_0159": cm, "fall_main_ok": verdict(cm, pf, nf),
            "calc_fall_fullday_015": cs, "fall_fullday_ok": verdict(cs, pf, nf),
            "corrected_pct_falling": PUBLISHED_CORRECTIONS.get(year, (pf, ""))[0],
            "fall_fullday_vs_corrected_ok": verdict(cs, PUBLISHED_CORRECTIONS.get(year, (pf, ""))[0], nf),
            "correction_source": PUBLISHED_CORRECTIONS.get(year, (None, ""))[1],
            "published_pct_lying": pl,
            "calc_lying_A_fullday": clA, "lying_A_ok": verdict(clA, pl, nA),
            "calc_lying_B_validdepth": clB, "lying_B_ok": verdict(clB, pl, nB),
            "n_fell": nf,
            "n_denom_main": s["n_stations_snow_reported"],
            "n_denom_fullday": s["n_stations_snow_reported"] - s["n_code9_restricted_no_snow"],
            "n_valid_depth": s["n_valid_depth_readings"],
            "n_depth_zero": s["n_depth_zero"],
            "n_NI": s["n_NI_stations_snow_reported"],
            "source": src,
        })

    fields = ["year", "published_pct_falling", "calc_fall_main_0159", "fall_main_ok",
              "calc_fall_fullday_015", "fall_fullday_ok", "corrected_pct_falling",
              "fall_fullday_vs_corrected_ok", "correction_source", "published_pct_lying",
              "calc_lying_A_fullday", "lying_A_ok", "calc_lying_B_validdepth", "lying_B_ok",
              "n_fell", "n_denom_main", "n_denom_fullday", "n_valid_depth", "n_depth_zero", "n_NI", "source"]
    with open(os.path.join(outdir, "replication_check.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for c in check:
            w.writerow({k: c.get(k, "") for k in fields})

    # Named-station check for 2022: press reports named exactly five stations
    # with sleet/snow falling on 25 Dec 2022. src_ids from the dv-202607
    # station metadata file.
    named_2022 = {
        "19260": "EDINBURGH, GOGARBANK",
        "00067": "LOCH GLASCARNOCH",
        "00044": "ALTNAHARRA NO 2",
        "01534": "GLENANNE NO 2",
        "01435": "LOUGH FEA",
    }
    rows_2022 = {r["src_id"].zfill(5): r for r in station_rows if r["year"] == 2022}
    fell_2022 = {k for k, r in rows_2022.items() if r["snow_day_id"] in ("1", "5")}
    named_lines = []
    for sid, nm in named_2022.items():
        r = rows_2022.get(sid)
        code = r["snow_day_id"] if r else "absent"
        named_lines.append((sid, nm, code if code != "" else "blank/conflict"))
    extra_2022 = sorted(fell_2022 - set(named_2022))

    with open(os.path.join(outdir, "named_stations_2022.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["src_id", "station", "snow_day_id_25dec2022"])
        w.writerows(named_lines)
        for sid in extra_2022:
            w.writerow([sid, rows_2022[sid]["station"] + " (NOT in press list)", rows_2022[sid]["snow_day_id"]])

    print(f"files read: {n_files}")
    print(f"25-Dec rows dropped (version_num != 1): {n_dropped_version}")
    print(f"station-years: {len(station_rows)}   conflicts: {len(conflicts)}")
    print()
    print("REPLICATION CHECK (tolerance ±%.0f pp)" % TOLERANCE_PP)
    print("  FALLING: main = 0/1/5/9 denominator; fullday = 0/1/5 only")
    print("  LYING (09:00 depth >= 1 cm): A = full-day network; B = stations with a valid depth reading")
    print(f"{'year':<6}{'pub':>4}{'main':>7}{'':6}{'fullday':>8}{'':6}{'pubLie':>7}{'lieA':>7}{'':6}"
          f"{'lieB':>7}{'':6}{'fell':>5}{'nFull':>6}{'nDepth':>7}{'nZero':>6}{'NI':>4}")
    for c in check:
        print(f"{c['year']:<6}{str(c['published_pct_falling']):>4}{str(c.get('calc_fall_main_0159', '')):>7}"
              f" {c['fall_main_ok']:<5}{str(c.get('calc_fall_fullday_015', '')):>8} {c['fall_fullday_ok']:<5}"
              f"{str(c['published_pct_lying']):>7}{str(c.get('calc_lying_A_fullday', '')):>7} {c['lying_A_ok']:<5}"
              f"{str(c.get('calc_lying_B_validdepth', '')):>7} {c['lying_B_ok']:<5}"
              f"{str(c.get('n_fell', '')):>5}{str(c.get('n_denom_fullday', '')):>6}"
              f"{str(c.get('n_valid_depth', '')):>7}{str(c.get('n_depth_zero', '')):>6}{str(c.get('n_NI', '')):>4}")
    print()
    print("2022 NAMED-STATION CHECK (press: snow/sleet fell at exactly these five)")
    for sid, nm, code in named_lines:
        ok = "OK" if code in ("1", "5") else "MISMATCH"
        print(f"  {sid} {nm:<22} code={code:<15} {ok}")
    if extra_2022:
        print(f"  extra stations with snow/sleet not in press list: {', '.join(extra_2022)}")
    else:
        print("  no extra stations with snow/sleet")

    # Pre-specified decision rule (fixed BEFORE seeing results, to avoid
    # choosing a definition because it happens to match):
    #   a denominator is "replicated" only if it PASSES in at least 80% of the
    #   years with data for the falling-snow series. Both are always reported.
    #   Tolerance and definitions must not be changed after seeing results
    #   without saying so explicitly in the write-up.
    print()
    print("DECISION RULE (pre-specified): replicated if PASS in >= 80% of years with data")
    for col, label in (("fall_main_ok", "falling, main"), ("fall_fullday_ok", "falling, full-day"),
                       ("fall_fullday_vs_corrected_ok", "falling, full-day vs corrected published"),
                       ("lying_A_ok", "lying A (full-day)"), ("lying_B_ok", "lying B (valid depth)")):
        graded = [c[col] for c in check if c[col] in ("PASS", "FAIL")]
        n_pass = sum(1 for g in graded if g == "PASS")
        share = n_pass / len(graded) if graded else 0
        status = "REPLICATED" if graded and share >= 0.8 else "NOT REPLICATED"
        print(f"  {label:<42} {n_pass}/{len(graded)} years pass -> {status}")
    for y, (v, why) in sorted(PUBLISHED_CORRECTIONS.items()):
        print(f"  correction applied in the separate line only: {y} -> {v}% ({why})")

    print()
    print("DATA-HANDLING LOG (check these before trusting any number)")
    print(f"  conflicting duplicates excluded : {len(conflicts)}  (conflicts.csv)")
    print(f"  non-standard timing rows logged : {len(nonstandard)}  (nonstandard_timing_rows.csv)")
    print(f"  unexpected code values excluded : {len(unexpected_codes)}  (unexpected_codes.csv)")
    print(f"  snow_day_id QC flags on used rows: {dict(qc_flags)}")
    n_est = sum(n for q, n in qc_flags.items() if is_estimate(q))
    n_sus = sum(n for q, n in qc_flags.items() if is_suspect(q))
    print(f"    -> automatic or corrected values (flag E digit 1 or 2): {n_est} rows; suspect: {n_sus} rows")
    print("    (Met Office NCIC: 1006 = automatic-sensor value that passed QC; per-year counts in yearly_summary.csv)")


if __name__ == "__main__":
    main()
