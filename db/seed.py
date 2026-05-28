"""Idempotent seed for DealerDesk 98 - only inserts if tables are empty."""
import random
from datetime import date, timedelta, datetime
from db.connection import get_connection

FIRST_NAMES = [
    "James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda",
    "William", "Barbara", "David", "Elizabeth", "Richard", "Susan", "Joseph", "Jessica",
    "Thomas", "Sarah", "Charles", "Karen", "Daniel", "Nancy", "Matthew", "Betty",
    "Anthony", "Sandra", "Mark", "Ashley", "Steven", "Kimberly",
]
LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas",
    "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson", "White",
    "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker",
]
CITIES = [
    ("Springfield", "IL"), ("Riverside", "CA"), ("Fairview", "TX"), ("Greenville", "SC"),
    ("Madison", "WI"), ("Georgetown", "KY"), ("Franklin", "TN"), ("Salem", "OR"),
    ("Arlington", "VA"), ("Auburn", "AL"),
]
SALESPEOPLE = ["Jordan Miller", "Alex Chen", "Sam Rivera", "Pat Johnson", "Chris Lee"]
ADVISORS = ["Robin Davis", "Casey Brooks", "Morgan Hayes", "Taylor Quinn"]
CUSTOMER_TYPES = ["Retail", "Retail", "Retail", "Retail", "Fleet", "Internal"]

MAKES_MODELS = {
    "Ford": ["F-150", "Escape", "Explorer", "Mustang", "Bronco"],
    "Toyota": ["Camry", "Corolla", "RAV4", "Tacoma", "Highlander"],
    "Honda": ["Civic", "Accord", "CR-V", "Pilot", "Odyssey"],
    "Chevrolet": ["Silverado 1500", "Equinox", "Malibu", "Tahoe", "Traverse"],
    "Nissan": ["Altima", "Rogue", "Sentra", "Frontier", "Pathfinder"],
    "Jeep": ["Wrangler", "Grand Cherokee", "Cherokee", "Compass"],
    "Subaru": ["Outback", "Forester", "Crosstrek", "Impreza"],
    "Ram": ["1500", "2500"],
}
TRIMS = ["Base", "S", "SE", "SEL", "LE", "XLE", "Limited", "Sport", "Touring", "Lariat", "LT", "LTZ", "Platinum"]
COLORS = ["White", "Black", "Silver", "Gray", "Red", "Blue", "Deep Blue", "Pearl White", "Gunmetal", "Forest Green"]

RO_TYPES = ["Maintenance", "Repair", "Warranty", "Recall", "Diagnostic", "Multi-Point Inspection"]
RO_STATUSES = ["Open", "In Progress", "Awaiting Parts", "Completed", "Closed", "Invoiced"]
CONCERNS = [
    "Customer states vehicle pulls to the right when braking",
    "Grinding noise from front end when stopping",
    "Check engine light is illuminated",
    "A/C not blowing cold air",
    "Requesting oil change and tire rotation",
    "Vehicle will not start intermittently",
    "Squealing noise on cold startup",
    "Vibration felt in steering wheel at highway speed",
    "TPMS / low tire pressure warning light on",
    "Due for scheduled 30,000 mile maintenance",
    "Battery keeps dying overnight",
    "Transmission slips when shifting from 2nd to 3rd",
]
CAUSES = [
    "Front brake pads worn below minimum specification",
    "Low refrigerant level due to evaporator core leak",
    "Battery failed load test; 320 CCA of rated 600",
    "Worn serpentine belt with visible cracking",
    "Front tires cupped, alignment out of specification",
    "Faulty downstream O2 sensor, code P0141 stored",
    "Cabin air filter heavily restricted",
    "Loose exhaust heat shield contacting underbody",
    "Brake rotors warped beyond runout tolerance",
    "Spark plugs worn, electrode gap out of spec",
]
CORRECTIONS = [
    "Replaced front brake pads and resurfaced rotors; road tested OK",
    "Evacuated and recharged A/C system; replaced evaporator core",
    "Replaced battery; tested charging system, within spec",
    "Replaced serpentine belt and tensioner assembly",
    "Performed 4-wheel alignment and rotated tires",
    "Replaced O2 sensor and cleared diagnostic codes",
    "Performed full synthetic oil change and multi-point inspection",
    "Replaced cabin and engine air filters",
    "Replaced spark plugs and ignition coils as needed",
    "Secured exhaust heat shield; road noise resolved",
]
RECOMMENDATIONS = [
    "Recommend rear brake service within 6 months",
    "Tires at 5/32 - recommend replacement soon",
    "Recommend fuel induction service at next visit",
    "No additional services recommended at this time",
    "Recommend wiper blade replacement",
    "Recommend coolant flush - due by mileage",
]

