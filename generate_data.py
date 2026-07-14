"""
UK Road Freight — semi-synthetic shipment dataset generator.

Produces 12 months (Jul 2025 - Jun 2026) of parcel/pallet freight shipments
for a fictional mid-size UK 3PL ("Meridian Freight Ltd", 8 depots).

Grounded in real UK logistics benchmarks:
  - Industry on-time delivery: ~92-95% (network average here lands ~93%)
  - RHA/DfT haulage operating cost: ~GBP 1.70-2.10 per mile for rigid/artic mix
  - Cost split: driver ~38%, fuel ~32%, vehicle/maintenance ~18%, overhead ~12%
  - SLA credits: 15% (Next-Day), 10% (48-Hour), 5% (Economy) of freight charge

Deliberately embedded operational patterns (the "business problems"):
  1. Birmingham depot: evening-shift loading delays -> chronic lateness
  2. Deliveries into Greater London: traffic congestion, worst for Next-Day
  3. Economy long-haul (>200 mi) priced at GBP 1.32/mile vs ~GBP 1.85/mile cost
     -> negative margin, concentrated on Glasgow/Newcastle economy lanes
  4. Newcastle depot: ageing fleet -> ~4x breakdown rate + repair costs
  5. December peak: +35% volume, network-wide on-time dip
  6. Winter weather: Dec-Feb delays on Scotland / North East lanes
"""

import csv
import math
import random
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

random.seed(42)

ROOT = Path(__file__).parent
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)

# ---------------------------------------------------------------- dimensions

DEPOTS = {
    # code: (name, city, lat, lon, daily_volume_weight)
    "LDN": ("London Dagenham", "London", 51.540, 0.130, 22),
    "BHM": ("Birmingham Hub", "Birmingham", 52.480, -1.900, 18),
    "MAN": ("Manchester Trafford", "Manchester", 53.480, -2.240, 15),
    "LDS": ("Leeds Stourton", "Leeds", 53.780, -1.520, 11),
    "BRS": ("Bristol Avonmouth", "Bristol", 51.500, -2.700, 10),
    "GLA": ("Glasgow Eurocentral", "Glasgow", 55.860, -4.250, 9),
    "NCL": ("Newcastle Team Valley", "Newcastle", 54.950, -1.670, 7),
    "SOU": ("Southampton Nursling", "Southampton", 50.930, -1.470, 8),
}

REGIONS = {
    # name: (lat, lon)
    "Greater London": (51.510, -0.130),
    "South East": (51.270, -0.790),
    "South West": (50.780, -3.550),
    "East of England": (52.240, 0.410),
    "West Midlands": (52.480, -2.000),
    "East Midlands": (52.830, -1.330),
    "North West": (53.620, -2.600),
    "Yorkshire & Humber": (53.930, -1.300),
    "North East": (54.900, -1.700),
    "Scotland": (56.200, -3.900),
    "Wales": (52.300, -3.600),
}

SERVICE_LEVELS = {
    # name: (share, promised_days, rate_per_mile, base_charge, sla_credit_pct)
    "Next-Day": (0.38, 1, 3.10, 48.0, 0.15),
    "48-Hour": (0.41, 2, 2.32, 36.0, 0.10),
    "Economy": (0.21, 4, 1.62, 26.0, 0.05),
}

SEGMENTS = [("E-commerce", 0.34), ("Retail", 0.28), ("Manufacturing", 0.22),
            ("Construction", 0.09), ("Healthcare", 0.07)]

VEHICLES = [("7.5t Rigid", 0.30), ("18t Rigid", 0.42), ("Artic 44t", 0.28)]


def haversine_miles(a, b):
    lat1, lon1, lat2, lon2 = map(math.radians, [a[0], a[1], b[0], b[1]])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 3959 * 2 * math.asin(math.sqrt(h))


# Road miles ~ 1.25x straight-line; each depot mostly serves nearby regions.
ROUTES = {}  # (depot, region) -> road_miles
for dcode, (dname, city, dlat, dlon, w) in DEPOTS.items():
    for rname, (rlat, rlon) in REGIONS.items():
        ROUTES[(dcode, rname)] = round(haversine_miles((dlat, dlon), (rlat, rlon)) * 1.25 + 12, 1)


def region_weights(dcode):
    """Closer regions get far more volume; every depot still trunks nationally."""
    weights = {}
    for rname in REGIONS:
        miles = ROUTES[(dcode, rname)]
        weights[rname] = 1.0 / (miles + 40) ** 1.5
    total = sum(weights.values())
    return {r: w / total for r, w in weights.items()}


REGION_W = {d: region_weights(d) for d in DEPOTS}


def pick(weighted):
    r, acc = random.random(), 0.0
    for item, w in weighted:
        acc += w
        if r <= acc:
            return item
    return weighted[-1][0]


