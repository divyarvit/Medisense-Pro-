"""
Thyroid Disorder Module — MediSense Pro v11
Two conditions screened:
  🔵 Hypothyroidism — underactive thyroid (slow, tired, cold, weight gain)
  🔴 Hyperthyroidism — overactive thyroid (fast, anxious, hot, weight loss)

Two modes:
  🏠 Symptom Screener  — 16 self-observable questions, zero devices needed
  🔬 TSH Interpreter   — Enter TSH (and optional T3/T4) → full interpretation

Clinical basis: ATA (American Thyroid Association) guidelines
India context: 4.2 crore Indians affected. Women 5-8x more likely than men.
Most go undiagnosed for years — symptoms attributed to stress, aging, menopause.
"""
import streamlit as st, math
from utils.report_renderer import render_clinical_report
from utils.database import save_report

# ─── SYMPTOM SCREENER SCORING ─────────────────────────────────────────────────
def _thyroid_score(data):
    hypo_score = 0   # underactive
    hyper_score = 0  # overactive
    flags = []

    age     = data["age"]
    sex     = data["sex"]
    family  = data["family_history"]
    autoim  = data["autoimmune_history"]
    preg    = data["pregnancy_related"]
    iodine  = data["iodine_area"]
    hypo_s  = data["hypo_symptoms"]
    hyper_s = data["hyper_symptoms"]
    neck    = data["neck_swelling"]
    rhr     = data["resting_hr"]

    # ── Risk Factors ──────────────────────────────────────────────────
    if sex == "Female":
        hypo_score  += 6; hyper_score += 4
        flags.append("🟡 Female sex — 5-8x higher thyroid disorder risk than male")
    if age >= 60:
        hypo_score  += 6
        flags.append("🟡 Age 60+ — hypothyroidism very common, often missed as 'just aging'")
    elif age >= 40:
        hypo_score  += 3
        flags.append("🟡 Age 40+ — thyroid screening recommended for all women")

    if family in ["Yes — parent or sibling with thyroid disorder",
                   "Yes — extended family with thyroid disorder"]:
        hypo_score  += 7; hyper_score += 5
        flags.append("🔴 Family history of thyroid disorder — strong genetic risk")

    if autoim == "Yes — Type 1 diabetes, Rheumatoid Arthritis, Lupus, Vitiligo, or Celiac":
        hypo_score  += 8; hyper_score += 5
        flags.append("🔴 Autoimmune condition — Hashimoto's (hypo) and Graves' (hyper) are autoimmune")

    if preg in ["Currently pregnant", "Delivered a baby in the last 12 months"]:
        hypo_score  += 7; hyper_score += 4
        flags.append("🔴 Pregnancy/postpartum — postpartum thyroiditis affects 5-10% of women")

    if iodine == "Yes — inland/rural area, limited seafood or iodized salt":
        hypo_score  += 5
        flags.append("🟡 Iodine deficiency area — major cause of hypothyroidism in rural India")

    # ── Hypothyroid Symptoms ──────────────────────────────────────────
    hypo_symptom_scores = {
        "Persistent fatigue — exhausted even after 8+ hours of sleep": 7,
        "Unexplained weight gain — gaining weight despite no diet change": 7,
        "Always feeling cold — feel cold when others are comfortable": 7,
        "Dry skin — skin is rough, flaky, and does not respond to moisturiser": 5,
        "Hair thinning or hair falling out more than usual": 6,
        "Constipation — difficult bowel movements, infrequent": 5,
        "Depression — low mood, lack of interest, started gradually": 5,
        "Slow thinking or memory problems — brain fog": 5,
        "Puffy face especially in the morning — around eyes": 4,
        "Hoarse or slow voice": 4,
        "Muscle weakness — difficulty climbing stairs or lifting": 4,
        "Irregular or heavier periods (women)": 5,
        "Slow resting heart rate — below 60 bpm": 4,
    }
    hypo_total = 0
    for sym in hypo_s:
        pts = hypo_symptom_scores.get(sym, 0)
        hypo_total += pts; hypo_score += pts
        if pts >= 6:
            flags.append(f"🔴 Hypo symptom: {sym}")
        elif pts >= 4:
            flags.append(f"🟡 Hypo symptom: {sym}")

    # ── Hyperthyroid Symptoms ─────────────────────────────────────────
    hyper_symptom_scores = {
        "Unexplained weight loss — losing weight despite eating normally or more": 8,
        "Always feeling hot — feel overheated when others are comfortable": 7,
        "Rapid or irregular heartbeat — palpitations, heart racing": 8,
        "Anxiety, nervousness, or irritability that feels unusual": 7,
        "Trembling hands — fine hand tremor": 7,
        "Excessive sweating without exertion": 6,
        "Difficulty sleeping — mind racing at night": 5,
        "Frequent bowel movements or loose stools": 5,
        "Muscle weakness — legs feel weak when climbing stairs": 4,
        "Eyes look bigger or feel irritated / dry / prominent": 6,
        "Irregular or lighter periods (women)": 5,
        "Fast resting heart rate — above 90-100 bpm": 7,
    }
    hyper_total = 0
    for sym in hyper_s:
        pts = hyper_symptom_scores.get(sym, 0)
        hyper_total += pts; hyper_score += pts
        if pts >= 6:
            flags.append(f"🔴 Hyper symptom: {sym}")
        elif pts >= 4:
            flags.append(f"🟡 Hyper symptom: {sym}")

    # ── Neck Swelling ─────────────────────────────────────────────────
    if neck == "Yes — visible or feel a lump/swelling in front of neck":
        hypo_score += 8; hyper_score += 8
        flags.append("🔴 Visible neck swelling/goitre — direct thyroid gland enlargement sign. See doctor immediately.")
    elif neck == "Yes — only when swallowing, slight fullness":
        hypo_score += 4; hyper_score += 4
        flags.append("🟡 Possible goitre — noticeable on swallowing")

    # ── Heart Rate Context ────────────────────────────────────────────
    if rhr > 0:
        if rhr > 100:
            hyper_score += 8
            flags.append(f"🔴 Resting HR {rhr} bpm — Tachycardia above 100 is classic hyperthyroid sign")
        elif rhr > 90:
            hyper_score += 4
            flags.append(f"🟡 Resting HR {rhr} bpm — Elevated, monitor for hyperthyroid pattern")
        elif rhr < 55:
            hypo_score += 6
            flags.append(f"🔴 Resting HR {rhr} bpm — Bradycardia below 55 is classic hypothyroid sign")
        elif rhr < 65:
            hypo_score += 3
            flags.append(f"🟡 Resting HR {rhr} bpm — Slow, possible hypothyroid signal")

    # ── Determine dominant condition ──────────────────────────────────
    hypo_score = min(hypo_score, 100)
    hyper_score = min(hyper_score, 100)

    if hypo_score >= 40 and hypo_score > hyper_score + 10:
        condition = "Hypothyroidism"
        score = hypo_score
        flags.append(f"🔵 Pattern strongly suggests: Hypothyroidism (underactive thyroid)")
    elif hyper_score >= 40 and hyper_score > hypo_score + 10:
        condition = "Hyperthyroidism"
        score = hyper_score
        flags.append(f"🔴 Pattern strongly suggests: Hyperthyroidism (overactive thyroid)")
    elif hypo_score >= 35 or hyper_score >= 35:
        condition = "Thyroid Disorder — Type Unclear"
        score = max(hypo_score, hyper_score)
        flags.append("🟡 Thyroid symptoms present but pattern unclear — TSH test needed to determine type")
    else:
        condition = "Low Thyroid Risk"
        score = max(hypo_score, hyper_score)

    if score >= 50:   risk = "High Risk"
    elif score >= 28: risk = "Moderate Risk"
    else:             risk = "Low Risk"

    return score, risk, condition, flags, hypo_score, hyper_score

