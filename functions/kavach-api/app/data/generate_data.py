"""
Generates a mock SQLite crime database for the Kavach prototype.

Tables:
- fir            : First Information Reports (case records)
- accused        : Accused persons
- victims        : Victims
- locations      : Crime locations
- fir_accused    : Links FIRs to accused persons
- fir_victims    : Links FIRs to victims
- transactions   : Financial transactions linked to accused
- crime_links    : Generic relationship edges (for network graph)

Run:
    python generate_data.py
"""

import sqlite3
import random
from datetime import datetime, timedelta
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "kavach.db")

random.seed(42)

CITIES = ["Bengaluru", "Mysuru", "Hubli", "Mangaluru", "Belagavi", "Kalaburagi", "Tumakuru", "Shivamogga"]
CRIME_TYPES = [
    "Theft", "Burglary", "Vehicle Theft", "Robbery", "Assault",
    "Cybercrime - Financial Fraud", "Chain Snatching", "Cheating",
    "Counterfeit Currency", "Drug Peddling", "Extortion", "House Breaking"
]
STATUSES = ["Under Investigation", "Chargesheet Filed", "Closed", "Convicted", "Acquitted"]
GENDERS = ["Male", "Female"]
FIRST_NAMES_M = ["Arjun", "Suresh", "Manjunath", "Prakash", "Naveen", "Ravi", "Ramesh", "Sandeep",
                 "Vinod", "Harish", "Ganesh", "Anil", "Deepak", "Yusuf", "Imran", "Karthik"]
FIRST_NAMES_F = ["Lakshmi", "Priya", "Sunita", "Anitha", "Kavya", "Rekha", "Shruthi", "Pooja",
                  "Meena", "Asha", "Nandini", "Divya"]
LAST_NAMES = ["Sharma", "Naik", "Patil", "Gowda", "Rao", "Kumar", "Shetty", "Reddy",
               "Hegde", "Pillai", "Khan", "Sayyed", "Shenoy", "Iyer"]

ECONOMIC_BACKGROUNDS = ["Low Income", "Lower-Middle Income", "Middle Income", "Upper-Middle Income"]
EDUCATION_LEVELS = ["No formal education", "Primary", "Secondary", "Higher Secondary", "Graduate", "Postgraduate"]


def random_name(gender):
    if gender == "Male":
        return f"{random.choice(FIRST_NAMES_M)} {random.choice(LAST_NAMES)}"
    return f"{random.choice(FIRST_NAMES_F)} {random.choice(LAST_NAMES)}"


def random_date(start_year=2024, end_year=2026):
    start = datetime(start_year, 1, 1)
    end = datetime(end_year, 6, 1)
    delta = end - start
    return (start + timedelta(days=random.randint(0, delta.days))).strftime("%Y-%m-%d")


