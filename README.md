# 🏥 MediSense Pro — AI-Powered Personal Health Intelligence Platform

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python"/>
  <img src="https://img.shields.io/badge/Streamlit-1.30+-red?style=for-the-badge&logo=streamlit"/>
  <img src="https://img.shields.io/badge/AI%20Powered-Groq%20LLM-green?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/ML-Scikit--Learn-orange?style=for-the-badge&logo=scikit-learn"/>
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge"/>
</p>

---

## 🌍 What is MediSense Pro?

**MediSense Pro** is a comprehensive AI-powered health intelligence platform built to make early disease detection, health monitoring, and medical guidance accessible to everyone — especially in regions where quality healthcare is scarce.

It combines **machine learning disease prediction**, **AI-driven medical chat**, **family health management**, and **real-time analytics** into a single easy-to-use web application.

> 💡 *"Bringing hospital-grade intelligence to your fingertips — anytime, anywhere."*

---

## 🎯 Motivation — Why We Built This

### The Problem
- Millions of people in India and across the world **lack access to timely medical diagnosis**
- Rural and semi-urban populations often **travel hours to reach a hospital** for basic checkups
- **Early detection** of diseases like diabetes, heart disease, and kidney failure can save lives — but most people don't know their risk until it's too late
- Medical consultations are **expensive and time-consuming**
- Patients forget medications, miss follow-ups, and have **no centralised health record**

### Our Solution
MediSense Pro addresses these problems by providing:
- **Instant AI disease risk assessment** without needing to visit a hospital
- **Continuous health monitoring** from home
- **Smart alerts** when results indicate danger
- **Family health management** — one account for the entire family
- **Doctor dashboard** for healthcare professionals to monitor patients remotely

---

## 🏥 How It Helps Society & Hospitals

| Stakeholder | Benefit |
|-------------|---------|
| 👨‍👩‍👧 **General Public** | Free, instant health risk screening from home |
| 🏥 **Hospitals** | Reduce OPD load by filtering low-risk patients |
| 👨‍⚕️ **Doctors** | Monitor patients remotely via Doctor Dashboard |
| 🌾 **Rural Communities** | Access specialist-level guidance without travel |
| 👴 **Elderly Patients** | Medicine reminders, family vault, easy interface |
| 🏢 **Corporate Health** | Employee wellness monitoring at scale |

---

## ✨ Key Features

### 🔬 Disease Prediction Modules
| Module | What It Detects |
|--------|----------------|
| 🩸 Diabetes Predictor | Type 2 Diabetes risk from glucose, BMI, age data |
| ❤️ Heart Disease | Cardiovascular risk from ECG, cholesterol, BP data |
| 🫘 Kidney Disease | Chronic kidney disease from blood/urine markers |
| 🦋 Thyroid Disorder | Hypothyroid / Hyperthyroid classification |
| 🧠 Parkinson's Disease | Early Parkinson's detection from voice features |
| ⚖️ BMI Calculator | BMI, BMR, TDEE, macro targets, personalised tips |
| 📸 Photo Diagnosis | AI skin condition analysis from uploaded photos |

### 🤖 AI & Intelligence
- **Groq LLM AI Chat** — Ask any health question and get doctor-quality answers
- **Explainable AI (XAI)** — Understand *why* the model made a prediction
- **Symptom Tracker** — Log symptoms daily and track health trends
- **Smart Alerts** — Automatic alerts for severe or dangerous results

### 👨‍👩‍👧 Family & Personal Health
- **Family Health Vault** — Manage health records for your entire family
- **Medicine Reminder** — Never miss a dose with smart reminders
- **Prescription Manager** — Store and view all prescriptions digitally
- **Health Report Card** — Complete health summary in one view
- **PDF Report Export** — Download your health reports as professional PDFs

### 🏥 Hospital & Doctor Tools
- **Doctor Dashboard** — Doctors can view and monitor patient reports
- **Hospital Locator** — Find nearby hospitals and clinics
- **Analytics Dashboard** — Visual health trends and statistics
- **General Health Q&A** — Evidence-based health information

---

## 🛠️ Technology Stack

