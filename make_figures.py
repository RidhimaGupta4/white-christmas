#!/usr/bin/env python3
"""
Figures for "What counts as a white Christmas?"

Reads the outputs of the two analysis scripts and writes publication figures
(PNG at 300 dpi for print, SVG for the web/GitHub) plus one CSV per figure
holding exactly the numbers drawn (the table view of each chart).

Usage:
  python3 -I make_figures.py results analysis figures

Inputs:
  results/yearly_summary.csv            (white_christmas_replication.py)
  analysis/white_christmas_by_year.csv  (white_christmas_analysis.py)

Design rules followed: one y-axis per panel (no dual axes); bars start at zero;
every percentage shown with its count; 95% intervals where a share of years
is shown; reference lines are solid hairlines and labelled; colour never
carries meaning alone (legend + direct labels + CSV table for every figure);
categorical palette validated for colour-vision deficiency.
"""

import csv
import math
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

# ---- palette (validated: CVD all-pairs PASS for slots 1-3, light surface) ----
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
BLUE = "#2a78d6"     # slot 1
ORANGE = "#eb6834"   # slot 2
NEUTRAL = "#c9c7bf"  # de-emphasis (not counted)
GRAY_BAR = "#a9a7a0" # de-emphasised comparison bars

SOURCE = "Data: Met Office MIDAS Open, UK daily weather observations (v202607), via CEDA. Open Government Licence."

_fonts = {f.name for f in font_manager.fontManager.ttflist}
FONT = "Inter" if "Inter" in _fonts else "DejaVu Sans"
plt.rcParams.update({
    "font.family": FONT,
    "font.size": 10,
    "axes.edgecolor": AXIS,
    "axes.labelcolor": INK2,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "xtick.labelcolor": INK2,
    "ytick.labelcolor": INK2,
    "axes.titlecolor": INK,
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
    "svg.fonttype": "none",
    "pdf.fonttype": 42,   # editable text in Illustrator (Significance asks for EPS / editable PDF)
    "ps.fonttype": 42,
})


def read(path):
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))


def wilson(k, n, z=1.96):
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return 100 * (c - h), 100 * (c + h)


def p_any(N, m, k):
    if m == 0:
        return 0.0
    if N - m < k:
        return 1.0
    return 1.0 - math.comb(N - m, k) / math.comb(N, k)