def build_database():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.executescript("""
    CREATE TABLE locations (
        location_id INTEGER PRIMARY KEY AUTOINCREMENT,
        area_name TEXT,
        city TEXT,
        latitude REAL,
        longitude REAL
    );

    CREATE TABLE accused (
        accused_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        age INTEGER,
        gender TEXT,
        economic_background TEXT,
        education_level TEXT,
        prior_offenses INTEGER,
        risk_score REAL
    );

    CREATE TABLE victims (
        victim_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        age INTEGER,
        gender TEXT,
        economic_background TEXT
    );

    CREATE TABLE fir (
        fir_id TEXT PRIMARY KEY,
        crime_type TEXT,
        date_filed TEXT,
        location_id INTEGER,
        status TEXT,
        modus_operandi TEXT,
        FOREIGN KEY(location_id) REFERENCES locations(location_id)
    );

    CREATE TABLE fir_accused (
        fir_id TEXT,
        accused_id INTEGER,
        role TEXT,
        FOREIGN KEY(fir_id) REFERENCES fir(fir_id),
        FOREIGN KEY(accused_id) REFERENCES accused(accused_id)
    );

    CREATE TABLE fir_victims (
        fir_id TEXT,
        victim_id INTEGER,
        FOREIGN KEY(fir_id) REFERENCES fir(fir_id),
        FOREIGN KEY(victim_id) REFERENCES victims(victim_id)
    );

    CREATE TABLE transactions (
        txn_id INTEGER PRIMARY KEY AUTOINCREMENT,
        accused_id INTEGER,
        counterparty_account TEXT,
        amount REAL,
        txn_date TEXT,
        flagged INTEGER,
        FOREIGN KEY(accused_id) REFERENCES accused(accused_id)
    );

    CREATE TABLE crime_links (
        link_id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_type TEXT,
        source_id TEXT,
        target_type TEXT,
        target_id TEXT,
        relation TEXT
    );
    """)

    # Locations
    location_ids = []
    for city in CITIES:
        for area in [f"{city} Central", f"{city} North", f"{city} South", f"{city} East"]:
            lat = round(12.5 + random.uniform(-2.5, 2.5), 5)
            lon = round(77.0 + random.uniform(-3.0, 3.0), 5)
            cur.execute(
                "INSERT INTO locations (area_name, city, latitude, longitude) VALUES (?, ?, ?, ?)",
                (area, city, lat, lon)
            )
            location_ids.append(cur.lastrowid)

    # Accused persons
    accused_ids = []
    for i in range(60):
        gender = random.choice(GENDERS)
        prior = random.choices([0, 1, 2, 3, 4, 5, 6], weights=[35, 20, 15, 10, 10, 5, 5])[0]
        # Risk score: function of prior offenses + randomness
        base = min(prior / 6, 1.0)
        risk = round(min(1.0, max(0.05, base * 0.7 + random.uniform(0, 0.3))), 2)
        cur.execute(
            """INSERT INTO accused (name, age, gender, economic_background, education_level, prior_offenses, risk_score)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                random_name(gender),
                random.randint(18, 55),
                gender,
                random.choice(ECONOMIC_BACKGROUNDS),
                random.choice(EDUCATION_LEVELS),
                prior,
                risk
            )
        )
        accused_ids.append(cur.lastrowid)

    # Victims
    victim_ids = []
    for i in range(80):
        gender = random.choice(GENDERS)
        cur.execute(
            "INSERT INTO victims (name, age, gender, economic_background) VALUES (?, ?, ?, ?)",
            (random_name(gender), random.randint(10, 75), gender, random.choice(ECONOMIC_BACKGROUNDS))
        )
        victim_ids.append(cur.lastrowid)

    # FIRs
    fir_ids = []

    # Define a small number of "organized groups" (gangs) with shared members,
    # so network/group-detection analytics have realistic, demo-friendly clusters.
    num_gangs = 4
    gang_members = []
    pool = accused_ids.copy()
    random.shuffle(pool)
    for g in range(num_gangs):
        size = random.randint(3, 5)
        members = pool[:size]
        pool = pool[size:]
        gang_members.append(members)

    # Remaining accused are "independent" operators
    independent_accused = pool

    for i in range(150):
        year = random.choice([2024, 2025, 2026])
        fir_id = f"FIR-{year}-{1000 + i}"
        crime_type = random.choice(CRIME_TYPES)
        location_id = random.choice(location_ids)
        status = random.choices(STATUSES, weights=[40, 25, 15, 12, 8])[0]
        mo_options = {
            "Theft": "Opportunistic theft from unattended premises during daytime",
            "Burglary": "Forced entry at night through rear windows/doors",
            "Vehicle Theft": "Two-wheeler theft from parking areas using duplicate keys",
            "Robbery": "Armed robbery targeting late-night commuters",
            "Assault": "Altercation escalating to physical assault, often alcohol-related",
            "Cybercrime - Financial Fraud": "Phishing/OTP fraud via phone calls impersonating bank officials",
            "Chain Snatching": "Two-wheeler-borne snatching targeting pedestrians near markets",
            "Cheating": "Investment/loan fraud through fake schemes",
            "Counterfeit Currency": "Circulation of fake currency notes via small vendors",
            "Drug Peddling": "Small-quantity narcotics sale near educational institutions",
            "Extortion": "Threat-based demand for money from local businesses",
            "House Breaking": "Breaking into vacant homes during festival/holiday periods",
        }
        cur.execute(
            "INSERT INTO fir (fir_id, crime_type, date_filed, location_id, status, modus_operandi) VALUES (?, ?, ?, ?, ?, ?)",
            (fir_id, crime_type, random_date(), location_id, status, mo_options.get(crime_type, "Unknown"))
        )
        fir_ids.append(fir_id)

        # ~25% of FIRs involve a gang (2-3 of its members appear together);
        # the rest involve a single independent/random accused (no incidental
        # co-accused pairings among independents, to keep network analytics
        # demo-friendly and avoid one giant connected component).
        if random.random() < 0.25 and gang_members:
            gang = random.choice(gang_members)
            k = random.randint(2, min(3, len(gang)))
            chosen_accused = random.sample(gang, k)
        else:
            source_pool = independent_accused if independent_accused else accused_ids
            chosen_accused = random.sample(source_pool, 1)

        for idx, acc_id in enumerate(chosen_accused):
            role = "Primary Accused" if idx == 0 else "Co-Accused"
            cur.execute("INSERT INTO fir_accused (fir_id, accused_id, role) VALUES (?, ?, ?)", (fir_id, acc_id, role))

        # Link 0-2 victims
        num_victims = random.choices([0, 1, 2], weights=[10, 70, 20])[0]
        chosen_victims = random.sample(victim_ids, min(num_victims, len(victim_ids)))
        for v_id in chosen_victims:
            cur.execute("INSERT INTO fir_victims (fir_id, victim_id) VALUES (?, ?)", (fir_id, v_id))

        # Crime link edges (accused-accused, accused-location, accused-victim)
        for acc_id in chosen_accused:
            cur.execute(
                "INSERT INTO crime_links (source_type, source_id, target_type, target_id, relation) VALUES (?, ?, ?, ?, ?)",
                ("accused", str(acc_id), "location", str(location_id), "operated_in")
            )
            for v_id in chosen_victims:
                cur.execute(
                    "INSERT INTO crime_links (source_type, source_id, target_type, target_id, relation) VALUES (?, ?, ?, ?, ?)",
                    ("accused", str(acc_id), "victim", str(v_id), "victimized")
                )
        if len(chosen_accused) > 1:
            for a in range(len(chosen_accused)):
                for b in range(a + 1, len(chosen_accused)):
                    cur.execute(
                        "INSERT INTO crime_links (source_type, source_id, target_type, target_id, relation) VALUES (?, ?, ?, ?, ?)",
                        ("accused", str(chosen_accused[a]), "accused", str(chosen_accused[b]), "co_accused")
                    )

    # Financial transactions for ~half of accused
    for acc_id in random.sample(accused_ids, len(accused_ids) // 2):
        for _ in range(random.randint(1, 4)):
            amount = round(random.uniform(2000, 250000), 2)
            flagged = 1 if amount > 100000 and random.random() < 0.6 else (1 if random.random() < 0.1 else 0)
            cur.execute(
                "INSERT INTO transactions (accused_id, counterparty_account, amount, txn_date, flagged) VALUES (?, ?, ?, ?, ?)",
                (acc_id, f"ACC{random.randint(100000,999999)}", amount, random_date(), flagged)
            )

    conn.commit()
    conn.close()
    print(f"Database created at {DB_PATH}")
    print(f"  Locations : {len(location_ids)}")
    print(f"  Accused   : {len(accused_ids)}")
    print(f"  Victims   : {len(victim_ids)}")
    print(f"  FIRs      : {len(fir_ids)}")
    print(f"  Organized groups (seeded): {len(gang_members)} -> sizes {[len(g) for g in gang_members]}")


if __name__ == "__main__":
    build_database()
