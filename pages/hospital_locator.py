"""
Feature 5: Nearest Hospital Locator
After any severe diagnosis — which hospital? which doctor? how far?
Answers the most practical question every patient has.
State-wise hospital database for India — works offline.
"""
import streamlit as st

# Curated hospital database — major cities across India
# Format: city → list of hospitals with specialities
HOSPITALS = {
    "Tirupati": [
        {"name":"Sri Venkateswara Institute of Medical Sciences (SVIMS)",
         "type":"Government","address":"Alipiri Road, Tirupati",
         "phone":"0877-2287777","distance":"2.1 km",
         "specialities":["Cardiology","Neurology","Oncology","General Medicine","Diabetology"],
         "emergency":True,"rating":4.3},
        {"name":"Ruia Government General Hospital",
         "type":"Government","address":"Tilak Road, Tirupati",
         "phone":"0877-2225101","distance":"1.8 km",
         "specialities":["General Medicine","Surgery","Orthopaedics","Gynaecology"],
         "emergency":True,"rating":4.0},
        {"name":"Apollo Speciality Hospital Tirupati",
         "type":"Private","address":"Tiruchanur Road, Tirupati",
         "phone":"0877-6671234","distance":"3.4 km",
         "specialities":["Cardiology","Neurology","Diabetology","Orthopaedics","Dermatology"],
         "emergency":True,"rating":4.5},
        {"name":"Narayana Medical College Hospital",
         "type":"Private","address":"Chinthareddypalem, Nellore",
         "phone":"0861-2339999","distance":"5.2 km",
         "specialities":["Cardiology","Diabetology","Neurology","General Surgery"],
         "emergency":True,"rating":4.2},
    ],
    "Chennai": [
        {"name":"Government General Hospital (GGH)",
         "type":"Government","address":"Park Town, Chennai 600003",
         "phone":"044-25305000","distance":"—",
         "specialities":["All Specialities","Emergency","Cardiology","Neurology"],
         "emergency":True,"rating":4.1},
        {"name":"Apollo Hospitals Chennai",
         "type":"Private","address":"Greams Road, Chennai",
         "phone":"044-28290200","distance":"—",
         "specialities":["Cardiology","Neurology","Oncology","Diabetology","Transplant"],
         "emergency":True,"rating":4.7},
        {"name":"MIOT International",
         "type":"Private","address":"Manapakkam, Chennai",
         "phone":"044-42002288","distance":"—",
         "specialities":["Orthopaedics","Cardiology","Neurology","Spine Surgery"],
         "emergency":True,"rating":4.6},
        {"name":"Madras Medical Mission",
         "type":"Private","address":"Mogappair, Chennai",
         "phone":"044-26565956","distance":"—",
         "specialities":["Cardiology","Cardiac Surgery","Paediatric Cardiology"],
         "emergency":True,"rating":4.5},
    ],
    "Bangalore": [
        {"name":"Bowring & Lady Curzon Hospital",
         "type":"Government","address":"Shivaji Nagar, Bengaluru",
         "phone":"080-25561066","distance":"—",
         "specialities":["General Medicine","Surgery","Neurology","Cardiology"],
         "emergency":True,"rating":3.9},
        {"name":"Manipal Hospital (Old Airport Road)",
         "type":"Private","address":"HAL Airport Road, Bengaluru",
         "phone":"080-25023344","distance":"—",
         "specialities":["Cardiology","Neurology","Oncology","Transplant","Diabetology"],
         "emergency":True,"rating":4.6},
        {"name":"Fortis Hospital Bangalore",
         "type":"Private","address":"Bannerghatta Road, Bengaluru",
         "phone":"080-66214444","distance":"—",
         "specialities":["Cardiology","Neurology","Orthopaedics","Oncology"],
         "emergency":True,"rating":4.5},
    ],
    "Hyderabad": [
        {"name":"Osmania General Hospital",
         "type":"Government","address":"Afzalgunj, Hyderabad",
         "phone":"040-24600136","distance":"—",
         "specialities":["General Medicine","Surgery","Cardiology","Neurology"],
         "emergency":True,"rating":4.0},
        {"name":"NIMS (Nizams Institute)",
         "type":"Government","address":"Punjagutta, Hyderabad",
         "phone":"040-23489000","distance":"—",
         "specialities":["Cardiology","Neurology","Oncology","Nephrology"],
         "emergency":True,"rating":4.3},
        {"name":"Apollo Hospitals Jubilee Hills",
         "type":"Private","address":"Jubilee Hills, Hyderabad",
         "phone":"040-23607777","distance":"—",
         "specialities":["Cardiology","Neurology","Oncology","Transplant","Diabetology"],
         "emergency":True,"rating":4.6},
        {"name":"Yashoda Hospitals Secunderabad",
         "type":"Private","address":"Alexander Road, Secunderabad",
         "phone":"040-45674567","distance":"—",
         "specialities":["Cardiology","Diabetology","Orthopaedics","General Surgery"],
         "emergency":True,"rating":4.4},
    ],
    "Mumbai": [
        {"name":"KEM Hospital",
         "type":"Government","address":"Acharya Donde Marg, Parel",
         "phone":"022-24136051","distance":"—",
         "specialities":["All Specialities","Trauma","Cardiology","Neurology"],
         "emergency":True,"rating":4.2},
        {"name":"Tata Memorial Hospital",
         "type":"Government","address":"Dr. E Borges Road, Parel",
         "phone":"022-24177000","distance":"—",
         "specialities":["Oncology","Cancer Surgery","Radiotherapy"],
         "emergency":False,"rating":4.8},
        {"name":"Kokilaben Dhirubhai Ambani Hospital",
         "type":"Private","address":"Four Bungalows, Andheri West",
         "phone":"022-30999999","distance":"—",
         "specialities":["Cardiology","Neurology","Transplant","Oncology","Robotic Surgery"],
         "emergency":True,"rating":4.7},
        {"name":"Lilavati Hospital",
         "type":"Private","address":"Bandra West, Mumbai",
         "phone":"022-26751000","distance":"—",
         "specialities":["Cardiology","Neurology","Orthopaedics","Diabetology"],
         "emergency":True,"rating":4.5},
    ],
    "Delhi": [
        {"name":"AIIMS New Delhi",
         "type":"Government","address":"Ansari Nagar, New Delhi",
         "phone":"011-26588500","distance":"—",
         "specialities":["All Specialities","Research","Cardiology","Neurology","Oncology"],
         "emergency":True,"rating":4.8},
        {"name":"Safdarjung Hospital",
         "type":"Government","address":"Ansari Nagar West, New Delhi",
         "phone":"011-26165060","distance":"—",
         "specialities":["General Medicine","Surgery","Cardiology","Orthopaedics"],
         "emergency":True,"rating":4.1},
        {"name":"Max Super Speciality Hospital Saket",
         "type":"Private","address":"Press Enclave Road, Saket",
         "phone":"011-26515050","distance":"—",
         "specialities":["Cardiology","Neurology","Oncology","Transplant","Diabetology"],
         "emergency":True,"rating":4.6},
        {"name":"Fortis Escorts Heart Institute",
         "type":"Private","address":"Okhla Road, New Delhi",
         "phone":"011-47135000","distance":"—",
         "specialities":["Cardiology","Cardiac Surgery","Electrophysiology"],
         "emergency":True,"rating":4.7},
    ],
    "Kolkata": [
        {"name":"SSKM (PG Hospital)",
         "type":"Government","address":"AJC Bose Road, Kolkata",
         "phone":"033-22041942","distance":"—",
         "specialities":["All Specialities","Cardiology","Neurology","Oncology"],
         "emergency":True,"rating":4.1},
        {"name":"Apollo Gleneagles Hospitals",
         "type":"Private","address":"Canal Circular Road, Kolkata",
         "phone":"033-23203040","distance":"—",
         "specialities":["Cardiology","Neurology","Oncology","Transplant"],
         "emergency":True,"rating":4.5},
    ],
    "Pune": [
        {"name":"Sassoon General Hospital",
         "type":"Government","address":"Pune Station, Pune",
         "phone":"020-26128000","distance":"—",
         "specialities":["General Medicine","Surgery","Cardiology","Emergency"],
         "emergency":True,"rating":3.9},
        {"name":"Ruby Hall Clinic",
         "type":"Private","address":"Sassoon Road, Pune",
         "phone":"020-26163391","distance":"—",
         "specialities":["Cardiology","Neurology","Oncology","Orthopaedics"],
         "emergency":True,"rating":4.5},
        {"name":"Jehangir Hospital",
         "type":"Private","address":"Sassoon Road, Pune",
         "phone":"020-66814444","distance":"—",
         "specialities":["Cardiology","Diabetology","Orthopaedics","General Surgery"],
         "emergency":True,"rating":4.4},
    ],
}