def style(ax, grid_axis="y"):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_visible(grid_axis == "x")
    ax.spines["left"].set_color(AXIS)
    ax.spines["bottom"].set_color(AXIS)
    ax.tick_params(length=0, pad=6)
    ax.grid(axis=grid_axis, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def header(fig, title, subtitle, top=0.955):
    h = fig.get_size_inches()[1]
    fig.text(0.055, top, title, fontsize=15, fontweight="bold", color=INK, ha="left", va="top")
    fig.text(0.055, top - 0.42 / h, subtitle, fontsize=10, color=INK2, ha="left", va="top", linespacing=1.4)


def footer(fig, note=None):
    h = fig.get_size_inches()[1]
    y = 0.12 / h
    fig.text(0.055, y, SOURCE, fontsize=7.5, color=MUTED, ha="left", va="bottom")
    if note:
        fig.text(0.055, y + 0.2 / h, note, fontsize=7.5, color=MUTED, ha="left", va="bottom", linespacing=1.35)


def save(fig, outdir, name):
    fig.savefig(os.path.join(outdir, name + ".png"), dpi=300)
    fig.savefig(os.path.join(outdir, name + ".svg"))
    fig.savefig(os.path.join(outdir, name + ".pdf"))
    fig.savefig(os.path.join(outdir, name + ".eps"))
    plt.close(fig)


def write_csv(outdir, name, header_row, rows):
    with open(os.path.join(outdir, name + "_data.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header_row)
        w.writerows(rows)


def main():
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)
    results, analysis, outdir = sys.argv[1:4]
    os.makedirs(outdir, exist_ok=True)
    ys = {int(r["year"]): r for r in read(os.path.join(results, "yearly_summary.csv"))}
    by = {int(r["year"]): r for r in read(os.path.join(analysis, "white_christmas_by_year.csv"))}
    years = [y for y in sorted(by) if y >= 1960]
    T = lambda v: v == "True"
    n_years = len(years)

    # ------------------------------------------------------------------ Fig 1
    defs = [
        ("Official rule: snow or sleet\nseen falling at any station", "D1_official_any_station", True),
        ("Same rule, excluding values\nflagged as automatic or corrected", "D4_direct_only_any", False),
        ("Same rule, snow only\n(sleet does not count)", "D5_snow_only_any", False),
        ("Snow or sleet falling at\n5% or more of stations", "D2_5pct_fullday", False),
        ("Widespread lying snow:\n40% or more of stations", "D3_widespread_lying", False),
    ]
    rows = []
    for label, col, official in defs:
        k = sum(T(by[y][col]) for y in years)
        lo, hi = wilson(k, n_years)
        rows.append((label, k, 100 * k / n_years, lo, hi, official))

    fig = plt.figure(figsize=(8, 5.4))
    ax = fig.add_axes([0.33, 0.19, 0.52, 0.58])
    style(ax, grid_axis="x")
    ypos = list(range(len(rows)))[::-1]
    for yp, (label, k, p, lo, hi, official) in zip(ypos, rows):
        ax.barh(yp, p, height=0.46, color=BLUE if official else GRAY_BAR, zorder=2)
        ax.plot([lo, hi], [yp, yp], color=INK2, linewidth=1.1, zorder=3, solid_capstyle="butt")
        for xe in (lo, hi):
            ax.plot([xe, xe], [yp - 0.09, yp + 0.09], color=INK2, linewidth=1.1, zorder=3)
        ax.text(hi + 1.5, yp, f"{p:.0f}%  ({k} of {n_years})", va="center", ha="left",
                fontsize=10, color=INK, fontweight="bold" if official else "normal")
    ax.set_yticks(ypos)
    ax.set_yticklabels([r[0] for r in rows], fontsize=9.5, color=INK)
    ax.set_xlim(0, 100)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"])
    ax.spines["left"].set_visible(False)
    header(fig, "How often is Christmas white? It depends on the definition",
           f"Share of Christmas Days 1960–2025 counted as 'white' under five definitions, UK Met Office stations.\n"
           f"Black lines show 95% intervals. Blue is the Met Office's own rule.")
    footer(fig, "Intervals: Wilson score, treating each year as independent. 1973 excluded from 'white' under the official rule:\n"
                "its only snow report is flagged suspect by Met Office quality control (including it gives 54 of 66).")
    save(fig, outdir, "fig1_definitions")
    write_csv(outdir, "fig1_definitions",
              ["definition", "white_years", "years", "pct", "ci95_low", "ci95_high"],
              [(r[0].replace("\n", " "), r[1], n_years, round(r[2], 1), round(r[3], 1), round(r[4], 1)) for r in rows])

    # ------------------------------------------------------------------ Fig 2
    data = [(int(by[y]["n_fullday"]), int(by[y]["n_fell"])) for y in years]
    kmax = min(N for N, _ in data)
    ks = list(range(1, kmax + 1))
    curve = [100 * sum(p_any(N, m, k) for N, m in data) / len(data) for k in ks]
    actual = 100 * sum(1 for _, m in data if m > 0) / len(data)
    n_min = min(N for N, _ in data)
    n_max = max(N for N, _ in data)

    fig = plt.figure(figsize=(8, 5.4))
    ax = fig.add_axes([0.09, 0.26, 0.84, 0.5])
    style(ax, grid_axis="y")
    ax.plot(ks, curve, color=BLUE, linewidth=2.2, zorder=3, solid_capstyle="round")
    ax.axhline(actual, color=INK2, linewidth=1.0, zorder=2)
    ax.text(kmax, actual + 2.2, f"Actual network each year ({n_min}–{n_max} stations): {actual:.0f}%",
            ha="right", va="bottom", fontsize=9.5, color=INK)
    marks = [k for k in (5, 10, 25, 50, kmax) if k <= kmax]
    for k in marks:
        v = curve[k - 1]
        ax.scatter([k], [v], s=46, color=BLUE, edgecolor=SURFACE, linewidth=2, zorder=4)
        ax.text(k, v - 6, f"{v:.0f}%", ha="center", va="top", fontsize=9.5, color=INK)
    ax.set_ylim(0, 100)
    ax.set_xlim(0, kmax + 1)
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_yticklabels(["0%", "25%", "50%", "75%", "100%"])
    ax.set_xticks(marks)
    ax.set_xlabel("Number of stations in the network", labelpad=8)
    header(fig, "More stations, more white Christmases",
           f"Same {n_years} Christmas Days (1960–2025), same weather. Share that would count as 'white' under the\n"
           f"official rule (snow or sleet at any station) if the network had only this many stations.")
    footer(fig, "Exact calculation (hypergeometric), averaged over the same 66 years for every network size; no simulation.\n"
                f"Assumes stations are drawn at random from each year's network, ignoring geography. Curve stops at {kmax}, the smallest yearly network.")
    save(fig, outdir, "fig2_network_size")
    write_csv(outdir, "fig2_network_size", ["stations_k", "pct_white_christmases"],
              [(k, round(v, 2)) for k, v in zip(ks, curve)] + [("actual_network", round(actual, 2))])

    # ------------------------------------------------------------------ Fig 3
    yrs = [y for y in sorted(ys) if y >= 1960]
    direct, filled, excluded = [], [], []
    for y in yrs:
        r = ys[y]
        full = int(r["n_stations_snow_reported"]) - int(r["n_code9_restricted_no_snow"])
        est = int(r["n_fullday_estimated_values"])
        direct.append(full - est)
        filled.append(est)
        excluded.append(int(r["n_code9_restricted_no_snow"]))

    fig = plt.figure(figsize=(9, 5.6))
    ax = fig.add_axes([0.075, 0.2, 0.89, 0.5])
    style(ax, grid_axis="y")
    w = 0.78
    ax.bar(yrs, direct, width=w, color=BLUE, edgecolor=SURFACE, linewidth=0.4, zorder=2, label="Counted: other values")
    ax.bar(yrs, filled, width=w, bottom=direct, color=ORANGE, edgecolor=SURFACE, linewidth=0.4, zorder=2,
           label="Counted: automatic weather sensor")
    bottoms = [a + b for a, b in zip(direct, filled)]
    ax.bar(yrs, excluded, width=w, bottom=bottoms, color=NEUTRAL, edgecolor=SURFACE, linewidth=0.4, zorder=2,
           label="Not counted: incomplete day (code 9)")
    ax.set_xlim(1959.2, max(yrs) + 0.8)
    ax.set_xticks(list(range(1960, max(yrs) + 1, 10)))
    ax.set_ylabel("Stations reporting on 25 December", labelpad=8)
    leg = ax.legend(loc="upper left", bbox_to_anchor=(0, 1.17), ncol=2, frameon=False, fontsize=9,
                    handlelength=1.1, handleheight=1.1, columnspacing=1.6)
    for t in leg.get_texts():
        t.set_color(INK)
    i23 = yrs.index(2023) if 2023 in yrs else None
    if i23 is not None:
        top23 = direct[i23] + filled[i23] + excluded[i23]
        ax.annotate(f"2023: counted stations fell\nfrom {direct[i23-1] + filled[i23-1]} to {direct[i23] + filled[i23]}",
                    xy=(2023, top23 + 4), xytext=(2009.5, top23 + 150), fontsize=9, color=INK, ha="center",
                    arrowprops=dict(arrowstyle="-", color=INK2, linewidth=0.8))
    if 1971 in yrs:
        i71 = yrs.index(1971)
        ax.annotate("Open-data record\nexpands in 1971", xy=(1971, direct[i71] + filled[i71] + excluded[i71] + 6),
                    xytext=(1965, 330), fontsize=9, color=INK, ha="center",
                    arrowprops=dict(arrowstyle="-", color=INK2, linewidth=0.8))
    ax.set_ylim(0, 620)
    header(fig, "The stations behind the statistic",
           "UK Met Office stations reporting a snow observation for Christmas Day.\n"
           "Only blue and orange count towards the Met Office's 'snow falling' percentage.", top=0.965)
    footer(fig, "Orange = automated observation (quality flag 1006 = automatic sensor, passed QC, per Met Office NCIC; also 2006 corrections, a small minority).\n"
                "Code 9 = part-day observing or, at automatic sites, a missing hourly sensor reading on a snow-free day. MIDAS Open holds about 96% of the archive.")
    save(fig, outdir, "fig3_network_history")
    write_csv(outdir, "fig3_network_history",
              ["year", "counted_other", "counted_automatic_or_corrected", "not_counted_code9"],
              list(zip(yrs, direct, filled, excluded)))

    # ------------------------------------------------------------------ Fig 4
    fell = [float(by[y]["pct_fell_fullday"]) if by[y]["pct_fell_fullday"] != "" else 0.0 for y in years]
    lying = [float(by[y]["pct_lying"]) if by[y]["pct_lying"] != "" else 0.0 for y in years]
    fig = plt.figure(figsize=(9, 6.6))
    ax1 = fig.add_axes([0.075, 0.52, 0.89, 0.24])
    ax2 = fig.add_axes([0.075, 0.18, 0.89, 0.24], sharex=ax1)
    for ax, vals, thr, thr_label, title in (
        (ax1, fell, 5, "", "Snow or sleet seen falling (% of counted stations). Line: 5%"),
        (ax2, lying, 40, "", "Snow lying at 09:00, 1 cm or more (% of stations measuring depth). Line: 40%, 'widespread'"),
    ):
        style(ax, grid_axis="y")
        ax.bar(years, vals, width=0.78, color=BLUE, edgecolor=SURFACE, linewidth=0.4, zorder=2)
        ax.axhline(thr, color=INK2, linewidth=0.9, zorder=3)
        ax.set_ylim(0, 100)
        ax.set_yticks([0, 50, 100])
        ax.set_yticklabels(["0%", "50%", "100%"])
        ax.set_title(title, loc="left", fontsize=10, color=INK, pad=6)
    for y in (1981, 1995, 2009, 2010):
        if y not in years:
            continue
        v = lying[years.index(y)]
        ax2.text(y + (0.35 if y == 2009 else 0), v + 2.5, str(y), ha="right" if y == 2009 else "center",
                 va="bottom", fontsize=8.5, color=INK, fontweight="bold")
    ax1.tick_params(labelbottom=False)
    ax2.set_xlim(1959.2, max(years) + 0.8)
    ax2.set_xticks(list(range(1960, max(years) + 1, 10)))
    header(fig, f"{n_years} Christmas Days, measured two ways",
           "Falling snow is common but usually patchy. Snow on the ground is rare: widespread\n"
           "lying snow happened four times, exactly matching the Met Office's own record.", top=0.97)
    footer(fig, "Station sets differ by panel, as in the Met Office's published figures: top = stations observed all day;\n"
                "bottom = stations with a valid 09:00 depth reading. 1973's single snow report is flagged suspect and excluded.")
    save(fig, outdir, "fig4_timeline")
    write_csv(outdir, "fig4_timeline", ["year", "pct_fell_counted_stations", "pct_lying_0900"],
              [(y, f, l) for y, f, l in zip(years, fell, lying)])

    # ------------------------------------------------------------------ Fig 5
    r23 = ys.get(2023)
    if r23:
        n_all = int(r23["n_stations_snow_reported"])
        n9 = int(r23["n_code9_restricted_no_snow"])
        n_full = n_all - n9
        k = int(r23["n_snow_or_sleet_fell"])
        bars = [
            (f"All {n_all} stations reporting", 100 * k / n_all, False),
            (f"Only the {n_full} stations with a\ncomplete day (Met Office method)", 100 * k / n_full, True),
        ]
        fig = plt.figure(figsize=(8, 4.2))
        ax = fig.add_axes([0.34, 0.24, 0.58, 0.42])
        style(ax, grid_axis="x")
        ax.spines["left"].set_visible(False)
        for yp, (label, v, hl) in zip([1, 0], bars):
            ax.barh(yp, v, height=0.46, color=BLUE if hl else GRAY_BAR, zorder=2)
            ax.text(v + 0.3, yp, f"{v:.1f}%  ({k} of {n_all if not hl else n_full})", va="center",
                    fontsize=10, color=INK, fontweight="bold" if hl else "normal")
        ax.set_yticks([1, 0])
        ax.set_yticklabels([b[0] for b in bars], fontsize=9.5, color=INK)
        ax.set_xlim(0, 15)
        ax.set_xticks([0, 5, 10, 15])
        ax.set_xticklabels(["0%", "5%", "10%", "15%"])
        header(fig, f"Christmas 2023: the same {k} snowy stations, two answers",
               "Share of stations where snow or sleet was seen falling on 25 December 2023.\n"
               "The Met Office published 11%.", top=0.95)
        footer(fig, f"Met Office rule (NCIC): an automatic station that reports snow in any hour is counted; one whose sensor misses any hour\n"
                    f"of a snow-free day is coded 9 and dropped. {n9} of {n_all} stations were coded 9 in 2023 "
                    f"(up from {int(ys[2022]['n_code9_restricted_no_snow'])} in 2022), due to sensor performance.")
        save(fig, outdir, "fig5_christmas_2023")
        write_csv(outdir, "fig5_christmas_2023", ["denominator", "stations", "snowy_stations", "pct"],
                  [("all reporting", n_all, k, round(100 * k / n_all, 2)),
                   ("complete day only (Met Office method)", n_full, k, round(100 * k / n_full, 2))])

    # ------------------------------------------------------------------ Fig 6
    # Gap between the official 'snow falling' percentage (code 9 excluded) and
    # the same percentage with code 9 stations counted as snow-free. Shown for
    # EVERY year in which code 9 exists in the data (1982 onwards), so no
    # window is cherry-picked. Per Met Office NCIC, code 9 is assigned only
    # when no snow was reported (snow in any hour overrides it).
    g_years, gaps, rows6 = [], [], []
    for y in years:
        # Prefer the analysis output (suspect-flagged values excluded), so this
        # figure and white_christmas_analysis.py use identical counts.
        n9 = int(by[y]["n_code9"]) if by[y].get("n_code9", "") != "" else int(ys[y]["n_code9_restricted_no_snow"])
        if y < 1982:
            continue
        f = int(by[y]["n_fell"])
        full = int(by[y]["n_fullday"])
        off = 100 * f / full if full else 0.0
        allst = 100 * f / (full + n9) if (full + n9) else 0.0
        g_years.append(y)
        gaps.append(off - allst)
        rows6.append((y, f, full, n9, round(off, 2), round(allst, 2), round(off - allst, 2)))
    fig = plt.figure(figsize=(9, 5.4))
    ax = fig.add_axes([0.075, 0.22, 0.89, 0.55])
    style(ax, grid_axis="y")
    ax.bar(g_years, gaps, width=0.78, color=BLUE, edgecolor=SURFACE, linewidth=0.4, zorder=2)
    if 2023 in g_years:
        i = g_years.index(2023)
        r = rows6[i]
        ax.annotate(f"2023: official {r[4]:.1f}% (7 of {r[2]})\nvs {r[5]:.1f}% counting all {r[2] + r[3]} stations",
                    xy=(2023, gaps[i] + 0.15), xytext=(2008.5, 7.3), fontsize=9, color=INK, ha="center",
                    arrowprops=dict(arrowstyle="-", color=INK2, linewidth=0.8))
    ax.set_xlim(1981.2, max(g_years) + 0.8)
    ax.set_xticks([1985, 1990, 1995, 2000, 2005, 2010, 2015, 2020, 2025])
    ax.set_ylim(0, 9)
    ax.set_yticks([0, 2, 4, 6, 8])
    ax.set_yticklabels(["0", "+2", "+4", "+6", "+8"])
    ax.set_ylabel("Percentage points", labelpad=8)
    header(fig, "Leaving out incomplete days pushes the figure up",
           "Points added to the official 'snow falling' percentage on Christmas Day by excluding stations coded 9,\n"
           "compared with counting them as snow-free. Every year with code 9 in the data (1982–2025).", top=0.955)
    footer(fig, "Met Office NCIC: code 9 is given only when no snow is reported; snow in any hour overrides it. So excluded stations are snow-free\n"
                "in the hours they did observe. The true figure most plausibly lies between the two values. Zero in years with no snow anywhere.")
    save(fig, outdir, "fig6_code9_gap")
    write_csv(outdir, "fig6_code9_gap",
              ["year", "stations_snow_or_sleet", "stations_complete_day", "stations_code9",
               "official_pct_code9_excluded", "pct_code9_as_snow_free", "gap_points"], rows6)

    print("figures written to", outdir)


if __name__ == "__main__":
    main()
