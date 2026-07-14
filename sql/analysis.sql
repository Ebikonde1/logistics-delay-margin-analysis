-- ============================================================================
-- Meridian Freight Ltd — Delivery Performance & Margin Analysis
-- Business question: Which routes/depots are driving late deliveries,
--                    and where is margin being lost?
-- Data: shipments (fact), depots (dim), regions (dim) — Jul 2025 to Jun 2026
-- Engine: SQLite
-- ============================================================================

-- ---------------------------------------------------------------------------
-- Q1. DEPOT SCORECARD — on-time %, delay profile, margin, SLA credits
--     Ranks every depot against the network average.
-- ---------------------------------------------------------------------------
-- name: depot_performance
SELECT
    s.origin_depot                                        AS depot_code,
    d.depot_name,
    d.lat, d.lon,
    COUNT(*)                                              AS shipments,
    ROUND(AVG(s.on_time) * 100, 1)                        AS on_time_pct,
    ROUND(AVG(CASE WHEN s.on_time = 0 THEN s.delay_minutes END), 0)
                                                          AS avg_delay_when_late_min,
    ROUND(SUM(s.revenue_gbp), 0)                          AS revenue_gbp,
    ROUND(SUM(s.revenue_gbp - s.cost_total_gbp - s.sla_credit_gbp), 0)
                                                          AS margin_gbp,
    ROUND((SUM(s.revenue_gbp - s.cost_total_gbp - s.sla_credit_gbp)
           / SUM(s.revenue_gbp)) * 100, 1)                AS margin_pct,
    ROUND(SUM(s.sla_credit_gbp), 0)                       AS sla_credits_gbp,
    ROUND(SUM(s.cost_total_gbp) / SUM(s.distance_miles), 2)
                                                          AS cost_per_mile_gbp
FROM shipments s
JOIN depots d ON d.depot_code = s.origin_depot
GROUP BY 1
ORDER BY on_time_pct ASC;

-- ---------------------------------------------------------------------------
-- Q2. ROUTE LEAGUE TABLE — worst lanes by SLA breach volume and margin
--     A "route" is depot -> delivery region. Min 100 shipments to be ranked.
-- ---------------------------------------------------------------------------
-- name: route_performance
SELECT
    s.route_id,
    s.origin_depot                                        AS depot_code,
    s.delivery_region,
    r.lat                                                 AS region_lat,
    r.lon                                                 AS region_lon,
    COUNT(*)                                              AS shipments,
    ROUND(AVG(s.on_time) * 100, 1)                        AS on_time_pct,
    SUM(CASE WHEN s.on_time = 0 THEN 1 ELSE 0 END)        AS late_shipments,
    ROUND(AVG(s.distance_miles), 0)                       AS avg_miles,
    ROUND(SUM(s.revenue_gbp) / SUM(s.distance_miles), 2)  AS revenue_per_mile,
    ROUND(SUM(s.cost_total_gbp) / SUM(s.distance_miles), 2)
                                                          AS cost_per_mile,
    ROUND(SUM(s.revenue_gbp - s.cost_total_gbp - s.sla_credit_gbp), 0)
                                                          AS margin_gbp,
    ROUND((SUM(s.revenue_gbp - s.cost_total_gbp - s.sla_credit_gbp)
           / SUM(s.revenue_gbp)) * 100, 1)                AS margin_pct,
    ROUND(SUM(s.sla_credit_gbp), 0)                       AS sla_credits_gbp
FROM shipments s
JOIN regions r ON r.region = s.delivery_region
GROUP BY 1
HAVING COUNT(*) >= 100
ORDER BY on_time_pct ASC;

-- ---------------------------------------------------------------------------
-- Q3. WHY ARE WE LATE? — delay reason mix, split by depot
--     Separates a network-wide problem (traffic) from a local one (loading).
-- ---------------------------------------------------------------------------
-- name: delay_reasons
SELECT
    s.origin_depot                                        AS depot_code,
    s.delay_reason,
    COUNT(*)                                              AS late_shipments,
    ROUND(AVG(s.delay_minutes), 0)                        AS avg_delay_min,
    ROUND(SUM(s.sla_credit_gbp), 0)                       AS sla_credits_gbp,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY s.origin_depot), 1)
                                                          AS pct_of_depot_lates
FROM shipments s
WHERE s.on_time = 0
GROUP BY 1, 2
ORDER BY 1, 3 DESC;