DEAL_TYPES = ["Finance", "Lease", "Cash"]
DEAL_STATUSES = ["Quote", "Pending", "Approved", "Sold", "Delivered", "Dead"]
SERVICE_REASONS = [
    "Oil Change", "Tire Rotation", "Brake Inspection", "Check Engine Light",
    "30K Mile Service", "60K Mile Service", "State Inspection", "Recall Service",
    "Battery Replacement", "A/C Service", "Alignment", "Multi-Point Inspection",
]
SALES_REASONS = [
    "Test Drive", "Trade Appraisal", "Finance Application", "Vehicle Delivery", "Sales Follow-Up",
]


def _rand_vin():
    return "".join(random.choices("ABCDEFGHJKLMNPRSTUVWXYZ0123456789", k=17))


def _rand_phone():
    return f"({random.randint(200,999)}) {random.randint(200,999)}-{random.randint(1000,9999)}"


def _rand_date(days_back_min, days_back_max):
    d = date.today() - timedelta(days=random.randint(days_back_min, days_back_max))
    return d.isoformat()


def seed():
    conn = get_connection()
    cur = conn.cursor()

    # Users
    if cur.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO users (username, password, role) VALUES (?,?,?)",
            [
                ("admin", "admin", "admin"),
                ("jmiller", "password", "salesperson"),
                ("rdavis", "password", "advisor"),
            ],
        )

    # Customers
    if cur.execute("SELECT COUNT(*) FROM customers").fetchone()[0] == 0:
        rows = []
        for i in range(30):
            fn, ln = FIRST_NAMES[i], LAST_NAMES[i]
            city, st = random.choice(CITIES)
            rows.append((
                f"C{10000 + i}", fn, ln, _rand_phone(),
                f"{fn.lower()}.{ln.lower()}@example.com",
                f"{random.randint(100,9999)} {random.choice(['Main','Oak','Elm','Cedar','Maple','Park','Lake','Hill'])} St",
                city, st, f"{random.randint(10000,99999)}",
                random.choice(CUSTOMER_TYPES), random.choice(SALESPEOPLE),
            ))
        cur.executemany(
            "INSERT INTO customers (customer_no,first_name,last_name,phone,email,address,city,state,zip,customer_type,salesperson)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?)", rows)

    # Vehicles - inventory (in stock) + customer-owned (for service)
    if cur.execute("SELECT COUNT(*) FROM vehicles").fetchone()[0] == 0:
        cust_ids = [r[0] for r in cur.execute("SELECT id FROM customers").fetchall()]
        veh = []
        for i in range(32):
            mk = random.choice(list(MAKES_MODELS.keys()))
            md = random.choice(MAKES_MODELS[mk])
            if random.random() < 0.4:  # used
                yr, mi, price = random.randint(2018, 2024), random.randint(18000, 90000), random.randint(14000, 38000)
            else:  # new
                yr, mi, price = random.randint(2025, 2026), random.randint(2, 60), random.randint(26000, 68000)
            veh.append((f"STK{1000 + i}", _rand_vin(), yr, mk, md,
                        random.choice(TRIMS), random.choice(COLORS),
                        mi, float(price), "In Stock", None))
        for j, cid in enumerate(cust_ids):
            mk = random.choice(list(MAKES_MODELS.keys()))
            md = random.choice(MAKES_MODELS[mk])
            veh.append((f"OWN{2000 + j}", _rand_vin(), random.randint(2012, 2023), mk, md,
                        random.choice(TRIMS), random.choice(COLORS),
                        random.randint(30000, 150000), 0.0, "Customer-Owned", cid))
        cur.executemany(
            "INSERT INTO vehicles (stock_no,vin,year,make,model,trim,color,mileage,price,status,customer_id)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?)", veh)

    # Repair Orders (against customer-owned vehicles)
    if cur.execute("SELECT COUNT(*) FROM repair_orders").fetchone()[0] == 0:
        owned = cur.execute(
            "SELECT id, customer_id, mileage FROM vehicles WHERE status='Customer-Owned'").fetchall()
        ros = []
        ctr = 0
        for v in owned:
            for _ in range(random.randint(1, 4)):
                ctr += 1
                idx = random.randint(0, len(CONCERNS) - 1)
                ros.append((
                    f"RO{50000 + ctr}", v["customer_id"], v["id"],
                    _rand_date(1, 720), random.choice(RO_TYPES), random.choice(ADVISORS),
                    max(0, (v["mileage"] or 0) - random.randint(0, 20000)),
                    random.choice(["Closed", "Closed", "Closed", "Invoiced", "Open"]),
                    CONCERNS[idx], random.choice(CAUSES), random.choice(CORRECTIONS),
                    random.choice(RECOMMENDATIONS), round(random.uniform(45, 1850), 2),
                ))
        cur.executemany(
            "INSERT INTO repair_orders (ro_number,customer_id,vehicle_id,date,type,advisor,mileage,status,concern,cause,correction,recommendations,total)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", ros)

    # Deals
    if cur.execute("SELECT COUNT(*) FROM deals").fetchone()[0] == 0:
        cust_ids = [r[0] for r in cur.execute("SELECT id FROM customers").fetchall()]
        instock = [dict(r) for r in cur.execute(
            "SELECT id, price FROM vehicles WHERE status='In Stock'").fetchall()]
        random.shuffle(instock)
        deals = []
        for i in range(20):
            cid = random.choice(cust_ids)
            status = random.choice(DEAL_STATUSES)
            veh_id, price = None, random.randint(15000, 60000)
            if instock and status in ("Sold", "Delivered"):
                v = instock.pop()
                veh_id, price = v["id"], int(v["price"]) or price
                cur.execute("UPDATE vehicles SET status='Sold', customer_id=? WHERE id=?", (cid, veh_id))
            elif instock:
                v = instock[-1]
                veh_id, price = v["id"], int(v["price"]) or price
            deals.append((
                f"D{8000 + i}", cid, veh_id, _rand_date(0, 120),
                random.choice(SALESPEOPLE), random.choice(DEAL_TYPES), float(price),
                random.choice(["", "2016 Honda Civic", "2014 Ford Focus", "2018 Toyota Camry", "None"]),
                status,
                random.choice(["", "Customer wants weekend delivery.", "Pending bank approval.", "Repeat customer."]),
            ))
        cur.executemany(
            "INSERT INTO deals (deal_number,customer_id,vehicle_id,date,salesperson,deal_type,sale_price,trade_in,status,notes)"
            " VALUES (?,?,?,?,?,?,?,?,?,?)", deals)

    # Appointments (Service + Sales)
    if cur.execute("SELECT COUNT(*) FROM appointments").fetchone()[0] == 0:
        cust_ids = [r[0] for r in cur.execute("SELECT id FROM customers").fetchall()]
        appts = []
        today = date.today()
        for _ in range(40):
            offset = random.randint(-7, 30)
            dt = datetime.combine(today + timedelta(days=offset),
                                  datetime.min.time().replace(hour=random.randint(8, 17),
                                                              minute=random.choice([0, 15, 30, 45])))
            dept = random.choice(["Service", "Service", "Service", "Sales"])
            if dept == "Service":
                reason, who = random.choice(SERVICE_REASONS), random.choice(ADVISORS)
            else:
                reason, who = random.choice(SALES_REASONS), random.choice(SALESPEOPLE)
            status = "Scheduled" if offset >= 0 else random.choice(["Completed", "No-Show", "Cancelled"])
            notes = "Customer requested morning slot." if random.random() < 0.3 else ""
            appts.append((random.choice(cust_ids), dt.isoformat(), who, reason, dept, status, notes))
        cur.executemany(
            "INSERT INTO appointments (customer_id,datetime,advisor,reason,dept,status,notes)"
            " VALUES (?,?,?,?,?,?,?)", appts)

    # Chaos defaults (keys kept identical to engine SCENARIO_MAP for reuse)
    if cur.execute("SELECT COUNT(*) FROM chaos_settings").fetchone()[0] == 0:
        defaults = [
            ("master_enabled", "0"),
            ("random_dialog", "1"),
            ("fake_freeze", "1"),
            ("session_timeout", "1"),
            ("unexpected_save", "1"),
            ("critical_error", "1"),
            ("field_corruption", "0"),
            ("save_failure", "0"),
            ("wrong_patient", "0"),
            ("bsod_overlay", "0"),
            ("slow_progress", "0"),
            ("frequency", "occasional"),
            ("trigger_mode", "event"),
            ("interval_seconds", "30"),
        ]
        cur.executemany("INSERT INTO chaos_settings (key,value) VALUES (?,?)", defaults)

    conn.commit()
    conn.close()


if __name__ == "__main__":
    from db.connection import init_db
    init_db()
    seed()
    print("Seed complete.")
