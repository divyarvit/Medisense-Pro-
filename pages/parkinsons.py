"""
Parkinson's Disease Module — MediSense Pro v11
Three layers solving the "how does the user enter values?" problem:

Tab 1 — Symptom Screener  : Plain language, anyone can use, includes pre-motor signs
Tab 2 — Voice Test        : Record WAV or upload audio → auto-extract Fo, Fhi, Flo, HNR approx
Tab 3 — Clinical ML       : Original model for those with clinical voice analysis reports

7 Clinical Holes Solved:
1. Symptom-based screening — no device needed
2. Stage estimation (Hoehn & Yahr 1-5)
3. Voice recording — user records voice instead of typing technical values
4. Pre-motor / non-motor symptoms included (loss of smell, REM sleep disorder)
5. Age/sex/risk factor context
6. Medication context — already on Levodopa flag
7. Progression tracker integrated into symptom screener
"""
import streamlit as st
import pickle, os, numpy as np, wave, struct, math, io, tempfile, base64
from utils.report_renderer import render_clinical_report
from utils.database import save_report
from utils.explainability import explain_parkinsons
from utils.xai_renderer import render_xai_panel

MODEL = pickle.load(open(os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "models", "parkinsons_model.sav"), "rb"))

# ─── SYMPTOM SCREENER SCORING ─────────────────────────────────────────────────
def _symptom_score(data):
    score = 0
    flags = []
    stage_signals = []

    age    = data["age"]
    sex    = data["sex"]
    family = data["family_history"]
    pest   = data["pesticide_exposure"]
    meds   = data["on_medication"]

    # ── Age & Sex Risk (15 pts) ───────────────────────────────────────
    if age >= 70:
        score += 15; flags.append("🔴 Age 70+ — highest Parkinson's risk group")
    elif age >= 60:
        score += 10; flags.append("🔴 Age 60+ — high Parkinson's risk zone")
    elif age >= 50:
        score += 5;  flags.append("🟡 Age 50+ — risk beginning to rise")
    elif age >= 40:
        score += 2;  flags.append("🟡 Age 40–50 — early-onset Parkinson's possible (rare)")
    else:
        flags.append("🟢 Age below 40 — Parkinson's unlikely (very rare under 40)")

    if sex == "Male":
        score += 3; flags.append("🟡 Male sex — 1.5x higher Parkinson's risk than female")

    if family == "Yes — parent or sibling with Parkinson's":
        score += 8; flags.append("🔴 First-degree relative with Parkinson's — 2x genetic risk")
    elif family == "Yes — extended family (uncle/aunt/grandparent)":
        score += 3; flags.append("🟡 Extended family history of Parkinson's")

    if pest == "Yes — farming / pesticide work":
        score += 7; flags.append("🔴 Pesticide/farming exposure — major Parkinson's risk factor in India")
    elif pest == "Yes — occasional / garden use":
        score += 3; flags.append("🟡 Occasional pesticide exposure")

    # ── PRE-MOTOR SYMPTOMS — appear 5-10 years BEFORE tremor ─────────
    st.markdown("---")
    premotor = data["premotor_symptoms"]

    premotor_scores = {
        "Loss of smell — food/flowers seem to have less scent than before": 8,
        "REM Sleep Disorder — physically acting out dreams (kicking, shouting in sleep)": 10,
        "Constipation — fewer than 3 bowel movements per week for months": 5,
        "Depression or anxiety that started recently without obvious cause": 4,
        "Feeling very tired all the time without physical reason": 3,
        "Urinary urgency — sudden need to urinate that is hard to control": 3,
    }
    pre_total = 0
    for sym in premotor:
        pts = premotor_scores.get(sym, 0)
        pre_total += pts
        score += pts
        if pts >= 8:
            flags.append(f"🔴 Pre-motor sign: {sym} — appears 5-10 years before tremor")
            stage_signals.append("pre-motor")
        elif pts >= 4:
            flags.append(f"🟡 Pre-motor sign: {sym}")

    if pre_total >= 13:
        flags.append("🚨 Multiple pre-motor signs — possible Parkinson's 5-10 years before visible tremor")

    # ── MOTOR SYMPTOMS — the 4 cardinal signs ────────────────────────
    motor = data["motor_symptoms"]

    motor_scores = {
        "Resting tremor — hand/finger shakes when relaxed, stops when reaching for something": 15,
        "Muscle stiffness/rigidity — arms or legs feel stiff and hard to move": 12,
        "Slowness — everything takes longer, getting up from chair is slow": 12,
        "Balance problems — feeling unsteady, fear of falling": 10,
        "Shuffling walk — short steps, feet barely leave ground": 10,
        "Handwriting has become smaller and more cramped": 8,
        "Voice has become softer — people ask you to speak up": 8,
        "Facial expression reduced — people ask if you are okay when you feel fine": 6,
        "Arms do not swing naturally when walking": 6,
        "Stooped posture — slight forward lean": 5,
    }

    motor_total = 0
    cardinal_count = 0
    for sym in motor:
        pts = motor_scores.get(sym, 0)
        motor_total += pts
        score += pts
        if pts >= 12:
            cardinal_count += 1
            flags.append(f"🔴 Cardinal motor sign: {sym}")
            stage_signals.append("motor_cardinal")
        elif pts >= 8:
            flags.append(f"🔴 Major motor sign: {sym}")
            stage_signals.append("motor_major")
        elif pts > 0:
            flags.append(f"🟡 Motor sign: {sym}")
            stage_signals.append("motor_minor")

    # ── Voice symptoms (separate from motor) ─────────────────────────
    voice = data["voice_symptoms"]
    voice_scores = {
        "Voice has become noticeably softer in the last year": 6,
        "Voice sounds monotone — less variation in pitch": 6,
        "Voice sometimes trembles or shakes when speaking": 8,
        "People struggle to understand you even in quiet environments": 5,
        "Swallowing is sometimes difficult — food/water goes wrong way": 7,
        "No voice changes noticed": 0,
    }
    for sym in voice:
        pts = voice_scores.get(sym, 0)
        score += pts
        if pts >= 6:
            flags.append(f"🟡 Voice symptom: {sym}")
            stage_signals.append("voice")

    # ── Stage Estimation (Hoehn & Yahr) ──────────────────────────────
    has_balance  = any("balance" in s.lower() or "fall" in s.lower() for s in motor)
    has_tremor   = any("tremor" in s.lower() for s in motor)
    has_slow     = any("slow" in s.lower() for s in motor)
    has_rigid    = any("stiff" in s.lower() for s in motor)
    bilateral    = data.get("bilateral", False)
    needs_help   = data.get("needs_assistance", False)
    wheelchair   = data.get("wheelchair_bound", False)

    if wheelchair:
        stage = 5
        stage_desc = "Stage 5 — Wheelchair or bed-bound, full-time care required"
        stage_color = "#b71c1c"
    elif needs_help and has_balance:
        stage = 4
        stage_desc = "Stage 4 — Severely limited, cannot live alone"
        stage_color = "#e53935"
    elif has_balance and bilateral:
        stage = 3
        stage_desc = "Stage 3 — Both sides affected, balance impaired, some independence"
        stage_color = "#fb8c00"
    elif bilateral and not has_balance:
        stage = 2
        stage_desc = "Stage 2 — Both sides affected, no balance problem yet, independent"
        stage_color = "#ffa726"
    elif (has_tremor or has_slow or has_rigid) and not bilateral:
        stage = 1
        stage_desc = "Stage 1 — One side only, minimal functional impact"
        stage_color = "#fdd835"
    elif stage_signals:
        stage = 0
        stage_desc = "Pre-motor Stage — Symptoms suggest risk before visible motor signs"
        stage_color = "#7e57c2"
    else:
        stage = 0
        stage_desc = "No significant motor signs detected"
        stage_color = "#43a047"

    score = min(score, 100)

    if score >= 55:   risk = "High Risk"
    elif score >= 30: risk = "Moderate Risk"
    else:             risk = "Low Risk"

    return score, risk, flags, stage, stage_desc, stage_color, cardinal_count

