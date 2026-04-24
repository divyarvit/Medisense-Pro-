import streamlit as st
import base64, os, sys, json
import urllib.request, urllib.error
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.database import save_report

GEMINI_KEY = "AIzaSyB73sen1ptu3V0wiAV1R28TQwU2OTCNO3k"
GEMINI_URL = (f"https://generativelanguage.googleapis.com/v1/models/"
              f"gemini-2.0-flash:generateContent?key={GEMINI_KEY}")

CATEGORIES = {
    "Skin / Rash":      "skin rash or skin condition",
    "Burn / Scald":     "burn or scald injury",
    "Wound / Cut":      "wound, cut, or laceration",
    "Eye Problem":      "eye condition or eye symptom",
    "Swelling / Lump":  "swelling or lump",
    "Nail Problem":     "nail condition",
    "Mouth / Throat":   "mouth or throat condition",
    "Other Symptom":    "visible medical symptom",
}

SYSTEM_PROMPT = """You are Dr. MediSense, an expert AI medical image analysis assistant.
A patient has uploaded a photo of a medical symptom. Analyse the image carefully and provide a structured clinical assessment.

Respond ONLY in this exact JSON format — no extra text, no markdown, no explanation outside JSON:
{{
  "visual_findings": "2-3 sentences describing exactly what you observe in the image clinically",
  "primary_diagnosis": "Most likely condition name",
  "conditions": [
    {{"name": "Condition 1", "probability": 55, "icd": "ICD-10 code", "reason": "Why this is most likely based on what you see"}},
    {{"name": "Condition 2", "probability": 28, "icd": "ICD-10 code", "reason": "Why this is second possibility"}},
    {{"name": "Condition 3", "probability": 17, "icd": "ICD-10 code", "reason": "Why this is third possibility"}}
  ],
  "severity": "Mild or Moderate or Severe",
  "severity_reason": "One sentence explaining why this severity level",
  "immediate_steps": [
    "Step 1 — specific actionable advice",
    "Step 2",
    "Step 3",
    "Step 4"
  ],
  "do_not": [
    "Do NOT do this",
    "Do NOT do this"
  ],
  "see_doctor_when": [
    "Specific red flag symptom 1",
    "Specific red flag symptom 2",
    "Specific red flag symptom 3"
  ],
  "specialist": "Which type of doctor to see",
  "home_care": "2-3 sentences of practical home care advice"
}}"""

