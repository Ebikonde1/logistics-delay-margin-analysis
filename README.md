# UK Logistics: Delivery Delays & Margin Analysis

An end-to-end data-analyst portfolio project answering a real operations question:

> **"Which routes and depots are driving late deliveries, and where is margin being lost?"**

Built around a semi-synthetic dataset for a fictional mid-size UK 3PL
("Meridian Freight Ltd" — 8 depots, 11 delivery regions, 31k shipments,
Jul 2025 – Jun 2026), modelled on real UK industry benchmarks: ~93% on-time
delivery, RHA-style operating costs of ~£1.85/mile, realistic cost splits
(driver 38% / fuel 32% / vehicle 18% / overhead 12%) and standard SLA credit terms.

**Headline findings** (full write-up in [recommendations.md](recommendations.md)):

1. The Economy service loses **£249k/year** — priced at £1.32/mile on long-haul
   against a £1.93/mile operating cost.
2. Birmingham's lateness (88.2% vs 93.3% network) is a **PM-shift loading problem**:
   79.9% on-time on evening dispatches vs 91.7% mornings, while every other depot
   is flat across the day.
3. Newcastle's fleet breaks down at **~4× the network rate** (22.8 vs 5.9 per 1,000
   shipments), costing ~£19.5k/year in unplanned repairs.
4. December peak drags the whole network to 89.8% on-time and doubles SLA credits.

---

## Project structure

```
├── generate_data.py        # dataset generator (stdlib only — no pip installs)
├── logistics.db            # SQLite database (shipments, depots, regions)
├── data/
│   ├── shipments.csv       # 31k-row fact table
│   ├── depots.csv          # depot dim with lat/lon (for Tableau maps)
│   └── regions.csv         # delivery-region dim with lat/lon
├── sql/analysis.sql        # 8 analysis queries, documented, one per question
├── run_analysis.py         # runs every query, exports outputs/*.csv
├── outputs/                # Tableau-ready extracts (one CSV per query)
├── dashboard.html          # standalone interactive dashboard (open in browser)
└── recommendations.md      # the written business recommendation
```

## How to run

```
py generate_data.py    # regenerates data/ and logistics.db (seeded — reproducible)
py run_analysis.py     # runs sql/analysis.sql, prints results, writes outputs/
```

Python 3.8+ standard library only.

## The SQL

`sql/analysis.sql` contains 8 queries, each answering one business sub-question:

| Query | Question |
|-------|----------|
| `depot_performance` | Scorecard: on-time %, margin, cost/mile, SLA credits per depot |
| `route_performance` | League table of 73 depot→region lanes (min 100 shipments) |
| `delay_reasons` | Failure-mode mix per depot — separates local vs network problems |
| `service_margin` | Margin by service level × distance band — finds the pricing leak |
| `monthly_trend` | Seasonality: volume, on-time %, credits by month |
| `failure_cost` | What each root cause costs in SLA credits annually |
| `breakdown_audit` | Fleet reliability per depot (breakdowns per 1,000 shipments) |
| `bhm_shift_analysis` | Birmingham deep-dive: lateness by dispatch shift vs network |

Techniques: multi-table joins, window functions (`SUM() OVER (PARTITION BY)`),
conditional aggregation, `HAVING` filters, banding with `CASE`, correlated subquery
for share-of-total.

## Building the Tableau dashboard

A pre-built workbook ships in the repo: **`meridian_freight_analysis.twb`**
(all five sheets plus the "Delivery & Margin Overview" dashboard, wired to the
`outputs/` CSVs).

> **Note if you cloned this repo:** the workbook stores absolute data paths
> (`C:/Users/DELL/logistics-portfolio-project/outputs/…`). On first open,
> Tableau will ask you to locate the files — point it at the `outputs/` folder
> of your clone and every sheet will populate.

To build it from scratch instead, connect Tableau (Public or Desktop) to the
`outputs/` CSVs — they are already aggregated to the right grain, so no LODs
needed for the core views.

**Sheet 1 — Late-delivery heatmap (route_performance.csv)**
Map: drag `region_lat`/`region_lon` to Rows/Columns as continuous dimensions,
`delivery_region` to Detail, `on_time_pct` to Colour (red-green diverging,
reversed, centred at 93), `late_shipments` to Size. Add `depot_code` to a filter
to interactively isolate each depot's footprint.

**Sheet 2 — Depot scorecard (depot_performance.csv)**
Bar chart of `on_time_pct` by `depot_name`, sorted ascending, with a constant
reference line at 93.3 (network average). Second axis or tooltip: `sla_credits_gbp`.

**Sheet 3 — Cost vs SLA breach scatter (route_performance.csv)**
Scatter: `cost_per_mile` (x) vs `on_time_pct` (y), size = `shipments`,
colour = `margin_pct`. The bottom-left cluster is the action list.

**Sheet 4 — Margin leak matrix (service_margin.csv)**
Highlight table: `service_level` rows × `distance_band` columns, colour by
`margin_pct`. The Economy row tells the pricing story at a glance.

**Sheet 5 — Peak-season trend (monthly_trend.csv)**
Dual-axis line: `on_time_pct` and `sla_credits_gbp` by `month`.

Assemble as one dashboard with the depot filter applied across sheets 1, 3.
A working stand-in (`dashboard.html`) ships in the repo — open it in any browser.

## Talking about this project in interviews

- **The story:** "I framed it as an operations review, not a data exercise. The
  network KPI looked healthy at 93.3% — the value was in decomposing the average."
- **Analytical depth:** the Birmingham finding shows a second-level question
  ("*which shift* is late, not *which depot*") — that's what distinguishes analysis
  from reporting.
- **Commercial framing:** every finding is priced (£249k pricing leak, £19.5k
  repairs, 204 excess lates) and paired with a costed recommendation.
- **Honesty:** the dataset is semi-synthetic, modelled on published UK benchmarks
  (RHA cost tables, industry OTD rates). Say so — then point out that the *method*
  (grain design, SQL, root-cause decomposition, costed recommendations) is exactly
  what you'd run on live TMS data.
