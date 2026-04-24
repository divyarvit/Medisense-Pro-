"""
Core diagnosis engine.
Handles: severity assessment, differential diagnosis,
confidence calculation, and clinical report generation.
"""

def assess_severity(params: dict) -> tuple:
    score = 0
    reasons = []

    temp     = float(params.get("temperature", 98.6))
    pulse    = int(params.get("pulse", 72))
    duration = int(params.get("duration_days", 1))

    if temp >= 103:
        score += 3; reasons.append(f"Very high fever ({temp}°F) — requires immediate attention")
    elif temp >= 100.4:
        score += 2; reasons.append(f"Fever present ({temp}°F) — above normal range of 98.6°F")
    elif temp < 96:
        score += 2; reasons.append(f"Abnormally low temperature ({temp}°F)")

    if pulse > 120:
        score += 3; reasons.append(f"Dangerously high pulse ({pulse} bpm) — normal is 60-100")
    elif pulse > 100:
        score += 2; reasons.append(f"Elevated pulse ({pulse} bpm) — above normal range")
    elif pulse < 50:
        score += 2; reasons.append(f"Low pulse ({pulse} bpm) — below normal range")

    if duration >= 7:
        score += 2; reasons.append(f"Symptoms lasting {duration} days — prolonged duration increases concern")
    elif duration >= 3:
        score += 1; reasons.append(f"Symptoms present for {duration} days")

    symptoms = params.get("symptoms", [])
    high_risk     = ["chest_pain","difficulty_breathing","severe_headache","confusion","blood_in_stool"]
    moderate_risk = ["vomiting","fatigue","dizziness","sweating"]

    for s in symptoms:
        if s in high_risk:
            score += 3; reasons.append(f"High-risk symptom detected: {s.replace('_',' ').title()}")
        elif s in moderate_risk:
            score += 1; reasons.append(f"Notable symptom: {s.replace('_',' ').title()}")

    if score >= 7:
        label       = "Severe"
        explanation = (f"Your condition is severe based on {len(reasons)} concerning factors. "
                       f"Temperature of {temp}°F, pulse of {pulse} bpm, and {duration} days duration "
                       f"together indicate you need immediate medical attention. "
                       f"Do not delay — visit a doctor or emergency today.")
    elif score >= 4:
        label       = "Moderate"
        explanation = (f"Your condition is moderate. With {len(symptoms)} symptoms reported over {duration} days, "
                       f"your body is fighting an active condition. "
                       f"Monitor closely — if symptoms worsen or fever rises above 103°F, see a doctor immediately.")
    else:
        label       = "Mild"
        explanation = (f"Your condition appears mild. Temperature is {temp}°F and pulse is {pulse} bpm — "
                       f"both within manageable range. With proper rest, hydration, and home care, "
                       f"most mild conditions resolve within 3-5 days.")

    return label, score, explanation, reasons


