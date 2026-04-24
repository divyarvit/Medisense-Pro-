import requests
import json

GROQ_KEY = "your_groq_api_key_here"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL    = "llama-3.3-70b-versatile"

def generate_diabetes_explanation(data, risk, score, dtype, flags, g_adjusted):
    age       = data.get("age", 0)
    glucose   = data.get("glucose", 0)
    post_meal = data.get("post_meal_glucose", 0)
    hba1c     = data.get("hba1c", 0)
    bmi       = data.get("bmi", 0)
    gender    = data.get("gender", "Male")
    systolic  = data.get("systolic", 0)
    diastolic = data.get("diastolic", 0)
    hr        = data.get("resting_hr", 0)
    sleep_h   = data.get("sleep", 0)
    steps     = data.get("steps", 0)
    spo2      = data.get("spo2", 0)
    stress    = data.get("stress", "Low")
    diet      = data.get("diet", "Normal")
    symptoms  = data.get("symptoms", [])
    family    = data.get("family_history", False)
    reading_type = data.get("reading_type", "Fasting")
    medications  = data.get("medications", [])

    sym_str = ", ".join(symptoms) if symptoms else "none reported"
    med_str = ", ".join(medications) if medications else "none"

    patient_summary = f"""
Patient: {age} year old {gender}, BMI {bmi:.1f}
Glucose: {glucose} mg/dL ({reading_type}), Post-meal: {post_meal} mg/dL, HbA1c: {hba1c}%
BP: {systolic}/{diastolic} mmHg, HR: {hr} bpm, SpO2: {spo2}%
Sleep: {sleep_h} hours, Steps: {steps}/day, Stress: {stress}, Diet: {diet}
Symptoms: {sym_str}
Family history: {'Yes' if family else 'No'}, Medications: {med_str}
Adjusted glucose: {g_adjusted:.0f} mg/dL, Risk: {risk} ({score}/100), Type: {dtype}"""

    prompt = f"""You are a clinical doctor explaining a diabetes screening result to a patient in India.
Use simple, warm, empathetic language. Mention the patient's ACTUAL VALUES by number in every section.

{patient_summary}

Generate exactly 5 sections. Be specific — use real numbers from above. 3-5 sentences each.

Return ONLY this JSON, no other text:
{{
  "section1": "Explain what is happening in this patient's body RIGHT NOW using their specific values. Mention glucose level, symptoms by name, BMI, SpO2, sleep — and explain what each abnormal value means for their body and why it is concerning.",
  "section2": "Explain WHY this is exactly {risk} — not higher, not lower. Use their specific numbers. What combination makes it this severity? What happens if they ignore it?",
  "why_condition1": "Why Type 2 Diabetes is most likely — use their specific glucose, symptoms, BMI. Mention each value by number.",
  "why_condition2": "Why Pre-diabetes is second possibility — use their borderline values. What test would confirm or rule it out?",
  "why_condition3": "Why Stress-induced Hyperglycemia is third — use their stress level and diet. Why is it less likely given their symptoms?"
}}"""

    try:
        headers = {
            "Authorization": f"Bearer {GROQ_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.4,
            "max_tokens": 1500,
        }
        resp = requests.post(GROQ_URL, headers=headers, json=payload, timeout=25)
        if resp.status_code == 200:
            content = resp.json()["choices"][0]["message"]["content"]
            content = content.strip()
            if "```" in content:
                parts = content.split("```")
                content = parts[1] if len(parts) > 1 else content
                if content.startswith("json"):
                    content = content[4:]
            content = content.strip()
            result = json.loads(content)
            return result
        else:
            return None
    except Exception as e:
        return None
