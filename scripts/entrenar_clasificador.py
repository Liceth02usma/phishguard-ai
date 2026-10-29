"""Entrenamiento offline del clasificador lineal para PhishGuard-AI (spec 007).

Lee data/evaluacion/fuente_entrenamiento/100correos.csv (32 columnas de genes + label),
entrena LogisticRegression con scikit-learn, verifica AC-SCO-01 (0 genes → score < 30),
y exporta data/modelo/clasificador_v1.json con coeficientes, intercepto y metadata.

Uso:
    python scripts/entrenar_clasificador.py

Requiere: scikit-learn, pandas (solo para entrenamiento, NO runtime).
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd  # type: ignore[import-untyped]
from sklearn.linear_model import LogisticRegression  # type: ignore[import-untyped]

PROYECTO = Path(__file__).resolve().parent.parent
CSV_PATH = PROYECTO / "data" / "evaluacion" / "fuente_entrenamiento" / "100correos.csv"
JSON_PATH = PROYECTO / "data" / "modelo" / "clasificador_v1.json"

# Genes en el orden de MAPEO_INDICES (genetic_logic.py)
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

HIPERPARAMETROS = {
    "solver": "lbfgs",
    "C": 1.0,
    "max_iter": 1000,
    "random_state": 42,
}


def sigmoide(z: float) -> float:
    """σ(z) = 1 / (1 + exp(-z))."""
    if z >= 0:
        return 1.0 / (1.0 + __import__("math").exp(-z))  # type: ignore[no-any-return]
    ez = __import__("math").exp(z)
    return ez / (1.0 + ez)  # type: ignore[no-any-return]


def score_desde_genes(coef: dict[str, float], intercept: float, genes: list[int]) -> float:
    """score = 100 × σ(Σ wᵢ·geneᵢ + b)."""
    z = intercept + sum(coef.get(g, 0.0) * v for g, v in zip(GENES_32, genes, strict=False))
    return 100.0 * sigmoide(z)


def main() -> None:
    # 1. Leer CSV
    if not CSV_PATH.exists():
        print(f"ERROR: CSV no encontrado en {CSV_PATH}", file=sys.stderr)
        sys.exit(1)

    df = pd.read_csv(CSV_PATH)
    print(f"CSV leído: {len(df)} filas, {len(df.columns)} columnas")

    # Verificar columnas
    esperadas = set(GENES_32) | {"label"}
    faltan = esperadas - set(df.columns)
    if faltan:
        print(f"ERROR: columnas faltantes en CSV: {faltan}", file=sys.stderr)
        sys.exit(1)

    X = df[GENES_32].values
    y = df["label"].values

    # 2. Entrenar
    clf = LogisticRegression(
        solver=HIPERPARAMETROS["solver"],
        C=HIPERPARAMETROS["C"],
        max_iter=HIPERPARAMETROS["max_iter"],
        random_state=HIPERPARAMETROS["random_state"],
    )
    clf.fit(X, y)

    # 3. Métricas de entrenamiento
    y_pred = clf.predict(X)
    tp = int(((y == 1) & (y_pred == 1)).sum())
    fn = int(((y == 1) & (y_pred == 0)).sum())
    fp = int(((y == 0) & (y_pred == 1)).sum())
    tn = int(((y == 0) & (y_pred == 0)).sum())
    accuracy = (tp + tn) / len(y)
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    print(f"Métricas: accuracy={accuracy:.4f}, recall={recall:.4f}, f1={f1:.4f}")

    # 4. Coeficientes
    coeficientes = {gene: float(w) for gene, w in zip(GENES_32, clf.coef_[0], strict=False)}
    intercepto = float(clf.intercept_[0])

    # 5. Verificar AC-SCO-01: 0 genes → score < 30
    score_cero = score_desde_genes(coeficientes, intercepto, [0] * 32)
    print(f"Score con 0 genes: {score_cero:.2f}")
    if score_cero >= 30:
        print(
            "AC-SCO-01 FALLA: score con 0 genes >= 30. "
            "Reentrenando con class_weight='balanced'..."
        )
        clf = LogisticRegression(
            solver=HIPERPARAMETROS["solver"],
            C=HIPERPARAMETROS["C"],
            max_iter=HIPERPARAMETROS["max_iter"],
            random_state=HIPERPARAMETROS["random_state"],
            class_weight="balanced",
        )
        clf.fit(X, y)
        coeficientes = {gene: float(w) for gene, w in zip(GENES_32, clf.coef_[0], strict=False)}
        intercepto = float(clf.intercept_[0])
        y_pred = clf.predict(X)
        tp = int(((y == 1) & (y_pred == 1)).sum())
        fn = int(((y == 1) & (y_pred == 0)).sum())
        fp = int(((y == 0) & (y_pred == 1)).sum())
        tn = int(((y == 0) & (y_pred == 0)).sum())
        accuracy = (tp + tn) / len(y)
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        score_cero = score_desde_genes(coeficientes, intercepto, [0] * 32)
        print(f"Reentrenado — Score con 0 genes: {score_cero:.2f}")
        if score_cero >= 30:
            print("ERROR: AC-SCO-01 sigue fallando tras class_weight='balanced'", file=sys.stderr)
            sys.exit(1)

    # 6. Exportar JSON
    modelo = {
        "version": "clasificador_v1",
        "fecha": date.today().isoformat(),
        "conjunto_entrenamiento": "100correos.csv",
        "hiperparametros": HIPERPARAMETROS,
        "metricas_entrenamiento": {
            "accuracy": round(accuracy, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
        },
        "intercepto": round(intercepto, 6),
        "coeficientes": {k: round(v, 6) for k, v in coeficientes.items()},
    }

    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    JSON_PATH.write_text(json.dumps(modelo, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Modelo exportado a {JSON_PATH}")
    print(f"AC-SCO-01: PASS (score 0 genes = {score_cero:.2f} < 30)")


if __name__ == "__main__":
    main()
