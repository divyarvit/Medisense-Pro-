import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from utils.database import save_report

def show():
    st.markdown("""<div class="main-header">
        <h1>⚖️ BMI & Body Health Calculator</h1>
        <p>Calculate your BMI, BMR, daily calorie needs, and get a personalised health plan</p>
    </div>""", unsafe_allow_html=True)

    col_in, col_out = st.columns([1, 1.4])

    with col_in:
        st.markdown("""<div style="background:white;border-radius:14px;padding:22px;
            box-shadow:0 2px 12px rgba(0,0,0,0.08);border-top:4px solid #1565c0">
            <h4 style="color:#1565c0;margin:0 0 16px">📝 Enter Your Details</h4>""",
            unsafe_allow_html=True)

        weight = st.number_input("⚖️ Weight (kg)", 20.0, 300.0, 65.0, 0.5)
        height = st.number_input("📏 Height (cm)", 100.0, 250.0, 165.0, 0.5)
        age    = st.number_input("🎂 Age (years)", 10, 100, 25)
        gender = st.selectbox("⚤ Gender", ["Female","Male"])
        activity = st.selectbox("🏃 Activity Level", [
            "Sedentary (office job, no exercise)",
            "Lightly Active (light exercise 1–3 days/week)",
            "Moderately Active (exercise 3–5 days/week)",
            "Very Active (hard exercise 6–7 days/week)",
            "Extremely Active (athlete / physical job)",
        ])
        goal = st.selectbox("🎯 Health Goal", [
            "Maintain current weight",
            "Lose weight (0.5 kg/week)",
            "Lose weight fast (1 kg/week)",
            "Gain muscle mass",
        ])
        st.markdown("</div>", unsafe_allow_html=True)
        calculate = st.button("🧮 Calculate My Health Metrics", use_container_width=True)

    with col_out:
        if calculate:
            h_m   = height / 100
            bmi   = round(weight / (h_m ** 2), 1)
            ideal = round(22.5 * (h_m ** 2), 1)
            diff  = round(weight - ideal, 1)

            # BMI Category
            if bmi < 18.5:
                cat, cat_c, cat_i = "Underweight",  "#2196f3", "🔵"
                advice = "You are below the healthy weight range. Focus on nutritious calorie-dense foods and strength training."
            elif bmi < 25:
                cat, cat_c, cat_i = "Normal Weight", "#43a047", "🟢"
                advice = "Excellent! You are in the healthy weight range. Maintain your current lifestyle."
            elif bmi < 30:
                cat, cat_c, cat_i = "Overweight",    "#fb8c00", "🟡"
                advice = "You are slightly above the healthy range. Moderate diet changes and regular exercise can help."
            elif bmi < 35:
                cat, cat_c, cat_i = "Obese Class I",  "#e53935", "🔴"
                advice = "Your BMI indicates obesity. Consult a doctor and start a supervised diet and exercise program."
            else:
                cat, cat_c, cat_i = "Obese Class II+","#b71c1c", "🔴"
                advice = "Your BMI indicates severe obesity. Please consult a doctor urgently for a personalised management plan."

            # BMR (Mifflin-St Jeor)
            if gender == "Male":
                bmr = round(10*weight + 6.25*height - 5*age + 5)
            else:
                bmr = round(10*weight + 6.25*height - 5*age - 161)

            # TDEE
            act_mult = {"Sedentary":1.2,"Lightly":1.375,"Moderately":1.55,"Very":1.725,"Extremely":1.9}
            act_key  = [k for k in act_mult if k.lower() in activity.lower()]
            mult     = act_mult.get(act_key[0] if act_key else "Sedentary", 1.375)
            tdee     = round(bmr * mult)

            # Goal calories
            goal_cal = {"Maintain":0,"Lose weight (0.5":-500,"Lose weight fast":-1000,"Gain":+500}
            gcal_key = [k for k in goal_cal if k.lower() in goal.lower()]
            cal_adj  = goal_cal.get(gcal_key[0] if gcal_key else "Maintain", 0)
            target   = tdee + cal_adj

            # ── BMI Gauge ──────────────────────────────────────────────────
            gauge_pct = min(max((bmi - 10) / (45 - 10), 0), 1) * 100
            st.markdown(f"""<div style="background:white;border-radius:14px;padding:22px;
                box-shadow:0 2px 12px rgba(0,0,0,0.08);margin-bottom:12px">
                <h4 style="color:#1565c0;margin:0 0 16px">📊 BMI Gauge</h4>
                <div style="position:relative;margin:8px 0 4px">
                    <div style="background:linear-gradient(90deg,#2196f3 0%,#43a047 30%,#fb8c00 60%,#e53935 80%,#b71c1c 100%);
                        height:20px;border-radius:10px;position:relative">
                        <div style="position:absolute;left:{gauge_pct}%;top:-6px;transform:translateX(-50%)">
                            <div style="width:0;height:0;border-left:8px solid transparent;
                                border-right:8px solid transparent;border-top:14px solid #333;
                                margin:0 auto"></div>
                        </div>
                    </div>
                    <div style="display:flex;justify-content:space-between;
                        font-size:10px;color:#888;margin-top:4px">
                        <span>10</span><span>Underweight</span><span>Normal</span>
                        <span>Overweight</span><span>Obese</span><span>45</span>
                    </div>
                </div>
                <div style="text-align:center;margin-top:16px">
                    <div style="font-size:3.5em;font-weight:800;color:{cat_c}">{bmi}</div>
                    <div style="font-size:1.2em;font-weight:700;color:{cat_c}">{cat_i} {cat}</div>
                    <div style="font-size:13px;color:#666;margin-top:4px">{advice}</div>
                    <div style="font-size:12px;color:#888;margin-top:8px">
                        Ideal weight for your height: <b>{ideal} kg</b>
                        {'  ·  ' + ('Lose' if diff>0 else 'Gain') + f' <b>{abs(diff)} kg</b> to reach ideal' if abs(diff)>1 else '  ·  <b>You are at your ideal weight! 🎉</b>'}
                    </div>
                </div>
            </div>""", unsafe_allow_html=True)

            # ── Metabolic Stats ────────────────────────────────────────────
            met_cols = st.columns(3)
            for mc, lbl, val, desc, col in [
                (met_cols[0],"🔥 BMR",      f"{bmr} kcal","Calories your body burns at complete rest","#e53935"),
                (met_cols[1],"⚡ TDEE",     f"{tdee} kcal","Total daily energy with your activity level","#fb8c00"),
                (met_cols[2],"🎯 Target",   f"{target} kcal",f"Daily calories for your goal: {goal[:20]}","#1565c0"),
            ]:
                with mc:
                    st.markdown(f"""<div style="background:white;border-radius:10px;
                        padding:14px;text-align:center;box-shadow:0 2px 8px rgba(0,0,0,0.08);
                        border-top:3px solid {col}">
                        <div style="font-size:1.1em;font-weight:700;color:{col}">{lbl}</div>
                        <div style="font-size:1.5em;font-weight:800;color:{col};margin:4px 0">{val}</div>
                        <div style="font-size:11px;color:#888;line-height:1.4">{desc}</div>
                    </div>""", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # ── Macros ─────────────────────────────────────────────────────
            protein = round(weight * (2.0 if "Gain" in goal else 1.6))
            fat     = round(target * 0.25 / 9)
            carbs   = round((target - protein*4 - fat*9) / 4)
            st.markdown(f"""<div style="background:#f8f9fa;border-radius:12px;padding:16px;
                border:1px solid #e0e0e0">
                <h5 style="color:#1565c0;margin:0 0 12px">🥗 Daily Macronutrient Targets</h5>
                <div style="display:flex;gap:8px">
                    {"".join([f'<div style="flex:1;background:white;border-radius:8px;padding:10px;text-align:center;box-shadow:0 1px 4px rgba(0,0,0,0.06)"><b style="color:{c}">{n}</b><br><span style="font-size:1.3em;font-weight:700">{v}g</span><br><small style="color:#888">{p}% of calories</small></div>' for n,v,p,c in [("🥩 Protein",protein,round(protein*4/target*100),"#e53935"),("🫒 Fats",fat,round(fat*9/target*100),"#fb8c00"),("🍚 Carbs",carbs,round(carbs*4/target*100),"#1565c0")]])}
                </div>
            </div>""", unsafe_allow_html=True)

            # ── Tips ───────────────────────────────────────────────────────
            st.markdown("<br>", unsafe_allow_html=True)
            tips_map = {
                "Underweight": ["🥑 Eat calorie-dense foods: nuts, avocado, dairy, eggs",
                                 "💪 Focus on strength training to build muscle, not just fat",
                                 "🍽️ Eat 5–6 small meals a day — never skip meals",
                                 "🥛 Drink milk, smoothies, and protein shakes between meals"],
                "Normal":      ["🏃 Maintain your 30-min daily exercise habit",
                                 "🥗 Keep eating a balanced diet with all food groups",
                                 "💧 Stay well hydrated — 8 glasses minimum daily",
                                 "🩺 Get an annual health check-up to stay on track"],
                "Overweight":  ["🚶 Walk 45 minutes daily — start with 20 and build up",
                                 "🍽️ Reduce portion sizes by 20% — use a smaller plate",
                                 "🚫 Cut sugar, fried food, and white rice first",
                                 "💧 Drink a glass of water before every meal"],
                "Obese":       ["🏥 Consult a doctor and registered dietitian urgently",
                                 "🚶 Start with gentle walking 20 min/day — increase slowly",
                                 "🥗 Follow a structured 1200–1500 kcal meal plan with doctor",
                                 "📊 Monitor weight weekly and blood sugar/BP regularly"],
            }
            tip_key = "Normal" if "Normal" in cat else ("Obese" if "Obese" in cat else cat)
            tips = tips_map.get(tip_key, tips_map["Normal"])

            st.markdown("""<div style="background:#e8f5e9;border-radius:12px;padding:16px;
                border-left:4px solid #43a047">
                <h5 style="color:#2e7d32;margin:0 0 10px">💡 Personalised Tips for You</h5>""",
                unsafe_allow_html=True)
            for tip in tips:
                st.markdown(f"""<div style="padding:5px 0;font-size:13px;color:#333">✔️ {tip}</div>""",
                            unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

            # Save report
            save_report(user_id=st.session_state.user_id,
                        module="BMI Calculator", severity=cat,
                        top_diagnosis=f"BMI {bmi} — {cat}",
                        confidence=85,
                        full_data=f"Weight:{weight}kg|Height:{height}cm|Age:{age}|Gender:{gender}|BMI:{bmi}|TDEE:{tdee}kcal")
            st.success("✅ BMI report saved to your history.")

        else:
            st.markdown("""<div style="background:#f0f4ff;border-radius:14px;padding:40px 24px;
                text-align:center;border:2px dashed #1565c0">
                <div style="font-size:4em">⚖️</div>
                <h3 style="color:#1565c0">Enter your details and click Calculate</h3>
                <p style="color:#888;font-size:14px">
                You'll get: BMI gauge · BMR · TDEE · Target calories · Macros · Personalised tips
                </p>
            </div>""", unsafe_allow_html=True)