# ── Symptom-specific reasoning per condition ──────────────────────────────
def _build_reasoning(condition_key: str, symptoms: set,
                     temp: float, pulse: int, duration: int) -> str:
    """
    Returns a specific 'Why this condition' sentence
    based on which symptoms the patient actually reported.
    """
    matched = []

    if condition_key == "viral_fever":
        if temp >= 99:       matched.append(f"elevated temperature ({temp}°F)")
        if "runny_nose"   in symptoms: matched.append("runny nose")
        if "body_ache"    in symptoms: matched.append("body aches")
        if "sore_throat"  in symptoms: matched.append("sore throat")
        if "cough"        in symptoms: matched.append("cough")
        if "fatigue"      in symptoms: matched.append("fatigue")
        if matched:
            return (f"Flagged because you reported {', '.join(matched)}. "
                    f"This combination of symptoms — especially fever with body ache and fatigue — "
                    f"is the classic presentation of a viral infection.")
        return "Symptoms pattern matches viral infection profile."

    elif condition_key == "food_poisoning":
        if "vomiting"    in symptoms: matched.append("vomiting")
        if "nausea"      in symptoms: matched.append("nausea")
        if "diarrhea"    in symptoms: matched.append("diarrhea")
        if "indigestion" in symptoms: matched.append("indigestion/stomach ache")
        if matched:
            return (f"Flagged because you reported {', '.join(matched)}. "
                    f"This combination strongly suggests digestive tract irritation from "
                    f"contaminated food or water, which is the hallmark of gastroenteritis.")
        return "Digestive symptom pattern matches gastroenteritis profile."

    elif condition_key == "jaundice":
        if "yellowish_urine" in symptoms: matched.append("yellowish urine")
        if "yellow_eyes"     in symptoms: matched.append("yellow eyes/skin")
        if "fatigue"         in symptoms: matched.append("fatigue")
        if "dark_urine"      in symptoms: matched.append("dark urine")
        if matched:
            return (f"Flagged because you reported {', '.join(matched)}. "
                    f"Yellow urine and yellow eyes are the two most specific signs of liver dysfunction. "
                    f"This combination requires urgent liver function testing.")
        return "Yellow discolouration pattern indicates possible liver involvement."

    elif condition_key == "cardiac":
        if "chest_pain"           in symptoms: matched.append("chest pain")
        if "difficulty_breathing" in symptoms: matched.append("difficulty breathing")
        if "arm_pain"             in symptoms: matched.append("arm/shoulder pain")
        if "sweating"             in symptoms: matched.append("excessive sweating")
        if pulse > 100:                        matched.append(f"elevated pulse ({pulse} bpm)")
        if matched:
            return (f"Flagged because you reported {', '.join(matched)}. "
                    f"Chest pain combined with breathing difficulty and arm pain "
                    f"is a warning pattern for cardiac stress that requires immediate evaluation.")
        return "Symptom combination warrants cardiac evaluation."

    elif condition_key == "dehydration":
        if "dizziness"  in symptoms: matched.append("dizziness")
        if "dry_mouth"  in symptoms: matched.append("dry mouth/thirst")
        if "fatigue"    in symptoms: matched.append("fatigue")
        if "headache"   in symptoms: matched.append("headache")
        if "dark_urine" in symptoms: matched.append("dark urine")
        if pulse > 90:               matched.append(f"slightly elevated pulse ({pulse} bpm)")
        if matched:
            return (f"Flagged because you reported {', '.join(matched)}. "
                    f"Dizziness, dry mouth, and dark urine are the three most reliable "
                    f"indicators of dehydration — your body is signalling fluid deficit.")
        return "Symptom pattern consistent with fluid deficit."

    elif condition_key == "respiratory":
        if "cough"                in symptoms: matched.append("persistent cough")
        if "difficulty_breathing" in symptoms: matched.append("difficulty breathing")
        if "chest_pain"           in symptoms: matched.append("chest discomfort")
        if temp >= 100.4:                      matched.append(f"fever ({temp}°F)")
        if matched:
            return (f"Flagged because you reported {', '.join(matched)}. "
                    f"Cough with breathing difficulty and fever is the classic triad "
                    f"of a lower respiratory tract infection like bronchitis or pneumonia.")
        return "Respiratory symptom pattern warrants evaluation."

    elif condition_key == "hypertension":
        if "severe_headache" in symptoms: matched.append("severe headache")
        if "dizziness"       in symptoms: matched.append("dizziness")
        if "blurred_vision"  in symptoms: matched.append("blurred vision")
        if pulse > 100:                   matched.append(f"elevated pulse ({pulse} bpm)")
        if matched:
            return (f"Flagged because you reported {', '.join(matched)}. "
                    f"Severe headache combined with dizziness and blurred vision "
                    f"is a common presentation of elevated blood pressure requiring monitoring.")
        return "Symptom pattern associated with elevated blood pressure."

    return "Symptom combination matches this condition's clinical profile."