-- ---------------------------------------------------------------------------
-- Q4. MARGIN LEAK — profitability by service level and distance band
--     Exposes the Economy long-haul pricing problem.
-- ---------------------------------------------------------------------------
-- name: service_margin
SELECT
    s.service_level,
    CASE WHEN s.distance_miles < 100  THEN 'a. <100 mi'
         WHEN s.distance_miles < 200  THEN 'b. 100-200 mi'
         WHEN s.distance_miles < 300  THEN 'c. 200-300 mi'
         ELSE                              'd. 300+ mi' END
                                                          AS distance_band,
    COUNT(*)                                              AS shipments,
    ROUND(SUM(s.revenue_gbp) / SUM(s.distance_miles), 2)  AS revenue_per_mile,
    ROUND(SUM(s.cost_total_gbp) / SUM(s.distance_miles), 2)
                                                          AS cost_per_mile,
    ROUND(SUM(s.revenue_gbp - s.cost_total_gbp - s.sla_credit_gbp), 0)
                                                          AS margin_gbp,
    ROUND((SUM(s.revenue_gbp - s.cost_total_gbp - s.sla_credit_gbp)
           / SUM(s.revenue_gbp)) * 100, 1)                AS margin_pct
FROM shipments s
GROUP BY 1, 2
ORDER BY 1, 2;

-- ---------------------------------------------------------------------------
-- Q5. MONTHLY TREND — volume, on-time %, margin by month (peak-season view)
-- ---------------------------------------------------------------------------
-- name: monthly_trend
SELECT
    strftime('%Y-%m', s.dispatch_date)                    AS month,
    COUNT(*)                                              AS shipments,
    ROUND(AVG(s.on_time) * 100, 1)                        AS on_time_pct,
    ROUND(SUM(s.revenue_gbp), 0)                          AS revenue_gbp,
    ROUND(SUM(s.revenue_gbp - s.cost_total_gbp - s.sla_credit_gbp), 0)
                                                          AS margin_gbp,
    ROUND(SUM(s.sla_credit_gbp), 0)                       AS sla_credits_gbp
FROM shipments s
GROUP BY 1
ORDER BY 1;

-- ---------------------------------------------------------------------------
-- Q6. COST OF FAILURE — what each root cause costs the business annually
--     SLA credits + excess vehicle cost (breakdown repairs) by reason.
-- ---------------------------------------------------------------------------
-- name: failure_cost
SELECT
    s.delay_reason,
    COUNT(*)                                              AS incidents,
    ROUND(SUM(s.sla_credit_gbp), 0)                       AS sla_credits_gbp,
    ROUND(AVG(s.delay_minutes), 0)                        AS avg_delay_min,
    ROUND(SUM(s.sla_credit_gbp) * 100.0 /
          (SELECT SUM(sla_credit_gbp) FROM shipments), 1) AS pct_of_all_credits
FROM shipments s
WHERE s.on_time = 0
GROUP BY 1
ORDER BY sla_credits_gbp DESC;

-- ---------------------------------------------------------------------------
-- Q7. BREAKDOWN AUDIT — fleet reliability by depot
--     Newcastle's ageing fleet shows up as an outlier breakdown rate.
-- ---------------------------------------------------------------------------
-- name: breakdown_audit
SELECT
    s.origin_depot                                        AS depot_code,
    COUNT(*)                                              AS shipments,
    SUM(CASE WHEN s.delay_reason = 'Vehicle Breakdown' THEN 1 ELSE 0 END)
                                                          AS breakdowns,
    ROUND(1000.0 * SUM(CASE WHEN s.delay_reason = 'Vehicle Breakdown'
                            THEN 1 ELSE 0 END) / COUNT(*), 1)
                                                          AS breakdowns_per_1000,
    ROUND(SUM(CASE WHEN s.delay_reason = 'Vehicle Breakdown'
                   THEN s.sla_credit_gbp ELSE 0 END), 0)  AS breakdown_sla_gbp
FROM shipments s
GROUP BY 1
ORDER BY breakdowns_per_1000 DESC;

-- ---------------------------------------------------------------------------
-- Q8. BIRMINGHAM DEEP-DIVE — is the loading problem shift-related?
--     Dispatch hour vs lateness for BHM vs rest of network.
-- ---------------------------------------------------------------------------
-- name: bhm_shift_analysis
SELECT
    CASE WHEN CAST(strftime('%H', s.dispatch_ts) AS INT) < 12 THEN 'a. Morning (05-12)'
         WHEN CAST(strftime('%H', s.dispatch_ts) AS INT) < 17 THEN 'b. Afternoon (12-17)'
         ELSE                                                      'c. Evening (17-21)' END
                                                          AS dispatch_shift,
    CASE WHEN s.origin_depot = 'BHM' THEN 'Birmingham' ELSE 'Rest of network' END
                                                          AS depot_group,
    COUNT(*)                                              AS shipments,
    ROUND(AVG(s.on_time) * 100, 1)                        AS on_time_pct
FROM shipments s
GROUP BY 1, 2
ORDER BY 1, 2;
