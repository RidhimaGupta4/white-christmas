#!/usr/bin/env python3
"""
Fast, targeted download of MIDAS Open uk-daily-weather-obs (dv-202607),
quality-checked (qc-version-1) files only, for chosen years only.

It builds each file's address directly from the official station metadata
file instead of crawling thousands of folder listings, and downloads several
files at once.

Usage (in Terminal, from ~/white_christmas, with TOKEN already exported):
  python3 -I fast_download.py STATION_METADATA_CSV YEARS

YEARS examples:
  replication          -> 2004 2009 2010 2015-2023 (what the replication needs)
  1960-2025            -> full history for the article

Files are saved under dap.ceda.ac.uk/badc/ukmo-midas-open/... exactly where
white_christmas_replication.py expects them. Files already present are skipped,
so it is safe to re-run. A station-year with no file on the server (404) is
normal: stations do not report every year.
"""

import csv
import os
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

VERSION = "202607"
BASE = f"https://dap.ceda.ac.uk/badc/ukmo-midas-open/data/uk-daily-weather-obs/dataset-version-{VERSION}"
LOCAL = f"dap.ceda.ac.uk/badc/ukmo-midas-open/data/uk-daily-weather-obs/dataset-version-{VERSION}"
WORKERS = 6
REPLICATION_YEARS = [2004, 2009, 2010] + list(range(2015, 2024))


def parse_years(arg):
    if arg == "replication":
        return REPLICATION_YEARS
    years = []
    for part in arg.split(","):
        if "-" in part:
            a, b = part.split("-")
            years += list(range(int(a), int(b) + 1))
        else:
            years.append(int(part))
    return sorted(set(years))


def read_stations(path):
    lines = open(path, encoding="utf-8", errors="replace").read().splitlines()
    i = lines.index("data")
    header = lines[i + 1].split(",")
    out = []
    for line in lines[i + 2:]:
        if not line or line.strip() == "end data":
            continue
        r = dict(zip(header, next(csv.reader([line]))))
        out.append(r)
    return out


def fetch(url, dest, token):
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return "skipped"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return "absent"
        if e.code in (401, 403):
            return "auth"
        return f"http{e.code}"
    except Exception as e:  # network hiccup: report, re-run later picks it up
        return "error"
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + ".part"
    with open(tmp, "wb") as fh:
        fh.write(data)
    os.replace(tmp, dest)
    return "ok"


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    token = os.environ.get("TOKEN", "")
    if not token:
        print("TOKEN is not set. Run: export TOKEN=\"$(pbpaste)\"")
        sys.exit(1)
    stations = read_stations(sys.argv[1])
    years = parse_years(sys.argv[2])

    jobs = []
    for s in stations:
        try:
            fy, ly = int(float(s["first_year"])), int(float(s["last_year"]))
        except ValueError:
            continue
        sid = s["src_id"].zfill(5)
        county, fname = s["historic_county"], s["station_file_name"]
        for y in years:
            if fy <= y <= ly:
                rel = (f"{county}/{sid}_{fname}/qc-version-1/"
                       f"midas-open_uk-daily-weather-obs_dv-{VERSION}_{county}_{sid}_{fname}_qcv-1_{y}.csv")
                jobs.append((f"{BASE}/{rel}", f"{LOCAL}/{rel}"))

    print(f"{len(stations)} stations, {len(years)} years -> {len(jobs)} candidate files")
    counts = {}
    done = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = [pool.submit(fetch, u, d, token) for u, d in jobs]
        for f in as_completed(futures):
            res = f.result()
            counts[res] = counts.get(res, 0) + 1
            done += 1
            if res == "auth":
                print("\nToken rejected (401/403). Stop with Ctrl+C, make a new token, re-export, re-run.")
            if done % 250 == 0 or done == len(jobs):
                print(f"  {done}/{len(jobs)}  {counts}", flush=True)

    print("\nFinished:", counts)
    print("ok = downloaded, skipped = already had it, absent = no file for that station-year (normal)")
    if counts.get("error") or any(k.startswith("http") for k in counts):
        print("Some downloads failed on network errors: just run the same command again.")


if __name__ == "__main__":
    main()