def generate_differential_diagnosis(params: dict) -> list:
    symptoms  = set(params.get("symptoms", []))
    temp      = float(params.get("temperature", 98.6))
    pulse     = int(params.get("pulse", 72))
    duration  = int(params.get("duration_days", 1))

    candidates = []

    # ── Viral Fever / Common Cold ──────────────────────────────────────────
    score = 0
    if temp >= 99:          score += 30
    if "runny_nose"   in symptoms: score += 20
    if "body_ache"    in symptoms: score += 15
    if "fatigue"      in symptoms: score += 10
    if "sore_throat"  in symptoms: score += 15
    if "cough"        in symptoms: score += 10
    if score > 0:
        candidates.append({
            "condition":   "Viral Fever / Common Cold",
            "probability": min(score, 90),
            "description": "A viral infection causing fever, body ache, and respiratory symptoms.",
            "reasoning":   _build_reasoning("viral_fever", symptoms, temp, pulse, duration),
            "icd":         "J06.9",
            "icd_name":    "Acute upper respiratory infection, unspecified"
        })

    # ── Food Poisoning / Gastroenteritis ──────────────────────────────────
    score = 0
    if "vomiting"    in symptoms: score += 30
    if "indigestion" in symptoms: score += 20
    if "diarrhea"    in symptoms: score += 30
    if "nausea"      in symptoms: score += 15
    if temp >= 99:   score += 10
    if score > 0:
        candidates.append({
            "condition":   "Food Poisoning / Gastroenteritis",
            "probability": min(score, 88),
            "description": "Infection or irritation of the digestive tract from contaminated food or water.",
            "reasoning":   _build_reasoning("food_poisoning", symptoms, temp, pulse, duration),
            "icd":         "A09",
            "icd_name":    "Infectious gastroenteritis and colitis"
        })

    # ── Jaundice / Hepatitis ───────────────────────────────────────────────
    score = 0
    if "yellowish_urine" in symptoms: score += 35
    if "yellow_eyes"     in symptoms: score += 35
    if "fatigue"         in symptoms: score += 10
    if "dark_urine"      in symptoms: score += 20
    if "nausea"          in symptoms: score += 10
    if score > 0:
        candidates.append({
            "condition":   "Jaundice / Hepatitis",
            "probability": min(score, 85),
            "description": "Liver condition causing yellowing of skin and eyes due to bilirubin buildup.",
            "reasoning":   _build_reasoning("jaundice", symptoms, temp, pulse, duration),
            "icd":         "R17",
            "icd_name":    "Unspecified jaundice"
        })

    # ── Cardiac Concern ───────────────────────────────────────────────────
    score = 0
    if "chest_pain"           in symptoms: score += 40
    if "difficulty_breathing" in symptoms: score += 30
    if pulse > 100:                        score += 20
    if "sweating"             in symptoms: score += 15
    if "arm_pain"             in symptoms: score += 20
    if score > 0:
        candidates.append({
            "condition":   "Cardiac Concern (Heart-related)",
            "probability": min(score, 92),
            "description": "Symptoms may indicate cardiac stress requiring urgent medical evaluation.",
            "reasoning":   _build_reasoning("cardiac", symptoms, temp, pulse, duration),
            "icd":         "I51.9",
            "icd_name":    "Heart disease, unspecified"
        })

    # ── Dehydration ───────────────────────────────────────────────────────
    score = 0
    if "dizziness"  in symptoms: score += 25
    if "dry_mouth"  in symptoms: score += 25
    if "fatigue"    in symptoms: score += 15
    if "headache"   in symptoms: score += 15
    if "dark_urine" in symptoms: score += 20
    if pulse > 90:               score += 10
    if score > 0:
        candidates.append({
            "condition":   "Dehydration",
            "probability": min(score, 80),
            "description": "Insufficient fluid intake or excessive fluid loss causing weakness and dizziness.",
            "reasoning":   _build_reasoning("dehydration", symptoms, temp, pulse, duration),
            "icd":         "E86.0",
            "icd_name":    "Volume depletion"
        })

    # ── Respiratory Infection ─────────────────────────────────────────────
    score = 0
    if "cough"                in symptoms: score += 25
    if "difficulty_breathing" in symptoms: score += 30
    if "chest_pain"           in symptoms: score += 20
    if temp >= 100.4:                      score += 15
    if score > 0:
        candidates.append({
            "condition":   "Respiratory Infection (Pneumonia/Bronchitis)",
            "probability": min(score, 82),
            "description": "Infection of the airways or lungs causing breathing difficulty and persistent cough.",
            "reasoning":   _build_reasoning("respiratory", symptoms, temp, pulse, duration),
            "icd":         "J22",
            "icd_name":    "Unspecified acute lower respiratory infection"
        })

    # ── Hypertension / Stress ─────────────────────────────────────────────
    score = 0
    if "severe_headache" in symptoms: score += 30
    if "dizziness"       in symptoms: score += 20
    if "blurred_vision"  in symptoms: score += 25
    if pulse > 100:                   score += 20
    if "nausea"          in symptoms: score += 10
    if score > 0:
        candidates.append({
            "condition":   "Hypertension / High Blood Pressure",
            "probability": min(score, 78),
            "description": "Elevated blood pressure causing headache, dizziness, and visual disturbances.",
            "reasoning":   _build_reasoning("hypertension", symptoms, temp, pulse, duration),
            "icd":         "I10",
            "icd_name":    "Essential (primary) hypertension"
        })

    # ── No Significant Concern ────────────────────────────────────────────
    if not candidates or max(c["probability"] for c in candidates) < 25:
        candidates.append({
            "condition":   "No Significant Condition Detected",
            "probability": 85,
            "description": "Your symptoms do not indicate a major health concern at this time.",
            "reasoning":   "Your reported symptoms and vitals are within acceptable ranges. Maintain hydration, rest, and monitor for any changes.",
            "icd":         "Z00.0",
            "icd_name":    "Encounter for general examination"
        })

    # Sort by probability, normalise to 100%
    candidates.sort(key=lambda x: x["probability"], reverse=True)
    top3  = candidates[:3]
    total = sum(c["probability"] for c in top3)
    for c in top3:
        c["probability"] = round((c["probability"] / total) * 100, 1)

    return top3


