import streamlit as st
import json, requests, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.database import save_report

GROQ_KEY = "your_groq_api_key_here"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL    = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """You are Dr. MediSense, a highly experienced AI doctor assistant.
You are conducting a medical consultation with a patient in India.

Your consultation style:
- Ask ONE focused clinical question at a time
- Questions must be specific to the patient's complaint (not generic)
- After 5-6 questions, provide a structured diagnosis
- Be warm, professional, and clear
- Always use simple language the patient understands
- Consider Indian context (climate, common diseases, lifestyle)

When you have gathered enough information, respond with a JSON diagnosis block like this:
{
  "type": "diagnosis",
  "summary": "Plain English summary of what is likely happening",
  "conditions": [
    {"name": "Condition", "probability": 60, "icd": "ICD-10", "description": "What this means"},
    {"name": "Condition 2", "probability": 25, "icd": "ICD-10", "description": "What this means"},
    {"name": "Condition 3", "probability": 15, "icd": "ICD-10", "description": "What this means"}
  ],
  "severity": "Mild or Moderate or Severe",
  "severity_reason": "Why this severity",
  "do": ["Action 1", "Action 2", "Action 3", "Action 4"],
  "dont": ["Don't 1", "Don't 2", "Don't 3"],
  "home_care": ["Home tip 1", "Home tip 2", "Home tip 3"],
  "see_doctor": ["Red flag 1", "Red flag 2", "Red flag 3"],
  "specialist": "Which doctor to see"
}

For the first response and follow-up questions, respond in plain conversational text.
Only output the JSON block when you have gathered sufficient clinical information (after at least 4-5 exchanges).
IMPORTANT: Output ONLY the JSON with no surrounding text when giving the final diagnosis."""


def call_groq(messages):
    try:
        api_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for msg in messages:
            api_messages.append({"role": msg["role"], "content": msg["content"]})
        payload = {"model": MODEL, "messages": api_messages,
                   "temperature": 0.3, "max_tokens": 800}
        headers = {"Authorization": f"Bearer {GROQ_KEY}",
                   "Content-Type": "application/json"}
        resp = requests.post(GROQ_URL, headers=headers, json=payload, timeout=30)
        if resp.status_code != 200:
            return None, f"API Error {resp.status_code}: {resp.text[:300]}"
        data = resp.json()
        return data["choices"][0]["message"]["content"], None
    except Exception as e:
        return None, str(e)


def is_diagnosis_json(text):
    t = text.strip()
    if t.startswith("```"): t = t.split("```")[1]
    if t.startswith("json"): t = t[4:]
    t = t.strip()
    try:
        data = json.loads(t)
        return data.get("type") == "diagnosis", data
    except:
        return False, None