SPECIALIST_TO_SPEC = {
    "Cardiologist":      "Cardiology",
    "Diabetologist":     "Diabetology",
    "Endocrinologist":   "Diabetology",
    "Neurologist":       "Neurology",
    "Oncologist":        "Oncology",
    "Orthopaedic":       "Orthopaedics",
    "Dermatologist":     "Dermatology",
    "Gynaecologist":     "Gynaecology",
    "General Physician": "General Medicine",
    "General Surgeon":   "General Surgery",
}

DIAGNOSIS_SPECIALIST = {
    "Diabetes":       ("Diabetologist / Endocrinologist","Diabetology"),
    "Heart Disease":  ("Cardiologist","Cardiology"),
    "Parkinson":      ("Neurologist","Neurology"),
    "Fever":          ("General Physician","General Medicine"),
    "Cardiac":        ("Cardiologist","Cardiology"),
    "Thyroid":        ("Endocrinologist","Diabetology"),
    "Skin":           ("Dermatologist","Dermatology"),
    "Cancer":         ("Oncologist","Oncology"),
}

def get_specialists_needed(diagnosis_text):
    for keyword, (specialist, spec) in DIAGNOSIS_SPECIALIST.items():
        if keyword.lower() in diagnosis_text.lower():
            return specialist, spec
    return "General Physician", "General Medicine"

