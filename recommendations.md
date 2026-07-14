# Delivery Performance & Margin Review — FY Jul 2025 – Jun 2026

**Prepared for:** Operations Director, Meridian Freight Ltd
**Analyst:** [Your name]
**Data:** 31,027 shipments, 8 depots, 11 delivery regions, 12 months (SQL analysis of shipment-level data)

---

## Executive summary

The network delivered **93.3% on-time** for the year — inside the 92–95% industry
band, but the average hides three concentrated problems. Fixing them is worth an
estimated **£290–340k a year**, roughly 12% of current network margin:

| # | Finding | Annual impact | Fix cost |
|---|---------|--------------|----------|
| 1 | Economy service is loss-making, catastrophically so beyond 200 miles | **−£249k margin** | Low (pricing change) |
| 2 | Birmingham's afternoon/evening shifts drive chronic loading delays | ~204 excess lates, £6k direct SLA credits + churn risk | Medium (staffing) |
| 3 | Newcastle's ageing fleet breaks down at ~4× the network rate | **~£19.5k excess repairs** + £1.8k credits | Medium (fleet capex) |

---

## Finding 1 — Economy is a loss-making product (−£249k/year)

Economy shipments generated **£1.33m revenue at a −18.7% margin (−£249k)**.
The loss deepens sharply with distance:

| Distance band | Revenue/mile | Cost/mile | Margin % |
|---------------|-------------|-----------|----------|
| < 100 mi | £2.16 | £2.29 | −6.3% |
| 100–200 mi | £1.82 | £2.02 | −11.8% |
| 200–300 mi | £1.44 | £1.96 | **−36.2%** |
| 300+ mi | £1.40 | £1.93 | **−38.2%** |

Root cause: Economy is priced at a flat ~£1.32/mile beyond 200 miles, while the
network's true operating cost is ~£1.93–1.96/mile at that distance. The 1,130
long-haul Economy shipments (avg 278 mi) turned £448k of revenue into a
**£165k loss** on their own. By contrast, Next-Day earns ~40% margin at every distance.

**Recommendation:**
- Reprice Economy ≥200 mi to a floor of £2.20/mile (cost + ~13%). At current volume
  this converts the −£165k into roughly +£35k — a **~£200k swing** even assuming
  20–30% volume attrition.
- Alternatively, consolidate long-haul Economy onto trunk linehaul (fill spare artic
  capacity on scheduled runs) or broker it to a partner network.
- Short-haul Economy (−6%) is a smaller problem; test a £5 base-charge increase before
  structural change.

## Finding 2 — Birmingham's problem is a shift problem, not a depot problem

Birmingham is the network's worst depot (**88.2% on-time vs 95.4%** best-in-network,
Manchester), and **71% of its late deliveries are loading delays** — a failure mode
that is 2–3× rarer everywhere else. The dispatch-hour split isolates the cause:

| Dispatch window | Birmingham on-time | Rest of network |
|-----------------|-------------------|-----------------|
| Morning (05–12) | 91.7% | 94.6% |
| Afternoon (12–17) | 87.9% | 94.4% |
| Evening (17–21) | **79.9%** | 94.6% |

The rest of the network is flat across the day; Birmingham degrades hour by hour.
This is the signature of an under-resourced back shift (loading crews, not drivers —
the delays occur before departure). Closing the PM gap to Birmingham's own morning
rate would avoid **~204 late shipments a year** (~£6.2k in direct SLA credits at
£30.30 average, plus the retention risk on the affected lanes — Birmingham already
pays £20.5k of the network's £83.2k total credits, the most of any depot).

**Recommendation:** Add loading crew to Birmingham's 15:00–21:00 window (est. 2 FTE,
~£56k/yr fully loaded) and set a depot-level trigger: escalate if any rolling
4-week PM on-time drops below 90%. Payback comes mainly through protecting the
£1.48m revenue base at the depot rather than the credits alone.

## Finding 3 — Newcastle's fleet is a reliability outlier

Newcastle records **22.8 breakdowns per 1,000 shipments vs a network median of ~5.9**
(next worst: Leeds at 8.8). Each breakdown adds ~£416 of unplanned repair cost
(£458 avg vehicle cost vs £42 on a normal job) and averages **227 minutes of delay** —
the longest of any failure mode. Annual cost: **~£19.5k excess repairs + £1.8k SLA
credits**, and breakdowns are the least recoverable delay type for the customer.

**Recommendation:** Prioritise Newcastle in the next fleet-replacement cycle
(2–3 vehicles). At ~£21k/year of directly attributable cost plus the residual-value
and downtime case, replacement likely clears the capex hurdle a year early.

## Finding 4 (watch item) — December peak degrades the whole network

Peak volume (+~15% Nov, +35% early Dec) pulled network on-time down to **89.8%**
in December and doubled monthly SLA credits to £11.9k. This is a capacity-planning
issue, not a depot issue — every depot dipped. Flag for the FY27 peak plan:
pre-book agency loading staff from mid-November, especially at Birmingham where
the structural PM gap compounds the seasonal one.

---

## Method note

Shipment-level data was aggregated in SQL (SQLite; queries in `sql/analysis.sql`)
to depot, route, service-level, and month grains. On-time is measured against the
promised delivery timestamp with a 45-minute grace window. Margin is revenue minus
direct operating cost (driver, fuel, vehicle, handling) minus SLA credits paid;
it excludes depot overhead allocation. Route rankings require ≥100 shipments.
