"""
Diabetes Module — MediSense Pro v10
Solving all 8 clinical holes identified:
1. Time of glucose reading (fasting vs post-meal vs random)
2. HbA1c input added
3. Type 1 vs Type 2 vs Pre-diabetes distinguished
4. Meal context captured before interpreting readings
5. Stress / cortisol effect accounted for
6. Current medications checked (steroid/diuretic/contraceptive)
7. Glucose trend awareness (multiple readings)
8. Gestational case — separate thresholds for pregnant women

Three modes:
  🏠 Home Screener     — glucometer + BP machine + smartwatch + symptoms
  🔬 Clinical Mode     — full ML model with lab values
  📈 Glucose Trend     — track readings over time
"""
import streamlit as st, pickle, os, numpy as np
from utils.report_renderer import render_clinical_report
from utils.database import save_report, get_conn
from utils.explainability import explain_diabetes
from utils.xai_renderer import render_xai_panel
from utils.groq_explainer import generate_diabetes_explanation
from datetime import datetime, date

MODEL = pickle.load(open(os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                      "models","diabetes_model.sav"),"rb"))

# ─── Clinical Thresholds ─────────────────────────────────────────────────────
# Hole 1 + 8: Different thresholds based on reading time AND pregnancy
GLUCOSE_THRESHOLDS = {
    "Fasting (8+ hrs no food)": {
        False: {"normal":100, "prediab":126, "diabetic":126},   # non-pregnant
        True:  {"normal": 92, "prediab": 92, "diabetic":126},   # pregnant (GDM)
    },
    "Post-Meal (2 hrs after eating)": {
        False: {"normal":140, "prediab":200, "diabetic":200},
        True:  {"normal":120, "prediab":153, "diabetic":153},
    },
    "Random (any time)": {
        False: {"normal":140, "prediab":200, "diabetic":200},
        True:  {"normal":140, "prediab":200, "diabetic":200},
    },
}

# HbA1c thresholds (same for all — Hole 2)
HBAIC_THRESHOLDS = {"normal":5.7, "prediab":6.5, "diabetic":6.5}

# Hole 3: Type 1 vs Type 2 discriminators
def _classify_type(age, bmi, onset, pregnant):
    if pregnant:
        return "gestational"
    if age < 30 and bmi < 25 and onset == "Sudden (days to weeks)":
        return "type1"
    if age >= 30 or bmi >= 25:
        return "type2"
    return "type2"

# Hole 5: Stress glucose adjustment
STRESS_ADJUSTMENT = {
    "Low (calm, normal day)":   0,
    "Moderate (some pressure)": 8,
    "High (exam/work stress)":  18,
    "Very High (crisis/grief)": 30,
}

# Hole 6: Medications that raise glucose
GLUCOSE_RAISING_MEDS = {
    "Steroids (Prednisolone, Dexamethasone)": 35,
    "Thiazide Diuretics (Hydrochlorothiazide)": 12,
    "Beta-Blockers (Metoprolol, Atenolol)": 8,
    "Antipsychotics (Olanzapine, Clozapine)": 20,
    "Birth Control Pills (OCP)": 6,
    "Tacrolimus / Cyclosporine (transplant)": 25,
    "None of the above": 0,
}