def render_diagnosis(data):
    severity  = data.get("severity", "Moderate")
    sev_color = {"Mild":"#43a047","Moderate":"#fb8c00","Severe":"#e53935"}.get(severity,"#888")
    sev_icon  = {"Mild":"🟢","Moderate":"🟡","Severe":"🔴"}.get(severity,"⚪")
    bar_cols  = ["#1565c0","#fb8c00","#9e9e9e"]

    st.markdown(f"""<div style="background:linear-gradient(135deg,#1565c0,#0d47a1);
        color:white;border-radius:16px;padding:20px 24px;margin:12px 0">
        <h2 style="margin:0">🏥 Dr. MediSense — Clinical Assessment</h2>
        <p style="opacity:0.85;margin:6px 0 0">AI-generated consultation report</p>
    </div>""", unsafe_allow_html=True)

    summary = data.get("summary", "")
    if summary:
        st.markdown(f"""<div style="background:#e3f2fd;border-left:6px solid #1565c0;
            border-radius:10px;padding:16px 18px;margin:10px 0;font-size:14px;line-height:1.7">
            📋 <b>Clinical Summary:</b><br><br>{summary}
        </div>""", unsafe_allow_html=True)

    st.markdown(f"""<div style="background:{sev_color};color:white;border-radius:12px;
        padding:14px;text-align:center;margin:10px 0">
        <h3 style="margin:0">{sev_icon} Severity: {severity}</h3>
        <p style="margin:5px 0 0;opacity:0.9;font-size:13px">{data.get("severity_reason","")}</p>
    </div>""", unsafe_allow_html=True)

    st.markdown("### 🔬 Differential Diagnosis")
    for i, cond in enumerate(data.get("conditions", [])[:3]):
        prob = cond.get("probability", 0)
        bc   = bar_cols[i] if i < 3 else "#ccc"
        rank = ["🥇 Most Likely","🥈 Second","🥉 Third"][i] if i < 3 else f"#{i+1}"
        st.markdown(f"""<div style="background:white;border:1px solid #e0e0e0;
            border-radius:12px;padding:14px 18px;margin:6px 0;
            box-shadow:0 2px 6px rgba(0,0,0,0.06)">
            <div style="display:flex;justify-content:space-between;align-items:center">
                <b style="font-size:15px">{cond.get('name','')}</b>
                <span style="background:{bc};color:white;padding:3px 12px;
                    border-radius:20px;font-weight:700">{prob}%</span>
            </div>
            <div style="background:#eee;border-radius:4px;height:8px;margin:8px 0">
                <div style="background:{bc};width:{prob}%;height:8px;border-radius:4px"></div>
            </div>
            <span style="font-size:12px;color:#888">{rank} · ICD-10: {cond.get('icd','—')}</span><br>
            <span style="font-size:13px;color:#555">{cond.get('description','')}</span>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### ✅ What TO DO")
        for item in data.get("do", []):
            st.markdown(f"""<div style="background:#e8f5e9;border-left:4px solid #43a047;
                border-radius:6px;padding:8px 13px;margin:4px 0;font-size:13px">✔️ {item}</div>""",
                unsafe_allow_html=True)
    with c2:
        st.markdown("### ❌ What NOT To Do")
        for item in data.get("dont", []):
            st.markdown(f"""<div style="background:#fce4ec;border-left:4px solid #e53935;
                border-radius:6px;padding:8px 13px;margin:4px 0;font-size:13px">✖️ {item}</div>""",
                unsafe_allow_html=True)

    st.markdown("### 🏠 Home Care")
    hc_cols = st.columns(2)
    for i, tip in enumerate(data.get("home_care", [])):
        with hc_cols[i % 2]:
            st.markdown(f"""<div style="background:#f3e5f5;border-left:4px solid #8e24aa;
                border-radius:6px;padding:8px 13px;margin:4px 0;font-size:13px">🏠 {tip}</div>""",
                unsafe_allow_html=True)

    st.markdown("### 🩺 When to See a Doctor")
    spec = data.get("specialist", "")
    if spec:
        st.markdown(f"""<div style="background:#e8f0fe;border-radius:8px;padding:10px 14px;
            font-size:13px;border-left:4px solid #1565c0;margin-bottom:8px">
            👨‍⚕️ <b>Recommended Specialist:</b> {spec}
        </div>""", unsafe_allow_html=True)
    for flag in data.get("see_doctor", []):
        emerg = any(w in flag.upper() for w in ["EMERGENCY","IMMEDIATELY","URGENT","SEVERE"])
        bg = "#ffebee" if emerg else "#fff3e0"
        bd = "#e53935" if emerg else "#fb8c00"
        st.markdown(f"""<div style="background:{bg};border-left:4px solid {bd};
            border-radius:6px;padding:8px 14px;margin:4px 0;font-size:13px">
            {"🚨" if emerg else "🩺"} {flag}</div>""", unsafe_allow_html=True)

    st.markdown("""<div style="background:#fff8e1;border:1px solid #ffc107;border-radius:8px;
        padding:12px 16px;font-size:12px;color:#555;margin-top:16px">
        ⚠️ <b>Disclaimer:</b> This is an AI-generated consultation summary for informational
        purposes only. It is NOT a prescription or confirmed medical diagnosis.
        Always consult a qualified doctor for proper treatment.
    </div>""", unsafe_allow_html=True)

    conds = data.get("conditions", [])
    return severity, conds[0].get("name","Consultation") if conds else "Consultation"


