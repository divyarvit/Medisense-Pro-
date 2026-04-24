import streamlit as st
from utils.diagnosis_engine import (assess_severity, generate_differential_diagnosis,
                                     calculate_confidence, get_do_dont,
                                     when_to_see_doctor, get_home_care)
from utils.report_renderer import render_clinical_report
from utils.database import save_report

SYMPTOM_OPTIONS = {
    "🌡️ Fever / High Temperature":   "fever",
    "🤧 Runny Nose / Sneezing":       "runny_nose",
    "😮‍💨 Cough":                     "cough",
    "😮 Difficulty Breathing":        "difficulty_breathing",
    "🤢 Nausea":                      "nausea",
    "🤮 Vomiting":                    "vomiting",
    "😣 Indigestion / Stomach Ache":  "indigestion",
    "🚽 Diarrhea":                    "diarrhea",
    "💛 Yellowish Urine":             "yellowish_urine",
    "👁️ Yellow Eyes / Skin":          "yellow_eyes",
    "😴 Fatigue / Weakness":          "fatigue",
    "🤕 Headache":                    "headache",
    "🤯 Severe Headache":             "severe_headache",
    "😵 Dizziness":                   "dizziness",
    "💔 Chest Pain":                  "chest_pain",
    "💪 Body Ache / Muscle Pain":     "body_ache",
    "😰 Excessive Sweating":          "sweating",
    "🦷 Sore Throat":                 "sore_throat",
    "🌫️ Blurred Vision":              "blurred_vision",
    "💧 Dry Mouth / Thirst":          "dry_mouth",
    "🟤 Dark / Brown Urine":          "dark_urine",
    "🩸 Blood in Stool":              "blood_in_stool",
    "💪 Arm / Shoulder Pain":         "arm_pain",
    "🧠 Confusion / Disorientation":  "confusion",
}

def show():
    st.markdown("""<div class="main-header">
        <h1>🔬 General Diagnosis</h1>
        <p>Symptom-based health assessment with differential diagnosis</p>
    </div>""", unsafe_allow_html=True)

    st.markdown("### 📝 Step 1 — Enter Your Vital Parameters")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        temp = st.number_input("🌡️ Temperature (°F)", 90.0, 115.0, 98.6, step=0.1)
        temp_note = ("🟢 Normal" if temp < 99 else ("🟡 Low Fever" if temp < 100.4
                      else ("🔴 Fever" if temp < 103 else "🚨 High Fever")))
        st.caption(temp_note)
    with c2:
        pulse = st.number_input("💓 Pulse Rate (bpm)", 30, 220, 72)
        pulse_note = ("🟢 Normal" if 60<=pulse<=100 else ("🟡 Low" if pulse<60 else "🔴 High"))
        st.caption(pulse_note)
    with c3:
        duration = st.number_input("📅 Duration (days)", 0, 60, 1)
    with c4:
        age    = st.number_input("🎂 Age", 1, 120, 25)
        gender = st.selectbox("⚤ Gender", ["Female","Male","Other"])

    st.markdown("### 📝 Step 2 — Select Your Symptoms")
    st.caption("Check all symptoms you are currently experiencing:")

    selected_symptoms = []
    cols = st.columns(4)
    for i, (label, key) in enumerate(SYMPTOM_OPTIONS.items()):
        with cols[i % 4]:
            if st.checkbox(label, key=f"sym_{key}"):
                selected_symptoms.append(key)

    st.markdown("### 📝 Step 3 — Any Additional Notes?")
    notes = st.text_area("Describe anything else (optional)", height=80,
                         placeholder="e.g. started after eating outside, had similar episode before...")

    if st.button("🔍 Generate Clinical Report", use_container_width=True):
        if not selected_symptoms and temp < 99 and 60 <= pulse <= 100:
            st.warning("Please enter at least one symptom or abnormal vital value.")
            return

        params = {
            "temperature":   temp,
            "pulse":         pulse,
            "duration_days": duration,
            "symptoms":      selected_symptoms,
            "age":           age,
            "gender":        gender,
        }

        with st.spinner("Analyzing your symptoms..."):
            severity, sev_score, sev_expl, sev_reasons = assess_severity(params)
            conditions = generate_differential_diagnosis(params)
            confidence = calculate_confidence(params)
            do_dont    = get_do_dont(conditions, severity)
            home_care  = get_home_care(conditions)
            when_doc   = when_to_see_doctor(severity, conditions)

        top_dx = conditions[0]["condition"] if conditions else "Unknown"

        st.markdown("---")
        st.markdown("## 📄 Clinical Assessment Report")
        st.markdown(f"**Patient:** {st.session_state.full_name} | **Age:** {age} | "
                    f"**Gender:** {gender} | **Duration:** {duration} day(s)")

        render_clinical_report(
            module_name      = "General Diagnosis",
            severity         = severity,
            severity_explanation = sev_expl,
            severity_reasons = sev_reasons,
            conditions       = conditions,
            confidence       = confidence,
            do_dont          = do_dont,
            home_care        = home_care,
            when_doctor      = when_doc,
            extra_info       = f"Symptoms: {', '.join(selected_symptoms) or 'None selected'}",
            patient_name     = st.session_state.get("full_name","Patient"),
            vital_summary    = f"Temp:{temp}F | Pulse:{pulse}bpm | Duration:{duration}d | Age:{age} | Gender:{gender}"
        )

        save_report(st.session_state.user_id, "General Diagnosis",
                    severity, top_dx, confidence,
                    f"Symptoms:{selected_symptoms}|Temp:{temp}|Pulse:{pulse}")
        st.success("✅ Report saved to your history.")