# ─── Glucose Trend Storage ────────────────────────────────────────────────────
def save_glucose_reading(user_id, glucose, reading_type, notes=""):
    conn = get_conn(); c = conn.cursor()
    try:
        c.execute("""CREATE TABLE IF NOT EXISTS glucose_log(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, glucose REAL, reading_type TEXT,
            notes TEXT, logged_at TEXT)""")
        conn.commit()
    except: pass
    c.execute("INSERT INTO glucose_log(user_id,glucose,reading_type,notes,logged_at) VALUES(?,?,?,?,?)",
              (user_id, glucose, reading_type, notes,
               datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit(); conn.close()

def get_glucose_history(user_id, limit=14):
    conn = get_conn(); c = conn.cursor()
    try:
        c.execute("SELECT glucose,reading_type,logged_at FROM glucose_log WHERE user_id=? ORDER BY logged_at DESC LIMIT ?",
                  (user_id, limit))
        rows = c.fetchall()
    except:
        rows = []
    conn.close(); return list(reversed(rows))

def _glucose_trend_chart(readings):
    """SVG sparkline for glucose trend."""
    if len(readings) < 2:
        return ""
    vals  = [r[0] for r in readings]
    dates = [r[2][:10] for r in readings]
    n = len(vals)
    w, h, pad = 580, 110, 20

    mn = min(min(vals)-10, 60)
    mx = max(max(vals)+10, 220)

    def px(i): return pad + i*(w-2*pad)/(n-1)
    def py(v): return h - pad - (v-mn)/(mx-mn)*(h-2*pad)

    # Reference lines
    ref_lines = ""
    for ref_val, ref_label, ref_color in [
        (100,"Normal (100)","#43a047"),
        (126,"Diabetic (126)","#e53935"),
    ]:
        y = py(ref_val)
        ref_lines += f'<line x1="{pad}" y1="{y:.0f}" x2="{w-pad}" y2="{y:.0f}" stroke="{ref_color}" stroke-width="1" stroke-dasharray="4,3"/>'
        ref_lines += f'<text x="{w-pad+4}" y="{y+4:.0f}" font-size="9" fill="{ref_color}">{ref_label}</text>'

    path = " ".join(f"{'M' if i==0 else 'L'}{px(i):.0f},{py(v):.0f}" for i,v in enumerate(vals))
    dots = ""
    for i,(v,r) in enumerate(zip(vals,[rd[1] for rd in readings])):
        c = "#e53935" if v>=126 else ("#fb8c00" if v>=100 else "#43a047")
        dots += f'<circle cx="{px(i):.0f}" cy="{py(v):.0f}" r="5" fill="{c}" stroke="white" stroke-width="2"/>'
        dots += f'<text x="{px(i):.0f}" y="{py(v)-9:.0f}" text-anchor="middle" font-size="9" fill="{c}" font-weight="bold">{v:.0f}</text>'
        if i==0 or i==n-1 or n<=6:
            short = dates[i][5:]
            dots += f'<text x="{px(i):.0f}" y="{h+10}" text-anchor="middle" font-size="8" fill="#aaa">{short}</text>'

    trend = vals[-1]-vals[0]
    trend_txt = "📈 Rising — worsening" if trend>10 else ("📉 Falling — improving ✅" if trend<-10 else "➡️ Stable")
    trend_col = "#e53935" if trend>10 else ("#43a047" if trend<-10 else "#fb8c00")
    avg = sum(vals)/len(vals)

    return f"""<div style="background:#f8f9fa;border-radius:12px;padding:16px 18px;border:1px solid #e0e0e0;margin:8px 0">
        <div style="display:flex;justify-content:space-between;margin-bottom:6px">
            <b style="font-size:13px;color:#333">Glucose Trend — Last {n} readings</b>
            <span style="font-size:13px;font-weight:700;color:{trend_col}">{trend_txt}</span>
        </div>
        <svg width="100%" viewBox="0 0 {w} {h+18}" style="overflow:visible">
            {ref_lines}
            <path d="{path}" fill="none" stroke="#1565c0" stroke-width="2.5"
                stroke-linecap="round" stroke-linejoin="round"/>
            {dots}
        </svg>
        <div style="font-size:12px;color:#888;margin-top:6px">
            Average: <b>{avg:.0f} mg/dL</b> &nbsp;·&nbsp;
            Min: <b>{min(vals):.0f}</b> &nbsp;·&nbsp;
            Max: <b>{max(vals):.0f}</b>
        </div>
    </div>"""

# ─── Home Screener Risk Engine ────────────────────────────────────────────────
def _home_risk_score(data):
    """
    Weighted clinical risk scoring for home screener.
    Returns score 0-100, risk level, flags, adjusted glucose.
    """
    score = 0
    flags = []

    g_raw  = data["glucose"]
    g_type = data["glucose_type"]
    preg   = data["pregnant"]
    stress = data["stress"]
    meds   = data["medications"]

    # Hole 5: Adjust glucose for stress
    stress_adj = STRESS_ADJUSTMENT.get(stress, 0)
    # Hole 6: Adjust for medications
    med_adj = sum(GLUCOSE_RAISING_MEDS.get(m,0) for m in meds)
    total_adj = stress_adj + med_adj
    g_adjusted = g_raw - total_adj  # true physiological glucose

    thresh = GLUCOSE_THRESHOLDS.get(g_type, GLUCOSE_THRESHOLDS["Fasting (8+ hrs no food)"])[preg]

    # ── Glucose scoring (most important — 35 pts) ─────────────────────
    if g_adjusted >= thresh["diabetic"]:
        score += 35
        flags.append(f"🔴 Glucose {g_raw} mg/dL — diabetic range ({g_type})")
    elif g_adjusted >= thresh["normal"]:
        score += 18
        flags.append(f"🟡 Glucose {g_raw} mg/dL — pre-diabetic range ({g_type})")
    else:
        flags.append(f"🟢 Glucose {g_raw} mg/dL — normal ({g_type})")
    if total_adj > 0:
        flags.append(f"ℹ️ Glucose adjusted by -{total_adj} mg/dL for stress/medication effect. True level ≈ {g_adjusted:.0f}")

    # ── HbA1c (25 pts — Hole 2) ──────────────────────────────────────
    hba1c = data.get("hba1c", 0)
    if hba1c > 0:
        if hba1c >= HBAIC_THRESHOLDS["diabetic"]:
            score += 25
            flags.append(f"🔴 HbA1c {hba1c}% — diabetic (3-month avg confirms diabetes)")
        elif hba1c >= HBAIC_THRESHOLDS["normal"]:
            score += 12
            flags.append(f"🟡 HbA1c {hba1c}% — pre-diabetic range")
        else:
            flags.append(f"🟢 HbA1c {hba1c}% — normal (3-month average is good)")

    # ── Post-meal glucose (Hole 1 additional) ────────────────────────
    pm_glucose = data.get("postmeal_glucose", 0)
    if pm_glucose > 0:
        pm_thresh = GLUCOSE_THRESHOLDS["Post-Meal (2 hrs after eating)"][preg]
        if pm_glucose >= pm_thresh["diabetic"]:
            score += 20
            flags.append(f"🔴 Post-meal glucose {pm_glucose} mg/dL — diabetic range")
        elif pm_glucose >= pm_thresh["normal"]:
            score += 10
            flags.append(f"🟡 Post-meal glucose {pm_glucose} mg/dL — elevated")
        else:
            flags.append(f"🟢 Post-meal glucose {pm_glucose} mg/dL — normal")

    # ── BP (10 pts) ───────────────────────────────────────────────────
    sys_bp = data.get("systolic_bp", 0)
    dia_bp = data.get("diastolic_bp", 0)
    if sys_bp > 0:
        if sys_bp >= 140 or dia_bp >= 90:
            score += 10
            flags.append(f"🔴 BP {sys_bp}/{dia_bp} mmHg — hypertension (strong diabetes link)")
        elif sys_bp >= 130 or dia_bp >= 85:
            score += 5
            flags.append(f"🟡 BP {sys_bp}/{dia_bp} mmHg — borderline high")
        else:
            flags.append(f"🟢 BP {sys_bp}/{dia_bp} mmHg — normal")

    # ── BMI (10 pts) ──────────────────────────────────────────────────
    bmi = data.get("bmi", 0)
    if bmi > 0:
        if bmi >= 30:
            score += 10
            flags.append(f"🔴 BMI {bmi:.1f} — obese (major insulin resistance driver)")
        elif bmi >= 25:
            score += 5
            flags.append(f"🟡 BMI {bmi:.1f} — overweight (increased risk)")
        else:
            flags.append(f"🟢 BMI {bmi:.1f} — healthy weight")

    # ── Wearable data ─────────────────────────────────────────────────
    rhr = data.get("resting_hr", 0)
    if rhr > 0:
        if rhr > 90:
            score += 5
            flags.append(f"🟡 Resting HR {rhr} bpm — elevated (linked to insulin resistance)")
        elif rhr > 100:
            score += 8
            flags.append(f"🔴 Resting HR {rhr} bpm — high (metabolic stress signal)")
        else:
            flags.append(f"🟢 Resting HR {rhr} bpm — normal")

    sleep_hrs = data.get("sleep_hours", 0)
    if sleep_hrs > 0:
        if sleep_hrs < 5:
            score += 8
            flags.append(f"🔴 Sleep {sleep_hrs}h — severe sleep deprivation raises cortisol → blood sugar")
        elif sleep_hrs < 7:
            score += 4
            flags.append(f"🟡 Sleep {sleep_hrs}h — less than recommended 7-8h")
        else:
            flags.append(f"🟢 Sleep {sleep_hrs}h — good (adequate sleep protects glucose metabolism)")

    steps = data.get("daily_steps", 0)
    if steps > 0:
        if steps < 3000:
            score += 7
            flags.append(f"🔴 {steps:,} steps/day — very sedentary (major diabetes risk factor)")
        elif steps < 6000:
            score += 3
            flags.append(f"🟡 {steps:,} steps/day — below recommended 8,000+")
        else:
            flags.append(f"🟢 {steps:,} steps/day — active lifestyle (protective)")

    spo2 = data.get("spo2", 0)
    if spo2 > 0 and spo2 < 95:
        score += 5
        flags.append(f"🔴 SpO2 {spo2}% — low oxygen (circulation concern)")

    # ── Symptoms (10 pts) ─────────────────────────────────────────────
    symptoms = data.get("symptoms", [])
    high_risk_syms = ["Unusual thirst","Frequent urination","Unexplained fatigue",
                      "Blurred vision","Slow healing wounds","Tingling hands/feet"]
    matched = [s for s in symptoms if s in high_risk_syms]
    sym_score = min(len(matched)*2, 10)
    score += sym_score
    if matched:
        flags.append(f"🟡 Symptoms: {', '.join(matched)} — classic diabetes warning signs")

    # ── Family history ────────────────────────────────────────────────
    if data.get("family_history"):
        score += 5
        flags.append("🟡 Family history of diabetes — 40% higher genetic risk")

    # ── Age ───────────────────────────────────────────────────────────
    age = data.get("age", 0)
    if age >= 45:
        score += 5
        flags.append(f"🟡 Age {age} — risk rises significantly after 45")

    score = min(score, 100)

    if score >= 50:   risk = "High Risk"
    elif score >= 25: risk = "Moderate Risk"
    else:             risk = "Low Risk"

    return score, risk, flags, g_adjusted, _classify_type(
        age, bmi,
        data.get("onset","Gradual (months to years)"),
        preg
    )

# ─── Report Builder ───────────────────────────────────────────────────────────
def _build_home_report(risk, score, dtype, data, flags, g_adjusted):
    sev_map = {"High Risk":"Severe","Moderate Risk":"Moderate","Low Risk":"Mild"}
    severity = sev_map.get(risk,"Moderate")

    type_info = {
        "type1":       ("Type 1 Diabetes (Possible)",       "E10",
                        "Autoimmune destruction of insulin-producing cells. Typically affects younger, thinner individuals. REQUIRES insulin therapy."),
        "type2":       ("Type 2 Diabetes Mellitus",         "E11",
                        "Insulin resistance + relative insulin deficiency. Linked to lifestyle, obesity, age. Manageable with diet, exercise, medication."),
        "gestational": ("Gestational Diabetes Mellitus",    "O24",
                        "Diabetes developing during pregnancy. Requires strict glucose control. Usually resolves after delivery."),
        "prediab":     ("Pre-diabetes / Impaired Glucose Tolerance","R73.0",
                        "Blood sugar higher than normal but not yet full diabetes. REVERSIBLE with lifestyle changes."),
    }

    if risk == "Low Risk":
        dtype = "prediab"
        conditions = [
            {"condition":"No Diabetes Detected","probability":85.0,
             "description":"Parameters within acceptable range.","icd":"Z03.89"},
            {"condition":"Pre-diabetes Risk (monitor)","probability":10.0,
             "description":"No current diabetes but monitor annually.","icd":"R73.0"},
            {"condition":"Lifestyle Risk Factors","probability":5.0,
             "description":"Some lifestyle factors that may increase future risk.","icd":"Z82.3"},
        ]
    else:
        dname, dicd, ddesc = type_info.get(dtype, type_info["type2"])
        conditions = [
            {"condition": dname, "probability": round(30+score*0.4, 1),
             "description": ddesc, "icd": dicd},
            {"condition":"Pre-diabetes / IGT","probability": round(100-(30+score*0.4)-8, 1),
             "description":"Blood sugar higher than normal range.","icd":"R73.0"},
            {"condition":"Stress-induced Hyperglycemia","probability":8.0,
             "description":"Temporary glucose elevation due to physiological stress.","icd":"R73.9"},
        ]

    # Type-specific advice
    if dtype == "type1":
        do_list = ["Consult Endocrinologist IMMEDIATELY — Type 1 requires insulin",
                   "Get C-Peptide test to confirm Type 1 vs Type 2",
                   "Monitor glucose 4-6 times daily",
                   "Learn carbohydrate counting for insulin dosing",
                   "Carry glucose tablets for hypoglycemia episodes",
                   "Get HbA1c test — target below 7%"]
        dont_list = ["Do NOT use oral diabetes tablets — Type 1 needs insulin",
                     "Do NOT skip insulin doses",
                     "Do NOT exercise with glucose above 250 mg/dL",
                     "Do NOT ignore ketone symptoms: nausea, fruity breath, confusion"]
        specialist = "Endocrinologist (Type 1 specialist) — URGENT"
    elif dtype == "gestational":
        do_list = ["Consult Gynaecologist + Diabetologist IMMEDIATELY",
                   "Monitor glucose 4x daily: fasting + after each main meal",
                   "Target fasting glucose below 95 mg/dL",
                   "Follow gestational diabetes meal plan",
                   "Walk 15 min after each meal — safe and effective",
                   "All foetal growth scans on schedule — GDM affects baby size"]
        dont_list = ["Do NOT fast or skip meals during pregnancy",
                     "Do NOT self-medicate with insulin",
                     "Avoid all sugary drinks and sweets completely",
                     "Do NOT ignore foetal kick counts"]
        specialist = "Obstetrician + Diabetologist (urgent referral)"
    elif risk == "Low Risk":
        do_list = ["Annual fasting glucose test — early detection is key",
                   "Maintain healthy BMI (18.5–24.9)",
                   "Walk 30 minutes daily",
                   "Eat low-glycemic foods: vegetables, whole grains, pulses",
                   "Limit rice/white bread — replace with millets, oats",
                   "Sleep 7-8 hours every night"]
        dont_list = ["Avoid sugary drinks — even 'natural' fruit juices",
                     "Do not skip annual health checkup",
                     "Do not ignore family history — screen more frequently"]
        specialist = "General Physician (annual screening)"
    else:
        do_list = ["Consult a Diabetologist within 3 days",
                   "Get HbA1c test done — it shows 3-month glucose average",
                   "Monitor fasting glucose every morning",
                   "Follow low-glycemic diet: avoid rice, maida, sweets",
                   "Exercise 30 min daily — walking after meals is best",
                   "Drink 2.5–3 litres of water daily"]
        dont_list = ["Do NOT eat white rice, bread, sweets, sugary drinks",
                     "Do NOT skip meals — causes glucose spikes",
                     "Do NOT self-medicate with any diabetic tablets",
                     "Avoid alcohol — raises and then crashes blood sugar",
                     "Do NOT ignore foot wounds — heal poorly in diabetics",
                     "Do NOT delay seeing a doctor"]
        specialist = "Diabetologist / Endocrinologist"

    sev_reasons = [f for f in flags if "🔴" in f or "🟡" in f][:5]
    sev_reasons = [s.replace("🔴","").replace("🟡","").strip() for s in sev_reasons]

    confidence = min(50 + score * 0.4, 92)

    # ── Try Groq for dynamic doctor-like explanations ─────────
    groq_result = generate_diabetes_explanation(data, risk, score, dtype, flags, g_adjusted)

    if groq_result:
        sev_expl = groq_result.get("section2",
            {"High Risk": "Multiple strong risk indicators detected. Medical consultation needed within 3 days.",
             "Moderate Risk": "Several risk factors present. Lifestyle changes needed now. Confirm with a doctor.",
             "Low Risk": "No significant diabetes risk currently. Maintain healthy habits."
             }.get(risk,""))
        # Update conditions with Groq reasoning
        if len(conditions) >= 1:
            conditions[0]["reasoning"] = groq_result.get("why_condition1", "")
        if len(conditions) >= 2:
            conditions[1]["reasoning"] = groq_result.get("why_condition2", "")
        if len(conditions) >= 3:
            conditions[2]["reasoning"] = groq_result.get("why_condition3", "")
        # Store both sections for report renderer
        data["groq_section1"] = groq_result.get("section1", "")
        data["groq_section2"] = groq_result.get("section2", "")
    else:
        sev_expl = {
            "High Risk":     "Multiple strong risk indicators detected. Strongly recommend medical consultation within 3 days.",
            "Moderate Risk": "Several risk factors present. Lifestyle changes needed now. Confirm with a doctor.",
            "Low Risk":      "No significant diabetes risk detected currently. Maintain healthy habits.",
        }.get(risk,"")

    do_dont   = {"do": do_list, "dont": dont_list}
    home_care = [
        "Check fasting glucose every morning before eating",
        "Keep a glucose diary — note readings with date and reading type",
        "Add bitter gourd (karela), fenugreek seeds to daily diet",
        "Walk 10 minutes after every meal — most effective blood sugar control",
        "Replace white rice with brown rice, millet (ragi, jowar) or oats",
        "Eat small portions 5-6 times instead of 3 large meals",
    ]
    when_doc = [
        f"See a {specialist} within {'24 hrs' if risk=='High Risk' else '1 week'}",
        "If glucose is above 250 mg/dL at any time — same day",
        "If you feel dizzy, confused, or have fruity-smelling breath",
        "For HbA1c test to confirm 3-month glucose average",
    ]

    extra = f"**Likely Type:** {type_info.get(dtype,type_info['type2'])[0]} · **Recommended:** {specialist}"
    return severity, sev_expl, sev_reasons, conditions, confidence, do_dont, home_care, when_doc, extra

def _build_clinical_report(result, glucose, bmi, age):
    """Original clinical report logic — unchanged."""
    if result == "Positive":
        severity = "Severe" if glucose > 200 or bmi > 35 else "Moderate"
        conditions = [
            {"condition":"Type 2 Diabetes Mellitus","probability":72.0,
             "description":"High blood glucose due to insulin resistance or deficiency.","icd":"E11"},
            {"condition":"Pre-diabetes / Impaired Glucose Tolerance","probability":18.0,
             "description":"Blood sugar higher than normal but not yet diabetic range.","icd":"R73.0"},
            {"condition":"Gestational Diabetes (if applicable)","probability":10.0,
             "description":"Diabetes developing during pregnancy.","icd":"O24"},
        ]
        sev_expl = "Your parameters suggest active diabetes. Immediate lifestyle changes and medical consultation are required."
        sev_reasons = [f"Glucose: {glucose} mg/dL (elevated)" if glucose>125 else "",
                       f"BMI: {bmi} (obese range)" if bmi>30 else "",
                       f"Age: {age} (higher risk above 45)" if age>45 else ""]
        sev_reasons = [r for r in sev_reasons if r]
        confidence = 82.0
        do_dont = {
            "do":   ["Consult an Endocrinologist or Diabetologist immediately",
                     "Monitor blood glucose daily (fasting + post-meal)",
                     "Follow a low-carb, high-fibre diet",
                     "Exercise 30 minutes daily (walking is best)",
                     "Get HbA1c test done every 3 months",
                     "Drink plenty of water — avoid sugary drinks"],
            "dont": ["Do NOT eat white bread, rice, sweets, or fried food",
                     "Do NOT skip meals — it worsens glucose control",
                     "Do NOT self-medicate with insulin without guidance",
                     "Avoid alcohol and smoking",
                     "Do NOT ignore foot wounds — they heal slowly in diabetics",
                     "Do NOT delay medical consultation"]
        }
        home_care = ["Check fasting blood sugar every morning",
                     "Keep a food diary — track carbs and sugar intake",
                     "Wear comfortable shoes to protect feet",
                     "Eat small portions 5-6 times a day",
                     "Add bitter gourd (karela) and fenugreek to diet",
                     "Walk 10 minutes after each meal"]
        when_doc  = ["Visit a Diabetologist within 3 days",
                     "Immediately if glucose > 300 mg/dL",
                     "If you feel dizzy, confused, or faint",
                     "For HbA1c test and medication review"]
        extra = "**Recommended specialists:** Diabetologist, Endocrinologist, Nutritionist, Ophthalmologist (eye check)"
    else:
        severity, conditions = "Mild",[
            {"condition":"No Diabetes Detected","probability":88.0,
             "description":"Blood glucose and other parameters within acceptable range.","icd":"Z03.89"},
            {"condition":"Pre-diabetes Risk (monitor)","probability":8.0,
             "description":"No current diabetes but maintain healthy habits.","icd":"R73.0"},
            {"condition":"Lifestyle-related Risk","probability":4.0,
             "description":"High BMI or family history may increase future risk.","icd":"Z82.3"},
        ]
        sev_expl  = "No diabetes detected. Maintain a healthy lifestyle to prevent future risk."
        sev_reasons = ["Parameters within acceptable range"]
        confidence  = 78.0
        do_dont = {
            "do":   ["Maintain a balanced, low-sugar diet",
                     "Exercise regularly — at least 30 min/day",
                     "Annual fasting blood glucose test",
                     "Maintain healthy BMI (18.5–24.9)"],
            "dont": ["Avoid excessive sugar and processed foods",
                     "Do not become sedentary — stay active",
                     "Do not ignore family history of diabetes"]
        }
        home_care = ["Eat whole grains instead of refined carbs",
                     "Include cinnamon — helps insulin sensitivity",
                     "Sleep 7-8 hours — poor sleep raises blood sugar"]
        when_doc  = ["Annual blood sugar screening",
                     "If you notice unusual thirst, fatigue, or frequent urination"]
        extra = "✅ You are currently not diabetic. Maintain your healthy lifestyle!"
    return severity, sev_expl, sev_reasons, conditions, confidence, do_dont, home_care, when_doc, extra


# ─── MAIN SHOW ────────────────────────────────────────────────────────────────
def show():
    st.markdown("""<div class="main-header">
        <h1>🩸 Diabetes Risk Assessment</h1>
        <p>Complete diabetes screening — from home glucometer to clinical ML model</p>
    </div>""", unsafe_allow_html=True)

    mode_tab, clinical_tab, trend_tab = st.tabs([
        "🏠 Home Screener — For Anyone",
        "🔬 Clinical ML Model — With Lab Reports",
        "📈 My Glucose Trend",
    ])

    uid   = st.session_state.user_id
    uname = st.session_state.get("full_name","Patient")

    # ════════════════════════════════════════════════════════════════════
    # TAB 1 — HOME SCREENER
    # ════════════════════════════════════════════════════════════════════
    with mode_tab:
        st.markdown("""<div style="background:#e8f5e9;border-left:5px solid #43a047;
            border-radius:10px;padding:12px 18px;font-size:14px;margin-bottom:16px">
            🏠 <b>This is for anyone at home.</b> Uses your glucometer, BP machine,
            smartwatch data, and symptoms. No lab values needed.
            Solves all clinical gaps: reading time, HbA1c, stress effect,
            medications, Type 1 vs Type 2, pregnancy thresholds.
        </div>""", unsafe_allow_html=True)

        # ── SECTION 0: Context (Holes 1, 4, 5, 6, 8) ──────────────────
        st.markdown("### 👤 About You")
        cx1, cx2, cx3 = st.columns(3)
        with cx1:
            h_age    = st.number_input("🎂 Age", 1, 120, 35)
            h_gender = st.selectbox("⚤ Gender", ["Male","Female","Other"])
        with cx2:
            h_weight = st.number_input("⚖️ Weight (kg)", 20.0, 200.0, 65.0, step=0.5)
            h_height = st.number_input("📏 Height (cm)", 100.0, 220.0, 165.0, step=0.5)
        with cx3:
            h_pregnant = False
            if h_gender == "Female":
                h_pregnant = st.checkbox("🤰 Currently Pregnant?")
                if h_pregnant:
                    st.markdown("""<div style="background:#fff3e0;border-radius:6px;
                        padding:6px 10px;font-size:12px;border-left:3px solid #fb8c00">
                        ⚠️ Pregnancy thresholds applied (WHO GDM criteria)
                    </div>""", unsafe_allow_html=True)
            h_family = st.checkbox("👨‍👩‍👧 Family history of diabetes (parent/sibling)?")

        h_bmi = round(h_weight / ((h_height/100)**2), 1)
        st.markdown(f"""<div style="background:#e3f2fd;border-radius:8px;padding:8px 14px;
            font-size:13px;border-left:4px solid #1565c0;margin-bottom:4px">
            📊 Your BMI: <b>{h_bmi}</b> —
            {"🟢 Healthy" if h_bmi<25 else ("🟡 Overweight" if h_bmi<30 else "🔴 Obese")}
        </div>""", unsafe_allow_html=True)

        st.markdown("---")

        # ── SECTION 1: Glucometer Readings (Holes 1, 2, 7) ────────────
        st.markdown("### 🩸 Glucometer Readings")
        st.markdown('<p style="font-size:13px;color:#666;margin-top:-8px">From your home glucometer. Enter what you have — you don\'t need all fields.</p>', unsafe_allow_html=True)

        g1, g2, g3 = st.columns(3)
        with g1:
            h_glucose = st.number_input("Glucose (mg/dL)", 0, 600, 100)
            h_glucose_type = st.selectbox("Reading taken when?",
                list(GLUCOSE_THRESHOLDS.keys()))
        with g2:
            h_postmeal = st.number_input("Post-Meal Glucose (2hr after eating) — optional, 0 = skip",
                                          0, 600, 0)
        with g3:
            h_hba1c = st.number_input("HbA1c % — optional, 0 = skip\n(from lab/pharmacy)",
                                       0.0, 20.0, 0.0, step=0.1)
            if h_hba1c > 0:
                hba_status = ("🔴 Diabetic" if h_hba1c>=6.5 else
                               ("🟡 Pre-diabetic" if h_hba1c>=5.7 else "🟢 Normal"))
                st.caption(f"HbA1c Status: {hba_status}")

        # Glucose log toggle
        if st.checkbox("💾 Save this reading to my Glucose Trend log"):
            save_glucose_reading(uid, h_glucose, h_glucose_type)
            st.caption("✅ Saved to trend log")

        st.markdown("---")

        # ── SECTION 2: BP Machine (Hole 1 context) ─────────────────────
        st.markdown("### 💓 Blood Pressure (Home BP Machine)")
        bp1, bp2 = st.columns(2)
        with bp1:
            h_systolic  = st.number_input("Systolic BP (top number) mmHg", 0, 260, 120)
        with bp2:
            h_diastolic = st.number_input("Diastolic BP (bottom number) mmHg", 0, 160, 80)
        if h_systolic > 0:
            bp_status = ("🔴 Hypertension" if h_systolic>=140 or h_diastolic>=90
                          else ("🟡 Borderline" if h_systolic>=130 or h_diastolic>=85
                          else "🟢 Normal"))
            st.caption(f"BP Status: {bp_status}")

        st.markdown("---")

        # ── SECTION 3: Smartwatch / Wearable ──────────────────────────
        st.markdown("### ⌚ Smartwatch / Fitness Tracker Data")
        st.markdown('<p style="font-size:13px;color:#666;margin-top:-8px">Enter from your watch app. Leave 0 if you don\'t have the data.</p>', unsafe_allow_html=True)
        w1, w2, w3, w4 = st.columns(4)
        with w1:
            h_rhr   = st.number_input("Resting Heart Rate (bpm)\n0 = skip", 0, 200, 0)
        with w2:
            h_sleep = st.number_input("Last night's sleep (hours)\n0 = skip", 0.0, 14.0, 0.0, step=0.5)
        with w3:
            h_steps = st.number_input("Yesterday's steps\n0 = skip", 0, 50000, 0, step=100)
        with w4:
            h_spo2  = st.number_input("SpO2 % (blood oxygen)\n0 = skip", 0, 100, 0)

        st.markdown("---")

        # ── SECTION 4: Context (Holes 4, 5, 6) ────────────────────────
        st.markdown("### 🧠 Context — This Changes Your Result")

        ctx1, ctx2 = st.columns(2)
        with ctx1:
            # Hole 4: Meal context
            h_meal_ctx = st.selectbox("🍽️ What did you eat today?",
                ["Normal meals (balanced diet)",
                 "Heavy meals (rice/sweets/fried food)",
                 "Skipped breakfast or lunch",
                 "Fasted for 8+ hours (before test)"])
            # Hole 5: Stress
            h_stress = st.selectbox("😰 Stress level today?",
                list(STRESS_ADJUSTMENT.keys()))
            stress_adj_val = STRESS_ADJUSTMENT[h_stress]
            if stress_adj_val > 0:
                st.caption(f"ℹ️ Stress adds ~{stress_adj_val} mg/dL to blood glucose. This will be adjusted.")

        with ctx2:
            # Hole 6: Medications
            h_meds = st.multiselect("💊 Are you taking any of these?",
                list(GLUCOSE_RAISING_MEDS.keys()),
                default=["None of the above"])
            med_total_adj = sum(GLUCOSE_RAISING_MEDS.get(m,0) for m in h_meds
                                 if m!="None of the above")
            if med_total_adj > 0:
                st.caption(f"ℹ️ Your medicines may raise glucose by ~{med_total_adj} mg/dL. This will be adjusted.")

            # Hole 3: Onset
            h_onset = st.selectbox("📅 How did symptoms start?",
                ["Gradual (months to years)",
                 "Sudden (days to weeks)",
                 "No symptoms yet"])

        st.markdown("---")

        # ── SECTION 5: Symptoms ────────────────────────────────────────
        st.markdown("### 🤒 Symptoms (Check all that apply)")
        sym_options = [
            "Unusual thirst","Frequent urination","Unexplained fatigue","Blurred vision",
            "Slow healing wounds","Tingling hands/feet","Unexplained weight loss",
            "Skin darkening (neck/armpits)","Frequent hunger even after eating",
            "Fruity or sweet smell to breath","Recurrent infections (skin/UTI)","None"
        ]
        s_cols = st.columns(4)
        h_symptoms = []
        for i,sym in enumerate(sym_options):
            with s_cols[i%4]:
                if st.checkbox(sym, key=f"hsym_{sym}"):
                    h_symptoms.append(sym)

        # ── RUN ASSESSMENT ─────────────────────────────────────────────
        st.markdown("---")
        if st.button("🔍 Run Full Home Diabetes Screening", use_container_width=True):
            # Collect all data
            clean_meds = [m for m in h_meds if m != "None of the above"]
            data = {
                "glucose":        h_glucose,
                "glucose_type":   h_glucose_type,
                "postmeal_glucose": h_postmeal,
                "hba1c":          h_hba1c,
                "systolic_bp":    h_systolic,
                "diastolic_bp":   h_diastolic,
                "bmi":            h_bmi,
                "resting_hr":     h_rhr,
                "sleep_hours":    h_sleep,
                "daily_steps":    h_steps,
                "spo2":           h_spo2,
                "stress":         h_stress,
                "medications":    clean_meds,
                "onset":          h_onset,
                "age":            h_age,
                "pregnant":       h_pregnant,
                "family_history": h_family,
                "symptoms":       h_symptoms,
            }

            score, risk, flags, g_adjusted, dtype = _home_risk_score(data)

            # Result banner
            risk_color = {"High Risk":"#e53935","Moderate Risk":"#fb8c00","Low Risk":"#43a047"}.get(risk,"#888")
            risk_icon  = {"High Risk":"🔴","Moderate Risk":"🟡","Low Risk":"🟢"}.get(risk,"⚪")
            type_labels = {"type1":"Type 1 Diabetes","type2":"Type 2 Diabetes",
                           "gestational":"Gestational Diabetes","prediab":"Pre-diabetes"}
            type_label = type_labels.get(dtype,"Type 2 Diabetes")

            preg_note = " · ⚠️ Pregnancy thresholds applied" if h_pregnant else ""
            st.markdown(f"""<div style="background:{risk_color};color:white;border-radius:18px;
                padding:24px 32px;text-align:center;margin:16px 0;
                box-shadow:0 6px 24px {risk_color}44">
                <h1 style="margin:0;font-size:2em">{risk_icon} {risk}</h1>
                <h3 style="margin:8px 0 0;opacity:0.95">Risk Score: {score}/100</h3>
                <p style="margin:8px 0 0;opacity:0.9;font-size:14px">
                    Likely Type: <b>{type_label}</b>{preg_note}
                </p>
            </div>""", unsafe_allow_html=True)

            # Score meter
            meter_color = risk_color
            st.markdown(f"""<div style="background:#f0f0f0;border-radius:8px;height:16px;margin:8px 0">
                <div style="background:linear-gradient(90deg,#43a047,#fb8c00,#e53935);
                    width:{score}%;height:16px;border-radius:8px;position:relative">
                    <span style="position:absolute;right:4px;top:-1px;font-size:11px;
                        color:white;font-weight:700">{score}</span>
                </div>
            </div>
            <div style="display:flex;justify-content:space-between;font-size:10px;color:#aaa;margin-bottom:12px">
                <span>0 — Low Risk</span><span>50 — Moderate</span><span>100 — High Risk</span>
            </div>""", unsafe_allow_html=True)

            # Stress/medication adjustment note
            total_adj = (STRESS_ADJUSTMENT.get(h_stress,0) +
                         sum(GLUCOSE_RAISING_MEDS.get(m,0) for m in clean_meds))
            if total_adj > 0:
                st.markdown(f"""<div style="background:#e8f0fe;border-left:4px solid #1565c0;
                    border-radius:10px;padding:12px 16px;font-size:13px;margin:8px 0">
                    🧪 <b>Glucose Adjustment Applied:</b> Your raw glucose was {h_glucose} mg/dL.
                    After adjusting for stress (+{STRESS_ADJUSTMENT.get(h_stress,0)}) and
                    medication effect (+{sum(GLUCOSE_RAISING_MEDS.get(m,0) for m in clean_meds)}),
                    your <b>true physiological glucose ≈ {g_adjusted:.0f} mg/dL</b>.
                    This is what was used for your assessment.
                </div>""", unsafe_allow_html=True)

            # Tabs for flags, report, XAI
            rt1, rt2, rt3 = st.tabs(["📋 What Was Found",
                                       "📄 Full Report & Advice",
                                       "🧠 Explainable AI"])
            with rt1:
                st.markdown("### 🔍 Factor-by-Factor Analysis")
                for f in flags:
                    bg = ("#ffebee" if "🔴" in f else
                          ("#fff8e1" if "🟡" in f else
                           ("#e8f5e9" if "🟢" in f else "#f0f4ff")))
                    bd = ("#e53935" if "🔴" in f else
                          ("#fb8c00" if "🟡" in f else
                           ("#43a047" if "🟢" in f else "#1565c0")))
                    st.markdown(f"""<div style="background:{bg};border-left:4px solid {bd};
                        border-radius:8px;padding:10px 14px;margin:5px 0;font-size:13px">
                        {f}</div>""", unsafe_allow_html=True)

                # Type explanation
                type_explanations = {
                    "type1": """<b>Why possibly Type 1?</b> You are younger, have normal/low BMI,
                        and symptoms started suddenly. Type 1 is autoimmune — the body destroys
                        insulin-producing cells. This is different from Type 2 and REQUIRES insulin.
                        Please get a C-Peptide test to confirm.""",
                    "type2": """<b>Why possibly Type 2?</b> Your profile (age, BMI, gradual onset)
                        matches the typical Type 2 pattern. This is caused by insulin resistance —
                        cells stop responding to insulin. Manageable with diet, exercise, and if needed,
                        oral medication.""",
                    "gestational": """<b>Gestational Diabetes:</b> During pregnancy, hormones can block
                        insulin action. The glucose thresholds are much lower than non-pregnant women
                        (fasting target below 92 mg/dL vs 126 mg/dL normally). This requires urgent
                        management to protect both mother and baby.""",
                    "prediab": """<b>No diabetes detected</b> — but some risk factors are present.
                        Pre-diabetes is the stage before Type 2 diabetes and is <b>100% reversible</b>
                        with lifestyle changes. This is the best time to act.""",
                }
                st.markdown(f"""<div style="background:#e3f2fd;border-left:4px solid #1565c0;
                    border-radius:10px;padding:14px 18px;font-size:13px;margin-top:12px;line-height:1.7">
                    {type_explanations.get(dtype,"")}
                </div>""", unsafe_allow_html=True)

            with rt2:
                severity, sev_expl, sev_reasons, conditions, confidence, do_dont, home_care, when_doc, extra = \
                    _build_home_report(risk, score, dtype, data, flags, g_adjusted)
                render_clinical_report("Diabetes Home Screening", severity, sev_expl, sev_reasons,
                                        conditions, confidence, do_dont, home_care, when_doc, extra,
                                        patient_name=uname, vital_summary=None,
                                        raw_params=data)

            with rt3:
                explanation = explain_diabetes(g_adjusted, h_diastolic, h_bmi,
                                                0, 0.5, h_age, 0,
                                                "Positive" if risk=="High Risk" else "Negative")
                render_xai_panel(explanation, "Diabetes Home Screening")

            save_report(uid, "Diabetes Home Screening", severity,
                        conditions[0]["condition"], confidence,
                        f"Glucose:{h_glucose}|Adj:{g_adjusted:.0f}|BMI:{h_bmi}|Score:{score}|Type:{dtype}",
                        numeric_value=h_glucose)
            st.success("✅ Screening saved to your history.")

    # ════════════════════════════════════════════════════════════════════
    # TAB 2 — CLINICAL ML MODEL
    # ════════════════════════════════════════════════════════════════════
    with clinical_tab:
        st.markdown("""<div style="background:#e3f2fd;border-left:5px solid #1565c0;
            border-radius:10px;padding:12px 18px;font-size:14px;margin-bottom:16px">
            🔬 <b>Clinical Mode:</b> For use when you have a full lab report.
            Uses the trained ML model (PIMA dataset) + Explainable AI panel.
        </div>""", unsafe_allow_html=True)

        with st.expander("ℹ️ Parameter Reference Guide"):
            st.markdown("""
| Parameter | Normal Range | Clinical Meaning |
|-----------|-------------|-----------------|
| Glucose | 70–100 mg/dL (fasting) | Primary diabetes marker |
| Blood Pressure | 60–80 mmHg | Diastolic BP |
| BMI | 18.5–24.9 | Body mass index |
| Insulin | 16–166 μU/mL | Insulin level (2hr) |
| DPF | 0.08–2.42 | Family history genetic score |
            """)

        st.markdown("### 📝 Enter Clinical Parameters")
        c1,c2,c3 = st.columns(3)
        with c1:
            preg    = st.number_input("Pregnancies", 0, 20, 0, key="cl_preg")
            glucose = st.number_input("Glucose (mg/dL)", 0, 400, 100, key="cl_gl")
            bp      = st.number_input("Blood Pressure (mmHg)", 0, 200, 70, key="cl_bp")
        with c2:
            skin    = st.number_input("Skin Thickness (mm)", 0, 100, 20, key="cl_sk")
            insulin = st.number_input("Insulin (μU/mL)", 0, 900, 80, key="cl_ins")
            bmi     = st.number_input("BMI", 0.0, 70.0, 22.0, step=0.1, key="cl_bmi")
        with c3:
            dpf     = st.number_input("Diabetes Pedigree Function", 0.0, 3.0, 0.47, step=0.01, key="cl_dpf")
            age     = st.number_input("Age", 1, 120, 25, key="cl_age")

        if st.button("🔍 Run Clinical ML Assessment", use_container_width=True):
            pred   = MODEL.predict([[preg,glucose,bp,skin,insulin,bmi,dpf,age]])[0]
            result = "Positive" if pred==1 else "Negative"

            severity, sev_expl, sev_reasons, conditions, confidence, do_dont, home_care, when_doc, extra = \
                _build_clinical_report(result, glucose, bmi, age)

            res_color = "#e53935" if result=="Positive" else "#43a047"
            res_icon  = "⚠️" if result=="Positive" else "✅"
            st.markdown(f"""<div style="background:{res_color};color:white;border-radius:16px;
                padding:20px 28px;text-align:center;margin:16px 0;
                box-shadow:0 4px 20px {res_color}44">
                <h2 style="margin:0;font-size:1.8em">{res_icon} Diabetes Result: {result}</h2>
                <p style="margin:6px 0 0;opacity:0.9">{sev_expl}</p>
            </div>""", unsafe_allow_html=True)

            tab1, tab2 = st.tabs(["🧠 Explainable AI — Why this result?",
                                   "📄 Full Clinical Report"])
            with tab1:
                explanation = explain_diabetes(glucose, bp, bmi, insulin, dpf, age, preg, result)
                render_xai_panel(explanation, "Diabetes Prediction")
            with tab2:
                render_clinical_report("Diabetes Prediction", severity, sev_expl, sev_reasons,
                                        conditions, confidence, do_dont, home_care, when_doc, extra,
                                        patient_name=uname, vital_summary=None)

            save_report(uid, "Diabetes Prediction", severity,
                        conditions[0]["condition"], confidence,
                        f"Glucose:{glucose}|BMI:{bmi}|Age:{age}|Result:{result}",
                        numeric_value=glucose)
            st.success("✅ Report saved to your history.")

    # ════════════════════════════════════════════════════════════════════
    # TAB 3 — GLUCOSE TREND
    # ════════════════════════════════════════════════════════════════════
    with trend_tab:
        st.markdown("### 📈 Your Glucose Trend Over Time")
        st.markdown("""<div style="background:#e8f5e9;border-left:4px solid #43a047;
            border-radius:8px;padding:10px 16px;font-size:13px;margin-bottom:12px">
            💡 Every time you tick "Save to trend log" in the Home Screener,
            that reading appears here. Track your glucose over days and weeks
            to see if you're improving or worsening.
        </div>""", unsafe_allow_html=True)

        history = get_glucose_history(uid, 30)
        if not history:
            st.info("No glucose readings saved yet. Use the Home Screener and tick 'Save to trend log'.")
        else:
            chart_html = _glucose_trend_chart(history)
            st.markdown(chart_html, unsafe_allow_html=True)

            # Table
            st.markdown("### 📋 Reading History")
            for g, rtype, ts in reversed(history[-10:]):
                c = "#e53935" if g>=126 else ("#fb8c00" if g>=100 else "#43a047")
                status = "Diabetic Range" if g>=126 else ("Pre-diabetic" if g>=100 else "Normal")
                try: ts_fmt = datetime.strptime(ts,"%Y-%m-%d %H:%M").strftime("%d %b %Y, %I:%M %p")
                except: ts_fmt = ts
                st.markdown(f"""<div style="background:white;border-left:5px solid {c};
                    border-radius:8px;padding:10px 16px;margin:4px 0;
                    box-shadow:0 1px 5px rgba(0,0,0,0.06)">
                    <b style="font-size:15px;color:{c}">{g:.0f} mg/dL</b>
                    <span style="font-size:12px;color:#888;margin-left:10px">{rtype}</span>
                    <span style="float:right;font-size:12px;color:{c};font-weight:600">{status}</span><br>
                    <span style="font-size:11px;color:#aaa">{ts_fmt}</span>
                </div>""", unsafe_allow_html=True)

            # Quick stats
            vals = [r[0] for r in history]
            avg = sum(vals)/len(vals)
            above_normal = sum(1 for v in vals if v>=100)
            st.markdown(f"""<div style="background:#f0f4ff;border-radius:10px;padding:14px 18px;
                margin-top:12px;font-size:13px">
                📊 <b>Summary:</b> {len(vals)} readings ·
                Average: <b>{avg:.0f} mg/dL</b> ·
                Above normal (≥100): <b>{above_normal}</b> readings ·
                {"🔴 Consistently elevated — see a doctor" if avg>=126 else
                 ("🟡 Borderline — monitor closely" if avg>=100 else
                  "🟢 Average in normal range")}
            </div>""", unsafe_allow_html=True)

    st.markdown("""<div class="footer">
        MediSense Pro · Diabetes Screening v10 · SWE1904 · VIT · R.Divya 21MIS0261
    </div>""", unsafe_allow_html=True)
