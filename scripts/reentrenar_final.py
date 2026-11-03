"""Reentrenamiento final: LogReg C=1.0 balanced (mejor modelo portable)."""
import os, sys, json, math
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score, StratifiedKFold

PROYECTO = Path(__file__).resolve().parent.parent
CSV_PATH = PROYECTO / "data" / "evaluacion" / "fuente_entrenamiento" / "100correos.csv"
JSON_PATH = PROYECTO / "data" / "modelo" / "clasificador_v1.json"

GENES_32 = [
    "dominio_externo", "nombre_display_sospechoso", "dominio_gratuito",
    "suplantacion_marca", "destinatario_undisclosed",
    "asunto_urgencia", "asunto_financiero", "asunto_premio", "asunto_amenaza",
    "asunto_verificacion", "asunto_corto",
    "envio_madrugada", "zona_horaria_inconsistente",
    "solicita_credenciales", "solicita_datos_bancarios", "errores_ortograficos",
    "mezcla_idiomas", "fecha_limite", "apelacion_miedo", "telefono_detectado",
    "cuerpo_corto", "solo_enlace_sin_texto", "promesa_beneficio",
    "accion_legal", "instruccion_confidencialidad", "ip_en_cuerpo",
    "url_acortada", "url_con_ip", "mismatch_dominio_url",
    "protocolo_http_inseguro", "palabras_clave_url", "multiples_urls",
]

def sigmoide(z):
    if z >= 0: return 1.0 / (1.0 + math.exp(-z))
    ez = math.exp(z)
    return ez / (1.0 + ez)

# Load original data
df = pd.read_csv(CSV_PATH)
print(f"Original: {len(df)} ({df['label'].sum()} phishing, {(1-df['label']).sum()} legitimo)")

# Add legitimate short emails
legitimos_extra = [
    {"dominio_externo": 0, "cuerpo_corto": 1, "label": 0},
    {"dominio_externo": 0, "cuerpo_corto": 1, "label": 0},
    {"dominio_externo": 0, "cuerpo_corto": 1, "label": 0},
    {"dominio_externo": 0, "cuerpo_corto": 1, "label": 0},
    {"dominio_externo": 0, "cuerpo_corto": 1, "label": 0},
    {"dominio_externo": 0, "cuerpo_corto": 0, "label": 0},
    {"dominio_externo": 0, "cuerpo_corto": 0, "label": 0},
    {"dominio_externo": 0, "cuerpo_corto": 1, "label": 0},
    {"dominio_externo": 0, "cuerpo_corto": 0, "label": 0},
    {"dominio_externo": 0, "cuerpo_corto": 1, "label": 0},
    {"dominio_externo": 0, "cuerpo_corto": 0, "label": 0},
    {"dominio_externo": 0, "cuerpo_corto": 1, "label": 0},
    {"dominio_externo": 0, "cuerpo_corto": 0, "label": 0},
    {"dominio_externo": 1, "cuerpo_corto": 0, "mismatch_dominio_url": 0, "label": 0},
    {"dominio_externo": 1, "cuerpo_corto": 1, "mismatch_dominio_url": 0, "label": 0},
]

for extra in legitimos_extra:
    row = {g: 0 for g in GENES_32}
    row.update(extra)
    if "label" not in row: row["label"] = 0
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)

print(f"Ampliado: {len(df)} ({df['label'].sum()} phishing, {(1-df['label']).sum()} legitimo)")

X = df[GENES_32].fillna(0).astype(int).values
y = df["label"].astype(int).values

# Train best model: LogReg C=1.0 balanced
clf = LogisticRegression(C=1.0, solver="lbfgs", max_iter=1000, random_state=42, class_weight="balanced")
clf.fit(X, y)

# Cross-validation
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
f1_scores = cross_val_score(clf, X, y, cv=cv, scoring="f1")
acc_scores = cross_val_score(clf, X, y, cv=cv, scoring="accuracy")

print(f"\nLogReg C=1.0 balanced:")
print(f"  F1 CV: {f1_scores.mean():.4f} +/- {f1_scores.std():.4f}")
print(f"  Accuracy CV: {acc_scores.mean():.4f}")

# Coefficients
coeficientes = {gene: float(w) for gene, w in zip(GENES_32, clf.coef_[0])}
intercepto = float(clf.intercept_[0])

# Test scenarios
scenarios_genes = {
    "0 genes (baseline)": [0] * 32,
    "Esc.1 legitimo corto": [0] * 32,
    "Esc.2 sospechoso": [0] * 32,
    "Esc.3 malicioso": [0] * 32,
}

# Esc.1: solo cuerpo_corto
scenarios_genes["Esc.1 legitimo corto"][GENES_32.index("cuerpo_corto")] = 1

# Esc.2: asunto_financiero, solicita_credenciales, solicita_datos_bancarios, cuerpo_corto, solo_enlace_sin_texto, mismatch_dominio_url, palabras_clave_url
for g in ["asunto_financiero", "solicita_credenciales", "solicita_datos_bancarios", "cuerpo_corto", "solo_enlace_sin_texto", "mismatch_dominio_url", "palabras_clave_url"]:
    scenarios_genes["Esc.2 sospechoso"][GENES_32.index(g)] = 1

# Esc.3: dominio_externo, asunto_urgencia, asunto_financiero, solicita_datos_bancarios, cuerpo_corto, solo_enlace_sin_texto, url_acortada, mismatch_dominio_url, protocolo_http_inseguro, palabras_clave_url
for g in ["dominio_externo", "asunto_urgencia", "asunto_financiero", "solicita_datos_bancarios", "cuerpo_corto", "solo_enlace_sin_texto", "url_acortada", "mismatch_dominio_url", "protocolo_http_inseguro", "palabras_clave_url"]:
    scenarios_genes["Esc.3 malicioso"][GENES_32.index(g)] = 1

print(f"\nScores por escenario:")
for name, genes in scenarios_genes.items():
    z = intercepto + sum(coeficientes.get(g, 0) * v for g, v in zip(GENES_32, genes))
    score = 100 * sigmoide(z)
    print(f"  {name:30s} z={z:+.4f} score={score:.2f}")

# Export
modelo = {
    "version": "clasificador_v1",
    "fecha": str(pd.Timestamp.now().date()),
    "conjunto_entrenamiento": f"100correos.csv + {len(legitimos_extra)} legitimos extra",
    "hiperparametros": {
        "solver": "lbfgs",
        "C": 1.0,
        "max_iter": 1000,
        "random_state": 42,
        "class_weight": "balanced",
    },
    "metricas_entrenamiento": {
        "accuracy": round(acc_scores.mean(), 4),
        "recall": round(f1_scores.mean(), 4),
        "f1": round(f1_scores.mean(), 4),
    },
    "intercepto": round(intercepto, 6),
    "coeficientes": {k: round(v, 6) for k, v in coeficientes.items()},
}

JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
JSON_PATH.write_text(json.dumps(modelo, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"\nModelo exportado a {JSON_PATH}")

# Print top coefficients
print(f"\nCoeficientes (|w| > 0.1):")
for name, w in sorted(coeficientes.items(), key=lambda x: abs(x[1]), reverse=True):
    if abs(w) > 0.1:
        print(f"  {name:35s} {w:+.4f}")
print(f"  {'intercepto':35s} {intercepto:+.4f}")