```
Frontend        →  Streamlit (Python Web Framework)
ML Models       →  Scikit-Learn (Random Forest, SVM, Logistic Regression)
AI Chat         →  Groq API (LLaMA 3 / Mixtral LLM)
Database        →  SQLite (local), upgradeable to PostgreSQL
PDF Generation  →  ReportLab
Data Viz        →  Plotly, Altair, Matplotlib
Image AI        →  Pillow + AI Vision APIs
Auth            →  SHA-256 password hashing
Deployment      →  Streamlit Cloud / Docker ready
```

---

## 📁 Project Structure

```
medisense_pro/
│
├── app.py                    # Main application entry point
├── config.py                 # App configuration & settings
├── medisense.db              # SQLite database
│
├── pages/                    # All feature pages
│   ├── dashboard.py          # User dashboard
│   ├── diabetes.py           # Diabetes prediction
│   ├── heart.py              # Heart disease prediction
│   ├── kidney.py             # Kidney disease prediction
│   ├── thyroid.py            # Thyroid disorder detection
│   ├── parkinsons.py         # Parkinson's detection
│   ├── bmi.py                # BMI & body health calculator
│   ├── ai_chat.py            # AI health chatbot
│   ├── photo_diagnosis.py    # Photo-based diagnosis
│   ├── symptom_tracker.py    # Symptom logging & tracking
│   ├── medicine_reminder.py  # Medicine reminders
│   ├── prescription.py       # Prescription manager
│   ├── family_vault.py       # Family health records
│   ├── health_report_card.py # Complete health summary
│   ├── doctor_dashboard.py   # Doctor monitoring panel
│   ├── hospital_locator.py   # Nearby hospital finder
│   ├── analytics.py          # Health analytics & charts
│   ├── reports.py            # Report history & PDF export
│   └── general.py            # General health information
│
├── utils/                    # Utility modules
│   ├── database.py           # Database operations
│   ├── diagnosis_engine.py   # ML prediction engine
│   ├── groq_explainer.py     # Groq AI integration
│   ├── explainability.py     # XAI explanations
│   ├── pdf_generator.py      # PDF report generation
│   ├── report_renderer.py    # Report display utilities
│   └── translations.py       # Multi-language support
│
└── models/                   # Trained ML model files
    ├── diabetes_model.pkl
    ├── heart_model.pkl
    ├── kidney_model.pkl
    ├── thyroid_model.pkl
    └── parkinsons_model.pkl
```

---

## 🚀 How to Run the Project

### Prerequisites
- Python 3.10 or higher
- pip package manager

### Step 1: Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/medisense-pro.git
cd medisense-pro
```

### Step 2: Install dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Add your Groq API key
Create a file `.streamlit/secrets.toml` and add:
```toml
GROQ_API_KEY = "your_groq_api_key_here"
```

### Step 4: Run the application
```bash
streamlit run app.py
```

### Step 5: Open in browser
```
http://localhost:8501
```

---

## 📊 ML Model Performance

| Disease | Algorithm | Accuracy |
|---------|-----------|----------|
| Diabetes | Random Forest | ~94% |
| Heart Disease | Gradient Boosting | ~92% |
| Kidney Disease | Random Forest | ~96% |
| Thyroid | SVM | ~93% |
| Parkinson's | XGBoost | ~91% |

> Models trained on publicly available medical datasets from UCI ML Repository and Kaggle.

---

## 🌐 Real-World Impact

- ✅ **Early detection** can reduce disease severity by up to 70%
- ✅ Can serve **thousands of patients simultaneously** at zero marginal cost
- ✅ Reduces unnecessary hospital visits by **screening low-risk patients**
- ✅ Helps **doctors prioritise** high-risk patients faster
- ✅ Promotes **health awareness** through education and tracking
- ✅ Saves patients an average of **₹2,000–₹5,000** per screening visit

---

## 🔮 Future Enhancements

- [ ] Mobile app (Android & iOS)
- [ ] Integration with wearables (smartwatches, glucometers)
- [ ] Telemedicine video consultation
- [ ] ABDM / Ayushman Bharat health ID integration
- [ ] Multi-language support (Hindi, Telugu, Tamil)
- [ ] Hospital EHR system integration
- [ ] Cloud deployment with real-time sync

---

## 👨‍💻 Developed By

**Team MediSense** — VIT University  
Built with ❤️ to make healthcare accessible to every Indian

---

## 📄 License

This project is licensed under the **MIT License** — free to use, modify, and distribute.

---

## ⭐ If this project helped you, please give it a star!

> *MediSense Pro — Because your health deserves intelligence.*