def calculate_confidence(params: dict) -> float:
    score = 0
    if params.get("temperature"):   score += 20
    if params.get("pulse"):         score += 20
    if params.get("duration_days"): score += 15
    symptoms = params.get("symptoms", [])
    if len(symptoms) >= 3:   score += 30
    elif len(symptoms) >= 1: score += 15
    if params.get("age"):    score += 10
    if params.get("gender"): score += 5
    return min(score, 95)


def get_do_dont(conditions: list, severity: str) -> dict:
    top = conditions[0]["condition"] if conditions else ""

    base_do = [
        "Rest adequately and avoid strenuous activity",
        "Drink at least 8-10 glasses of water daily",
        "Monitor your temperature and pulse regularly",
        "Eat light, easily digestible meals",
        "Maintain good hygiene — wash hands frequently",
    ]
    base_dont = [
        "Do NOT self-medicate without consulting a doctor",
        "Do NOT ignore worsening symptoms",
        "Do NOT skip meals or fluids",
        "Avoid alcohol, smoking, and junk food",
        "Do NOT share utensils or be in close contact with others",
    ]

    specific_do = {
        "Viral Fever / Common Cold": [
            "Take paracetamol for fever as directed",
            "Steam inhalation for nasal congestion",
            "Gargle with warm salt water for sore throat",
        ],
        "Food Poisoning / Gastroenteritis": [
            "Take ORS (Oral Rehydration Solution) frequently",
            "Follow BRAT diet: Banana, Rice, Applesauce, Toast",
            "Avoid dairy and spicy food until recovered",
        ],
        "Jaundice / Hepatitis": [
            "Take complete bed rest",
            "Eat high-carb, low-fat food",
            "Drink coconut water and fresh juices",
            "Get Liver Function Test (LFT) done immediately",
        ],
        "Cardiac Concern (Heart-related)": [
            "SEEK EMERGENCY CARE IMMEDIATELY",
            "Chew aspirin 325mg if available and no allergy",
            "Lie down and avoid any physical exertion",
        ],
        "Dehydration": [
            "Drink ORS or electrolyte solution every 15 minutes",
            "Increase fluid intake gradually",
            "Eat water-rich fruits like watermelon and cucumber",
        ],
        "Respiratory Infection (Pneumonia/Bronchitis)": [
            "Steam inhalation 3 times daily",
            "Sleep with head elevated on extra pillow",
            "Warm fluids — ginger tea, warm water with honey",
        ],
        "Hypertension / High Blood Pressure": [
            "Sit quietly and breathe slowly and deeply",
            "Reduce salt intake immediately",
            "Measure BP if a machine is available",
        ],
    }
    specific_dont = {
        "Cardiac Concern (Heart-related)": [
            "Do NOT drive yourself to hospital — call 108",
            "Do NOT eat or drink until medically evaluated",
            "Do NOT ignore chest pain even if mild",
        ],
        "Jaundice / Hepatitis": [
            "Completely avoid alcohol",
            "Do NOT take paracetamol — harmful to liver",
            "Avoid oily and fried foods completely",
        ],
        "Hypertension / High Blood Pressure": [
            "Do NOT consume caffeine or energy drinks",
            "Do NOT exercise vigorously until BP is checked",
            "Avoid stress and screen time",
        ],
    }

    dos   = base_do   + specific_do.get(top, [])
    donts = base_dont + specific_dont.get(top, [])

    if severity == "Severe":
        dos.insert(0, "⚠️ CONSULT A DOCTOR OR VISIT EMERGENCY IMMEDIATELY")

    return {"do": dos[:6], "dont": donts[:6]}