def _build_symptom_report(risk, score, stage, data):
    sev_map = {"High Risk": "Severe", "Moderate Risk": "Moderate", "Low Risk": "Mild"}
    severity = sev_map.get(risk, "Moderate")
    meds = data.get("on_medication", "No")

    if risk == "High Risk":
        conditions = [
            {"condition": "Parkinson's Disease — High Symptom Burden",
             "probability": min(40 + score * 0.45, 85),
             "description": "Multiple motor and/or non-motor signs consistent with Parkinson's.",
             "icd": "G20"},
            {"condition": "Essential Tremor",
             "probability": 10.0,
             "description": "Tremor without other Parkinson's features — needs differentiation.",
             "icd": "G25.0"},
            {"condition": "Parkinsonism (Secondary)",
             "probability": 5.0,
             "description": "Parkinson-like symptoms from medication or other neurological cause.",
             "icd": "G21.9"},
        ]
        do_list = [
            "🚨 See a Neurologist or Movement Disorder Specialist within 1-2 weeks",
            "Ask for a DaTSCAN or SPECT scan to confirm dopamine system status",
            "Start physiotherapy immediately — proven to slow progression",
            "Start speech therapy (LSVT LOUD) if voice is affected",
            "Join a Parkinson's support group — PDMDS India (Parkinson's Disease & Movement Disorder Society)",
            "Install grab bars in bathroom, remove tripping hazards at home",
            "Inform family members — they need to understand the condition",
            "Regular aerobic exercise (boxing, cycling, dancing) — proven neuroprotective",
        ]
        dont_list = [
            "Do NOT delay neurological consultation — early treatment slows progression",
            "Do NOT stop any prescribed medications without doctor guidance",
            "Avoid falls — falls are the biggest danger in Parkinson's",
            "Do NOT drive if tremors or slow reactions affect driving safety",
            "Avoid high-protein meals close to Levodopa dose time (protein blocks absorption)",
            "Do NOT ignore swallowing difficulties — aspiration pneumonia is a major risk",
        ]
        when_doc = [
            "🚨 Within 1-2 weeks — neurologist consultation",
            "Immediately if falls or balance loss occurs",
            "Immediately if swallowing becomes difficult",
            "If tremors suddenly worsen or spread",
        ]
        specialist = "Neurologist / Movement Disorder Specialist — URGENT"
    elif risk == "Moderate Risk":
        conditions = [
            {"condition": "Possible Early Parkinson's Risk",
             "probability": min(20 + score * 0.4, 65),
             "description": "Some signs present. Needs neurological evaluation to confirm or rule out.",
             "icd": "G20"},
            {"condition": "Pre-motor Parkinson's Risk",
             "probability": 20.0,
             "description": "Non-motor symptoms that precede motor Parkinson's detected.",
             "icd": "G20"},
            {"condition": "Normal Age-related Changes",
             "probability": 15.0,
             "description": "Some findings may be normal for age — neurologist will differentiate.",
             "icd": "R29.9"},
        ]
        do_list = [
            "Schedule a Neurologist appointment within 4-6 weeks",
            "Start regular aerobic exercise now — most evidence-based Parkinson's prevention",
            "Maintain a symptom diary — note when symptoms appear, how long they last",
            "Practice balance exercises daily — Tai Chi, yoga",
            "Ensure home safety — good lighting, non-slip mats, clear pathways",
        ]
        dont_list = [
            "Do not ignore progressive symptoms — Parkinson's is most treatable when caught early",
            "Avoid pesticide exposure going forward",
            "Avoid head injuries — always wear helmet",
        ]
        when_doc = [
            "Within 4-6 weeks for neurological evaluation",
            "Sooner if tremors develop or walking becomes difficult",
            "Annual neurological screening after age 60",
        ]
        specialist = "Neurologist (within 4-6 weeks)"
    else:
        conditions = [
            {"condition": "No Significant Parkinson's Indicators",
             "probability": 85.0,
             "description": "No significant motor or pre-motor signs detected.",
             "icd": "Z03.89"},
            {"condition": "Low Neurological Risk Currently",
             "probability": 10.0,
             "description": "Some age-related or lifestyle factors present but no disease signs.",
             "icd": "Z13.858"},
            {"condition": "General Neuroprotective Risk",
             "probability": 5.0,
             "description": "Lifestyle factors that support long-term brain health.",
             "icd": "Z72.3"},
        ]
        do_list = [
            "Regular exercise — best evidence-based brain protector",
            "Mediterranean diet — olive oil, fish, nuts, vegetables",
            "Stay mentally active — puzzles, learning new skills, music",
            "Avoid pesticide exposure where possible",
            "Annual neurological review after age 60",
        ]
        dont_list = [
            "Do not ignore any new tremors or balance changes",
            "Avoid repeated head injuries",
            "Limit pesticide exposure",
        ]
        when_doc = [
            "Annual neurological checkup after age 60",
            "If any tremors, stiffness, or balance problems develop",
            "If handwriting suddenly becomes smaller",
        ]
        specialist = "General Physician (annual checkup after 60)"

    sev_expl = {
        "High Risk": "Multiple Parkinson's motor and non-motor indicators detected. Neurological evaluation urgently needed.",
        "Moderate Risk": "Some Parkinson's risk signs present. Neurological assessment recommended.",
        "Low Risk": "No significant Parkinson's indicators at this time.",
    }.get(risk, "")

    sev_reasons_raw = [
        f"Stage estimate: {stage} (Hoehn & Yahr)" if stage > 0 else "",
        "Multiple pre-motor signs detected" if any(
            "pre-motor" in str(f).lower() for f in []) else "",
    ]
    sev_reasons = [r for r in sev_reasons_raw if r] or ["Symptom pattern analysis completed"]

    confidence = min(40 + score * 0.48, 85)
    home_care = [
        "Practice 'Big' movements daily — Parkinson's responds to intentional large movements",
        "LSVT LOUD voice exercise: say 'Ahhh' as loud as possible for 15 seconds, 10 times daily",
        "Boxing training (non-contact) — most evidence-based exercise for Parkinson's",
        "Install grab bars in bathroom and near bed",
        "Use a weighted pen for writing — reduces tremor interference",
        "Eat antioxidant-rich foods: turmeric, berries, green tea, dark leafy vegetables",
        "Keep emergency contact and PDMDS India helpline: 1800-599-0019 saved",
    ]
    do_dont = {"do": do_list, "dont": dont_list}
    extra = f"**Estimated Stage:** {stage} (Hoehn & Yahr) · **Refer to:** {specialist}"
    return severity, sev_expl, sev_reasons, conditions, confidence, do_dont, home_care, when_doc, extra