def _build_thyroid_report(risk, score, condition, hypo_s, hyper_s):
    sev_map = {"High Risk": "Severe", "Moderate Risk": "Moderate", "Low Risk": "Mild"}
    severity = sev_map.get(risk, "Moderate")

    is_hypo  = "Hypo" in condition
    is_hyper = "Hyper" in condition

    if risk == "High Risk":
        if is_hypo:
            conditions = [
                {"condition": "Hypothyroidism — High Likelihood",
                 "probability": min(35 + score * 0.45, 85),
                 "description": "Underactive thyroid — insufficient thyroid hormone production.",
                 "icd": "E03.9"},
                {"condition": "Hashimoto's Thyroiditis",
                 "probability": 10.0,
                 "description": "Autoimmune destruction of thyroid — most common cause of hypothyroidism.",
                 "icd": "E06.3"},
                {"condition": "Subclinical Hypothyroidism",
                 "probability": 5.0,
                 "description": "TSH elevated but T4 still normal — early stage.",
                 "icd": "E02"},
            ]
            sev_expl = "Multiple hypothyroidism symptoms detected. TSH blood test strongly recommended."
            do_list = [
                "Get a TSH blood test immediately — costs ₹150 at any diagnostic lab",
                "Also request T3 and T4 levels with the same blood draw",
                "See an Endocrinologist or physician within 2 weeks",
                "If on Levothyroxine — do not skip doses, take on empty stomach",
                "Eat iodine-rich foods — iodised salt, fish, dairy",
                "Regular exercise even when tired — improves metabolism",
                "Get an annual thyroid function test from now on",
            ]
            dont_list = [
                "Do not take iron or calcium supplements within 4 hours of thyroid medication",
                "Avoid raw cruciferous vegetables in excess (cabbage, cauliflower) — interfere with thyroid",
                "Do not ignore fatigue and weight gain as 'just stress' — get tested",
                "Do not stop thyroid medication without doctor guidance",
            ]
        else:
            conditions = [
                {"condition": "Hyperthyroidism — High Likelihood",
                 "probability": min(35 + score * 0.45, 85),
                 "description": "Overactive thyroid — excessive thyroid hormone production.",
                 "icd": "E05.9"},
                {"condition": "Graves' Disease",
                 "probability": 12.0,
                 "description": "Autoimmune hyperthyroidism — most common cause.",
                 "icd": "E05.0"},
                {"condition": "Toxic Multinodular Goitre",
                 "probability": 3.0,
                 "description": "Multiple nodules producing excess hormone.",
                 "icd": "E05.2"},
            ]
            sev_expl = "Multiple hyperthyroidism symptoms detected. TSH blood test urgently recommended."
            do_list = [
                "🚨 Get a TSH blood test urgently — rapid heart rate + hyperthyroid can cause cardiac complications",
                "See an Endocrinologist within 1 week",
                "Monitor resting heart rate daily",
                "Rest and avoid strenuous exercise until evaluated — hyperthyroid stresses the heart",
                "Eat calcium-rich foods — hyperthyroidism weakens bones",
                "Avoid iodine-rich foods and iodine supplements until diagnosis confirmed",
            ]
            dont_list = [
                "Do NOT take iodine supplements — can worsen hyperthyroidism",
                "Do not take stimulants — caffeine, energy drinks worsen palpitations",
                "Do NOT ignore rapid heartbeat — see a doctor urgently",
                "Avoid foods very high in iodine (seaweed, kelp) until treatment starts",
            ]
        when_doc = [
            "🚨 Within 1 week — Endocrinologist or physician urgently",
            "Immediately if rapid heartbeat becomes severe or irregular",
            "Immediately if visible neck swelling grows",
        ]
        specialist = "Endocrinologist — URGENT"
    elif risk == "Moderate Risk":
        conditions = [
            {"condition": f"Possible {'Hypothyroidism' if is_hypo else 'Hyperthyroidism' if is_hyper else 'Thyroid Disorder'}",
             "probability": min(20 + score * 0.4, 65),
             "description": "Several thyroid symptoms present. TSH test will clarify.",
             "icd": "E07.9"},
            {"condition": "Subclinical Thyroid Disorder",
             "probability": 20.0,
             "description": "Mild thyroid dysfunction — symptoms present but may be early stage.",
             "icd": "E02"},
            {"condition": "Non-Thyroid Causes",
             "probability": 15.0,
             "description": "Some symptoms overlap with stress, anaemia, or menopause.",
             "icd": "R53"},
        ]
        sev_expl = "Several thyroid disorder signs present. A TSH blood test will confirm or rule out."
        do_list = [
            "Get a TSH blood test within 2-4 weeks — costs ₹150",
            "See a physician within 4-6 weeks",
            "Track symptoms — note if they are getting worse or better",
        ]
        dont_list = [
            "Do not self-medicate with thyroid supplements",
            "Do not ignore persistent fatigue and weight changes",
        ]
        when_doc = [
            "Within 4-6 weeks for TSH test and physician review",
            "Sooner if palpitations or neck swelling develops",
        ]
        specialist = "Physician / Endocrinologist (within 4-6 weeks)"
    else:
        conditions = [
            {"condition": "Low Thyroid Disorder Risk Currently",
             "probability": 85.0,
             "description": "No significant thyroid symptoms identified.",
             "icd": "Z03.89"},
            {"condition": "General Endocrine Health",
             "probability": 10.0,
             "description": "Normal range for thyroid-related symptoms.",
             "icd": "Z13.88"},
            {"condition": "Preventive Monitoring",
             "probability": 5.0,
             "description": "Age and risk-based monitoring recommended.",
             "icd": "Z13.88"},
        ]
        sev_expl = "No significant thyroid disorder symptoms identified at this time."
        do_list = [
            "Use iodised salt — most important thyroid prevention habit",
            "Annual TSH test for all women after age 40",
            "Eat thyroid-supportive diet: seafood, dairy, nuts, eggs",
        ]
        dont_list = [
            "Do not ignore new fatigue, weight changes, or neck swelling",
            "Avoid iodine deficiency — use iodised salt always",
        ]
        when_doc = [
            "Annual checkup with TSH after age 40 for women",
            "If fatigue, weight change, or neck swelling develops",
        ]
        specialist = "General Physician (annual checkup)"

    confidence = min(38 + score * 0.46, 85)
    home_care = [
        "Use iodised salt at every meal — most important thyroid prevention in India",
        "Take thyroid medication (if prescribed) on empty stomach, 30 min before food",
        "Never take iron, calcium, or antacids within 4 hours of thyroid medication",
        "Track weight weekly — sudden gain (hypo) or loss (hyper) needs doctor attention",
        "Monitor resting heart rate — fast (hyper) or slow (hypo) are key signals",
        "Thyroid Foundation of India helpline for support and guidance",
    ]
    sev_reasons = [
        f"Dominant pattern: {condition}",
        f"Symptom score: {score}/100",
    ]
    do_dont = {"do": do_list, "dont": dont_list}
    extra = f"**Pattern:** {condition} · **Refer:** {specialist}"
    return severity, sev_expl, sev_reasons, conditions, confidence, do_dont, home_care, when_doc, extra