def when_to_see_doctor(severity: str, conditions: list) -> list:
    base = [
        "Symptoms persist for more than 3 days without improvement",
        "Fever rises above 103°F (39.4°C)",
        "You experience difficulty breathing",
        "Symptoms suddenly worsen",
    ]
    if severity == "Severe":
        return ["⛑️ VISIT EMERGENCY ROOM OR CALL 108 IMMEDIATELY"] + base
    if severity == "Moderate":
        return ["Consult a doctor within 24 hours"] + base
    return ["Consult a doctor if no improvement in 2-3 days"] + base


def get_home_care(conditions: list) -> list:
    top = conditions[0]["condition"] if conditions else ""
    general = [
        "Rest in a well-ventilated, comfortable room",
        "Use a cool damp cloth on forehead for fever",
        "Keep track of symptoms — note any changes",
        "Wear loose, comfortable clothing",
    ]
    specific = {
        "Viral Fever / Common Cold": [
            "Steam inhalation 2-3 times a day",
            "Honey + ginger + tulsi tea soothes throat",
            "Saline nasal drops for congestion",
        ],
        "Food Poisoning / Gastroenteritis": [
            "Sip small amounts of water every 10 minutes",
            "Avoid solid food for first 6-8 hours",
            "Probiotics (curd/yogurt) after 24 hours to restore gut flora",
        ],
        "Dehydration": [
            "Homemade ORS: 1L water + 6 tsp sugar + half tsp salt",
            "Coconut water is excellent for natural electrolytes",
            "Cool the body with a damp cloth if temperature is elevated",
        ],
        "Jaundice / Hepatitis": [
            "Sleep with head slightly elevated",
            "Avoid direct sunlight if skin is yellowing",
            "Take short gentle walks once fever subsides",
        ],
        "Respiratory Infection (Pneumonia/Bronchitis)": [
            "Humidify the room — helps airways",
            "Avoid cold drinks and cold air",
            "Breathe in steam from hot water bowl for 10 minutes",
        ],
        "Hypertension / High Blood Pressure": [
            "Sit in a calm, quiet environment",
            "Practice slow deep breathing for 10 minutes",
            "Avoid screen time and bright lights",
        ],
    }
    return general + specific.get(top, [])