# ---------------------------------------------------------------- generation

START, END = date(2025, 7, 1), date(2026, 6, 30)

def month_volume_factor(d):
    f = 1.0
    if d.month == 12:
        f = 1.35 if d.day <= 21 else 0.55          # peak then Christmas shutdown
    elif d.month == 11:
        f = 1.18                                    # Black Friday build-up
    elif d.month in (1, 8):
        f = 0.90
    if d.weekday() == 5:
        f *= 0.35                                   # Saturday
    elif d.weekday() == 6:
        f = 0.0                                     # no Sunday dispatch
    return f


rows = []
sid = 100000
day = START
while day <= END:
    vf = month_volume_factor(day)
    if vf > 0:
        for dcode, (dname, city, dlat, dlon, base_w) in DEPOTS.items():
            n = max(0, int(random.gauss(base_w * 1.15 * vf, base_w * 0.18)))
            regw = list(REGION_W[dcode].items())
            for _ in range(n):
                sid += 1
                region = pick(regw)
                miles = ROUTES[(dcode, region)] * random.uniform(0.88, 1.15)
                service = pick([(k, v[0]) for k, v in SERVICE_LEVELS.items()])
                _, promised_days, rate, base_charge, credit_pct = SERVICE_LEVELS[service]
                segment = pick(SEGMENTS)
                vehicle = pick(VEHICLES)
                pallets = max(1, min(26, int(random.lognormvariate(1.1, 0.8))))

                # ---- revenue (embedded problem 3: economy long-haul flat cap)
                if service == "Economy" and miles > 200:
                    revenue = base_charge + miles * 1.32   # under-priced flat rate
                else:
                    revenue = base_charge + miles * rate
                revenue *= (1 + 0.03 * (pallets - 3) * 0.1)
                revenue *= random.uniform(0.95, 1.06)

                # ---- cost  (~GBP 1.85/mile network average)
                cpm = random.gauss(1.85, 0.12)
                if vehicle == "7.5t Rigid":
                    cpm *= 1.08
                elif vehicle == "Artic 44t":
                    cpm *= 0.94
                if day.month in (12, 1, 2):
                    cpm *= 1.04                             # winter fuel
                cost_total = miles * cpm + 18               # fixed handling
                cost_driver = cost_total * random.gauss(0.38, 0.02)
                cost_fuel = cost_total * random.gauss(0.32, 0.02)
                cost_vehicle = cost_total * random.gauss(0.18, 0.015)

                dispatch = datetime.combine(day, datetime.min.time()) + \
                    timedelta(hours=random.uniform(5, 20))

                # ---- delay model
                reason, delay_min = "None", 0
                p_late = {"Next-Day": 0.055, "48-Hour": 0.038, "Economy": 0.030}[service]
                if dcode == "BHM":                          # problem 1: loading,
                    p_late += 0.165 if dispatch.hour >= 15 else 0.035   # PM shift
                if region == "Greater London":
                    p_late += 0.055 if service == "Next-Day" else 0.030   # problem 2
                if day.month == 12 and day.day <= 21:
                    p_late += 0.045                         # problem 5: peak
                winter_north = (day.month in (12, 1, 2)
                                and region in ("Scotland", "North East"))
                if winter_north:
                    p_late += 0.040                         # problem 6: weather

                p_breakdown = 0.024 if dcode == "NCL" else 0.006   # problem 4

                if random.random() < p_breakdown:
                    reason = "Vehicle Breakdown"
                    delay_min = int(random.lognormvariate(5.3, 0.5))       # ~200 min
                    cost_vehicle += random.uniform(120, 650)               # repair
                    cost_total = cost_driver + cost_fuel + cost_vehicle + \
                        (cost_total - cost_driver - cost_fuel - cost_vehicle)
                elif random.random() < p_late:
                    if dcode == "BHM" and random.random() < 0.62:
                        reason = "Loading Delay"
                        delay_min = int(random.lognormvariate(4.9, 0.5))   # ~135 min
                    elif region == "Greater London" and random.random() < 0.60:
                        reason = "Traffic Congestion"
                        delay_min = int(random.lognormvariate(4.6, 0.5))   # ~100 min
                    elif winter_north and random.random() < 0.55:
                        reason = "Adverse Weather"
                        delay_min = int(random.lognormvariate(5.1, 0.6))
                    else:
                        reason = random.choice(
                            ["Traffic Congestion", "Loading Delay",
                             "Address Issue", "Customer Unavailable"])
                        delay_min = int(random.lognormvariate(4.5, 0.6))

                on_time = 1 if delay_min <= 45 else 0       # 45-min grace window
                sla_credit = round(revenue * credit_pct, 2) if not on_time else 0.0

                planned = dispatch + timedelta(days=promised_days,
                                               hours=random.uniform(-2, 6))
                actual = planned + timedelta(minutes=delay_min) - \
                    timedelta(minutes=random.uniform(0, 120) if delay_min == 0 else 0)

                rows.append({
                    "shipment_id": f"MF{sid}",
                    "dispatch_ts": dispatch.strftime("%Y-%m-%d %H:%M"),
                    "dispatch_date": day.isoformat(),
                    "origin_depot": dcode,
                    "delivery_region": region,
                    "route_id": f"{dcode}-{region.replace(' ', '')[:8].upper()}",
                    "service_level": service,
                    "customer_segment": segment,
                    "vehicle_type": vehicle,
                    "pallets": pallets,
                    "distance_miles": round(miles, 1),
                    "planned_delivery_ts": planned.strftime("%Y-%m-%d %H:%M"),
                    "actual_delivery_ts": actual.strftime("%Y-%m-%d %H:%M"),
                    "delay_minutes": delay_min,
                    "on_time": on_time,
                    "delay_reason": reason,
                    "revenue_gbp": round(revenue, 2),
                    "cost_driver_gbp": round(cost_driver, 2),
                    "cost_fuel_gbp": round(cost_fuel, 2),
                    "cost_vehicle_gbp": round(cost_vehicle, 2),
                    "cost_total_gbp": round(cost_driver + cost_fuel + cost_vehicle +
                                            max(cost_total - cost_driver - cost_fuel -
                                                cost_vehicle, 0), 2),
                    "sla_credit_gbp": sla_credit,
                })
    day += timedelta(days=1)