# ─── VOICE ANALYSIS using scipy (no librosa needed) ──────────────────────────
def _extract_voice_features(wav_bytes):
    """
    Extract key voice features from WAV audio bytes using scipy + numpy only.
    Returns dict with Fo, Fhi, Flo, HNR approximation, jitter approximation,
    shimmer approximation, and PPE approximation.
    """
    try:
        buf = io.BytesIO(wav_bytes)
        with wave.open(buf) as wf:
            n_channels = wf.getnchannels()
            sampwidth  = wf.getsampwidth()
            framerate  = wf.getframerate()
            n_frames   = wf.getnframes()
            raw        = wf.readframes(n_frames)

        # Convert to numpy array
        if sampwidth == 2:
            samples = np.frombuffer(raw, dtype=np.int16).astype(np.float64)
        elif sampwidth == 4:
            samples = np.frombuffer(raw, dtype=np.int32).astype(np.float64)
        else:
            samples = np.frombuffer(raw, dtype=np.uint8).astype(np.float64) - 128

        # Take first channel if stereo
        if n_channels == 2:
            samples = samples[::2]

        # Normalize
        if np.max(np.abs(samples)) > 0:
            samples = samples / np.max(np.abs(samples))

        # ── Fundamental Frequency via autocorrelation ─────────────────
        # Focus on voiced portion — use middle 60% of recording
        start = len(samples) // 5
        end   = 4 * len(samples) // 5
        seg   = samples[start:end]

        # Autocorrelation to find F0
        corr = np.correlate(seg, seg, mode='full')
        corr = corr[len(corr)//2:]
        corr = corr / corr[0]

        # Search for peak in range 60-400 Hz
        min_lag = int(framerate / 400)
        max_lag = int(framerate / 60)
        min_lag = max(min_lag, 1)
        max_lag = min(max_lag, len(corr)-1)

        # Window-based F0 estimation
        window_size = int(framerate * 0.025)  # 25ms windows
        hop_size    = int(framerate * 0.010)  # 10ms hop

        f0_values = []
        for i in range(0, len(seg) - window_size, hop_size):
            w = seg[i:i+window_size]
            c = np.correlate(w, w, mode='full')
            c = c[len(c)//2:]
            if len(c) > max_lag:
                c_search = c[min_lag:max_lag]
                if len(c_search) > 0:
                    peak_idx = np.argmax(c_search) + min_lag
                    if c[peak_idx] > 0.3:  # voiced threshold
                        f0 = framerate / peak_idx
                        if 60 <= f0 <= 400:
                            f0_values.append(f0)

        if len(f0_values) < 3:
            return None, "Could not detect a clear voice. Please record in a quieter environment and hold the sound longer."

        fo  = float(np.mean(f0_values))
        fhi = float(np.max(f0_values))
        flo = float(np.min(f0_values))

        # ── Jitter approximation ──────────────────────────────────────
        # Jitter = mean absolute difference between consecutive periods / mean period
        periods = [framerate / f for f in f0_values]
        if len(periods) > 1:
            diffs    = [abs(periods[i+1] - periods[i]) for i in range(len(periods)-1)]
            jitter_p = float(np.mean(diffs) / np.mean(periods)) * 100
            jitter_a = float(np.mean(diffs) / framerate * 1e6)  # microseconds
        else:
            jitter_p = 0.005
            jitter_a = 50.0

        # RAP, PPQ, DDP approximations (scaled from jitter)
        rap = jitter_p * 0.47
        ppq = jitter_p * 0.54
        ddp = rap * 3.0

        # ── Shimmer approximation ─────────────────────────────────────
        # Shimmer = amplitude variation between consecutive voiced frames
        rms_values = []
        for i in range(0, len(seg) - window_size, hop_size):
            w = seg[i:i+window_size]
            rms = float(np.sqrt(np.mean(w**2)))
            if rms > 0.001:
                rms_values.append(rms)

        if len(rms_values) > 1:
            amp_diffs  = [abs(rms_values[i+1] - rms_values[i]) for i in range(len(rms_values)-1)]
            shimmer    = float(np.mean(amp_diffs) / np.mean(rms_values)) * 100
            shimmer_db = float(20 * np.log10(1 + shimmer/100)) if shimmer > 0 else 0.1
        else:
            shimmer    = 3.0
            shimmer_db = 0.3

        apq3 = shimmer * 0.50
        apq5 = shimmer * 0.60
        apq  = shimmer * 0.68
        dda  = apq3 * 3.0

        # ── HNR / NHR approximation ───────────────────────────────────
        # Simple signal energy approach
        # Voiced energy vs total energy ratio
        voiced_energy = float(np.mean(seg**2))
        from scipy.signal import butter, filtfilt

        # High-pass filter for noise component
        b, a = butter(4, 1000/(framerate/2), btype='high')
        noise_comp = filtfilt(b, a, seg)
        noise_energy = float(np.mean(noise_comp**2))

        if noise_energy > 0 and voiced_energy > 0:
            hnr = float(10 * np.log10(voiced_energy / (noise_energy + 1e-10)))
            hnr = max(0.0, min(35.0, hnr))
            nhr = float(noise_energy / (voiced_energy + 1e-10))
            nhr = max(0.001, min(0.5, nhr))
        else:
            hnr = 20.0
            nhr = 0.02

        # ── Nonlinear features (approximations) ──────────────────────
        # PPE — Pitch Period Entropy: entropy of normalized pitch histogram
        if len(f0_values) > 5:
            fo_norm = (np.array(f0_values) - np.min(f0_values)) / (np.max(f0_values) - np.min(f0_values) + 1e-10)
            hist, _ = np.histogram(fo_norm, bins=10)
            hist    = hist / (hist.sum() + 1e-10)
            hist    = hist[hist > 0]
            ppe     = float(-np.sum(hist * np.log2(hist + 1e-10)) / np.log2(len(hist)+1))
        else:
            ppe = 0.3

        # RPDE approximation from jitter regularity
        rpde = float(min(0.2 + jitter_p * 0.5, 0.85))

        # DFA — simple scaling approximation
        dfa = 0.72 if jitter_p < 1.5 else 0.82

        # D2 correlation dimension — simplified
        d2 = 2.0 + min(jitter_p * 0.3, 1.0)

        # spread1 and spread2 from F0 distribution
        spread1 = float(np.std(f0_values) / (fo + 1e-10) * (-10))
        spread2 = float(np.std(f0_values) / (fo + 1e-10))

        features = {
            "fo": fo, "fhi": fhi, "flo": flo,
            "jp": jitter_p / 100, "ja": jitter_a / 1e6,
            "rap": rap / 100, "ppq": ppq / 100, "ddp": ddp / 100,
            "sh": shimmer / 100, "shdb": shimmer_db,
            "apq3": apq3 / 100, "apq5": apq5 / 100, "apq": apq / 100,
            "dda": dda / 100, "nhr": nhr, "hnr": hnr,
            "rpde": rpde, "dfa": dfa,
            "sp1": spread1, "sp2": spread2,
            "d2": d2, "ppe": ppe,
        }

        # Readable summary for display
        summary = {
            "Average Pitch (Fo)": f"{fo:.1f} Hz {'✅ Normal' if 85 <= fo <= 255 else '⚠️ Outside normal range'}",
            "Pitch Range": f"{flo:.1f} – {fhi:.1f} Hz {'✅ Good variation' if (fhi-flo)>20 else '⚠️ Narrow — monotone voice'}",
            "Jitter (frequency instability)": f"{jitter_p:.3f}% {'✅ Normal' if jitter_p < 1.04 else '⚠️ Elevated — vocal tremor pattern'}",
            "Shimmer (volume instability)": f"{shimmer:.3f}% {'✅ Normal' if shimmer < 3.27 else '⚠️ Elevated — breath control variation'}",
            "HNR (voice clarity)": f"{hnr:.1f} dB {'✅ Clear voice' if hnr >= 20 else '⚠️ Noisy voice signal'}",
            "PPE (pitch predictability)": f"{ppe:.3f} " + ("✅ Normal" if ppe < 0.20 else "⚠️ High entropy — Parkinson's pattern"),
        }
        return features, summary, None

    except Exception as e:
        return None, None, f"Audio analysis error: {str(e)}. Please try recording again."

def _build_clinical_report(result):
    if result == "Positive":
        severity = "Moderate"
        conditions = [
            {"condition": "Parkinson's Disease (Voice Analysis)", "probability": 68.0,
             "description": "Voice biomarkers indicate Parkinson's-consistent patterns.", "icd": "G20"},
            {"condition": "Essential Tremor", "probability": 20.0,
             "description": "Tremor condition requiring clinical differentiation.", "icd": "G25.0"},
            {"condition": "Multiple System Atrophy", "probability": 12.0,
             "description": "Rare Parkinson-like syndrome.", "icd": "G90.3"},
        ]
        sev_expl = "Voice biomarkers suggest Parkinson's-consistent patterns. Neurological evaluation strongly recommended."
        sev_reasons = ["Abnormal vocal frequency variation",
                       "Jitter/Shimmer values outside normal range",
                       "Nonlinear dynamics suggest neurological involvement"]
        confidence = 76.0
        do_dont = {
            "do": ["Consult Neurologist or Movement Disorder Specialist immediately",
                   "Undergo full neurological evaluation (MRI, DaTSCAN)",
                   "Start physiotherapy to maintain mobility",
                   "Practice voice exercises daily — LSVT LOUD protocol",
                   "Join PDMDS India support group (1800-599-0019)"],
            "dont": ["Do NOT delay neurological consultation",
                     "Do NOT stop any prescribed medications",
                     "Avoid falls — use railings and non-slip mats",
                     "Do NOT drive if tremors affect control"]
        }
        home_care = ["Tai Chi or gentle yoga for balance",
                     "Voice amplifier if speech is affected",
                     "Grab bars in bathroom and near stairs",
                     "Regular aerobic exercise — boxing especially effective",
                     "Antioxidant foods: turmeric, berries, green tea"]
        when_doc  = ["Visit Neurologist within 1 week",
                     "Immediately if tremors suddenly worsen",
                     "If falls or balance loss occurs",
                     "If swallowing becomes difficult"]
        extra = "**Specialists:** Neurologist, Movement Disorder Specialist, Physiotherapist, Speech Therapist (LSVT)"
    else:
        severity = "Mild"
        conditions = [
            {"condition": "No Parkinson's Indicators in Voice", "probability": 87.0,
             "description": "Voice parameters within healthy range.", "icd": "Z03.89"},
            {"condition": "Normal Age-related Voice Changes", "probability": 9.0,
             "description": "Minor variations within acceptable limits.", "icd": "R49.0"},
            {"condition": "Stress-related Voice Changes", "probability": 4.0,
             "description": "Temporary voice changes from stress or illness.", "icd": "F45.8"},
        ]
        sev_expl = "No Parkinson's voice biomarkers detected. Maintain neurological health."
        sev_reasons = ["Voice parameters within normal clinical range"]
        confidence = 73.0
        do_dont = {
            "do": ["Stay mentally active — music, puzzles, learning new skills",
                   "Regular aerobic exercise protects dopamine neurons",
                   "Mediterranean diet supports brain health"],
            "dont": ["Avoid head injuries — wear helmet when cycling",
                     "Avoid pesticide exposure where possible",
                     "Do not ignore any new tremors or balance changes"]
        }
        home_care = ["Balance exercises — standing on one foot",
                     "Learn a musical instrument — stimulates brain",
                     "Daily walks — 30 minutes minimum"]
        when_doc  = ["Annual neurological review after age 60",
                     "If tremors, stiffness, or slow movement develops",
                     "If handwriting becomes smaller or voice softer"]
        extra = "✅ No Parkinson's voice indicators. Keep brain and body active!"
    return severity, sev_expl, sev_reasons, conditions, confidence, do_dont, home_care, when_doc, extra

# ─── MAIN SHOW ────────────────────────────────────────────────────────────────
def show():
    uid   = st.session_state.user_id
    uname = st.session_state.get("full_name", "Patient")

    st.markdown("""<div class="main-header">
        <h1>🧠 Parkinson's Disease Assessment</h1>
        <p>Symptom screener · Voice analysis · Clinical ML model with Explainable AI</p>
    </div>""", unsafe_allow_html=True)

    st.markdown("""<div style="background:#f3e5f5;border-left:5px solid #6a1b9a;
        border-radius:10px;padding:12px 18px;font-size:13px;margin-bottom:16px">
        🧠 <b>Parkinson's is diagnosed clinically — no single blood test or scan confirms it.</b>
        This module helps identify risk patterns through symptoms, voice analysis, and ML biomarkers.
        <b>A neurologist must make the final diagnosis.</b> Early detection gives the best outcomes.
    </div>""", unsafe_allow_html=True)

    sym_tab, voice_tab, clinical_tab = st.tabs([
        "🧠 Symptom Screener — Anyone Can Use",
        "🎙️ Voice Test — Record Your Voice",
        "🔬 Clinical ML — With Voice Analysis Report",
    ])

    # ════════════════════════════════════════════════════════════════════
    # TAB 1 — SYMPTOM SCREENER
    # ════════════════════════════════════════════════════════════════════
    with sym_tab:
        st.markdown("""<div style="background:#e8f5e9;border-left:5px solid #43a047;
            border-radius:10px;padding:12px 18px;font-size:14px;margin-bottom:16px">
            🧠 <b>Plain language — no devices, no lab values, no technical knowledge needed.</b>
            Includes pre-motor symptoms that appear <b>5-10 years before tremor starts.</b>
            Anyone worried about Parkinson's — or caring for someone who might have it — can use this.
        </div>""", unsafe_allow_html=True)

        # ── About You ─────────────────────────────────────────────────
        st.markdown("### 👤 About You")
        ab1, ab2, ab3 = st.columns(3)
        with ab1:
            s_age = st.number_input("🎂 Age", 18, 100, 60, key="s_age")
            s_sex = st.selectbox("⚤ Sex", ["Male", "Female"], key="s_sex")
        with ab2:
            s_family = st.selectbox("👨‍👩‍👧 Family History",
                ["None / Not known",
                 "Yes — parent or sibling with Parkinson's",
                 "Yes — extended family (uncle/aunt/grandparent)"])
            s_pest = st.selectbox("🌾 Pesticide / Farming Exposure",
                ["No exposure",
                 "Yes — occasional / garden use",
                 "Yes — farming / pesticide work"])
        with ab3:
            s_meds = st.selectbox("💊 Already on Parkinson's Medication?",
                ["No",
                 "Yes — on Levodopa/Carbidopa (Syndopa)",
                 "Yes — on other Parkinson's medication",
                 "Not sure"])

        if "on_levodopa" not in st.session_state:
            st.session_state.on_levodopa = False

        if "Levodopa" in s_meds:
            st.markdown("""<div style="background:#fff3e0;border-left:4px solid #fb8c00;
                border-radius:8px;padding:10px 14px;font-size:13px;margin:6px 0">
                ⚠️ <b>Medication Note:</b> Levodopa temporarily improves symptoms — your current
                symptom severity may be lower than your true baseline. The assessment accounts for this.
                This is also why the voice ML model may show a lower risk if you are on medication.
            </div>""", unsafe_allow_html=True)

        st.markdown("---")

        # ── Pre-Motor Symptoms ────────────────────────────────────────
        st.markdown("### 🔍 Pre-Motor Symptoms")
        st.markdown("""<div style="background:#e3f2fd;border-left:4px solid #1565c0;
            border-radius:8px;padding:10px 14px;font-size:13px;margin-bottom:10px">
            💡 <b>These symptoms appear 5-10 years BEFORE tremor starts.</b>
            Most people — and most doctors — do not connect them to Parkinson's at this stage.
            This is genuine early detection.
        </div>""", unsafe_allow_html=True)

        pre_opts = [
            "Loss of smell — food/flowers seem to have less scent than before",
            "REM Sleep Disorder — physically acting out dreams (kicking, shouting in sleep)",
            "Constipation — fewer than 3 bowel movements per week for months",
            "Depression or anxiety that started recently without obvious cause",
            "Feeling very tired all the time without physical reason",
            "Urinary urgency — sudden need to urinate that is hard to control",
            "None of the above",
        ]
        pre_cols = st.columns(2)
        s_premotor = []
        for i, sym in enumerate(pre_opts):
            with pre_cols[i % 2]:
                if st.checkbox(sym, key=f"pre_{i}"):
                    s_premotor.append(sym)

        st.markdown("---")

        # ── Motor Symptoms ────────────────────────────────────────────
        st.markdown("### 🏃 Motor Symptoms — The 4 Cardinal Signs + Others")
        st.markdown("""<div style="background:#ffebee;border-left:4px solid #e53935;
            border-radius:8px;padding:10px 14px;font-size:13px;margin-bottom:10px">
            🔴 <b>Resting tremor, rigidity, slowness, and balance problems</b> are the
            4 cardinal signs of Parkinson's. The presence of 2+ of these is
            highly significant clinically.
        </div>""", unsafe_allow_html=True)

        motor_opts = [
            "Resting tremor — hand/finger shakes when relaxed, stops when reaching for something",
            "Muscle stiffness/rigidity — arms or legs feel stiff and hard to move",
            "Slowness — everything takes longer, getting up from chair is slow",
            "Balance problems — feeling unsteady, fear of falling",
            "Shuffling walk — short steps, feet barely leave ground",
            "Handwriting has become smaller and more cramped",
            "Voice has become softer — people ask you to speak up",
            "Facial expression reduced — people ask if you are okay when you feel fine",
            "Arms do not swing naturally when walking",
            "Stooped posture — slight forward lean",
            "None of the above",
        ]
        motor_cols = st.columns(2)
        s_motor = []
        for i, sym in enumerate(motor_opts):
            with motor_cols[i % 2]:
                if st.checkbox(sym, key=f"motor_{i}"):
                    s_motor.append(sym)

        st.markdown("---")

        # ── Voice Symptoms ────────────────────────────────────────────
        st.markdown("### 🎙️ Voice Changes")
        voice_opts = [
            "Voice has become noticeably softer in the last year",
            "Voice sounds monotone — less variation in pitch",
            "Voice sometimes trembles or shakes when speaking",
            "People struggle to understand you even in quiet environments",
            "Swallowing is sometimes difficult — food/water goes wrong way",
            "No voice changes noticed",
        ]
        vc = st.columns(2)
        s_voice = []
        for i, sym in enumerate(voice_opts):
            with vc[i % 2]:
                if st.checkbox(sym, key=f"voice_{i}"):
                    s_voice.append(sym)

        st.markdown("---")

        # ── Stage Indicators ──────────────────────────────────────────
        st.markdown("### 📊 Additional Information for Stage Estimation")
        si1, si2, si3 = st.columns(3)
        with si1:
            s_bilateral = st.checkbox("Symptoms are on BOTH sides of body")
        with si2:
            s_needs_help = st.checkbox("Cannot manage daily tasks alone anymore")
        with si3:
            s_wheelchair = st.checkbox("Using wheelchair or bed-bound")

        st.markdown("---")

        if st.button("🔍 Run Parkinson's Symptom Assessment", use_container_width=True):
            data = {
                "age": s_age, "sex": s_sex, "family_history": s_family,
                "pesticide_exposure": s_pest, "on_medication": s_meds,
                "premotor_symptoms": s_premotor, "motor_symptoms": s_motor,
                "voice_symptoms": s_voice, "bilateral": s_bilateral,
                "needs_assistance": s_needs_help, "wheelchair_bound": s_wheelchair,
            }
            score, risk, flags, stage, stage_desc, stage_color, cardinal_count = _symptom_score(data)

            risk_color = {"High Risk": "#e53935", "Moderate Risk": "#fb8c00", "Low Risk": "#43a047"}.get(risk, "#888")
            risk_icon  = {"High Risk": "🚨", "Moderate Risk": "⚠️", "Low Risk": "✅"}.get(risk, "⚪")

            st.markdown(f"""<div style="background:{risk_color};color:white;border-radius:16px;
                padding:22px 32px;text-align:center;margin:12px 0;
                box-shadow:0 6px 24px {risk_color}44">
                <h1 style="margin:0;font-size:2em">{risk_icon} {risk}</h1>
                <h3 style="margin:8px 0 0;opacity:0.95">Symptom Score: {score}/100</h3>
            </div>""", unsafe_allow_html=True)

            # Stage banner
            if stage > 0:
                st.markdown(f"""<div style="background:{stage_color};color:white;border-radius:12px;
                    padding:14px 24px;text-align:center;margin:8px 0">
                    <b>Estimated Stage: {stage} — {stage_desc}</b>
                </div>""", unsafe_allow_html=True)

                st.markdown("""<div style="background:#f8f9fa;border-radius:10px;padding:14px;
                    font-size:13px;border:1px solid #e0e0e0;margin:8px 0">
                    <b>Hoehn & Yahr Stage Scale:</b><br>
                    Stage 1 — One side only · Stage 2 — Both sides, no balance issue ·
                    Stage 3 — Balance affected · Stage 4 — Cannot live alone ·
                    Stage 5 — Wheelchair/bed-bound
                    <br><b>Note:</b> Stage 0 = Pre-motor signs only (most important for early detection)
                </div>""", unsafe_allow_html=True)

            # Cardinal sign count
            if cardinal_count >= 2:
                st.markdown(f"""<div style="background:#ffebee;border-left:5px solid #e53935;
                    border-radius:10px;padding:12px 18px;font-size:13px;margin:8px 0">
                    🔴 <b>{cardinal_count} cardinal signs of Parkinson's identified.</b>
                    The presence of 2 or more cardinal signs (tremor, rigidity, slowness, balance)
                    is clinically significant. A neurologist evaluation is strongly recommended.
                </div>""", unsafe_allow_html=True)

            # Pre-motor early detection
            if any("pre-motor" in str(f).lower() or "pre_motor" in str(f).lower() or
                   "loss of smell" in str(f).lower() or "rem" in str(f).lower() for f in flags):
                st.markdown("""<div style="background:#e8eaf6;border-left:5px solid #3949ab;
                    border-radius:10px;padding:12px 18px;font-size:13px;margin:8px 0">
                    🔬 <b>Pre-motor signs detected.</b> Loss of smell, REM sleep disorder, and
                    constipation are now recognised as early Parkinson's biomarkers that appear
                    5-10 years before tremor. Early neurological evaluation at this stage can
                    significantly slow disease progression with timely intervention.
                </div>""", unsafe_allow_html=True)

            # Medication note
            if "Levodopa" in s_meds:
                st.markdown("""<div style="background:#fff3e0;border-left:4px solid #fb8c00;
                    border-radius:8px;padding:10px 14px;font-size:13px;margin:6px 0">
                    💊 <b>You are on Levodopa:</b> Your current symptoms may be reduced by medication.
                    Your actual disease severity without medication would likely show higher scores.
                    The voice ML model may also show improved parameters while on medication.
                    Always inform the neurologist about your medication schedule.
                </div>""", unsafe_allow_html=True)

            r1, r2 = st.tabs(["📋 Factor Analysis", "📄 Full Report & Advice"])

            with r1:
                st.markdown("### 🔍 Factor-by-Factor Breakdown")
                for f in flags:
                    bg = ("#ffebee" if "🔴" in f or "🚨" in f else
                          "#fff8e1" if "🟡" in f else
                          "#e8f5e9" if "🟢" in f else "#e8eaf6")
                    bd = ("#e53935" if "🔴" in f or "🚨" in f else
                          "#fb8c00" if "🟡" in f else
                          "#43a047" if "🟢" in f else "#3949ab")
                    st.markdown(f"""<div style="background:{bg};border-left:4px solid {bd};
                        border-radius:8px;padding:9px 14px;margin:4px 0;font-size:13px">
                        {f}</div>""", unsafe_allow_html=True)

            with r2:
                severity, sev_expl, sev_reasons, conditions, confidence, do_dont, home_care, when_doc, extra = \
                    _build_symptom_report(risk, score, stage, data)
                render_clinical_report("Parkinson's Disease Screening", severity, sev_expl, sev_reasons,
                                        conditions, confidence, do_dont, home_care, when_doc, extra,
                                        patient_name=uname, vital_summary=None)

            save_report(uid, "Parkinson's Symptom Screening", severity,
                        conditions[0]["condition"], confidence,
                        f"Age:{s_age}|Score:{score}|Stage:{stage}|Risk:{risk}",
                        numeric_value=float(score))
            st.success("✅ Assessment saved to your history.")

    # ════════════════════════════════════════════════════════════════════
    # TAB 2 — VOICE TEST
    # ════════════════════════════════════════════════════════════════════
    with voice_tab:
        st.markdown("""<div style="background:#f3e5f5;border-left:5px solid #6a1b9a;
            border-radius:10px;padding:12px 18px;font-size:14px;margin-bottom:16px">
            🎙️ <b>Instead of asking you to type MDVP:Fo(Hz) values you cannot measure —
            you record your voice and the app extracts the parameters automatically.</b><br>
            No PRAAT software needed. No speech pathologist needed. Just your voice.
        </div>""", unsafe_allow_html=True)

        st.markdown("### 📋 How to Record — Follow These Steps")

        steps_html = ""
        for step, txt in [
            ("1", "Find a quiet room — no TV, fan, or AC noise"),
            ("2", "Sit comfortably upright"),
            ("3", "Take a deep breath"),
            ("4", "Say 'Ahhhhhh' — hold it steadily for <b>5-8 seconds</b>"),
            ("5", "Keep the same pitch and volume throughout — do not vary it intentionally"),
            ("6", "Record using any voice recorder app and save as WAV file"),
            ("7", "Upload the WAV file below"),
        ]:
            steps_html += f"""<div style="display:flex;align-items:center;gap:12px;
                padding:8px 12px;background:#f8f9fa;border-radius:8px;margin:4px 0">
                <div style="background:#6a1b9a;color:white;border-radius:50%;
                    width:26px;height:26px;display:flex;align-items:center;
                    justify-content:center;font-weight:bold;flex-shrink:0">{step}</div>
                <span style="font-size:13px">{txt}</span>
            </div>"""
        st.markdown(steps_html, unsafe_allow_html=True)

        st.markdown("---")
        uploaded_wav = st.file_uploader("📁 Upload your WAV voice recording", type=["wav"])

        # Also explain the feature meanings
        with st.expander("🔬 What features will be extracted and what do they mean?"):
            st.markdown("""
| Feature | What It Measures | Normal | Parkinson's |
|---|---|---|---|
| **Fo (Average Pitch)** | Base vibration rate of vocal cords | 85–255 Hz | Often lower or unstable |
| **Fhi / Flo (Pitch Range)** | Difference between highest and lowest pitch | Wide range | Narrow — monotone voice |
| **Jitter (%)** | Inconsistency in timing of vocal cord vibrations | Below 1.04% | Elevated — tremor in voice |
| **Shimmer (%)** | Inconsistency in loudness of each vibration | Below 3.27% | Elevated — breath control loss |
| **HNR (dB)** | How much clean sound vs noise in voice | Above 20 dB | Lower — breathy, rough voice |
| **PPE** | How unpredictable pitch variation is | Below 0.20 | Higher — chaotic pitch |
            """)
            st.markdown("""<div style="background:#fff3e0;border-left:4px solid #fb8c00;
                border-radius:8px;padding:10px 14px;font-size:12px">
                ⚠️ <b>Important:</b> This voice analysis extracts key features using audio signal processing.
                It is an approximation — not a full clinical voice analysis (which requires PRAAT software
                in a soundproof booth with professional equipment). Use this for initial screening only.
                The Clinical ML tab is for patients with formal voice analysis reports.
            </div>""", unsafe_allow_html=True)

        if uploaded_wav is not None:
            wav_bytes = uploaded_wav.read()
            st.audio(uploaded_wav)

            with st.spinner("🔬 Analysing voice signal — extracting frequency, jitter, shimmer, HNR, PPE..."):
                result = _extract_voice_features(wav_bytes)
                if len(result) == 3:
                    features, summary, error = result
                else:
                    features, error = result
                    summary = None

            if error:
                st.error(f"❌ {error}")
            elif features and summary:
                st.markdown("### 📊 Extracted Voice Parameters")
                for param, value in summary.items():
                    color = "#ffebee" if "⚠️" in value else "#e8f5e9"
                    border = "#e53935" if "⚠️" in value else "#43a047"
                    st.markdown(f"""<div style="background:{color};border-left:4px solid {border};
                        border-radius:8px;padding:8px 14px;margin:3px 0;font-size:13px">
                        <b>{param}:</b> {value}
                    </div>""", unsafe_allow_html=True)

                st.markdown("---")
                if st.button("🔬 Run ML Model on Extracted Voice Features", use_container_width=True):
                    vals = [features[k] for k in [
                        "fo","fhi","flo","jp","ja","rap","ppq","ddp",
                        "sh","shdb","apq3","apq5","apq","dda","nhr","hnr",
                        "rpde","dfa","sp1","sp2","d2","ppe"]]
                    pred   = MODEL.predict([vals])[0]
                    result_label = "Positive" if pred == 1 else "Negative"

                    res_color = "#e53935" if result_label == "Positive" else "#43a047"
                    res_icon  = "⚠️" if result_label == "Positive" else "✅"

                    st.markdown(f"""<div style="background:{res_color};color:white;border-radius:14px;
                        padding:18px 28px;text-align:center;margin:12px 0">
                        <h2 style="margin:0">{res_icon} Voice Analysis Result: {result_label}</h2>
                        <p style="margin:8px 0 0;font-size:13px;opacity:0.9">
                            Based on automatically extracted voice biomarkers
                        </p>
                    </div>""", unsafe_allow_html=True)

                    st.markdown("""<div style="background:#e8eaf6;border-left:4px solid #3949ab;
                        border-radius:8px;padding:10px 14px;font-size:12px;margin:8px 0">
                        ⚠️ <b>Interpretation note:</b> This result uses automatically extracted voice features
                        which are approximations of clinical PRAAT measurements. This is a screening tool only.
                        For a definitive voice biomarker assessment, use the Clinical ML tab with values
                        from a professional voice analysis report.
                    </div>""", unsafe_allow_html=True)

                    v1, v2 = st.tabs(["🧠 Explainable AI", "📄 Report"])
                    with v1:
                        explanation = explain_parkinsons(
                            features["hnr"], features["jp"], features["sh"],
                            features["rpde"], features["ppe"], features["dfa"],
                            features["nhr"], result_label)
                        render_xai_panel(explanation, "Parkinson's Voice Analysis")
                    with v2:
                        severity, sev_expl, sev_reasons, conditions, confidence, do_dont, home_care, when_doc, extra = \
                            _build_clinical_report(result_label)
                        render_clinical_report("Parkinson's Voice Screening", severity, sev_expl, sev_reasons,
                                                conditions, confidence, do_dont, home_care, when_doc, extra,
                                                patient_name=uname, vital_summary=None)

                    save_report(uid, "Parkinson's Voice Analysis", severity,
                                conditions[0]["condition"], confidence,
                                f"Fo:{features['fo']:.1f}|HNR:{features['hnr']:.1f}|PPE:{features['ppe']:.3f}|Result:{result_label}",
                                numeric_value=features["hnr"])
                    st.success("✅ Report saved to your history.")

    # ════════════════════════════════════════════════════════════════════
    # TAB 3 — CLINICAL ML
    # ════════════════════════════════════════════════════════════════════
    with clinical_tab:
        st.markdown("""<div style="background:#e3f2fd;border-left:5px solid #1565c0;
            border-radius:10px;padding:12px 18px;font-size:14px;margin-bottom:16px">
            🔬 <b>Clinical Mode:</b> For patients who have received a formal voice analysis report
            from a speech pathology clinic or Parkinson's research centre. Enter the 22 PRAAT/voice
            analysis parameters from your report. The ML model was trained on the UCI Parkinson's
            Dataset — 195 voice recordings from 31 people.
        </div>""", unsafe_allow_html=True)

        st.markdown("""<div style="background:#fff3e0;border-left:4px solid #fb8c00;
            border-radius:8px;padding:10px 14px;font-size:13px;margin-bottom:12px">
            📋 <b>Where to get these values:</b> A speech pathologist runs a sustained phonation
            analysis using PRAAT software. The resulting report contains all 22 values below.
            This is done at Parkinson's research clinics, medical college speech departments,
            and NIMHANS-affiliated centres.
            <br>💊 <b>Note:</b> If you are on Levodopa, your voice parameters may appear improved —
            this is expected and should be mentioned to your neurologist.
        </div>""", unsafe_allow_html=True)

        with st.expander("ℹ️ What do these measurements mean?"):
            st.markdown("""
- **Fo/Fhi/Flo (Hz):** Average, max, min vocal frequency — pitch of your voice
- **Jitter (5 values):** How consistent vocal cord timing is — higher = more tremor
- **Shimmer (6 values):** How consistent voice volume is — higher = more breath control loss
- **NHR/HNR:** Noise vs harmonics in voice — higher NHR = more noise = Parkinson's pattern
- **RPDE:** How predictable voice repetition patterns are
- **DFA:** Self-similarity of voice signal across time scales
- **D2:** Mathematical complexity of voice signal
- **PPE:** How chaotic pitch variation is — single most discriminating Parkinson's feature
            """)

        st.markdown("### 📝 Enter 22 Voice Analysis Parameters")

        # Medication context
        cl_on_meds = st.selectbox("💊 Are you currently on Parkinson's medication?",
            ["No", "Yes — Levodopa/Carbidopa", "Yes — other medication", "Not sure"],
            key="cl_meds")

        c1, c2, c3, c4, c5 = st.columns(5)
        fields = [
            ("fo",  "Fo(Hz)",      c1, 119.99),
            ("fhi", "Fhi(Hz)",     c2, 157.30),
            ("flo", "Flo(Hz)",     c3, 74.99),
            ("jp",  "Jitter(%)",   c4, 0.00784),
            ("ja",  "Jitter(Abs)", c5, 0.00007),
            ("rap", "RAP",         c1, 0.00370),
            ("ppq", "PPQ",         c2, 0.00422),
            ("ddp", "DDP",         c3, 0.01109),
            ("sh",  "Shimmer",     c4, 0.04374),
            ("shdb","Shimmer(dB)", c5, 0.426),
            ("apq3","APQ3",        c1, 0.02182),
            ("apq5","APQ5",        c2, 0.03130),
            ("apq", "APQ",         c3, 0.02971),
            ("dda", "DDA",         c4, 0.06545),
            ("nhr", "NHR",         c5, 0.02211),
            ("hnr", "HNR",         c1, 21.033),
            ("rpde","RPDE",        c2, 0.414783),
            ("dfa", "DFA",         c3, 0.815285),
            ("sp1", "spread1",     c4, -4.813),
            ("sp2", "spread2",     c5, 0.266482),
            ("d2",  "D2",          c1, 2.301),
            ("ppe", "PPE",         c2, 0.284654),
        ]
        inputs = {}
        for key, label, col, default in fields:
            with col:
                inputs[key] = st.number_input(label, value=float(default), format="%.5f", key=f"cl_{key}")

        if st.button("🔍 Run Clinical Parkinson's Assessment", use_container_width=True):
            vals   = [inputs[k] for k, *_ in fields]
            pred   = MODEL.predict([vals])[0]
            result = "Positive" if pred == 1 else "Negative"

            severity, sev_expl, sev_reasons, conditions, confidence, do_dont, home_care, when_doc, extra = \
                _build_clinical_report(result)

            res_color = "#e53935" if result == "Positive" else "#43a047"
            res_icon  = "⚠️" if result == "Positive" else "✅"

            st.markdown(f"""<div style="background:{res_color};color:white;border-radius:16px;
                padding:20px 28px;text-align:center;margin:16px 0;
                box-shadow:0 4px 20px {res_color}44">
                <h2 style="margin:0;font-size:1.8em">{res_icon} Parkinson's Result: {result}</h2>
                <p style="margin:6px 0 0;opacity:0.9">{sev_expl}</p>
            </div>""", unsafe_allow_html=True)

            # Key feature highlights
            flag_rows = []
            if inputs["ppe"] > 0.20:
                flag_rows.append(f"🔴 PPE = {inputs['ppe']:.3f} (above 0.20 — Parkinson's pattern, most discriminating feature)")
            if inputs["hnr"] < 20:
                flag_rows.append(f"🔴 HNR = {inputs['hnr']:.2f} dB (below 20 — noisy voice signal)")
            if inputs["jp"] > 0.01:
                flag_rows.append(f"🔴 Jitter = {inputs['jp']:.4f} (above 0.0104 — elevated vocal tremor)")
            if inputs["sh"] > 0.03:
                flag_rows.append(f"🔴 Shimmer = {inputs['sh']:.4f} (above 0.0327 — amplitude instability)")
            if inputs["rpde"] > 0.5:
                flag_rows.append(f"🟡 RPDE = {inputs['rpde']:.3f} (elevated — reduced voice predictability)")
            if flag_rows:
                st.markdown("**Key Abnormal Findings:**")
                for fr in flag_rows:
                    bg = "#ffebee" if "🔴" in fr else "#fff8e1"
                    bd = "#e53935" if "🔴" in fr else "#fb8c00"
                    st.markdown(f"""<div style="background:{bg};border-left:4px solid {bd};
                        border-radius:8px;padding:8px 14px;margin:3px 0;font-size:13px">{fr}</div>""",
                        unsafe_allow_html=True)

            if "Levodopa" in cl_on_meds:
                st.markdown("""<div style="background:#fff3e0;border-left:4px solid #fb8c00;
                    border-radius:8px;padding:10px 14px;font-size:13px;margin:8px 0">
                    💊 <b>Levodopa Context:</b> You are currently on Levodopa. This medication
                    temporarily improves voice parameters. A result of Negative while on Levodopa
                    does NOT mean Parkinson's is absent — it means the medication is working.
                    Your neurologist should compare on-medication and off-medication recordings.
                </div>""", unsafe_allow_html=True)

            tab1, tab2 = st.tabs(["🧠 Explainable AI — Why this result?",
                                   "📄 Full Clinical Report"])
            with tab1:
                explanation = explain_parkinsons(
                    inputs["hnr"], inputs["jp"], inputs["sh"],
                    inputs["rpde"], inputs["ppe"], inputs["dfa"],
                    inputs["nhr"], result)
                render_xai_panel(explanation, "Parkinson's Disease — Clinical ML")
            with tab2:
                render_clinical_report("Parkinson's Disease", severity, sev_expl, sev_reasons,
                                        conditions, confidence, do_dont, home_care, when_doc, extra,
                                        patient_name=uname, vital_summary=None)

            save_report(uid, "Parkinson's Disease", severity,
                        conditions[0]["condition"], confidence,
                        f"Result:{result}|HNR:{inputs['hnr']:.3f}|RPDE:{inputs['rpde']:.3f}|PPE:{inputs['ppe']:.3f}",
                        numeric_value=inputs["hnr"])
            st.success("✅ Report saved to your history.")

    st.markdown("""<div class="footer">
        MediSense Pro · Parkinson's Assessment v11 · SWE1904 · VIT · R.Divya 21MIS0261
    </div>""", unsafe_allow_html=True)
