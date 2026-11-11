# Figures

Each figure comes as a 300 dpi PNG, an SVG (web), and an editable PDF and EPS (the formats Significance asks for), plus a `_data.csv` holding exactly the numbers drawn.
Regenerate them all with:

```
python3 -I make_figures.py results analysis figures
```

Data: Met Office MIDAS Open, UK daily weather observations, dataset version 202607, via CEDA, under the Open Government Licence.

---

## Figure 1: How often is Christmas white? It depends on the definition
`fig1_definitions.png`

**Caption.** Share of Christmas Days 1960–2025 counted as white under five definitions. The Met Office's own rule (snow or sleet seen falling at any station) gives 80% (53 of 66). Requiring snow at 5% or more of stations halves that to 50%. Widespread lying snow happened in only 4 of 66 years (6%). Lines show 95% Wilson intervals, treating years as independent.

**Alt text.** Horizontal bar chart. Official rule 80% (53 of 66). Excluding values flagged as automatic or corrected 80% (53 of 66). Snow only, excluding sleet, 71% (47 of 66). Snow or sleet at 5% or more of stations 50% (33 of 66). Widespread lying snow 6% (4 of 66).

**Note.** 1973 is not counted as white because its only snow report is flagged suspect by Met Office quality control. Including it gives 54 of 66.

## Figure 2: More stations, more white Christmases
`fig2_network_size.png`

**Caption.** The same 66 Christmas Days, recounted as if the network had only k stations. With 5 stations, 34% of Christmases would count as white; with 25, 57%; with 65, 66%. The real networks (65 to 510 stations a year) give 80%. Exact hypergeometric calculation, averaged over the same 66 years for every k, with no simulation.

**Alt text.** A line rising steeply, then flattening: 34% at 5 stations, 44% at 10, 57% at 25, 64% at 50 and 66% at 65. A horizontal reference line at 80% marks the actual networks.

**Assumption.** Stations are treated as drawn at random from each year's network, ignoring geography. The figure isolates the counting effect of network size; it is not a model of any real network.

## Figure 3: The stations behind the statistic
`fig3_network_history.png`

**Caption.** Stations reporting a Christmas Day snow observation, 1960–2025. Orange: automated observations; the Met Office National Climate Information Centre (NCIC) confirmed that quality flag 1006 means an automatic-sensor value that passed quality control (this colour also includes a small number of 2006 corrections). Blue: all other counted values. Grey: code 9, an incomplete day, which the Met Office percentage leaves out; at automatic sites this means at least one of the 24 hourly sensor readings was missing on a day with no snow reported. In 2023 the counted stations fell from 145 to 65, which NCIC attributes to weather-sensor performance.

**Alt text.** Stacked bars by year. Totals rise from about 75 in 1960 to about 460 in 1971, stay near 450–530 until the mid-1990s, then fall to about 210–230. From 2013 most counted stations are orange (automatic sensors), and grey grows. 2023 has a thin counted section and a tall grey section.

**Note.** Station counts are those in the open dataset, which holds about 96% of the full Met Office archive. The 1971 jump reflects what the open record holds; its cause is not established here.

## Figure 4: 66 Christmas Days, measured two ways
`fig4_timeline.png`

**Caption.** Top: percentage of counted stations where snow or sleet was seen falling, with a line at 5%. Bottom: percentage of stations with 1 cm or more of snow lying at 09:00, with a line at 40% marking "widespread". Widespread lying snow occurred in 1981, 1995, 2009 and 2010, exactly matching the Met Office's published record.

**Alt text.** Two bar charts sharing a 1960–2025 axis. Falling snow varies widely, peaking near 60% (1970, 2004). Lying snow is mostly near zero, with four bars above 40%: 1981 (53%), 1995 (41%), 2009 (58%) and 2010 (85%).

**Note.** The two panels use different station sets, as the Met Office's published figures do.

## Figure 5: Christmas 2023, the same 7 snowy stations, two answers
`fig5_christmas_2023.png`

**Caption.** On 25 December 2023, snow or sleet was seen falling at 7 stations. That is 3.2% of all 219 stations reporting, or 10.8% of the 65 stations with a complete day (the Met Office method). The Met Office published 11%. Under the Met Office rule (confirmed by NCIC), an automatic station that reports snow in any hour is counted, but one whose sensor misses any hour of a snow-free day is coded 9 and dropped. Code-9 stations rose from 63 in 2022 to 154 in 2023 because of sensor performance.

**Alt text.** Two horizontal bars: all 219 stations reporting, 3.2% (7 of 219), in grey; only the 65 stations with a complete day, 10.8% (7 of 65), in blue.


## Figure 6: Leaving out incomplete days pushes the figure up
`fig6_code9_gap.png`

**Caption.** Percentage points added to the official "snow falling" figure for Christmas Day by excluding stations coded 9 (incomplete days), compared with counting them as snow-free, for every year in which code 9 appears in the data (1982–2025). The Met Office National Climate Information Centre confirmed that code 9 is given only when no snow is reported; snow in any hour overrides it. Excluded stations therefore saw no snow in the hours they observed, so the true figure most plausibly lies between the two values. The gap was under 2 points every year before 2010, typically 2–4 points since, and 7.6 points in 2023 (10.8% official against 3.2% counting all 219 stations).

**Alt text.** Bar chart of yearly gaps, 1982–2025. Bars are below 2 percentage points until 2009, then mostly 2–4 points from 2010, rising to 7.6 points in 2023. Years with no snow anywhere show zero.

**Assumption.** The comparison treats code 9 stations as snow-free. Snow during their missing hours cannot be ruled out, which is why the two values are presented as a range rather than a correction.

---

### Design choices
- One y-axis per panel. Bars start at zero.
- Every percentage is shown with its count.
- Reference lines are solid and labelled.
- Colour never carries meaning alone: there is always a legend or direct label, and every figure has its data table.
- The categorical palette passed colour-vision-deficiency checks (all pairs, light background). The aqua slot is not used, which avoids its low contrast.