def show():
    st.markdown("""<div class="main-header">
        <h1>🤖 AI Doctor Chat</h1>
        <p>Real-time consultation powered by Groq AI — not predefined answers</p>
    </div>""", unsafe_allow_html=True)

    st.markdown("""<div style="background:#e8f5e9;border-radius:10px;padding:11px 16px;
        border-left:4px solid #43a047;font-size:13px;margin-bottom:16px">
        ✅ <b>Powered by Groq AI (Llama 3.3 70B)</b> — Dr. MediSense asks intelligent follow-up
        questions based on YOUR specific symptoms, not a fixed script. Every consultation is unique.
    </div>""", unsafe_allow_html=True)

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    if "chat_diagnosis_done" not in st.session_state:
        st.session_state.chat_diagnosis_done = False
    if "chat_diagnosis_data" not in st.session_state:
        st.session_state.chat_diagnosis_data = None

    col_btn, col_info = st.columns([1, 3])
    with col_btn:
        if st.button("🔄 New Consultation", use_container_width=True):
            st.session_state.chat_messages = []
            st.session_state.chat_diagnosis_done = False
            st.session_state.chat_diagnosis_data = None
            st.rerun()
    with col_info:
        count = len([m for m in st.session_state.chat_messages if m["role"] == "user"])
        st.markdown(f"""<div style="background:#f0f4ff;border-radius:8px;padding:8px 14px;
            font-size:13px;color:#555">
            💬 {count} exchanges so far
            {"— Dr. MediSense will give diagnosis soon" if count >= 4 else "— Keep answering for diagnosis"}
        </div>""", unsafe_allow_html=True)

    st.markdown("---")

    if not st.session_state.chat_messages:
        st.markdown("""<div style="background:linear-gradient(135deg,#e3f2fd,#bbdefb);
            border-radius:14px;padding:20px 24px;margin:8px 0;border-left:6px solid #1565c0">
            <div style="display:flex;align-items:center;gap:12px;margin-bottom:8px">
                <span style="font-size:2.5em">👨‍⚕️</span>
                <div>
                    <b style="font-size:1.1em;color:#1565c0">Dr. MediSense</b>
                    <span style="font-size:12px;color:#888;margin-left:8px">AI Doctor · Powered by Groq</span>
                </div>
            </div>
            <p style="margin:0;font-size:14px;line-height:1.7;color:#1a1a2e">
                Hello! I'm Dr. MediSense. I'm here to help assess your symptoms and provide
                health guidance. Please tell me — <b>what health concern brings you here today?</b>
                Describe your main symptom or complaint and I'll ask you some follow-up questions.
            </p>
        </div>""", unsafe_allow_html=True)

    for msg in st.session_state.chat_messages:
        if msg["role"] == "user":
            st.markdown(f"""<div style="display:flex;justify-content:flex-end;margin:8px 0">
                <div style="background:#1565c0;color:white;border-radius:16px 16px 4px 16px;
                    padding:12px 16px;max-width:75%;font-size:14px;line-height:1.6">
                    👤 {msg["content"]}
                </div>
            </div>""", unsafe_allow_html=True)
        elif msg["role"] == "assistant" and not msg.get("is_diagnosis"):
            st.markdown("**👨‍⚕️ Dr. MediSense:**")
            st.info(str(msg["content"]))

    if st.session_state.chat_diagnosis_done and st.session_state.chat_diagnosis_data:
        st.markdown("---")
        render_diagnosis(st.session_state.chat_diagnosis_data)
        return

    st.markdown("<br>", unsafe_allow_html=True)
    with st.container():
        user_input = st.text_input(
            "💬 Your message to Dr. MediSense",
            placeholder="Type your symptom or answer the doctor's question...",
            key=f"chat_input_{len(st.session_state.chat_messages)}"
        )
        send = st.button("📤 Send", use_container_width=True)

    if send and user_input.strip():
        st.session_state.chat_messages.append({
            "role": "user", "content": user_input.strip()
        })
        api_messages = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.chat_messages
            if not m.get("is_diagnosis")
        ]
        with st.spinner("👨‍⚕️ Dr. MediSense is thinking..."):
            response, error = call_groq(api_messages)

        if error:
            st.error(f"Could not connect: {error}")
        elif not response:
            st.warning("No response received. Please try again.")
        else:
            response_text = str(response).strip()
            is_dx, dx_data = is_diagnosis_json(response_text)
            if is_dx and dx_data:
                st.session_state.chat_diagnosis_done = True
                st.session_state.chat_diagnosis_data = dx_data
                severity  = dx_data.get("severity", "Moderate")
                conds     = dx_data.get("conditions", [])
                top_dx    = conds[0].get("name","Consultation") if conds else "Consultation"
                conf      = conds[0].get("probability", 70) if conds else 70
                symptom_q = st.session_state.chat_messages[0]["content"] if st.session_state.chat_messages else ""
                save_report(
                    user_id=st.session_state.user_id, module="AI Doctor Chat",
                    severity=severity, diagnosis=top_dx, confidence=conf,
                    full_report=f"Chief complaint: {symptom_q[:100]}",
                )
            else:
                st.session_state.chat_messages.append({
                    "role": "assistant", "content": response_text
                })
                st.markdown("**👨‍⚕️ Dr. MediSense:**")
                st.info(response_text)
                st.button("Continue →", key="continue_btn")
                st.stop()
        st.rerun()

    st.markdown("""<div class="footer">
        MediSense Pro · AI Doctor Chat · Groq AI · SWE1904 · VIT · R.Divya 21MIS0261
    </div>""", unsafe_allow_html=True)