def _interpret_tsh(tsh, t3=None, t4=None, symptoms=None):
    """Interpret TSH value with optional T3/T4"""
    if tsh < 0.1:
        status = "Severely Suppressed — Overt Hyperthyroidism"
        color  = "#b71c1c"
        icon   = "🔴"
        detail = (f"TSH of {tsh} is severely suppressed. This is consistent with overt "
                  f"hyperthyroidism — the thyroid is overproducing hormones. "
                  f"This requires urgent endocrinologist evaluation and treatment.")
        urgency = "🚨 See Endocrinologist URGENTLY"
        icd = "E05.9"
    elif tsh < 0.4:
        status = "Low — Subclinical or Overt Hyperthyroidism"
        color  = "#e53935"
        icon   = "🔴"
        detail = (f"TSH of {tsh} is below normal range (0.4–4.0). Low TSH means "
                  f"the pituitary gland is reducing its signal because thyroid hormone "
                  f"levels are too high. T3/T4 test needed to confirm overt vs subclinical.")
        urgency = "See Endocrinologist within 1 week"
        icd = "E05.90"
    elif tsh <= 4.0:
        status = "Normal"
        color  = "#43a047"
        icon   = "🟢"
        detail = (f"TSH of {tsh} is within the normal range (0.4–4.0 mIU/L). "
                  f"Thyroid function is normal. Symptoms, if present, are likely from another cause.")
        urgency = "No urgent action needed"
        icd = "Z03.89"
    elif tsh <= 10.0:
        status = "Elevated — Subclinical Hypothyroidism"
        color  = "#fb8c00"
        icon   = "🟡"
        detail = (f"TSH of {tsh} is elevated above 4.0. This is subclinical hypothyroidism — "
                  f"the thyroid is struggling and the pituitary is sending stronger signals. "
                  f"T4 may still be normal. Treatment decision depends on symptoms and T4 level.")
        urgency = "See Physician within 2-4 weeks"
        icd = "E02"
    elif tsh <= 20.0:
        status = "High — Hypothyroidism"
        color  = "#e53935"
        icon   = "🔴"
        detail = (f"TSH of {tsh} is significantly elevated. This confirms Hypothyroidism — "
                  f"the thyroid is underproducing hormones. Treatment with Levothyroxine is "
                  f"typically recommended at this level.")
        urgency = "See Endocrinologist within 1 week"
        icd = "E03.9"
    else:
        status = "Very High — Overt Hypothyroidism"
        color  = "#b71c1c"
        icon   = "🔴"
        detail = (f"TSH of {tsh} is severely elevated. This confirms overt Hypothyroidism. "
                  f"Immediate treatment is required. Check for Hashimoto's thyroiditis "
                  f"with Anti-TPO antibody test.")
        urgency = "🚨 See Endocrinologist URGENTLY"
        icd = "E03.9"

    return status, color, icon, detail, urgency, icd

