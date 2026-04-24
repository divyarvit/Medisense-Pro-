import streamlit as st, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from utils.database import init_db, login_user, register_user, get_alerts, get_reports
from utils.translations import lang_selector, t, LANG_OPTIONS

st.set_page_config(
    page_title="MediSense Pro — AI Disease Diagnosis",
    page_icon="🏥", layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Syne:wght@700;800&display=swap');

*, body { font-family: 'Plus Jakarta Sans', sans-serif !important; }

/* ── PAGE BACKGROUND ── */
.stApp { background: #f0f4f8 !important; }
[data-testid="stAppViewContainer"] > .main { background: #f0f4f8 !important; }
[data-testid="block-container"] { padding-top: 1.5rem !important; }

/* ── HERO SECTION ── */
.login-hero {
    background: linear-gradient(135deg, #0a2540 0%, #1565c0 55%, #0288d1 100%);
    border-radius: 28px; padding: 56px 40px 44px;
    text-align: center; color: white; margin-bottom: 32px;
    box-shadow: 0 20px 60px rgba(10,37,64,0.35);
    position: relative; overflow: hidden;
}
.login-hero::before {
    content: ''; position: absolute; top: -80px; right: -80px;
    width: 320px; height: 320px;
    background: radial-gradient(circle, rgba(255,255,255,0.08) 0%, transparent 70%);
    border-radius: 50%;
}
.login-hero::after {
    content: ''; position: absolute; bottom: -100px; left: -60px;
    width: 280px; height: 280px;
    background: radial-gradient(circle, rgba(2,136,209,0.2) 0%, transparent 70%);
    border-radius: 50%;
}
.login-hero .pulse-ring {
    position: absolute; top: 40px; left: 60px;
    width: 120px; height: 120px;
    border: 1px solid rgba(255,255,255,0.08); border-radius: 50%;
}
.login-hero h1 {
    font-family: 'Syne', sans-serif !important;
    font-size: 3.2em; font-weight: 800; margin: 0 0 10px;
    letter-spacing: -1px;
    text-shadow: 0 2px 20px rgba(0,0,0,0.2);
}
.login-hero .tagline { font-size: 1.1em; opacity: 0.85; margin: 0 0 24px; font-weight: 400; }
.login-hero .subtitle { font-size: 0.82em; opacity: 0.55; margin: 16px 0 0; }

.hero-icon {
    display: inline-flex; align-items: center; justify-content: center;
    width: 72px; height: 72px; border-radius: 20px;
    background: rgba(255,255,255,0.15);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255,255,255,0.25);
    font-size: 2em; margin-bottom: 16px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.15);
}

.feature-badge {
    display: inline-block;
    background: rgba(255,255,255,0.12);
    border: 1px solid rgba(255,255,255,0.22);
    border-radius: 100px; padding: 6px 16px;
    font-size: 12.5px; margin: 4px; font-weight: 500;
    backdrop-filter: blur(4px);
    transition: background 0.2s;
}

/* ── FEATURE CARDS ── */
.feat-card {
    background: white; border-radius: 20px;
    padding: 24px 18px; text-align: center;
    box-shadow: 0 4px 24px rgba(0,0,0,0.07);
    border: 1px solid rgba(21,101,192,0.08);
    border-top: 3px solid #1565c0;
    transition: all 0.25s ease;
    height: 150px;
}
.feat-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 12px 36px rgba(21,101,192,0.15);
    border-top-color: #0288d1;
}
.feat-card .feat-icon { font-size: 2.2em; margin-bottom: 8px; }
.feat-card .feat-title { font-size: 13px; font-weight: 700; color: #1565c0; margin-bottom: 4px; }
.feat-card .feat-desc { font-size: 11px; color: #888; line-height: 1.5; }

/* ── AUTH CARD ── */
.auth-card {
    background: white; border-radius: 24px;
    box-shadow: 0 8px 48px rgba(0,0,0,0.1);
    padding: 32px 36px 28px;
    border: 1px solid rgba(21,101,192,0.08);
}

/* ── TABS ── */
.stTabs [data-baseweb="tab-list"] {
    background: #f0f4f8 !important;
    border-radius: 12px !important;
    padding: 4px !important;
    gap: 4px !important;
    border-bottom: none !important;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    padding: 8px 20px !important;
    color: #666 !important;
}
.stTabs [aria-selected="true"] {
    background: white !important;
    color: #1565c0 !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08) !important;
}
.stTabs [data-baseweb="tab-highlight"] { display: none !important; }
.stTabs [data-baseweb="tab-border"] { display: none !important; }

/* ── INPUTS ── */
.stTextInput>div>div>input, .stNumberInput>div>div>input,
.stSelectbox>div>div>div {
    border-radius: 12px !important;
    border: 1.5px solid #e2e8f0 !important;
    padding: 11px 16px !important;
    font-size: 14px !important;
    background: #fafbfc !important;
    transition: all 0.2s !important;
}
.stTextInput>div>div>input:focus {
    border-color: #1565c0 !important;
    box-shadow: 0 0 0 3px rgba(21,101,192,0.1) !important;
    background: white !important;
}

/* ── SIDEBAR ── */
[data-testid="stSidebar"] {
    background: linear-gradient(175deg, #0a2540 0%, #0d3b6e 40%, #1565c0 100%) !important;
    border-right: none !important;
}
[data-testid="stSidebar"] > div:first-child {
    padding-top: 0 !important;
}
.sidebar-profile {
    background: rgba(255,255,255,0.1);
    backdrop-filter: blur(12px);
    color: white; border-radius: 16px; padding: 18px 14px;
    margin-bottom: 14px; text-align: center;
    border: 1px solid rgba(255,255,255,0.15);
}
.sidebar-avatar {
    width: 52px; height: 52px; border-radius: 14px;
    background: linear-gradient(135deg, rgba(255,255,255,0.25), rgba(255,255,255,0.1));
    display: inline-flex; align-items: center; justify-content: center;
    font-size: 1.6em; margin-bottom: 8px;
    border: 1px solid rgba(255,255,255,0.2);
}

/* ── NAV ── */
.nav-section {
    color: rgba(255,255,255,0.4);
    font-size: 9.5px; font-weight: 700;
    letter-spacing: 1.5px; text-transform: uppercase;
    padding: 12px 4px 4px; margin: 0;
}
.nav-divider {
    border: none;
    border-top: 1px solid rgba(255,255,255,0.08);
    margin: 8px 0;
}

/* ── NAV BUTTONS ── */
.stButton>button {
    background: transparent !important;
    color: rgba(255,255,255,0.8) !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 9px 12px !important;
    font-weight: 500 !important;
    font-size: 13px !important;
    width: 100% !important;
    text-align: left !important;
    transition: all 0.15s ease !important;
    box-shadow: none !important;
}
.stButton>button:hover {
    background: rgba(255,255,255,0.12) !important;
    color: white !important;
    transform: translateX(2px) !important;
    box-shadow: none !important;
}

/* ── ACTION BUTTONS (inside pages) ── */
div[data-testid="stVerticalBlock"] > div > div > div > .stButton>button {
    color: white !important;
    background: linear-gradient(135deg, #1565c0, #0a2540) !important;
    color: white !important;
    border-radius: 12px !important;
    padding: 12px 28px !important;
    font-weight: 700 !important;
    font-size: 14px !important;
    box-shadow: 0 4px 16px rgba(21,101,192,0.3) !important;
    text-align: center !important;
    letter-spacing: 0.3px !important;
}
div[data-testid="stVerticalBlock"] > div > div > div > .stButton>button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 24px rgba(21,101,192,0.45) !important;
}

/* ── METRIC CARD ── */
.metric-card {
    background: white; border-radius: 16px;
    padding: 22px 16px; text-align: center;
    box-shadow: 0 2px 16px rgba(0,0,0,0.07);
    border: 1px solid #eef2f7;
    transition: all 0.2s;
}
.metric-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 8px 28px rgba(21,101,192,0.12);
}

/* ── DEMO BOX ── */
.demo-box {
    background: linear-gradient(135deg, #e8f4fd, #f0f9ff);
    border: 1px solid #b3d9f7;
    border-radius: 14px; padding: 14px 18px;
    font-size: 13px; color: #0a2540;
    margin-top: 8px;
}

/* ── MAIN HEADER (logged in) ── */
.main-header {
    background: linear-gradient(135deg, #0a2540 0%, #1565c0 60%, #0288d1 100%);
    padding: 28px 36px; border-radius: 20px; color: white;
    text-align: center; margin-bottom: 24px;
    box-shadow: 0 8px 32px rgba(10,37,64,0.3);
}
.main-header h1 {
    font-family: 'Syne', sans-serif !important;
    margin: 0; font-size: 2.2em; font-weight: 800; letter-spacing: -0.5px;
}
.main-header p { margin: 8px 0 0; opacity: 0.85; font-size: 1.05em; }

/* ── FOOTER ── */
.footer {
    text-align: center; color: #bbb; font-size: 11px;
    margin-top: 36px; padding-top: 18px;
    border-top: 1px solid #e8ecf4;
}

/* ── SCROLLBAR ── */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: #f0f4f8; }
::-webkit-scrollbar-thumb { background: #1565c0; border-radius: 6px; }

/* ── ALERTS / INFO ── */
.stAlert { border-radius: 12px !important; }

/* ── LOGIN BUTTON SPECIFIC ── */
button[kind="primary"], .stButton>button[data-testid="baseButton-secondary"] {
    color: white !important;
}
/* Force login/register buttons white text */
#lbtn, #rbtn { color: white !important; }

/* ── SECTION DIVIDER ── */
.section-label {
    font-size: 11px; font-weight: 700; letter-spacing: 1.5px;
    text-transform: uppercase; color: #94a3b8;
    margin: 20px 0 10px; padding-bottom: 6px;
    border-bottom: 1px solid #e8ecf4;
}
</style>""", unsafe_allow_html=True)

# ── Init DB & session ──────────────────────────────────────────────────────────
init_db()
for k, v in [("logged_in", False), ("user_id", None), ("username", ""),
             ("full_name", ""), ("city", ""), ("page", "🏠 Dashboard")]:
    if k not in st.session_state:
        st.session_state[k] = v

# ── LOGIN / REGISTER PAGE ─────────────────────────────────────────────────────
def auth_page():
    # ── HERO ──────────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="login-hero">
        <div class="pulse-ring"></div>
        <div class="hero-icon">🏥</div>
        <h1>MediSense Pro</h1>
        <p class="tagline">AI-Powered Disease Diagnosis &amp; Intelligent Health Recommendations</p>
        <div style="margin: 20px 0 8px">
            <span class="feature-badge">🔬 6 Disease Modules</span>
            <span class="feature-badge">🤖 AI Doctor Chat</span>
            <span class="feature-badge">📊 Health Analytics</span>
            <span class="feature-badge">📄 PDF Reports</span>
            <span class="feature-badge">🧠 Explainable AI</span>
            <span class="feature-badge">👨‍👩‍👧 Family Health Vault</span>
        </div>
        <p class="subtitle" style="margin-top:16px">
            VIT Capstone Project · SWE1904 · R.Divya — 21MIS0261 · Guide: Prof. Benjula Anbu Malar M B
        </p>
    </div>""", unsafe_allow_html=True)

    # ── FEATURE CARDS ─────────────────────────────────────────────────────────
    feat_cols = st.columns(4)
    features = [
        ("🔬", "6 Disease Modules",   "Diabetes · Heart · Parkinson's · Kidney · Thyroid · General"),
        ("🧠", "Explainable AI",      "Every prediction shows WHY — factor-by-factor breakdown"),
        ("🤖", "AI Doctor Chat",      "Real-time consultation powered by Groq AI"),
        ("👨‍👩‍👧", "Family Health Vault", "Manage entire family health from one account"),
    ]
    for col, (icon, title, desc) in zip(feat_cols, features):
        with col:
            st.markdown(f"""<div class="feat-card">
                <div class="feat-icon">{icon}</div>
                <div class="feat-title">{title}</div>
                <div class="feat-desc">{desc}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── AUTH CARD ─────────────────────────────────────────────────────────────
    _, col_mid, _ = st.columns([1, 1.6, 1])
    with col_mid:
        st.markdown('<div class="auth-card">', unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["🔐  Login", "📝  Register"])

        with tab1:
            st.markdown("""<div style="margin-bottom:20px;margin-top:8px">
                <h3 style="margin:0 0 4px;font-size:1.3em;color:#0a2540;font-weight:700">Welcome back! 👋</h3>
                <p style="margin:0;color:#94a3b8;font-size:13px">Sign in to access your health dashboard</p>
            </div>""", unsafe_allow_html=True)

            uname = st.text_input("👤  Username", placeholder="Enter your username", key="lu")
            passw = st.text_input("🔒  Password", type="password", placeholder="Enter your password", key="lp")
            st.markdown("<br>", unsafe_allow_html=True)

            if st.button("🔐  Sign In to MediSense Pro", key="lbtn", use_container_width=True):
                if uname and passw:
                    user = login_user(uname, passw)
                    if user:
                        st.session_state.update({
                            "logged_in": True, "user_id": user[0],
                            "username": user[1], "full_name": user[3] or user[1],
                            "city": user[9] or ""})
                        st.rerun()
                    else:
                        st.error("❌ Invalid username or password.")
                else:
                    st.warning("⚠️ Please fill in both fields.")

            st.markdown("""<div class="demo-box" style="margin-top:16px">
                🔑 <b>Quick Demo:</b>&nbsp; Username: <code style="background:#dbeafe;color:#1d4ed8;
                padding:2px 7px;border-radius:5px">demo</code>&nbsp;&nbsp;
                Password: <code style="background:#dbeafe;color:#1d4ed8;
                padding:2px 7px;border-radius:5px">demo123</code>
            </div>""", unsafe_allow_html=True)

        with tab2:
            st.markdown("""<div style="margin-bottom:20px">
                <h3 style="margin:0 0 4px;font-size:1.3em;color:#0a2540;font-weight:700">Create your health profile 🩺</h3>
                <p style="margin:0;color:#94a3b8;font-size:13px">Join MediSense Pro — it's free</p>
            </div>""", unsafe_allow_html=True)

            a1, a2 = st.columns(2)
            with a1:
                rn  = st.text_input("Full Name *",  placeholder="Your full name")
                ru  = st.text_input("Username *",   placeholder="Choose username")
                rp  = st.text_input("Password *",   type="password", placeholder="Min 6 chars")
                ra  = st.number_input("Age *", 1, 120, 20)
            with a2:
                rg  = st.selectbox("Gender *", ["Female", "Male", "Other"])
                rb  = st.selectbox("Blood Group", ["O+","O-","A+","A-","B+","B-","AB+","AB-","Unknown"])
                rc  = st.text_input("City *",    placeholder="Your city")
                rph = st.text_input("Phone",     placeholder="Optional")
            re = st.text_input("Email", placeholder="Optional")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🚀  Create Account & Get Started", key="rbtn", use_container_width=True):
                if rn and ru and rp and rc:
                    if len(rp) < 6:
                        st.error("❌ Password must be at least 6 characters.")
                    else:
                        ok, msg = register_user(ru, rp, rn, ra, rg, rb, rph, re, rc)
                        if ok:
                            st.success("✅ Account created! Please switch to Login tab.")
                            st.balloons()
                        else:
                            st.error(f"❌ {msg}")
                else:
                    st.warning("⚠️ Please fill all required (*) fields.")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("""<div class="footer">
        ⚕️ MediSense Pro is for informational and educational purposes only.
        Not a substitute for professional medical advice. Always consult a qualified doctor.
    </div>""", unsafe_allow_html=True)


# ── NAV BUTTON HELPER ─────────────────────────────────────────────────────────
def _nav_btn(icon, label, page_key=None):
    """Render a single nav button. page_key defaults to '{icon} {label}'"""
    key = page_key or f"{icon} {label}"
    is_active = st.session_state.page == key

    # Highlight active page
    if is_active:
        st.markdown(f"""<div style="background:rgba(255,255,255,0.22);border-radius:8px;
            padding:7px 12px;margin:1px 0;color:white;font-size:13px;font-weight:600;
            border-left:3px solid white">
            {icon}&nbsp;&nbsp;{label}
        </div>""", unsafe_allow_html=True)
        # Invisible button to keep state working
        if st.button(f"{icon}  {label}", key=f"nav_{label}", use_container_width=True):
            pass
    else:
        if st.button(f"{icon}  {label}", key=f"nav_{label}", use_container_width=True):
            st.session_state.page = key
            st.rerun()

def _section(title):
    st.markdown(f'<p class="nav-section">{title}</p>', unsafe_allow_html=True)

def _divider():
    st.markdown('<hr class="nav-divider">', unsafe_allow_html=True)


# ── MAIN APP ──────────────────────────────────────────────────────────────────
def main_app():
    uid   = st.session_state.user_id
    uname = st.session_state.full_name
    city  = st.session_state.city or "City not set"

    # ── Get report count for sidebar badge ────────────────────────────
    try:
        reports     = get_reports(uid)
        total_rpts  = len(reports)
        severe_rpts = sum(1 for r in reports if r[3] == "Severe")
    except:
        total_rpts = severe_rpts = 0

    # ── SIDEBAR ───────────────────────────────────────────────────────
    with st.sidebar:

        # Profile card
        st.markdown(f"""<div class="sidebar-profile">
            <div class="sidebar-avatar">👤</div>
            <h3 style="margin:4px 0 2px;font-size:0.95em;font-weight:700;color:white">{uname}</h3>
            <p style="opacity:0.6;margin:0;font-size:0.75em;color:white">📍 {city}</p>
            {f'<div style="margin-top:10px;font-size:11px;background:rgba(255,255,255,0.12);border-radius:8px;padding:5px 10px;color:rgba(255,255,255,0.85)">📋 {total_rpts} report{"s" if total_rpts!=1 else ""}{" &nbsp;·&nbsp; 🔴 "+str(severe_rpts)+" severe" if severe_rpts else ""}</div>' if total_rpts else '<div style="margin-top:10px;font-size:11px;opacity:0.45;color:white">No reports yet</div>'}
        </div>""", unsafe_allow_html=True)

        # ── Section: Home ─────────────────────────────────────────────
        _section("Home")
        _nav_btn("🏠", "Dashboard")
        _nav_btn("📈", "Health Analytics")

        _divider()

        # ── Section: Diagnose ─────────────────────────────────────────
        _section("Diagnose")
        _nav_btn("🔬", "General Diagnosis")
        _nav_btn("🩸", "Diabetes",          "🩸 Diabetes Prediction")
        _nav_btn("❤️", "Heart Disease")
        _nav_btn("🧠", "Parkinson's",       "🧠 Parkinson's Disease")
        _nav_btn("🫘", "Kidney Disease")
        _nav_btn("🦋", "Thyroid Disorder")

        _divider()

        # ── Section: Monitor ──────────────────────────────────────────
        _section("Monitor & Track")
        _nav_btn("⚖️", "BMI Calculator")
        _nav_btn("📅", "Symptom Tracker")
        _nav_btn("📊", "Health Report Card")

        _divider()

        # ── Section: AI Tools ─────────────────────────────────────────
        _section("AI Tools")
        _nav_btn("🤖", "AI Doctor Chat")
        _nav_btn("📸", "Visual Diagnosis")

        _divider()

        # ── Section: Records ──────────────────────────────────────────
        _section("Records")
        _nav_btn("📋", "My Reports")
        _nav_btn("🖨️", "Prescription Card")
        _nav_btn("💊", "Medicine Reminder")

        _divider()

        # ── Section: Family ───────────────────────────────────────────
        _section("My Family")
        _nav_btn("👨‍👩‍👧", "Family Vault")

        _divider()

        # ── Section: Doctor ───────────────────────────────────────────
        _section("Doctor Portal")
        _nav_btn("👨‍⚕️", "Doctor Dashboard")

        _divider()

        # ── Language + Alerts + Logout ────────────────────────────────
        lang_selector()

        try:
            unread = get_alerts(uid, unread_only=True)
            if unread:
                st.markdown(f"""<div style="background:#e53935;color:white;border-radius:8px;
                    padding:7px 12px;text-align:center;font-size:12px;margin:6px 0">
                    🔔 {len(unread)} unread alert{'s' if len(unread)>1 else ''}
                </div>""", unsafe_allow_html=True)
        except:
            pass

        if st.button("🚪  Logout", key="nav_logout", use_container_width=True):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

        st.markdown("""<div style="text-align:center;color:rgba(255,255,255,0.4);
            font-size:10px;margin-top:16px;line-height:1.8">
            MediSense Pro v12<br>SWE1904 · VIT Vellore<br>
            R.Divya · 21MIS0261<br>
            <span style="color:rgba(255,255,255,0.25)">⚠️ Not a medical device</span>
        </div>""", unsafe_allow_html=True)

    # ── PAGE ROUTING ──────────────────────────────────────────────────
    page = st.session_state.page

    if   page == "🏠 Dashboard":           from pages.dashboard          import show; show()
    elif page == "📈 Health Analytics":     from pages.analytics          import show; show()

    elif page == "🔬 General Diagnosis":    from pages.general            import show; show()
    elif page == "🩸 Diabetes Prediction":  from pages.diabetes           import show; show()
    elif page == "❤️ Heart Disease":        from pages.heart              import show; show()
    elif page == "🧠 Parkinson's Disease":  from pages.parkinsons         import show; show()
    elif page == "🫘 Kidney Disease":       from pages.kidney             import show; show()
    elif page == "🦋 Thyroid Disorder":     from pages.thyroid            import show; show()

    elif page == "⚖️ BMI Calculator":       from pages.bmi                import show; show()
    elif page == "📅 Symptom Tracker":      from pages.symptom_tracker    import show; show()
    elif page == "📊 Health Report Card":   from pages.health_report_card import show; show()

    elif page == "🤖 AI Doctor Chat":       from pages.ai_chat            import show; show()
    elif page == "📸 Visual Diagnosis":     from pages.photo_diagnosis    import show; show()

    elif page == "📋 My Reports":           from pages.reports            import show; show()
    elif page == "🖨️ Prescription Card":    from pages.prescription       import show; show()
    elif page == "💊 Medicine Reminder":    from pages.medicine_reminder  import show; show()

    elif page == "👨‍👩‍👧 Family Vault":         from pages.family_vault       import show; show()

    elif page == "👨‍⚕️ Doctor Dashboard":     from pages.doctor_dashboard   import show; show()


if st.session_state.logged_in:
    main_app()
else:
    auth_page()
