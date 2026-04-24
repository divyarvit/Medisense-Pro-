# ================================================================
# MediSense Pro — Complete Model Training Script
# AI-Based Disease Diagnosis & Recommendation System
#
# Student  : R. Divya | 21MIS0261
# Course   : SWE1904 — Capstone Project
# Guide    : Prof. Benjula Anbu Malar M B
# Institute: VIT Vellore
# ================================================================

import pandas as pd
import numpy as np
import pickle
import os
import warnings
warnings.filterwarnings('ignore')

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, roc_auc_score, confusion_matrix, classification_report
)

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(BASE_DIR, 'datasets')
MODEL_DIR   = os.path.join(BASE_DIR, 'models')
os.makedirs(MODEL_DIR, exist_ok=True)

def train_and_evaluate(X_train, X_test, y_train, y_test, dataset_name):
    print(f"\n{'='*68}")
    print(f"  TRAINING: {dataset_name}")
    print(f"{'='*68}")
    print(f"  Training samples : {X_train.shape[0]}")
    print(f"  Testing  samples : {X_test.shape[0]}")
    print(f"  Features         : {X_train.shape[1]}")
    print(f"{'-'*68}")

    models = {
        'Logistic Regression' : LogisticRegression(max_iter=1000, random_state=42),
        'Decision Tree'       : DecisionTreeClassifier(random_state=42),
        'Random Forest'       : RandomForestClassifier(n_estimators=100, random_state=42),
        'SVM'                 : SVC(probability=True, random_state=42),
        'KNN'                 : KNeighborsClassifier(n_neighbors=5),
    }

    results = {}
    print(f"  {'Algorithm':<22} {'Accuracy':>9} {'Precision':>10} {'Recall':>8} {'F1':>8} {'ROC-AUC':>9}")
    print(f"  {'-'*22} {'-'*9} {'-'*10} {'-'*8} {'-'*8} {'-'*9}")

    for name, model in models.items():
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        y_prob = model.predict_proba(X_test)[:, 1]
        acc  = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, zero_division=0)
        rec  = recall_score(y_test, y_pred, zero_division=0)
        f1   = f1_score(y_test, y_pred, zero_division=0)
        auc  = roc_auc_score(y_test, y_prob)
        results[name] = {'model': model, 'accuracy': acc,
                         'precision': prec, 'recall': rec,
                         'f1': f1, 'auc': auc, 'y_pred': y_pred}
        print(f"  {name:<22} {acc:>8.2%} {prec:>9.2%} {rec:>8.2%} {f1:>8.2%} {auc:>9.2%}")

    best_name = max(results, key=lambda x: results[x]['accuracy'])
    best = results[best_name]
    print(f"\n  Best Model : {best_name}")
    print(f"  Accuracy   : {best['accuracy']:.2%}")
    print(f"  F1-Score   : {best['f1']:.2%}")
    print(f"  ROC-AUC    : {best['auc']:.2%}")
    return results, best_name

print("="*68)
print("  MEDISENSE PRO — COMPLETE MODEL TRAINING PIPELINE")
print("  Diabetes | Heart Disease | Parkinson's")
print("="*68)

# ── DIABETES ──────────────────────────────────────────────────
df_d = pd.read_csv(os.path.join(DATASET_DIR, 'diabetes.csv'))
print(f"\nDiabetes Dataset  | Shape: {df_d.shape} | Target: Outcome (0/1)")
print(f"Class counts: {dict(df_d['Outcome'].value_counts())}")

zero_cols = ['Glucose', 'BloodPressure', 'SkinThickness', 'Insulin', 'BMI']
df_d_clean = df_d.copy()
for col in zero_cols:
    df_d_clean[col] = df_d_clean[col].replace(0, df_d_clean[col].median())

X_d = df_d_clean.drop('Outcome', axis=1)
y_d = df_d_clean['Outcome']
X_d_sc = StandardScaler().fit_transform(X_d)
X_train_d, X_test_d, y_train_d, y_test_d = train_test_split(
    X_d_sc, y_d, test_size=0.2, random_state=42, stratify=y_d)

results_d, best_d = train_and_evaluate(
    X_train_d, X_test_d, y_train_d, y_test_d,
    "DIABETES — PIMA Indian Diabetes Dataset (768 records, 8 features)")

cv_d = cross_val_score(results_d[best_d]['model'], X_d_sc, y_d, cv=5)
print(f"\n5-Fold CV: {[f'{s:.2%}' for s in cv_d]}")
print(f"Mean: {cv_d.mean():.2%}  Std: {cv_d.std():.2%}")
print(classification_report(y_test_d, results_d[best_d]['y_pred'],
      target_names=['Non-Diabetic', 'Diabetic']))
