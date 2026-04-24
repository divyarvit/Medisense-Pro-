import sqlite3, hashlib, os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "medisense.db")

def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def init_db():
    conn = get_conn(); c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        full_name TEXT, age INTEGER, gender TEXT,
        blood_group TEXT, phone TEXT, email TEXT, city TEXT,
        created_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS reports(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, module TEXT,
        severity TEXT, diagnosis TEXT,
        confidence REAL, full_report TEXT,
        created_at TEXT,
        numeric_value REAL,
        FOREIGN KEY(user_id) REFERENCES users(id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS alerts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, alert_type TEXT,
        message TEXT, is_read INTEGER DEFAULT 0,
        created_at TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id))''')
    # Add numeric_value column if upgrading existing DB
    try:
        c.execute("ALTER TABLE reports ADD COLUMN numeric_value REAL")
    except: pass
    conn.commit(); conn.close()

def register_user(username, password, full_name, age, gender, blood_group, phone, email, city):
    conn = get_conn(); c = conn.cursor()
    try:
        c.execute('''INSERT INTO users(username,password,full_name,age,gender,
                     blood_group,phone,email,city,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)''',
                  (username, hash_pw(password), full_name, age, gender,
                   blood_group, phone, email, city,
                   datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit(); return True, "Registration successful!"
    except sqlite3.IntegrityError:
        return False, "Username already exists."
    finally:
        conn.close()

def login_user(username, password):
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=? AND password=?",
              (username, hash_pw(password)))
    user = c.fetchone(); conn.close(); return user

def get_user(user_id):
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id=?", (user_id,))
    u = c.fetchone(); conn.close(); return u

def update_user(user_id, full_name, age, gender, blood_group, phone, email, city):
    conn = get_conn(); c = conn.cursor()
    c.execute('''UPDATE users SET full_name=?,age=?,gender=?,blood_group=?,
                 phone=?,email=?,city=? WHERE id=?''',
              (full_name, age, gender, blood_group, phone, email, city, user_id))
    conn.commit(); conn.close()

def save_report(user_id, module, severity, diagnosis, confidence, full_report, numeric_value=None):
    conn = get_conn(); c = conn.cursor()
    c.execute('''INSERT INTO reports(user_id,module,severity,diagnosis,
                 confidence,full_report,created_at,numeric_value) VALUES(?,?,?,?,?,?,?,?)''',
              (user_id, module, severity, diagnosis, confidence,
               full_report, datetime.now().strftime("%Y-%m-%d %H:%M"), numeric_value))
    conn.commit()
    # Auto-generate smart alerts
    _check_and_create_alerts(c, user_id, module, severity, diagnosis, numeric_value)
    conn.commit(); conn.close()

def _check_and_create_alerts(c, user_id, module, severity, diagnosis, numeric_value):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    alerts = []
    if severity == "Severe":
        alerts.append(("urgent", f"🚨 {module}: Severe result detected — {diagnosis}. Please consult a doctor immediately."))
    if "Diabetes" in module and numeric_value and numeric_value > 180:
        alerts.append(("health", f"⚠️ Blood glucose reading of {numeric_value:.0f} mg/dL is dangerously high. See a doctor today."))
    if "Heart" in module and severity in ["Severe","Moderate"]:
        alerts.append(("health", f"❤️ Heart Disease risk detected. Schedule a cardiologist appointment this week."))
    if "Blood Pressure" in diagnosis and severity != "Mild":
        alerts.append(("health", f"🩺 Hypertension risk noted. Monitor your BP daily and reduce salt intake."))
    for atype, msg in alerts:
        c.execute("INSERT INTO alerts(user_id,alert_type,message,created_at) VALUES(?,?,?,?)",
                  (user_id, atype, msg, now))

def get_reports(user_id):
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT * FROM reports WHERE user_id=? ORDER BY created_at DESC", (user_id,))
    rows = c.fetchall(); conn.close(); return rows

def get_reports_for_module(user_id, module, limit=20):
    conn = get_conn(); c = conn.cursor()
    c.execute("""SELECT created_at, severity, confidence, numeric_value, diagnosis
                 FROM reports WHERE user_id=? AND module=?
                 ORDER BY created_at ASC LIMIT ?""", (user_id, module, limit))
    rows = c.fetchall(); conn.close(); return rows

def get_alerts(user_id, unread_only=False):
    conn = get_conn(); c = conn.cursor()
    if unread_only:
        c.execute("SELECT * FROM alerts WHERE user_id=? AND is_read=0 ORDER BY created_at DESC", (user_id,))
    else:
        c.execute("SELECT * FROM alerts WHERE user_id=? ORDER BY created_at DESC LIMIT 20", (user_id,))
    rows = c.fetchall(); conn.close(); return rows

def mark_alerts_read(user_id):
    conn = get_conn(); c = conn.cursor()
    c.execute("UPDATE alerts SET is_read=1 WHERE user_id=?", (user_id,))
    conn.commit(); conn.close()

def get_health_risk_score(user_id):
    """Compute composite health risk score 0-100 from recent reports."""
    conn = get_conn(); c = conn.cursor()
    c.execute("""SELECT module, severity, confidence, created_at
                 FROM reports WHERE user_id=?
                 ORDER BY created_at DESC""", (user_id,))
    rows = c.fetchall(); conn.close()
    if not rows: return None, {}
    sev_weight = {"Severe": 100, "Moderate": 55, "Mild": 20}
    module_scores = {}
    seen = set()
    for row in rows:
        mod = row[0]
        if mod in seen: continue
        seen.add(mod)
        base = sev_weight.get(row[1], 30)
        module_scores[mod] = base
    if not module_scores: return None, {}
    score = round(sum(module_scores.values()) / len(module_scores))
    return score, module_scores

# ─── FAMILY HEALTH VAULT ──────────────────────────────────────────────────────
def add_family_member(owner_id, name, relation, age, gender, blood_group, conditions=""):
    conn = get_conn(); c = conn.cursor()
    try:
        c.execute("ALTER TABLE users ADD COLUMN is_family_member INTEGER DEFAULT 0")
    except: pass
    try:
        c.execute('''CREATE TABLE IF NOT EXISTS family_members(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER, name TEXT, relation TEXT,
            age INTEGER, gender TEXT, blood_group TEXT,
            known_conditions TEXT, created_at TEXT,
            FOREIGN KEY(owner_id) REFERENCES users(id))''')
    except: pass
    c.execute('''INSERT INTO family_members(owner_id,name,relation,age,gender,blood_group,known_conditions,created_at)
                 VALUES(?,?,?,?,?,?,?,?)''',
              (owner_id, name, relation, age, gender, blood_group, conditions,
               datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit(); conn.close()

def get_family_members(owner_id):
    conn = get_conn(); c = conn.cursor()
    try:
        c.execute('''CREATE TABLE IF NOT EXISTS family_members(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER, name TEXT, relation TEXT,
            age INTEGER, gender TEXT, blood_group TEXT,
            known_conditions TEXT, created_at TEXT)''')
        conn.commit()
    except: pass
    c.execute("SELECT * FROM family_members WHERE owner_id=? ORDER BY relation", (owner_id,))
    rows = c.fetchall(); conn.close(); return rows

def delete_family_member(member_id):
    conn = get_conn(); c = conn.cursor()
    c.execute("DELETE FROM family_members WHERE id=?", (member_id,))
    conn.commit(); conn.close()

def save_family_report(owner_id, member_id, member_name, module, severity, diagnosis, confidence, full_report):
    conn = get_conn(); c = conn.cursor()
    try:
        c.execute("ALTER TABLE reports ADD COLUMN family_member_id INTEGER DEFAULT NULL")
        c.execute("ALTER TABLE reports ADD COLUMN family_member_name TEXT DEFAULT NULL")
    except: pass
    c.execute('''INSERT INTO reports(user_id,module,severity,diagnosis,confidence,full_report,created_at,family_member_id,family_member_name)
                 VALUES(?,?,?,?,?,?,?,?,?)''',
              (owner_id, module, severity, diagnosis, confidence, full_report,
               datetime.now().strftime("%Y-%m-%d %H:%M"), member_id, member_name))
    conn.commit(); conn.close()

# ─── SYMPTOM PROGRESSION TRACKER ─────────────────────────────────────────────
def init_symptom_tracker():
    conn = get_conn(); c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS symptom_logs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, tracker_name TEXT,
        day_num INTEGER, date TEXT,
        temperature REAL, pulse INTEGER,
        symptoms TEXT, severity_score INTEGER,
        notes TEXT, created_at TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id))''')
    conn.commit(); conn.close()

