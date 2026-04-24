import streamlit as st
from datetime import datetime


def render_clinical_report(module_name, severity, severity_explanation,
                            severity_reasons, conditions, confidence,
                            do_dont, home_care, when_doctor,
                            extra_info=None, patient_name="Patient",
                            vital_summary=None, raw_params=None):
    """
    Full clinical report renderer — used by ALL modules.
    raw_params: optional dict with temperature, pulse, duration_days, symptoms
    """
    now      = datetime.now().strftime("%d %b %Y, %I:%M %p")
    top_dx   = conditions[0]["condition"] if conditions else "Unknown"
    sev_color = {"Mild":"#43a047","Moderate":"#fb8c00","Severe":"#e53935"}.get(severity,"#888")
    sev_icon  = {"Mild":"🟢","Moderate":"🟡","Severe":"🔴"}.get(severity,"⚪")
    conf_color = "#43a047" if confidence>=70 else ("#fb8c00" if confidence>=45 else "#e53935")

    # Extract raw params for condition-specific summary
    rp       = raw_params or {}
    symptoms = rp.get("symptoms", [])
    temp     = float(rp.get("temperature", 98.6))
    pulse    = int(rp.get("pulse", 72))
    duration = int(rp.get("duration_days", 1))

    # ── Report Header ─────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#1565c0,#0d47a1);color:white;
         border-radius:14px;padding:20px 24px;margin:10px 0 6px">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap">
            <div>
                <h2 style="margin:0;font-size:1.4em">🏥 Clinical Assessment Report</h2>
                <p style="margin:4px 0 0;opacity:0.85;font-size:13px">{module_name} · {now}</p>
            </div>
            <div style="text-align:right;margin-top:4px">
                <span style="background:rgba(255,255,255,0.2);padding:4px 12px;
                    border-radius:20px;font-size:13px">Patient: {patient_name}</span>
            </div>
        </div>
    </div>""", unsafe_allow_html=True)

    # ── SECTION 1: Clinical Summary ───────────────────────────────────────
    st.markdown("---")
    st.markdown("## 📋 Section 1 — Clinical Summary")

    symptom_list = ""
    if vital_summary:
        symptom_list = f"<br><span style='color:#555;font-size:13px'>📌 <b>Reported Data:</b> {vital_summary}</span>"

    # Use Groq-generated section 1 if available, else static
    groq_section1 = rp.get("groq_section1", "")
    if groq_section1:
        condition_summary = groq_section1
    else:
        condition_summary = _get_condition_summary(top_dx, symptoms, temp, pulse, duration, raw_params=rp)

    st.markdown(f"""
    <div style="background:#e8f0fe;border-left:6px solid #1565c0;border-radius:10px;
         padding:20px 22px;margin:10px 0">
        <h4 style="color:#0d47a1;margin:0 0 10px">🩺 What is happening with you?</h4>
        <p style="margin:0;color:#1a1a2e;font-size:15px;line-height:1.75">
            Based on your consultation, <b>the most likely diagnosis is {top_dx}</b>.
        </p>
        <br>
        <p style="margin:0;color:#333;font-size:14px;line-height:1.8">
            {condition_summary}
        </p>
        {symptom_list}
    </div>""", unsafe_allow_html=True)

    # ── SECTION 2: Severity Assessment ───────────────────────────────────
    st.markdown("---")
    st.markdown("## 🚨 Section 2 — Severity Assessment")

    # Use Groq severity explanation if available, else use generic
    groq_sev = rp.get("groq_section2", "")
    if groq_sev:
        sev_desc = groq_sev
    elif severity_explanation:
        sev_desc = severity_explanation
    else:
        sev_desc = {
            "Mild":     ("Your condition is currently <b>manageable at home</b> with proper rest, hydration, and care. "
                         "No emergency action is required, but monitor your symptoms carefully over the next 24–48 hours."),
            "Moderate": ("Your condition requires <b>medical attention within the next 24–48 hours</b>. "
                         "Do not ignore your symptoms — they may worsen without proper treatment. "
                         "Visit a clinic or doctor soon."),
            "Severe":   ("⚠️ Your symptoms suggest a <b>serious medical condition</b> that requires <b>prompt attention</b>. "
                         "Please do not delay — visit a doctor, clinic, or emergency room as soon as possible.")
        }.get(severity, "")

    st.markdown(f"""
    <div style="background:{sev_color};color:white;border-radius:12px;
         padding:20px 24px;margin:10px 0">
        <h2 style="margin:0 0 8px">{sev_icon} Severity Level: {severity}</h2>
        <p style="margin:0;opacity:0.95;font-size:14px;line-height:1.6">{sev_desc}</p>
    </div>""", unsafe_allow_html=True)

    if severity_reasons:
        st.markdown("**Why this severity? — Factors identified:**")
        cols = st.columns(2)
        for i, r in enumerate(severity_reasons):
            with cols[i % 2]:
                st.markdown(f"""<div style="background:#fff8e1;border-left:3px solid #ffc107;
                    border-radius:6px;padding:8px 12px;margin:3px 0;font-size:13px">
                    ⚡ {r}</div>""", unsafe_allow_html=True)

    # ── SECTION 3: Confidence Level ───────────────────────────────────────
    st.markdown("---")
    st.markdown("## 📊 Section 3 — Assessment Confidence")

    conf_label = "High" if confidence>=70 else ("Moderate" if confidence>=45 else "Low")
    conf_expl  = {
        "High":     "The assessment is based on comprehensive clinical data. The advice and diagnosis are well-supported.",
        "Moderate": "Good data was collected, but some parameters were missing. The advice is reliable but see a doctor to confirm.",
        "Low":      "Limited data was provided. This is a preliminary assessment only — please consult a doctor for accuracy."
    }[conf_label]

    st.markdown(f"""
    <div style="background:#f8f9fa;border-radius:10px;padding:16px 20px;
         border:1px solid #e0e0e0;margin:10px 0">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
            <b style="font-size:15px">Confidence Level:
                <span style="color:{conf_color}">{confidence:.0f}% — {conf_label}</span></b>
        </div>
        <div style="background:#e0e0e0;border-radius:6px;height:14px;margin:8px 0">
            <div style="background:{conf_color};width:{confidence}%;height:14px;
                 border-radius:6px;transition:width 0.5s"></div>
        </div>
        <p style="margin:6px 0 0;font-size:13px;color:#555">{conf_expl}</p>
    </div>""", unsafe_allow_html=True)

    # ── SECTION 4: Differential Diagnosis ────────────────────────────────
    st.markdown("---")
    st.markdown("## 🔬 Section 4 — Differential Diagnosis")
    st.markdown("""<p style="color:#555;font-size:14px;margin:0 0 12px">
    A differential diagnosis lists the <b>most likely conditions</b> that could explain your symptoms,
    ranked by probability. This is <b>not a confirmed diagnosis</b> — only a doctor can confirm with tests.
    </p>""", unsafe_allow_html=True)

    for i, cond in enumerate(conditions):
        rank_icon  = ["🥇","🥈","🥉"][i] if i<3 else "📌"
        bar_color  = ["#1565c0","#fb8c00","#9e9e9e"][i] if i<3 else "#ccc"
        rank_label = ["Most Likely","Second Possibility","Third Possibility"][i] if i<3 else "Other"
        prob       = cond.get("probability", 0)

        # Use specific reasoning from diagnosis engine if available
        reasoning  = cond.get("reasoning") or _get_why_diagnosis(cond["condition"], i)

        # ICD with full name
        icd_code = cond.get("icd", "—")
        icd_name = cond.get("icd_name", "")
        icd_display = f"{icd_code} — {icd_name}" if icd_name else icd_code

        st.markdown(f"""
        <div style="background:white;border:1px solid #e0e0e0;border-radius:12px;
             padding:16px 20px;margin:10px 0;box-shadow:0 2px 6px rgba(0,0,0,0.07)">
            <div style="display:flex;justify-content:space-between;align-items:center">
                <span style="font-size:16px;font-weight:700">{rank_icon} {cond['condition']}</span>
                <span style="background:{bar_color};color:white;padding:3px 12px;
                    border-radius:20px;font-weight:700;font-size:14px">{prob}%</span>
            </div>
            <div style="background:#eee;border-radius:6px;height:10px;margin:10px 0">
                <div style="background:{bar_color};width:{prob}%;height:10px;border-radius:6px"></div>
            </div>
            <p style="margin:0 0 8px;color:#333;font-size:13px;line-height:1.6">
                <b>What it is:</b> {cond.get('description','')}
            </p>
            <p style="margin:0 0 8px;color:#444;font-size:13px;line-height:1.6;
                background:#f8f9fa;padding:8px 12px;border-radius:6px;border-left:3px solid {bar_color}">
                <b>Why it's {rank_label.lower()}:</b> {reasoning}
            </p>
            <div style="display:flex;gap:12px;margin-top:8px;flex-wrap:wrap">
                <span style="background:#f0f4ff;color:#1565c0;padding:3px 12px;
                    border-radius:10px;font-size:12px">🏷️ ICD-10: {icd_display}</span>
                <span style="background:#f0fff4;color:#2e7d32;padding:3px 12px;
                    border-radius:10px;font-size:12px">📊 {rank_label}</span>
            </div>
        </div>""", unsafe_allow_html=True)

    # ── SECTION 5: Do / Don't ─────────────────────────────────────────────
    st.markdown("---")
    st.markdown("## ✅ Section 5 — What To Do & What NOT To Do")
    st.markdown('<p style="color:#555;font-size:14px;margin:0 0 12px">Follow these clinical recommendations carefully for recovery and management.</p>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("""<div style="background:#e8f5e9;border-radius:10px;padding:14px 16px;margin-bottom:8px">
            <h4 style="color:#2e7d32;margin:0 0 10px">✅ DO These Things</h4>""", unsafe_allow_html=True)
        for item in do_dont.get("do",[]):
            st.markdown(f"""<div style="background:white;border-left:4px solid #43a047;border-radius:6px;
                padding:9px 13px;margin:5px 0;font-size:13px;line-height:1.5;
                box-shadow:0 1px 3px rgba(0,0,0,0.05)">✔️ {item}</div>""",
                unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        st.markdown("""<div style="background:#fce4ec;border-radius:10px;padding:14px 16px;margin-bottom:8px">
            <h4 style="color:#c62828;margin:0 0 10px">❌ DO NOT Do These</h4>""", unsafe_allow_html=True)
        for item in do_dont.get("dont",[]):
            st.markdown(f"""<div style="background:white;border-left:4px solid #e53935;border-radius:6px;
                padding:9px 13px;margin:5px 0;font-size:13px;line-height:1.5;
                box-shadow:0 1px 3px rgba(0,0,0,0.05)">✖️ {item}</div>""",
                unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # ── SECTION 6: Home Care ──────────────────────────────────────────────
    st.markdown("---")
    st.markdown("## 🏠 Section 6 — Home Care Instructions")
    st.markdown('<p style="color:#555;font-size:14px;margin:0 0 12px">Evidence-based home remedies and self-care steps you can start immediately.</p>', unsafe_allow_html=True)

    hc_cols = st.columns(2)
    for i, tip in enumerate(home_care):
        with hc_cols[i % 2]:
            st.markdown(f"""<div style="background:#e3f2fd;border-left:4px solid #1565c0;
                border-radius:8px;padding:10px 14px;margin:5px 0;font-size:13px;
                line-height:1.6;box-shadow:0 1px 3px rgba(0,0,0,0.05)">
                🏠 {tip}</div>""", unsafe_allow_html=True)

    # ── SECTION 7: When to See Doctor ────────────────────────────────────
    st.markdown("---")
    st.markdown("## 🩺 Section 7 — When to Consult a Doctor")
    st.markdown('<p style="color:#555;font-size:14px;margin:0 0 12px">Do NOT wait if any of the following apply to you.</p>', unsafe_allow_html=True)

    for point in when_doctor:
        is_emergency = any(w in point.upper() for w in
            ["IMMEDIATELY","EMERGENCY","URGENT","NOW","CALL 108","SAME DAY"])
        is_soon = any(w in point.upper() for w in ["SOON","24 HOUR","48 HOUR","WITHIN"])
        if is_emergency:
            bg, border, icon = "#ffebee","#e53935","🚨"
        elif is_soon:
            bg, border, icon = "#fff3e0","#fb8c00","⚠️"
        else:
            bg, border, icon = "#f3e5f5","#8e24aa","🩺"
        st.markdown(f"""<div style="background:{bg};border-left:5px solid {border};
            border-radius:8px;padding:10px 16px;margin:6px 0;font-size:14px;line-height:1.5">
            {icon} {point}</div>""", unsafe_allow_html=True)

    # ── Disclaimer ────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("""
    <div style="background:#fff8e1;border:2px solid #ffc107;border-radius:10px;
         padding:16px 20px;font-size:13px;color:#555;line-height:1.6">
        ⚠️ <b>Medical Disclaimer:</b> This clinical report is generated by an AI system
        for <b>educational and informational purposes only</b>. It is <b>NOT a substitute</b>
        for professional medical advice, diagnosis, or treatment by a qualified
        licensed healthcare professional. Always consult your doctor before making
        any health decisions. In case of emergency, call <b>108</b> immediately.
    </div>""", unsafe_allow_html=True)


# ── Condition-specific clinical summary ──────────────────────────────────────
def _get_condition_summary(condition, symptoms, temp, pulse, duration, raw_params=None):
    sym = set(symptoms) if symptoms else set()
    rp  = raw_params or {}

    # ── Diabetes-specific summaries ───────────────────────────
    glucose  = rp.get("glucose", 0)
    hba1c    = rp.get("hba1c", 0)
    bmi      = rp.get("bmi", 0)
    age      = rp.get("age", 0)
    steps    = rp.get("steps", 0)
    stress   = rp.get("stress", "")
    dtype    = rp.get("diabetes_type", "")

    if condition in ("Type 2 Diabetes Mellitus", "Type 2 Diabetes (Possible)"):
        parts = []
        if glucose > 125:
            parts.append(f"your fasting glucose of {glucose} mg/dL is above the diabetic threshold of 126 mg/dL")
        if hba1c and hba1c > 6.4:
            parts.append(f"your HbA1c of {hba1c}% confirms that your 3-month blood sugar average has been in the diabetic range")
        if bmi and bmi > 27:
            parts.append(f"your BMI of {bmi:.1f} indicates excess body weight which directly causes insulin resistance — the root cause of Type 2 diabetes")
        if not parts:
            parts.append("multiple metabolic risk factors are present together pointing to Type 2 diabetes")
        return (
            "In Type 2 Diabetes, your body either does not produce enough insulin or your cells have stopped responding to it properly — "
            "this is called insulin resistance. As a result, glucose cannot enter your cells for energy and builds up in your bloodstream instead. "
            f"In your case, {'. Also, '.join(parts)}. "
            "The good news is that Type 2 diabetes is highly manageable — and when caught at this stage, "
            "lifestyle changes alone can significantly improve or even normalise glucose levels."
        )

    if condition in ("Pre-diabetes / IGT", "Pre-diabetes / Impaired Glucose Tolerance"):
        if hba1c and 5.7 <= hba1c <= 6.4:
            return (
                f"Your HbA1c of {hba1c}% places you in the pre-diabetic range of 5.7–6.4%. "
                "HbA1c measures your average blood sugar over the past 3 months — this means your glucose has been consistently above normal for months, "
                "even if a single fasting test looks acceptable. "
                "Pre-diabetes has no symptoms — most people only discover it through testing. "
                "This is the most critical window to act — with the right diet and exercise changes, "
                "pre-diabetes is completely reversible and full Type 2 diabetes can be prevented."
            )
        return (
            f"Your blood glucose of {glucose} mg/dL falls in the pre-diabetic range of 100–125 mg/dL. "
            "This means your body is struggling to keep blood sugar in the normal range but has not yet crossed the diabetic threshold. "
            "Your pancreas is working harder than normal to compensate, which eventually leads to burnout and full diabetes if not addressed. "
            "This is a completely reversible condition — studies show that losing just 5–7% of body weight and walking 30 minutes daily "
            "reduces the risk of progression to Type 2 diabetes by 58%."
        )

    if condition == "No Diabetes Detected":
        return (
            "Your blood glucose and metabolic parameters are within the clinically acceptable range. "
            "Your pancreas is producing adequate insulin and your cells are responding to it correctly — "
            "this is the hallmark of healthy glucose metabolism. "
            "However, diabetes develops silently over years without any symptoms. "
            "Annual fasting glucose testing is recommended, especially given that India has one of the highest diabetes burdens globally."
        )

    summaries = {
        "Dehydration": (
            "Your body is currently losing more fluid than it is taking in. "
            "When fluid levels drop, blood volume decreases and less oxygen reaches your muscles and brain — "
            "which is why you are experiencing "
            + ("dizziness, dry mouth, and fatigue. "
               if sym & {"dizziness","dry_mouth","fatigue"}
               else "weakness and discomfort. ")
            + "Your immediate priority is fluid replenishment — drink water or ORS every 15 minutes. "
            "Dehydration can worsen rapidly if not corrected, especially in hot weather."
        ),
        "Viral Fever / Common Cold": (
            f"Your immune system is actively fighting a viral infection. "
            f"The fever of {temp}°F is your body's natural defence — making conditions unfavourable for the virus. "
            + ("The body aches, fatigue, and runny nose are classic signs your immune system "
               "is releasing inflammatory signals to fight the virus. "
               if sym & {"body_ache","fatigue","runny_nose"}
               else "The symptoms you are experiencing are typical of a viral upper respiratory infection. ")
            + "Most viral fevers resolve in 5–7 days with rest and hydration. "
            "Focus on rest, fluids, and paracetamol for fever control."
        ),
        "Food Poisoning / Gastroenteritis": (
            "Your digestive system has been exposed to contaminated food or water. "
            "Your body is responding by trying to expel the harmful substance — causing "
            + ("the vomiting and diarrhea you are experiencing. "
               if sym & {"vomiting","diarrhea"}
               else "your stomach symptoms. ")
            + "The biggest risk right now is dehydration from fluid loss. "
            "Replace lost fluids with ORS or coconut water every few minutes, even in small sips. "
            "Most cases resolve within 24–48 hours with proper care."
        ),
        "Jaundice / Hepatitis": (
            "Your liver is under stress and not processing bilirubin properly. "
            "Bilirubin is a yellow pigment from broken-down red blood cells — when the liver cannot filter it, "
            "it builds up in blood and tissues, "
            + ("causing the yellowing of your eyes and urine that you have noticed. "
               if sym & {"yellow_eyes","yellowish_urine"}
               else "causing the symptoms you are experiencing. ")
            + "This requires urgent medical attention and a Liver Function Test (LFT). "
            "Do not delay — liver conditions can worsen quickly without treatment."
        ),
        "Cardiac Concern (Heart-related)": (
            "Your symptoms suggest your heart may be under significant stress. "
            + ("Chest pain combined with difficulty breathing and sweating "
               if sym & {"chest_pain","difficulty_breathing","sweating"}
               else "The symptoms you are reporting ")
            + "are warning signs that the heart muscle may not be receiving adequate blood supply. "
            "This is time-sensitive — every minute matters. "
            "Call 108 or go to the nearest emergency room immediately. "
            "Do not drive yourself — sit down, stay calm, and call for help right now."
        ),
        "Respiratory Infection (Pneumonia/Bronchitis)": (
            "Your airways or lung tissue appear to be infected, causing inflammation in the respiratory tract. "
            + ("The persistent cough and difficulty breathing "
               if sym & {"cough","difficulty_breathing"}
               else "Your breathing symptoms ")
            + "are your body's attempt to clear the infection from the airways. "
            f"With a temperature of {temp}°F over {duration} day(s), this needs medical attention soon. "
            "A doctor will need to examine your lungs and may prescribe antibiotics."
        ),
        "Hypertension / High Blood Pressure": (
            "Your symptoms suggest your blood pressure may be elevated. "
            + ("The severe headache and dizziness you are experiencing "
               if sym & {"severe_headache","dizziness"}
               else "Your reported symptoms ")
            + "are common signs of elevated blood pressure affecting the brain's blood vessels. "
            "Sit quietly, breathe slowly, and measure your blood pressure if a machine is available. "
            "See a doctor today — do not ignore these symptoms."
        ),
    }

    default = (
        f"Based on your reported symptoms over {duration} day(s), "
        "your body is showing signs of an active condition. "
        + (f"The symptoms you described — "
           f"{', '.join([s.replace('_',' ') for s in list(sym)[:3]]) if sym else 'as reported'} — "
           "are consistent with this diagnosis. " if sym else "")
        + "Please follow the recommendations below carefully and consult a doctor if symptoms worsen."
    )

    return summaries.get(condition, default)


def _get_condition_explanation(condition):
    explanations = {
        "Dehydration":
            "Dehydration occurs when your body loses more fluid than it takes in. "
            "Even mild dehydration affects energy levels, concentration, and physical performance.",
        "Viral Fever / Common Cold":
            "A viral fever is your immune system fighting a viral infection. "
            "The elevated temperature is actually your body making it harder for the virus to survive.",
        "Food Poisoning / Gastroenteritis":
            "Food poisoning happens when you consume food or water contaminated with bacteria, viruses, or toxins. "
            "Your digestive system reacts by trying to expel the harmful substance.",
        "Jaundice / Hepatitis":
            "Jaundice occurs when bilirubin — a yellow pigment from old red blood cells — builds up in the body "
            "because the liver cannot process it fast enough.",
        "Cardiac Concern (Heart-related)":
            "Cardiac symptoms require immediate attention. The heart muscle needs a constant supply of oxygen-rich blood. "
            "Any interruption to this supply is a medical emergency.",
        "Respiratory Infection (Pneumonia/Bronchitis)":
            "A respiratory infection involves inflammation of the airways or lungs caused by bacteria or viruses. "
            "It reduces the lungs' ability to exchange oxygen efficiently.",
        "Hypertension / High Blood Pressure":
            "High blood pressure means the force of blood against artery walls is consistently too high. "
            "Over time this silently damages blood vessels, heart, and kidneys.",
    }
    return explanations.get(condition,
        "This condition has been identified based on your reported symptoms and vitals. "
        "Please consult a doctor for a thorough evaluation and confirmed diagnosis.")


def _get_why_diagnosis(condition, rank):
    reasoning = {
        0: {
            "Viral Fever / Common Cold": "Viral fever accounts for over 70% of all fever cases. Fever with body ache is the classic viral presentation.",
            "Food Poisoning / Gastroenteritis": "Most common cause of acute stomach symptoms, especially after outside food.",
            "Jaundice / Hepatitis": "Yellow urine and yellow eyes together are the most specific signs of liver dysfunction.",
            "Cardiac Concern (Heart-related)": "Chest pain with breathing difficulty is a high-priority cardiac warning combination.",
            "Dehydration": "Dizziness, dry mouth, and dark urine together are the most reliable indicators of dehydration.",
            "Respiratory Infection (Pneumonia/Bronchitis)": "Cough with breathing difficulty and fever is the classic triad of lower respiratory infection.",
            "Hypertension / High Blood Pressure": "Severe headache with dizziness and visual disturbance is a common hypertensive presentation.",
        },
        1: {
            "Viral Fever / Common Cold": "Shares symptom overlap with the primary diagnosis — viral infections commonly present together.",
            "Dehydration": "Dehydration commonly accompanies fever and vomiting — fluid loss is a secondary concern.",
            "Hypertension / High Blood Pressure": "BP elevation should be ruled out when headache and dizziness are present together.",
        },
        2: {
            "Viral Fever / Common Cold": "Less likely given the symptom pattern, but viral infection cannot be fully excluded.",
            "Dehydration": "Mild dehydration is possible as a contributing factor even when not the primary diagnosis.",
        }
    }
    return reasoning.get(rank, {}).get(condition,
        "Symptom combination is consistent with this condition and should be considered during medical evaluation.")
