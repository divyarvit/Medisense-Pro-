"""
XAI Renderer — renders the explainability panel in Streamlit.
Used by diabetes.py, heart.py, parkinsons.py
"""
import streamlit as st

def render_xai_panel(explanation, module_name):
    """
    Renders the full Explainable AI panel.
    Call this after the prediction result is known.
    """
    result   = explanation["result"]
    features = explanation["features"]
    summary  = explanation["summary"]
    whatif   = explanation["whatif"]
    top_risks= explanation["top_risks"]

    res_color = "#e53935" if result == "Positive" else "#43a047"
    res_icon  = "⚠️" if result == "Positive" else "✅"

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#1a237e,#1565c0);
        color:white;border-radius:18px;padding:22px 28px;margin:16px 0">
        <div style="display:flex;align-items:center;gap:12px">
            <span style="font-size:2.2em">🧠</span>
            <div>
                <h2 style="margin:0;font-size:1.4em">Explainable AI — Why did the AI decide this?</h2>
                <p style="margin:4px 0 0;opacity:0.85;font-size:13px">
                    Every factor that influenced this prediction, ranked by impact
                </p>
            </div>
        </div>
    </div>""", unsafe_allow_html=True)

    # ── Plain English Summary ─────────────────────────────────────────────
    st.markdown(f"""<div style="background:#e8f0fe;border-left:6px solid #1565c0;
        border-radius:12px;padding:16px 20px;margin:8px 0;font-size:14px;line-height:1.8">
        <b style="color:#1565c0">📋 Plain English Explanation:</b><br><br>
        {summary}
    </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # ── Feature Importance Chart ──────────────────────────────────────────
    st.markdown("### 📊 Feature Importance — What Influenced This Prediction")
    st.markdown('<p style="color:#666;font-size:13px;margin:-8px 0 12px">Each bar shows how much that parameter contributed to the AI\'s decision. Red = high risk contribution.</p>', unsafe_allow_html=True)

    for feat in features:
        pct   = feat["contrib_pct"]
        color = feat["color"]
        level = feat["level"]
        icon  = feat["icon"]
        val   = feat["value"]
        unit  = feat["unit"]
        name  = feat["name"]

        # Bar fill width — max bar = 100% of container
        bar_w = pct  # already a percentage

        st.markdown(f"""
        <div style="background:white;border-radius:12px;padding:13px 18px;
            margin:6px 0;border:1px solid #eee;
            box-shadow:0 1px 6px rgba(0,0,0,0.06);
            border-left:5px solid {color}">
            <div style="display:flex;justify-content:space-between;
                align-items:center;margin-bottom:7px">
                <div>
                    <span style="font-weight:700;font-size:14px">{name}</span>
                    <span style="color:#888;font-size:12px;margin-left:8px">
                        {val:.4g} {unit}</span>
                </div>
                <div style="text-align:right">
                    <span style="background:{color};color:white;padding:2px 10px;
                        border-radius:12px;font-size:12px;font-weight:600">
                        {icon} {level}</span>
                    <span style="color:{color};font-weight:700;
                        font-size:15px;margin-left:10px">{pct}%</span>
                </div>
            </div>
            <div style="background:#f0f0f0;border-radius:6px;height:10px;position:relative">
                <div style="background:linear-gradient(90deg,{color},{color}aa);
                    width:{bar_w}%;height:10px;border-radius:6px;
                    transition:width 0.5s ease"></div>
            </div>
            <div style="font-size:11px;color:#999;margin-top:5px">
                {feat['meaning']}
            </div>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # ── Risk Factor Spotlight ─────────────────────────────────────────────
    if top_risks and result == "Positive":
        st.markdown("### 🔴 Key Risk Factors — These Need Your Attention")
        cols = st.columns(min(len(top_risks), 3))
        for i, feat in enumerate(top_risks[:3]):
            with cols[i]:
                st.markdown(f"""<div style="background:{feat['color']}18;
                    border:2px solid {feat['color']};border-radius:14px;
                    padding:16px;text-align:center;height:140px">
                    <div style="font-size:2em">{feat['icon']}</div>
                    <b style="color:{feat['color']};font-size:13px">{feat['name']}</b><br>
                    <span style="font-size:1.3em;font-weight:800;color:{feat['color']}">
                        {feat['value']:.4g} {feat['unit']}</span><br>
                    <span style="font-size:11px;color:#666">{feat['level']}</span>
                </div>""", unsafe_allow_html=True)
        st.markdown("---")

    # ── What-If Analysis ─────────────────────────────────────────────────
    if whatif:
        st.markdown("### 💡 What-If Analysis — How to Reduce Your Risk")
        direction_icon = "⬇️" if whatif["direction"] == "decrease" else "⬆️"
        st.markdown(f"""<div style="background:linear-gradient(135deg,#e8f5e9,#f1f8e9);
            border:2px solid #43a047;border-radius:14px;padding:20px 24px;margin:8px 0">
            <h4 style="color:#2e7d32;margin:0 0 12px">
                {direction_icon} If <b>{whatif['feature']}</b> changed from
                <b style="color:#e53935">{whatif['current']:.4g}</b> →
                <b style="color:#43a047">{whatif['target']:.4g}</b>:
            </h4>
            <p style="font-size:14px;color:#333;line-height:1.7;margin:0">
                {whatif['message']}
            </p>
            <div style="margin-top:12px;background:white;border-radius:8px;
                padding:10px 14px;font-size:13px;color:#555;border-left:3px solid #43a047">
                💊 <b>Action:</b> Ask your doctor about specific targets for <b>{whatif['feature']}</b>
                and how to reach them through diet, exercise, or medication.
            </div>
        </div>""", unsafe_allow_html=True)

    # ── Model Transparency Note ───────────────────────────────────────────
    st.markdown(f"""<div style="background:#f8f9fa;border-radius:10px;
        padding:14px 18px;margin-top:16px;font-size:12px;color:#777;
        border:1px solid #e0e0e0">
        🔬 <b>Model Transparency:</b> This {module_name} model uses a trained
        Machine Learning classifier. Feature importance shown above is calculated
        using clinical threshold-based weighting — each parameter's contribution
        reflects how far it deviates from its normal clinical range.
        This is an Explainable AI (XAI) approach that makes AI decisions
        transparent and understandable to both patients and clinicians.<br><br>
        ⚠️ This is a decision-support tool only. Always confirm with a qualified doctor.
    </div>""", unsafe_allow_html=True)