# ---------------------------------------------------------------- write CSVs

with open(DATA / "shipments.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=rows[0].keys())
    w.writeheader()
    w.writerows(rows)

with open(DATA / "depots.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["depot_code", "depot_name", "city", "lat", "lon"])
    for c, (n, city, lat, lon, _) in DEPOTS.items():
        w.writerow([c, n, city, lat, lon])

with open(DATA / "regions.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["region", "lat", "lon"])
    for r, (lat, lon) in REGIONS.items():
        w.writerow([r, lat, lon])

# ---------------------------------------------------------------- load SQLite

db = ROOT / "logistics.db"
db.unlink(missing_ok=True)
con = sqlite3.connect(db)
con.execute("""CREATE TABLE shipments (
    shipment_id TEXT PRIMARY KEY, dispatch_ts TEXT, dispatch_date TEXT,
    origin_depot TEXT, delivery_region TEXT, route_id TEXT,
    service_level TEXT, customer_segment TEXT, vehicle_type TEXT,
    pallets INTEGER, distance_miles REAL,
    planned_delivery_ts TEXT, actual_delivery_ts TEXT,
    delay_minutes INTEGER, on_time INTEGER, delay_reason TEXT,
    revenue_gbp REAL, cost_driver_gbp REAL, cost_fuel_gbp REAL,
    cost_vehicle_gbp REAL, cost_total_gbp REAL, sla_credit_gbp REAL)""")
con.execute("""CREATE TABLE depots (depot_code TEXT PRIMARY KEY,
    depot_name TEXT, city TEXT, lat REAL, lon REAL)""")
con.execute("""CREATE TABLE regions (region TEXT PRIMARY KEY, lat REAL, lon REAL)""")

con.executemany(
    f"INSERT INTO shipments VALUES ({','.join('?' * 22)})",
    [tuple(r.values()) for r in rows])
con.executemany("INSERT INTO depots VALUES (?,?,?,?,?)",
                [(c, n, city, lat, lon) for c, (n, city, lat, lon, _) in DEPOTS.items()])
con.executemany("INSERT INTO regions VALUES (?,?,?)",
                [(r, lat, lon) for r, (lat, lon) in REGIONS.items()])
con.commit()

# ---------------------------------------------------------------- sanity print

q = lambda s: con.execute(s).fetchall()
n, = q("SELECT COUNT(*) FROM shipments")[0]
otd, = q("SELECT ROUND(AVG(on_time)*100,1) FROM shipments")[0]
rev, cost, credits = q("""SELECT ROUND(SUM(revenue_gbp)/1e6,2),
    ROUND(SUM(cost_total_gbp)/1e6,2), ROUND(SUM(sla_credit_gbp)/1e3,1)
    FROM shipments""")[0]
print(f"shipments: {n:,}")
print(f"network on-time: {otd}%  (industry benchmark 92-95%)")
print(f"revenue: GBP {rev}m | cost: GBP {cost}m | SLA credits paid: GBP {credits}k")
print("\non-time % by depot:")
for row in q("""SELECT origin_depot, ROUND(AVG(on_time)*100,1), COUNT(*)
                FROM shipments GROUP BY 1 ORDER BY 2"""):
    print(f"  {row[0]}: {row[1]}%  ({row[2]:,} shipments)")
con.close()