pickle.dump(results_d[best_d]['model'],
            open(os.path.join(MODEL_DIR, 'diabetes_model.sav'), 'wb'))
print("Model saved -> models/diabetes_model.sav")

# ── HEART DISEASE ─────────────────────────────────────────────
df_h = pd.read_csv(os.path.join(DATASET_DIR, 'heart.csv'))
print(f"\nHeart Disease Dataset  | Shape: {df_h.shape} | Target: target (0/1)")
print(f"Class counts: {dict(df_h['target'].value_counts())}")

X_h = df_h.drop('target', axis=1)
y_h = df_h['target']
X_h_sc = StandardScaler().fit_transform(X_h)
X_train_h, X_test_h, y_train_h, y_test_h = train_test_split(
    X_h_sc, y_h, test_size=0.2, random_state=42, stratify=y_h)

results_h, best_h = train_and_evaluate(
    X_train_h, X_test_h, y_train_h, y_test_h,
    "HEART DISEASE — Cleveland Dataset (303 records, 13 features)")

cv_h = cross_val_score(results_h[best_h]['model'], X_h_sc, y_h, cv=5)
print(f"\n5-Fold CV: {[f'{s:.2%}' for s in cv_h]}")
print(f"Mean: {cv_h.mean():.2%}  Std: {cv_h.std():.2%}")
print(classification_report(y_test_h, results_h[best_h]['y_pred'],
      target_names=['No Disease', 'Heart Disease']))
pickle.dump(results_h[best_h]['model'],
            open(os.path.join(MODEL_DIR, 'heart_disease_model1.sav'), 'wb'))
print("Model saved -> models/heart_disease_model1.sav")

# ── PARKINSON'S ───────────────────────────────────────────────
df_p = pd.read_csv(os.path.join(DATASET_DIR, 'parkinsons.csv'))
if 'name' in df_p.columns:
    df_p = df_p.drop('name', axis=1)
print(f"\nParkinson's Dataset  | Shape: {df_p.shape} | Target: status (0/1)")
print(f"Class counts: {dict(df_p['status'].value_counts())}")
print("Features: Jitter, Shimmer, HNR, RPDE, DFA, PPE (22 voice measurements)")

X_p = df_p.drop('status', axis=1)
y_p = df_p['status']
X_p_sc = StandardScaler().fit_transform(X_p)
X_train_p, X_test_p, y_train_p, y_test_p = train_test_split(
    X_p_sc, y_p, test_size=0.2, random_state=42, stratify=y_p)

results_p, best_p = train_and_evaluate(
    X_train_p, X_test_p, y_train_p, y_test_p,
    "PARKINSON'S — UCI Voice Dataset (195 recordings, 22 features)")

cv_p = cross_val_score(results_p[best_p]['model'], X_p_sc, y_p, cv=5)
print(f"\n5-Fold CV: {[f'{s:.2%}' for s in cv_p]}")
print(f"Mean: {cv_p.mean():.2%}  Std: {cv_p.std():.2%}")
print(classification_report(y_test_p, results_p[best_p]['y_pred'],
      target_names=['Healthy', "Parkinson's"]))
pickle.dump(results_p[best_p]['model'],
            open(os.path.join(MODEL_DIR, 'parkinsons_model.sav'), 'wb'))
print("Model saved -> models/parkinsons_model.sav")

# ── FINAL SUMMARY ─────────────────────────────────────────────
print(f"\n{'='*68}")
print(f"  TRAINING COMPLETE — FINAL SUMMARY")
print(f"{'='*68}")
print(f"  {'Module':<18} {'Records':>8} {'Best Algorithm':<22} {'Accuracy':>9} {'CV Mean':>8}")
print(f"  {'-'*18} {'-'*8} {'-'*22} {'-'*9} {'-'*8}")
print(f"  {'Diabetes':<18} {'768':>8} {best_d:<22} {results_d[best_d]['accuracy']:>8.2%} {cv_d.mean():>7.2%}")
print(f"  {'Heart Disease':<18} {'303':>8} {best_h:<22} {results_h[best_h]['accuracy']:>8.2%} {cv_h.mean():>7.2%}")
park_label = "Parkinson's"
print(f"  {park_label:<18} {'195':>8} {best_p:<22} {results_p[best_p]['accuracy']:>8.2%} {cv_p.mean():>7.2%}")
print(f"\n  All models saved to: {MODEL_DIR}")
print(f"  Methodology: 80:20 stratified split + 5-fold cross validation")
print(f"{'='*68}\n")