def analyse_with_gemini(image_bytes, category_desc, patient_description, duration):
    img_b64 = base64.b64encode(image_bytes).decode("utf-8")
    prompt = (f"The patient says this is a {category_desc}. "
              f"Patient's description: '{patient_description}'. "
              f"Duration: {duration}. "
              f"Carefully examine the image and provide your clinical assessment.")
    payload = json.dumps({
        "contents": [{
            "parts": [
                {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}},
                {"text": SYSTEM_PROMPT + "\n\n" + prompt}
            ]
        }],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 1000}
    }).encode("utf-8")

    req = urllib.request.Request(GEMINI_URL, data=payload,
                                  headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            raw  = data["candidates"][0]["content"]["parts"][0]["text"]
            # Strip markdown fences if present
            raw  = raw.strip()
            if raw.startswith("```"): raw = raw.split("```")[1]
            if raw.startswith("json"): raw = raw[4:]
            return json.loads(raw.strip()), None
    except urllib.error.HTTPError as e:
        return None, f"API Error {e.code}: {e.read().decode()}"
    except json.JSONDecodeError as e:
        return None, f"Could not parse AI response: {e}"
    except Exception as e:
        return None, f"Connection error: {e}"

def render_ai_report(result, category_name, duration):
    severity   = result.get("severity", "Moderate")
    sev_color  = {"Mild":"#43a047","Moderate":"#fb8c00","Severe":"#e53935"}.get(severity,"#888")
    sev_icon   = {"Mild":"🟢","Moderate":"🟡","Severe":"🔴"}.get(severity,"⚪")
    conditions = result.get("conditions", [])
    bar_colors = ["#1565c0","#fb8c00","#9e9e9e"]

    st.markdown(f"""<div style="background:#e8f5e9;border-radius:8px;
        padding:10px 14px;font-size:13px;border-left:4px solid #43a047;margin-bottom:16px">
        ✅ <b>Gemini AI Vision Analysis</b> — Image actually read and analysed in real-time
    </div>""", unsafe_allow_html=True)

    # Visual Findings
    st.markdown(f"""<div style="background:#e3f2fd;border-left:6px solid #1565c0;
        border-radius:10px;padding:16px 18px;margin:8px 0">
        <b style="color:#1565c0">🔍 What the AI Sees in Your Photo:</b><br><br>
        <span style="font-size:14px;line-height:1.7;color:#1a1a2e">
        {result.get("visual_findings","")}</span>
    </div>""", unsafe_allow_html=True)

    # Severity
    st.markdown(f"""<div style="background:{sev_color};color:white;border-radius:12px;
        padding:16px;text-align:center;margin:12px 0">
        <h2 style="margin:0">{sev_icon} Severity: {severity}</h2>
        <p style="margin:6px 0 0;opacity:0.9;font-size:13px">
        {result.get("severity_reason","")}</p>
    </div>""", unsafe_allow_html=True)

    # Differential diagnosis
    st.markdown("### 🔬 Differential Diagnosis")
    for i, cond in enumerate(conditions[:3]):
        prob = cond.get("probability", 0)
        bc   = bar_colors[i] if i < 3 else "#ccc"
        rank = ["🥇 Most Likely","🥈 Second Possibility","🥉 Third Possibility"][i]
        st.markdown(f"""<div style="background:white;border:1px solid #e0e0e0;
            border-radius:12px;padding:14px 18px;margin:8px 0;
            box-shadow:0 2px 6px rgba(0,0,0,0.07)">
            <div style="display:flex;justify-content:space-between;align-items:center">
                <b style="font-size:15px">{cond.get('name','')}</b>
                <span style="background:{bc};color:white;padding:3px 12px;
                    border-radius:20px;font-weight:700">{prob}%</span>
            </div>
            <div style="background:#eee;border-radius:4px;height:8px;margin:8px 0">
                <div style="background:{bc};width:{prob}%;height:8px;border-radius:4px"></div>
            </div>
            <span style="font-size:12px;color:#888">{rank}</span><br>
            <span style="font-size:13px;color:#555">{cond.get('reason','')}</span><br>
            <span style="font-size:11px;color:#aaa">ICD-10: {cond.get('icd','—')}</span>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # Do / Don't
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### ✅ Immediate Care Steps")
        for step in result.get("immediate_steps", []):
            st.markdown(f"""<div style="background:#e8f5e9;border-left:4px solid #43a047;
                border-radius:6px;padding:9px 13px;margin:5px 0;font-size:13px">
                ✔️ {step}</div>""", unsafe_allow_html=True)
    with c2:
        st.markdown("### ❌ What NOT To Do")
        for item in result.get("do_not", []):
            st.markdown(f"""<div style="background:#fce4ec;border-left:4px solid #e53935;
                border-radius:6px;padding:9px 13px;margin:5px 0;font-size:13px">
                ✖️ {item}</div>""", unsafe_allow_html=True)

    st.markdown("---")

    # Home care
    home = result.get("home_care","")
    if home:
        st.markdown(f"""<div style="background:#e3f2fd;border-radius:10px;
            padding:14px 18px;border-left:4px solid #1565c0;margin:8px 0">
            <b>🏠 Home Care:</b><br>
            <span style="font-size:13px;line-height:1.6">{home}</span>
        </div>""", unsafe_allow_html=True)

    # When to see doctor
    st.markdown("### 🩺 When to See a Doctor")
    specialist = result.get("specialist","")
    if specialist:
        st.markdown(f"""<div style="background:#e8f0fe;border-radius:8px;
            padding:10px 14px;font-size:13px;border-left:4px solid #1565c0;margin-bottom:8px">
            👨‍⚕️ <b>Recommended Specialist:</b> {specialist}
        </div>""", unsafe_allow_html=True)
    for flag in result.get("see_doctor_when", []):
        is_emerg = any(w in flag.upper() for w in ["EMERGENCY","IMMEDIATELY","URGENT","🚨"])
        bg = "#ffebee" if is_emerg else "#fff3e0"
        bd = "#e53935" if is_emerg else "#fb8c00"
        icon = "🚨" if is_emerg else "🩺"
        st.markdown(f"""<div style="background:{bg};border-left:4px solid {bd};
            border-radius:6px;padding:8px 14px;margin:4px 0;font-size:13px">
            {icon} {flag}</div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("""<div style="background:#fff8e1;border:1px solid #ffc107;
        border-radius:8px;padding:12px 16px;font-size:12px;color:#555">
        ⚠️ <b>Medical Disclaimer:</b> This AI visual analysis is for informational purposes only.
        It is NOT a clinical diagnosis. Always consult a qualified doctor for any medical concern.
        Gemini AI Vision analyses the image but cannot replace an in-person medical examination.
    </div>""", unsafe_allow_html=True)

def show():
    st.markdown("""<div class="main-header">
        <h1>📸 AI Visual Symptom Analysis</h1>
        <p>Upload a photo — Gemini AI Vision actually reads and analyses your symptom in real-time</p>
    </div>""", unsafe_allow_html=True)

    st.markdown("""<div style="background:#e8f5e9;border-radius:12px;padding:12px 18px;
        border-left:5px solid #43a047;margin-bottom:16px;font-size:14px">
        ✅ <b>Powered by Google Gemini Vision AI</b> — The AI actually reads your photo and gives
        real analysis, not predefined answers. Every photo gets a unique assessment.
    </div>""", unsafe_allow_html=True)

    col_upload, col_result = st.columns([1, 1.2])

    with col_upload:
        st.markdown("### 📤 Upload Your Photo")

        category_name = st.selectbox("🏷️ Type of symptom",
                                      list(CATEGORIES.keys()))
        cat_desc = CATEGORIES[category_name]

        uploaded = st.file_uploader("📷 Upload photo (JPG/PNG)",
                                     type=["jpg","jpeg","png"])

        description = st.text_area("📝 Describe in your own words",
                                    placeholder="e.g. I burnt my hand on hot water, it's been painful for 2 hours...",
                                    height=90)

        duration = st.selectbox("⏱️ How long have you had this?",
                                  ["Less than 24 hours","1–3 days","4–7 days",
                                   "1–2 weeks","More than 2 weeks"])

        analyse = st.button("🔍 Analyse with Gemini AI",
                             use_container_width=True,
                             disabled=(uploaded is None))

        if not uploaded:
            st.markdown("""<div style="background:#f8f9fa;border-radius:10px;padding:24px;
                text-align:center;border:2px dashed #1565c0;margin-top:8px">
                <div style="font-size:3em">📸</div>
                <p style="color:#888;font-size:13px;margin:8px 0">
                Upload a clear photo to begin AI analysis</p>
            </div>""", unsafe_allow_html=True)

        with st.expander("📋 Tips for a good photo"):
            st.markdown("""
            - 💡 Use good lighting — near a window works best
            - 🔍 Get close — fill the frame with the affected area
            - 📐 Hold camera steady — no blur
            - 🖼️ Plain background preferred
            """)

    with col_result:
        if uploaded:
            st.markdown("### 🖼️ Your Photo")
            st.image(uploaded)

        if uploaded and analyse:
            with st.spinner("🤖 Gemini AI is reading and analysing your photo..."):
                img_bytes = uploaded.read()
                result, error = analyse_with_gemini(
                    img_bytes, cat_desc, description or "No description provided", duration
                )

            st.markdown("---")
            st.markdown("## 🏥 AI Visual Analysis Report")

            if error:
                st.error(f"❌ API Error: {error}")
                st.info("Please check your internet connection and try again.")
            elif result:
                render_ai_report(result, category_name, duration)
                severity = result.get("severity","Moderate")
                top_dx   = result.get("primary_diagnosis", category_name)
                save_report(
                    user_id     = st.session_state.user_id,
                    module      = "Visual Symptom Analysis",
                    severity    = severity,
                    diagnosis   = top_dx,
                    confidence  = result.get("conditions",[{}])[0].get("probability",70) if result.get("conditions") else 70,
                    full_report = f"Category:{category_name}|Duration:{duration}|Desc:{(description or '')[:80]}",
                )
                st.success("✅ Analysis saved to your reports history.")
            else:
                st.error("Could not get analysis. Please try again.")

    st.markdown("""<div class="footer">
        MediSense Pro · Gemini AI Vision · SWE1904 · VIT · R.Divya 21MIS0261
    </div>""", unsafe_allow_html=True)