def show():
    st.markdown("""<div class="main-header">
        <h1>🏥 Nearest Hospital Locator</h1>
        <p>Find the right hospital and specialist for your diagnosis — with contact details</p>
    </div>""", unsafe_allow_html=True)

    st.markdown("""<div style="background:#e8f5e9;border-left:5px solid #43a047;
        border-radius:10px;padding:12px 18px;font-size:14px;margin-bottom:16px">
        🗺️ <b>What this does:</b> After a diagnosis, every patient asks — "which hospital should I go to?"
        This feature answers that. Find hospitals in your city that have the right specialist,
        with phone numbers, type (government/private), and the exact department you need.
    </div>""", unsafe_allow_html=True)

    # City and condition selector
    c1, c2 = st.columns(2)
    with c1:
        city = st.selectbox("📍 Your City", sorted(HOSPITALS.keys()),
                             index=0)
    with c2:
        conditions_list = ["Select from recent diagnosis","Diabetes / Endocrinology",
                           "Heart Disease / Cardiology","Parkinson's / Neurology",
                           "Cancer / Oncology","Bone & Joint / Orthopaedics",
                           "Skin Disease / Dermatology","General Illness / Fever",
                           "Women's Health / Gynaecology","All Hospitals (Emergency)"]
        condition = st.selectbox("🏥 I need a specialist for", conditions_list)

    # Determine required speciality
    spec_filter = None
    if condition != "Select from recent diagnosis" and condition != "All Hospitals (Emergency)":
        cond_map = {
            "Diabetes / Endocrinology":    "Diabetology",
            "Heart Disease / Cardiology":  "Cardiology",
            "Parkinson's / Neurology":     "Neurology",
            "Cancer / Oncology":           "Oncology",
            "Bone & Joint / Orthopaedics": "Orthopaedics",
            "Skin Disease / Dermatology":  "Dermatology",
            "General Illness / Fever":     "General Medicine",
            "Women's Health / Gynaecology":"Gynaecology",
        }
        spec_filter = cond_map.get(condition)

    # Filters
    f1, f2 = st.columns(2)
    with f1:
        hosp_type = st.selectbox("🏥 Hospital Type", ["All","Government Only","Private Only"])
    with f2:
        emerg_only = st.checkbox("🚨 Show Emergency-ready hospitals only", value=False)

    hospitals = HOSPITALS.get(city, [])

    # Apply filters
    filtered = []
    for h in hospitals:
        if hosp_type == "Government Only" and h["type"] != "Government": continue
        if hosp_type == "Private Only"    and h["type"] != "Private":    continue
        if emerg_only and not h["emergency"]: continue
        if spec_filter and spec_filter not in h["specialities"] and \
           "All Specialities" not in h["specialities"]: continue
        filtered.append(h)

    st.markdown("---")

    if not filtered:
        st.warning("No hospitals match your filters. Try adjusting the filters above.")
        return

    # Highlight required speciality
    if spec_filter:
        st.markdown(f"""<div style="background:#e3f2fd;border-left:5px solid #1565c0;
            border-radius:10px;padding:12px 18px;font-size:14px;margin-bottom:12px">
            🔍 Showing hospitals in <b>{city}</b> with
            <b style="color:#1565c0">{spec_filter}</b> department
            · <b>{len(filtered)} hospital(s) found</b>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""<div style="background:#f0f4ff;border-radius:10px;padding:10px 16px;
            font-size:13px;margin-bottom:12px">
            Showing <b>{len(filtered)} hospital(s)</b> in {city}
        </div>""", unsafe_allow_html=True)

    # Hospital cards
    for h in filtered:
        type_color = "#1565c0" if h["type"]=="Government" else "#6a1b9a"
        type_bg    = "#e3f2fd" if h["type"]=="Government" else "#f3e5f5"
        rating     = h.get("rating", 4.0)
        stars      = "⭐" * int(rating) + ("½" if rating % 1 >= 0.5 else "")

        matched_specs = [s for s in h["specialities"]
                         if spec_filter and (spec_filter in s or s=="All Specialities")]

        with st.expander(f"🏥 {h['name']} — {h['type']} · ⭐{rating}", expanded=True):
            r1, r2 = st.columns([2.5, 1])
            with r1:
                st.markdown(f"""
                <div>
                    <h3 style="margin:0 0 4px;color:#1a1a2e">{h['name']}</h3>
                    <span style="background:{type_bg};color:{type_color};padding:3px 10px;
                        border-radius:12px;font-size:12px;font-weight:600">
                        {h['type']} Hospital
                    </span>
                    {"<span style='background:#ffebee;color:#e53935;padding:3px 10px;border-radius:12px;font-size:12px;margin-left:6px'>🚨 24/7 Emergency</span>" if h['emergency'] else ""}
                    <p style="margin:10px 0 4px;font-size:13px;color:#555">
                        📍 {h['address']}
                    </p>
                    <p style="margin:0;font-size:14px;color:#1565c0;font-weight:700">
                        📞 {h['phone']}
                    </p>
                </div>""", unsafe_allow_html=True)

            with r2:
                st.markdown(f"""<div style="background:#f8f9fa;border-radius:10px;
                    padding:12px;text-align:center;border:1px solid #e0e0e0">
                    <p style="margin:0;font-size:11px;color:#888">RATING</p>
                    <p style="margin:4px 0;font-size:1.6em">⭐{rating}</p>
                    {f'<p style="margin:0;font-size:11px;color:#888">Distance</p><p style="margin:2px 0;font-weight:700;color:#1565c0">{h["distance"]}</p>' if h["distance"]!="—" else ""}
                </div>""", unsafe_allow_html=True)

            # Specialities
            st.markdown("**🏥 Available Specialities:**")
            spec_html = "".join([
                f'<span style="background:{"#e8f5e9" if s==spec_filter or "All" in s else "#f0f4ff"};'
                f'color:{"#2e7d32" if s==spec_filter or "All" in s else "#1565c0"};'
                f'border:1px solid {"#a5d6a7" if s==spec_filter or "All" in s else "#90caf9"};'
                f'padding:3px 10px;border-radius:12px;font-size:12px;margin:2px;display:inline-block">'
                f'{"✅ " if s==spec_filter else ""}{s}</span>'
                for s in h["specialities"]
            ])
            st.markdown(f'<div style="margin:6px 0">{spec_html}</div>', unsafe_allow_html=True)

            # Action buttons
            b1, b2, b3 = st.columns(3)
            with b1:
                st.markdown(f"""<div style="background:#1565c0;color:white;border-radius:8px;
                    padding:10px;text-align:center;font-size:13px;font-weight:600">
                    📞 Call: {h['phone']}
                </div>""", unsafe_allow_html=True)
            with b2:
                maps_url = f"https://maps.google.com/?q={h['name'].replace(' ','+')}+{city}"
                st.markdown(f"""<a href="{maps_url}" target="_blank"
                    style="text-decoration:none">
                    <div style="background:#43a047;color:white;border-radius:8px;
                        padding:10px;text-align:center;font-size:13px;font-weight:600">
                        🗺️ Open in Google Maps
                    </div></a>""", unsafe_allow_html=True)
            with b3:
                emerg_color = "#e53935" if h["emergency"] else "#9e9e9e"
                st.markdown(f"""<div style="background:{emerg_color};color:white;border-radius:8px;
                    padding:10px;text-align:center;font-size:13px;font-weight:600">
                    {"🚨 24/7 Emergency" if h["emergency"] else "⏰ Appointment Only"}
                </div>""", unsafe_allow_html=True)

    # Emergency helpline
    st.markdown("---")
    st.markdown("""<div style="background:#e53935;color:white;border-radius:14px;
        padding:20px 24px;text-align:center">
        <h2 style="margin:0">🚨 Emergency? Call NOW</h2>
        <div style="display:flex;justify-content:center;gap:40px;margin-top:12px;font-size:1.1em">
            <div><b>108</b><br><span style="opacity:0.85;font-size:12px">Ambulance (Free)</span></div>
            <div><b>104</b><br><span style="opacity:0.85;font-size:12px">Health Helpline</span></div>
            <div><b>102</b><br><span style="opacity:0.85;font-size:12px">Maternal/Child</span></div>
            <div><b>112</b><br><span style="opacity:0.85;font-size:12px">National Emergency</span></div>
        </div>
    </div>""", unsafe_allow_html=True)

    st.markdown("""<div class="footer">
        MediSense Pro · Hospital Locator · SWE1904 · VIT · R.Divya 21MIS0261
    </div>""", unsafe_allow_html=True)