def log_symptom_entry(user_id, tracker_name, day_num, temperature, pulse, symptoms, severity_score, notes):
    conn = get_conn(); c = conn.cursor()
    c.execute('''INSERT INTO symptom_logs(user_id,tracker_name,day_num,date,temperature,pulse,symptoms,severity_score,notes,created_at)
                 VALUES(?,?,?,?,?,?,?,?,?,?)''',
              (user_id, tracker_name, day_num,
               datetime.now().strftime("%Y-%m-%d"),
               temperature, pulse, symptoms, severity_score, notes,
               datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit(); conn.close()

def get_symptom_logs(user_id, tracker_name=None):
    conn = get_conn(); c = conn.cursor()
    if tracker_name:
        c.execute("SELECT * FROM symptom_logs WHERE user_id=? AND tracker_name=? ORDER BY day_num", (user_id, tracker_name))
    else:
        c.execute("SELECT * FROM symptom_logs WHERE user_id=? ORDER BY created_at DESC", (user_id,))
    rows = c.fetchall(); conn.close(); return rows

def get_tracker_names(user_id):
    conn = get_conn(); c = conn.cursor()
    c.execute("SELECT DISTINCT tracker_name FROM symptom_logs WHERE user_id=? ORDER BY created_at DESC", (user_id,))
    rows = c.fetchall(); conn.close()
    return [r[0] for r in rows]

# ─── MEDICINE REMINDER ────────────────────────────────────────────────────────
def init_medicines():
    conn = get_conn(); c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS medicines(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, name TEXT, dosage TEXT,
        frequency TEXT, timing TEXT, start_date TEXT,
        end_date TEXT, condition_for TEXT, notes TEXT,
        active INTEGER DEFAULT 1, created_at TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id))''')
    conn.commit(); conn.close()

def add_medicine(user_id, name, dosage, frequency, timing, start_date, end_date, condition_for, notes):
    conn = get_conn(); c = conn.cursor()
    c.execute('''INSERT INTO medicines(user_id,name,dosage,frequency,timing,start_date,end_date,condition_for,notes,active,created_at)
                 VALUES(?,?,?,?,?,?,?,?,?,1,?)''',
              (user_id, name, dosage, frequency, timing, start_date, end_date, condition_for, notes,
               datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit(); conn.close()

def get_medicines(user_id, active_only=True):
    conn = get_conn(); c = conn.cursor()
    if active_only:
        c.execute("SELECT * FROM medicines WHERE user_id=? AND active=1 ORDER BY timing", (user_id,))
    else:
        c.execute("SELECT * FROM medicines WHERE user_id=? ORDER BY created_at DESC", (user_id,))
    rows = c.fetchall(); conn.close(); return rows

def delete_medicine(med_id):
    conn = get_conn(); c = conn.cursor()
    c.execute("UPDATE medicines SET active=0 WHERE id=?", (med_id,))
    conn.commit(); conn.close()