# ─── MAIN SHOW ────────────────────────────────────────────────────────────────
def show():
    uid   = st.session_state.user_id
    uname = st.session_state.get("full_name", "Patient")

    st.markdown("""<div class="main-header">
        <h1>🦋 Thyroid Disorder Assessment</h1>
        <p>Hypothyroidism · Hyperthyroidism · TSH interpretation · India's most under-diagnosed condition</p>
    </div>""", unsafe_allow_html=True)

    st.markdown("""<div style="background:#f3e5f5;border-left:5px solid #6a1b9a;
        border-radius:10px;padding:12px 18px;font-size:13px;margin-bottom:16px">
        🦋 <b>4.2 crore Indians have thyroid disorders — most are undiagnosed.</b>
        Women are 5-8x more likely than men. Symptoms like fatigue, weight change,
        and mood shifts are typically dismissed as stress or aging for years.
        A single TSH blood test (₹150) gives a near-definitive answer.
    </div>""", unsafe_allow_html=True)

    sym_tab, tsh_tab = st.tabs([
        "🏠 Symptom Screener — Zero Devices Needed",
        "🔬 TSH Interpreter — Enter Your Blood Test Value",
    ])

    # ════════════════════════════════════════════════════════════════════
    # TAB 1 — SYMPTOM SCREENER
    # ════════════════════════════════════════════════════════════════════
    with sym_tab:
        st.markdown("""<div style="background:#e8f5e9;border-left:5px solid #43a047;
            border-radius:10px;padding:12px 18px;font-size:13px;margin-bottom:16px">
            🏠 <b>The easiest module in MediSense Pro.</b> Every question is about how
            you feel and what you notice. No devices. No lab tests. No technical knowledge.
            Just honest answers. This is the closest thing to a free thyroid test you can get.
        </div>""", unsafe_allow_html=True)

        # ── About You ─────────────────────────────────────────────────
        st.markdown("### 👤 About You")
        ab1, ab2, ab3 = st.columns(3)
        with ab1:
            t_age = st.number_input("🎂 Age", 18, 100, 40, key="t_age")
            t_sex = st.selectbox("⚤ Sex", ["Female", "Male"], key="t_sex")
        with ab2:
            t_family = st.selectbox("👨‍👩‍👧 Family History of Thyroid Disorder",
                ["None / Not known",
                 "Yes — extended family with thyroid disorder",
                 "Yes — parent or sibling with thyroid disorder"])
            t_autoim = st.selectbox("🛡️ Autoimmune Condition?",
                ["None",
                 "Yes — Type 1 diabetes, Rheumatoid Arthritis, Lupus, Vitiligo, or Celiac"])
        with ab3:
            t_preg = st.selectbox("🤰 Pregnancy / Recent Delivery?",
                ["Not applicable",
                 "Currently pregnant",
                 "Delivered a baby in the last 12 months",
                 "History of thyroid during previous pregnancy"])
            t_iodine = st.selectbox("🧂 Location / Diet",
                ["City — iodised salt used regularly",
                 "Yes — inland/rural area, limited seafood or iodized salt"])

        st.markdown("---")

        # ── Neck Check ────────────────────────────────────────────────
        st.markdown("### 🔍 Quick Self-Check — Look at Your Neck")
        st.markdown("""<div style="background:#e3f2fd;border-left:4px solid #1565c0;
            border-radius:8px;padding:10px 14px;font-size:13px;margin-bottom:10px">
            💡 <b>How to check:</b> Stand in front of a mirror. Tilt your head back slightly.
            Swallow a mouthful of water. Watch the area just below your Adam's apple.
            Any bulging or asymmetry means possible thyroid enlargement.
        </div>""", unsafe_allow_html=True)

        t_neck = st.selectbox("What do you see/feel in the front of your neck?",
            ["Nothing unusual",
             "Yes — only when swallowing, slight fullness",
             "Yes — visible or feel a lump/swelling in front of neck"])

        # Optional HR
        t_rhr = st.number_input("⌚ Resting Heart Rate (bpm) from smartwatch — 0 to skip",
                                 0, 200, 0, key="t_rhr")

        st.markdown("---")

        # ── Hypothyroid Symptoms ──────────────────────────────────────
        st.markdown("### 🔵 Underactive Thyroid Symptoms (Hypothyroidism)")
        st.markdown("""<div style="background:#e8eaf6;border-left:4px solid #3949ab;
            border-radius:8px;padding:8px 14px;font-size:13px;margin-bottom:8px">
            🔵 Hypothyroidism = thyroid produces too <b>little</b> hormone → everything slows down.
            Classic pattern: <b>tired · cold · weight gain · hair loss · constipated · depressed</b>
        </div>""", unsafe_allow_html=True)

        hypo_opts = [
            "Persistent fatigue — exhausted even after 8+ hours of sleep",
            "Unexplained weight gain — gaining weight despite no diet change",
            "Always feeling cold — feel cold when others are comfortable",
            "Dry skin — skin is rough, flaky, and does not respond to moisturiser",
            "Hair thinning or hair falling out more than usual",
            "Constipation — difficult bowel movements, infrequent",
            "Depression — low mood, lack of interest, started gradually",
            "Slow thinking or memory problems — brain fog",
            "Puffy face especially in the morning — around eyes",
            "Hoarse or slow voice",
            "Muscle weakness — difficulty climbing stairs or lifting",
            "Irregular or heavier periods (women)",
            "Slow resting heart rate — below 60 bpm",
            "None of the above",
        ]
        hc = st.columns(2)
        t_hypo = []
        for i, sym in enumerate(hypo_opts):
            with hc[i % 2]:
                if st.checkbox(sym, key=f"hypo_{i}"):
                    t_hypo.append(sym)

        st.markdown("---")

        # ── Hyperthyroid Symptoms ─────────────────────────────────────
        st.markdown("### 🔴 Overactive Thyroid Symptoms (Hyperthyroidism)")
        st.markdown("""<div style="background:#ffebee;border-left:4px solid #e53935;
            border-radius:8px;padding:8px 14px;font-size:13px;margin-bottom:8px">
            🔴 Hyperthyroidism = thyroid produces too <b>much</b> hormone → everything speeds up.
            Classic pattern: <b>anxious · hot · weight loss · fast heart · trembling · can't sleep</b>
        </div>""", unsafe_allow_html=True)

        hyper_opts = [
            "Unexplained weight loss — losing weight despite eating normally or more",
            "Always feeling hot — feel overheated when others are comfortable",
            "Rapid or irregular heartbeat — palpitations, heart racing",
            "Anxiety, nervousness, or irritability that feels unusual",
            "Trembling hands — fine hand tremor",
            "Excessive sweating without exertion",
            "Difficulty sleeping — mind racing at night",
            "Frequent bowel movements or loose stools",
            "Muscle weakness — legs feel weak when climbing stairs",
            "Eyes look bigger or feel irritated / dry / prominent",
            "Irregular or lighter periods (women)",
            "Fast resting heart rate — above 90-100 bpm",
            "None of the above",
        ]
        hrc = st.columns(2)
        t_hyper = []
        for i, sym in enumerate(hyper_opts):
            with hrc[i % 2]:
                if st.checkbox(sym, key=f"hyper_{i}"):
                    t_hyper.append(sym)

        st.markdown("---")

        if st.button("🔍 Run Thyroid Screening", use_container_width=True, key="t_sym_btn"):
            data = {
                "age": t_age, "sex": t_sex,
                "family_history": t_family, "autoimmune_history": t_autoim,
                "pregnancy_related": t_preg, "iodine_area": t_iodine,
                "hypo_symptoms": t_hypo, "hyper_symptoms": t_hyper,
                "neck_swelling": t_neck, "resting_hr": t_rhr,
            }
            score, risk, condition, flags, hypo_s, hyper_s = _thyroid_score(data)

            is_hypo  = "Hypo" in condition
            is_hyper = "Hyper" in condition
            rc = {"High Risk":"#e53935","Moderate Risk":"#fb8c00","Low Risk":"#43a047"}.get(risk)
            ri = {"High Risk":"🚨","Moderate Risk":"⚠️","Low Risk":"✅"}.get(risk)
            cond_color = "#1565c0" if is_hypo else ("#e53935" if is_hyper else "#6a1b9a")

            st.markdown(f"""<div style="background:{rc};color:white;border-radius:16px;
                padding:22px 32px;text-align:center;margin:12px 0;
                box-shadow:0 6px 24px {rc}44">
                <h1 style="margin:0;font-size:2em">{ri} {risk}</h1>
                <h3 style="margin:8px 0 0;opacity:0.95">{condition}</h3>
                <p style="margin:6px 0 0;opacity:0.85;font-size:13px">
                    Symptom Score: {score}/100
                </p>
            </div>""", unsafe_allow_html=True)

            # Score comparison bar
            if hypo_s > 0 or hyper_s > 0:
                st.markdown(f"""<div style="background:#f8f9fa;border-radius:10px;
                    padding:14px 18px;margin:10px 0;font-size:13px;border:1px solid #e0e0e0">
                    <b>Pattern Analysis:</b><br>
                    🔵 Hypothyroid pattern score: <b>{hypo_s}/100</b>
                    &nbsp;&nbsp;|&nbsp;&nbsp;
                    🔴 Hyperthyroid pattern score: <b>{hyper_s}/100</b><br>
                    <div style="display:flex;gap:8px;margin-top:8px">
                        <div style="flex:1">
                            <div style="font-size:11px;color:#3949ab;margin-bottom:2px">Hypo</div>
                            <div style="background:#e0e0e0;border-radius:4px;height:8px">
                                <div style="background:#3949ab;width:{min(hypo_s,100)}%;height:8px;border-radius:4px"></div>
                            </div>
                        </div>
                        <div style="flex:1">
                            <div style="font-size:11px;color:#e53935;margin-bottom:2px">Hyper</div>
                            <div style="background:#e0e0e0;border-radius:4px;height:8px">
                                <div style="background:#e53935;width:{min(hyper_s,100)}%;height:8px;border-radius:4px"></div>
                            </div>
                        </div>
                    </div>
                </div>""", unsafe_allow_html=True)

            # Neck swelling flag
            if "visible or feel a lump" in t_neck:
                st.markdown("""<div style="background:#b71c1c;color:white;border-radius:10px;
                    padding:12px 18px;font-size:13px;margin:8px 0">
                    🚨 <b>Visible neck swelling/goitre detected.</b>
                    This is a direct sign of thyroid gland enlargement.
                    See a doctor immediately — even if you feel no other symptoms.
                    Goitres can sometimes affect breathing or swallowing.
                </div>""", unsafe_allow_html=True)

            # TSH suggestion
            st.markdown(f"""<div style="background:#e8f5e9;border-left:5px solid #43a047;
                border-radius:10px;padding:12px 18px;font-size:13px;margin:8px 0">
                💡 <b>Next Step:</b> A single <b>TSH blood test</b> (₹150 at any lab)
                will confirm or rule out thyroid disorder. Use the <b>TSH Interpreter tab</b>
                to understand your result once you have it.
                {'Ask for Anti-TPO antibody test too — checks for Hashimoto&#39;s.' if is_hypo else
                 'Ask for T3/T4 along with TSH — helps confirm hyperthyroid type.' if is_hyper else ''}
            </div>""", unsafe_allow_html=True)

            r1, r2 = st.tabs(["📋 Factor Analysis", "📄 Full Report"])
            with r1:
                for f in flags:
                    bg = ("#ffebee" if "🔴" in f else
                          "#e8eaf6" if "🔵" in f else
                          "#fff8e1" if "🟡" in f else "#e8f5e9")
                    bd = ("#e53935" if "🔴" in f else
                          "#3949ab" if "🔵" in f else
                          "#fb8c00" if "🟡" in f else "#43a047")
                    st.markdown(f"""<div style="background:{bg};border-left:4px solid {bd};
                        border-radius:8px;padding:9px 14px;margin:4px 0;font-size:13px">{f}</div>""",
                        unsafe_allow_html=True)
            with r2:
                sev, se, sr, cond_list, conf, dd, hc_care, wd, ex = \
                    _build_thyroid_report(risk, score, condition, hypo_s, hyper_s)
                render_clinical_report("Thyroid Disorder Screening", sev, se, sr, cond_list, conf,
                                        dd, hc_care, wd, ex, patient_name=uname)

            save_report(uid, "Thyroid Screening", sev,
                        condition, conf,
                        f"Age:{t_age}|Sex:{t_sex}|Score:{score}|Pattern:{condition}|Hypo:{hypo_s}|Hyper:{hyper_s}",
                        numeric_value=float(score))
            st.success("✅ Assessment saved to your history.")

    # ════════════════════════════════════════════════════════════════════
    # TAB 2 — TSH INTERPRETER
    # ════════════════════════════════════════════════════════════════════
    with tsh_tab:
        st.markdown("""<div style="background:#e3f2fd;border-left:5px solid #1565c0;
            border-radius:10px;padding:12px 18px;font-size:13px;margin-bottom:16px">
            🔬 <b>For patients who have done a thyroid blood test.</b>
            Enter your TSH value and the app explains exactly what it means,
            what your risk level is, and what to do next. TSH test costs ₹150
            at any diagnostic lab — no doctor prescription needed in most states.
        </div>""", unsafe_allow_html=True)

        st.markdown("""<div style="background:#f8f9fa;border-radius:10px;padding:14px 18px;
            font-size:13px;border:1px solid #e0e0e0;margin-bottom:16px">
            <b>TSH Reference Ranges:</b><br>
            🟢 Normal: 0.4 – 4.0 mIU/L &nbsp;|&nbsp;
            🔴 Low (&lt;0.4): Possible Hyperthyroidism &nbsp;|&nbsp;
            🟡 Slightly High (4–10): Subclinical Hypothyroidism &nbsp;|&nbsp;
            🔴 High (&gt;10): Hypothyroidism &nbsp;|&nbsp;
            🔴 Very High (&gt;20): Overt Hypothyroidism<br>
            <i>Note: Some labs use 0.5–5.0. Always compare with your lab's reference range.</i>
        </div>""", unsafe_allow_html=True)

        ti1, ti2 = st.columns(2)
        with ti1:
            tsh_val = st.number_input("🧪 TSH (mIU/L)", 0.001, 150.0, 2.5,
                                       step=0.1, format="%.3f",
                                       help="From your blood test report. Normal: 0.4–4.0 mIU/L")
            t3_val  = st.number_input("🧪 T3 (pg/mL or pmol/L) — 0 to skip",
                                       0.0, 50.0, 0.0, step=0.1,
                                       help="Free T3 — Normal: 2.3–4.2 pg/mL")
        with ti2:
            t4_val  = st.number_input("🧪 Free T4 (ng/dL or pmol/L) — 0 to skip",
                                       0.0, 10.0, 0.0, step=0.01,
                                       help="Free T4 — Normal: 0.8–1.8 ng/dL")
            tsh_age = st.number_input("🎂 Age (for context)", 18, 100, 40, key="tsh_age")
            tsh_sex = st.selectbox("⚤ Sex", ["Female", "Male"], key="tsh_sex")

        if tsh_val > 0:
            status, color, icon, detail, urgency, icd = _interpret_tsh(tsh_val, t3_val, t4_val)

            st.markdown(f"""<div style="background:{color};color:white;border-radius:14px;
                padding:18px 28px;text-align:center;margin:14px 0">
                <h2 style="margin:0">{icon} TSH {tsh_val} mIU/L</h2>
                <h3 style="margin:8px 0 0;opacity:0.95">{status}</h3>
                <p style="margin:8px 0 0;font-size:13px;opacity:0.9">{urgency}</p>
            </div>""", unsafe_allow_html=True)

            st.markdown(f"""<div style="background:#f8f9fa;border-radius:10px;padding:14px 18px;
                font-size:13px;border-left:4px solid {color};margin:8px 0">
                {detail}
            </div>""", unsafe_allow_html=True)

            # T3/T4 interpretation
            if t4_val > 0:
                t4_status = ("🟢 Normal" if 0.8 <= t4_val <= 1.8 else
                              "🔴 Low — confirms Hypothyroidism" if t4_val < 0.8 else
                              "🔴 High — confirms Hyperthyroidism")
                st.markdown(f"""<div style="background:#f8f9fa;border-radius:8px;
                    padding:10px 14px;font-size:13px;margin:4px 0;
                    border-left:4px solid {'#43a047' if '🟢' in t4_status else '#e53935'}">
                    Free T4: {t4_val} ng/dL — {t4_status} (Normal: 0.8–1.8 ng/dL)
                </div>""", unsafe_allow_html=True)

            if t3_val > 0:
                t3_status = ("🟢 Normal" if 2.3 <= t3_val <= 4.2 else
                              "🔴 Low" if t3_val < 2.3 else
                              "🔴 High — T3 toxicosis pattern")
                st.markdown(f"""<div style="background:#f8f9fa;border-radius:8px;
                    padding:10px 14px;font-size:13px;margin:4px 0;
                    border-left:4px solid {'#43a047' if '🟢' in t3_status else '#e53935'}">
                    Free T3: {t3_val} pg/mL — {t3_status} (Normal: 2.3–4.2 pg/mL)
                </div>""", unsafe_allow_html=True)

            # What to do next
            if tsh_val < 0.4:
                next_steps = [
                    "Get Free T3 and Free T4 if not already done",
                    "TSH Receptor Antibody (TRAb) test to check for Graves' Disease",
                    "Thyroid ultrasound to check for nodules",
                    "See Endocrinologist within 1 week",
                ]
            elif tsh_val > 4.0:
                next_steps = [
                    "Get Free T4 to determine if overt or subclinical",
                    "Anti-TPO antibody test to check for Hashimoto's",
                    "Repeat TSH in 4-6 weeks if borderline",
                    f"{'See Endocrinologist urgently' if tsh_val > 10 else 'See Physician within 2-4 weeks'}",
                ]
            else:
                next_steps = [
                    "TSH is normal — thyroid function is healthy",
                    "Repeat annually if you have risk factors (female, family history, autoimmune condition)",
                    "If symptoms persist despite normal TSH — look for other causes",
                ]

            st.markdown("**What to Do Next:**")
            for step in next_steps:
                st.markdown(f"""<div style="background:#e8f5e9;border-left:3px solid #43a047;
                    border-radius:6px;padding:7px 12px;margin:3px 0;font-size:13px">
                    ✅ {step}
                </div>""", unsafe_allow_html=True)

            if st.button("📄 Save TSH Interpretation Report", use_container_width=True):
                risk_from_tsh = ("High Risk" if tsh_val < 0.4 or tsh_val > 10 else
                                  "Moderate Risk" if tsh_val > 4 else "Low Risk")
                cond_from_tsh = ("Hyperthyroidism" if tsh_val < 0.4 else
                                  "Hypothyroidism" if tsh_val > 4 else "Normal Thyroid Function")
                score_proxy   = int(abs(tsh_val - 2.0) / 18.0 * 100)

                sev, se, sr, cond_list, conf, dd, hc_care, wd, ex = \
                    _build_thyroid_report(risk_from_tsh, score_proxy, cond_from_tsh, 0, 0)
                render_clinical_report("Thyroid — TSH Interpretation", sev, se, sr, cond_list,
                                        conf, dd, hc_care, wd, ex, patient_name=uname)

                save_report(uid, "Thyroid TSH Interpretation", sev,
                            cond_from_tsh, conf,
                            f"TSH:{tsh_val}|T4:{t4_val}|T3:{t3_val}|Status:{status}",
                            numeric_value=float(tsh_val))
                st.success("✅ Report saved to your history.")

    st.markdown("""<div class="footer">
        MediSense Pro · Thyroid Assessment · SWE1904 · VIT · R.Divya 21MIS0261
    </div>""", unsafe_allow_html=True)
