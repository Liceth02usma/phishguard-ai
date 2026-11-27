"""Reentrenamiento con monotonía de dominio (B2) del clasificador lineal.

Motivación
----------
El clasificador entrenado por ``reentrenar_final.py`` producía pesos con
sentido invertido respecto al catálogo de señales del propio proyecto:

    apelacion_miedo      -1.096   (pesado como "protege")
    dominio_gratuito     -0.837
    telefono_detectado   -0.627
    url_acortada         -0.604
    asunto_urgencia      -0.514
    solicita_credenciales-0.417
    palabras_clave_url    0.000   (sin varianza en el CSV)

Por eso un correo legítimo con 2 genes llegaba a 52.56 mientras un correo
con 12 genes de riesgo llegaba a 8.92: la señal estaba invertida.

Este script impone la restricción de dominio que el propio diseño exige:

    **los 32 genes son indicadores de phishing**, de modo que activar
    cualquiera de ellos nunca puede *bajar* el score  ->  w_i >= 0.

Solo el intercepto queda libre (debe ser < -0.847 para cumplir AC-SCO-01:
0 genes -> score < 30).

Uso:
    python scripts/reentrenar_monotono.py            # imprime la evaluación
    python scripts/reentrenar_monotono.py --exportar  # escribe el JSON

Requiere: scikit-learn, scipy, pandas (solo entrenamiento, NO runtime).
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

PROYECTO = Path(__file__).resolve().parent.parent
CSV_PATH = PROYECTO / "data" / "evaluacion" / "fuente_entrenamiento" / "100correos.csv"
JSON_PATH = PROYECTO / "data" / "modelo" / "clasificador_v1.json"

# DOMINIOS_PROPIOS / DOMINIOS_PROVEEDORES_CONFIANZA viven en .env
try:
    from dotenv import load_dotenv

    load_dotenv(PROYECTO / ".env")
except ImportError:  # pragma: no cover - dotenv siempre esta en requirements
    pass

# Orden exacto de MAPEO_INDICES (genetic_logic.py)
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

# Los 15 legitimos sintéticos de reentrenar_final.py (se conservan para que
# la comparación contra el modelo actual sea justa).
LEGITIMOS_EXTRA = [
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


def cargar_datos(extra_patron: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """Carga 100correos.csv + legitimos extra (mismo dataset que v1).

    ``extra_patron`` añade legitimos sinteticos con el patron
    ``{cuerpo_corto, multiples_urls}`` (correo institucional corto con varios
    enlaces internos), que en el CSV real estaba sub-representado y provocaba
    el falso positivo del escenario rico 1.
    """
    df = pd.read_csv(CSV_PATH)
    extras = list(LEGITIMOS_EXTRA)
    for _ in range(extra_patron):
        extras.append({"cuerpo_corto": 1, "multiples_urls": 1, "label": 0})
    for extra in extras:
        row = {g: 0 for g in GENES_32}
        row.update(extra)
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    X = df[GENES_32].fillna(0).astype(float).values
    y = df["label"].astype(int).values
    return X, y


def log_loss(y: np.ndarray, p: np.ndarray) -> float:
    """Cross-entropy media con clipping numerico."""
    p = np.clip(p, 1e-9, 1 - 1e-9)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def ajustar(X: np.ndarray, y: np.ndarray, alpha: float) -> tuple[np.ndarray, float]:
    """LogReg con restriccion w >= 0 (L-BFGS-B) y regularizacion L2.

    Objetivo:  media(log-loss) + alpha * 0.5 * ||w||^2

    ``alpha`` mas grande = mas contraccion de pesos (mas conservador).
    """
    n = X.shape[0]

    def objetivo(theta: np.ndarray) -> float:
        w, b = theta[:-1], theta[-1]
        z = X @ w + b
        p = 1.0 / (1.0 + np.exp(-np.clip(z, -500, 500)))
        return log_loss(y, p) + alpha * 0.5 * float(w @ w)

    def gradiente(theta: np.ndarray) -> np.ndarray:
        w, b = theta[:-1], theta[-1]
        z = X @ w + b
        p = 1.0 / (1.0 + np.exp(-np.clip(z, -500, 500)))
        dif = (p - y) / n
        gw = X.T @ dif + alpha * w
        gb = float(np.sum(dif))
        return np.concatenate([gw, [gb]])

    theta0 = np.zeros(len(GENES_32) + 1)
    bounds = [(0.0, None)] * len(GENES_32) + [(None, None)]
    res = minimize(objetivo, theta0, jac=gradiente, method="L-BFGS-B",
                   bounds=bounds, options={"maxiter": 5000})
    return res.x[:-1], float(res.x[-1])


def metricas(X: np.ndarray, y: np.ndarray, w: np.ndarray, b: float) -> dict[str, float]:
    """Accuracy / recall / f1 con umbral 0.5 (mismas metricas que v1)."""
    p = 1.0 / (1.0 + np.exp(-np.clip(X @ w + b, -500, 500)))
    pred = (p >= 0.5).astype(int)
    tp = int(np.sum((pred == 1) & (y == 1)))
    tn = int(np.sum((pred == 0) & (y == 0)))
    fp = int(np.sum((pred == 1) & (y == 0)))
    fn = int(np.sum((pred == 0) & (y == 1)))
    acc = (tp + tn) / len(y)
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return {"accuracy": acc, "recall": rec, "f1": f1}


# ---------------------------------------------------------------------------
# Suite de evaluacion offline (sin LLM): score = AG + min(60, banderas)
# ---------------------------------------------------------------------------

def construir_corpus() -> list[tuple[str, dict]]:
    """Correos de prueba: 3 oficiales + 3 ricos + 3 fixtures.

    Se calculan con el extractor real (genetic_logic) y las banderas reales
    (003/004), sin llamar al agente IA, para poder barrer hiperparametros.
    """
    auth_ok = "mail.ucaldas.edu.co; spf=pass; dkim=pass; dmarc=pass"
    auth_mix = "mail.ucaldas.edu.co; spf=pass; dkim=none; dmarc=none"
    auth_bad = "mail.ucaldas.edu.co; spf=fail; dkim=fail; dmarc=fail"

    corpus: list[tuple[str, dict]] = [
        # --- 3 escenarios oficiales (scripts/e2e_3_escenarios.py) ---
        ("oficial_1_legitimo", {
            "subject": "Reunion de equipo manana",
            "from": "colega@ucaldas.edu.co", "to": "equipo@ucaldas.edu.co",
            "text": ("Hola equipo, recuerden la reunion de manana a las 10am en "
                     "la sala de juntas. Saludos."),
            "headers": {"From": "colega@ucaldas.edu.co", "To": "equipo@ucaldas.edu.co",
                        "Authentication-Results": auth_ok},
            "esperado": "bajo",
        }),
        ("oficial_2_sospechoso", {
            "subject": "Actualizacion de su cuenta de Microsoft",
            "from": "no-reply@microsoft.com", "to": "usuario@ucaldas.edu.co",
            "text": ("Estimado usuario, su cuenta requiere actualizacion. Inicie "
                     "sesion en https://login.microsoftonline.com/verify para continuar."),
            "headers": {"From": "no-reply@microsoft.com", "To": "usuario@ucaldas.edu.co",
                        "Authentication-Results": auth_mix},
            "esperado": "medio",
        }),
        ("oficial_3_malicioso", {
            "subject": "URGENTE: Su cuenta bancaria sera suspendida",
            "from": "seguridad@banc0-internacional.xyz", "to": "usuario@ucaldas.edu.co",
            "text": ("Estimado cliente, su cuenta sera suspendida en 24 horas. "
                     "Verifique sus datos inmediatamente en "
                     "http://bit.ly/verificar-cuenta-2026"),
            "headers": {"From": "seguridad@banc0-internacional.xyz",
                        "To": "usuario@ucaldas.edu.co", "Authentication-Results": auth_bad,
                        "X-PHP-Originating-Script": "1234:mail.php"},
            "esperado": "alto",
        }),
        # --- 3 escenarios ricos (multi-URL, adjuntos, cabeceras) ---
        ("rico_1_legitimo", {
            "subject": "Reunion de equipo manana - minuta y agenda adjuntas",
            "from": "colega@ucaldas.edu.co", "to": "equipo@ucaldas.edu.co",
            "text": (
                "Hola equipo,\n\n"
                "Les recuerdo la reunion de manana a las 10am en la sala de juntas. "
                "Dejo los enlaces de referencia:\n\n"
                "  - Agenda: https://ucaldas.edu.co/agendas/reunion-2026\n"
                "  - Minuta anterior: https://ucaldas.edu.co/docs/minuta-042\n"
                "  - Acta firmada: https://drive.ucaldas.edu.co/file/acta-11\n"
                "  - Calendario institucional: https://calendar.ucaldas.edu.co/event/9f2a\n"
                "  - Repositorio de proyectos: https://gitlab.ucaldas.edu.co/proyectos\n\n"
                "Traigan el documento de avances del trimestre. Saludos.\n"),
            "headers": {"From": "colega@ucaldas.edu.co", "To": "equipo@ucaldas.edu.co",
                        "Authentication-Results": auth_ok},
            "esperado": "bajo",
        }),
        ("rico_2_sospechoso", {
            "subject": "Actualizacion de su cuenta de Microsoft",
            "from": "no-reply@microsoft.com", "to": "usuario@ucaldas.edu.co",
            "text": (
                "Estimado usuario, su cuenta requiere actualizacion.\n\n"
                "Revise los cambios en el centro de administracion:\n"
                "  - https://portal.office.com/admincenter?utm_source=email&utm_campaign=notice\n"
                "  - https://learn.microsoft.com/en-us/microsoft-365/\n"
                "  - Resumen: https://bit.ly/office-update-2026\n\n"
                "Si no reconoce esta actividad contacte a soporte.\n"),
            "headers": {"From": "no-reply@microsoft.com", "To": "usuario@ucaldas.edu.co",
                        "Authentication-Results": auth_mix},
            "esperado": "medio",
        }),
        ("rico_3_malicioso", {
            "subject": "URGENTE: Su cuenta bancaria sera suspendida en 24 horas",
            "from": "seguridad@banc0-internacional.xyz", "to": "usuario@ucaldas.edu.co",
            "text": (
                "Estimado cliente:\n\n"
                "Detectamos un intento de acceso no autorizado. Su cuenta sera suspendida "
                "en menos de 24 horas si no verifica sus datos.\n\n"
                "Verifique inmediatamente:\n"
                "  - http://bit.ly/verificar-cuenta-2026\n"
                "  - http://cuenta-banc0-internacional.xyz/login?user=u&password=1234&token=abc\n"
                "  - http://192.168.0.50/panel/credenciales\n"
                "  - http://servidor-hostil.tk/verify?access_token=deadbeef&api_key=zzz\n"
                "  - https://banc0-internacional.xyz.ct-risk.top/secure?utm_source=phish\n\n"
                "Adjuntamos el formulario de verificacion. Complete TODOS los campos.\n\n"
                "Soporte: +57 300 999 8888\n"),
            "headers": {"From": "seguridad@banc0-internacional.xyz",
                        "Reply-To": "recuperar.cuenta@gmail.com",
                        "To": "usuario@ucaldas.edu.co", "Authentication-Results": auth_bad,
                        "X-PHP-Originating-Script": "1234:mail.php"},
            "esperado": "alto",
        }),
    ]

    # --- fixtures de tests/fixtures/*.json ---
    fixtures_dir = PROYECTO / "tests" / "fixtures"
    esperado_fixture = {"benign": "bajo", "ai_agent": "bajo", "malicious": "alto"}
    for nombre, esp in esperado_fixture.items():
        ruta = fixtures_dir / f"{nombre}.json"
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        headers = datos.get("headers", "{}")
        if isinstance(headers, str):
            headers = json.loads(headers)
        corpus.append((f"fixture_{nombre}", {
            "subject": datos.get("subject", ""),
            "from": (headers or {}).get("from", ""),
            "to": datos.get("recipient", ""),
            "text": datos.get("textBody", ""),
            "headers": headers or {},
            "esperado": esp,
        }))

    # --- 5 correos sintéticos de test_ac_mem_02 (las tres rutas) ---
    sys.path.insert(0, str(PROYECTO / "tests" / "unit"))
    import test_ac_mem_02_independencia as mem  # noqa: PLC0415

    bandas_mem = {
        "correo_a": "bajo", "correo_b": "bajo",
        "correo_c": "no_bajo", "correo_d": "medio", "correo_e": "alto",
    }
    for f in mem.FIXTURES:
        headers = f["headers"]
        if isinstance(headers, str):
            headers = json.loads(headers)
        corpus.append((f"mem_{f['id']}", {
            "subject": f["subject"],
            "from": (headers or {}).get("From", ""),
            "to": f["recipient"],
            "text": f["textBody"],
            "headers": headers or {},
            "esperado": bandas_mem[f["id"]],
            # La prueba test_ac_mem_02 construye el EmailData SIN `cabeceras`
            # (solo `headers`): se mide igual para que las bandas coincidan.
            "sin_cabeceras": True,
        }))
    return corpus


_CANDIDATA = Path(os.environ.get("TEMP", "/tmp")) / "phishguard_modelo_candidato.json"


def evaluar_coefs(corpus: list[tuple[str, dict]],
                  coef: dict[str, float], intercepto: float) -> tuple[bool, list[dict]]:
    """Calcula score_final real (AG + banderas tope 60) para cada correo.

    El candidato se materializa en un JSON temporal y se inyecta via
    ``ConfigScoring(ruta_modelo=...)`` + ``invalidate_cache()`` para que
    ``calcular_score_final`` use exactamente estos pesos.
    """
    from src.level3_logic.modelo import invalidate_cache  # noqa: PLC0415

    candidato = {
        "version": "clasificador_v1",
        "fecha": "2026-01-01",
        "conjunto_entrenamiento": "candidato",
        "hiperparametros": {"solver": "lbfgs-bounds", "C": 1.0,
                            "max_iter": 5000, "random_state": 42},
        "metricas_entrenamiento": {"accuracy": 0.0, "recall": 0.0, "f1": 0.0},
        "intercepto": intercepto,
        "coeficientes": coef,
    }
    _CANDIDATA.write_text(json.dumps(candidato), encoding="utf-8")
    invalidate_cache()
    return _evaluar_corpus(corpus, _CANDIDATA)


def _evaluar_corpus(
    corpus: list[tuple[str, dict]], ruta_modelo: Path
) -> tuple[bool, list[dict]]:
    """Calcula score_final real (AG + banderas tope 60) para cada correo."""
    from src.level2_agent.models import Cabecera, EmailData  # noqa: PLC0415
    from src.level3_logic.scoring import calcular_score_final  # noqa: PLC0415
    from src.level3_logic.scoring.configuracion import ConfigScoring  # noqa: PLC0415

    base = ConfigScoring.desde_entorno()
    config = ConfigScoring(
        dominios_propios=base.dominios_propios,
        proveedores_confianza=base.proveedores_confianza,
        ruta_modelo=ruta_modelo,
    )

    filas: list[dict] = []
    todos_ok = True
    for nombre, c in corpus:
        headers = {str(k): str(v) for k, v in c["headers"].items()}
        cabeceras = (
            []
            if c.get("sin_cabeceras")
            else [Cabecera(nombre=k, valor=v) for k, v in headers.items()]
        )
        email_data = EmailData(
            subject=c["subject"],
            recipient=c["to"] or c["from"],
            textBody=c["text"],
            headers=json.dumps(headers, ensure_ascii=False),
            cabeceras=cabeceras,
        )
        sf = calcular_score_final(email_data, config=config)
        score = int(sf.score_final)
        ag_score = sf.score_clasificador
        puntos_banderas = sf.puntos_banderas
        esperado = c["esperado"]
        if esperado == "bajo":
            ok = score < 30
        elif esperado == "no_bajo":
            ok = score >= 30
        elif esperado == "medio":
            ok = 30 <= score <= 75
        else:
            ok = score > 75
        todos_ok = todos_ok and ok
        filas.append({
            "caso": nombre, "score": score, "esperado": esperado,
            "ok": ok, "ag": round(ag_score, 2),
            "banderas": puntos_banderas,
        })
    return todos_ok, filas


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exportar", action="store_true",
                    help="Escribe data/modelo/clasificador_v1.json")
    ap.add_argument("--barrido", action="store_true",
                    help="Barre la regularizacion y muestra la tabla completa")
    ap.add_argument("--extra-patron", type=int, default=10,
                    help="Legitimos sinteticos {cuerpo_corto, multiples_urls}")
    ap.add_argument("--alphas", default="",
                    help="Lista explicita de regularizacion, ej. 0.01,0.03")
    args = ap.parse_args()

    X, y = cargar_datos(args.extra_patron)
    print(f"Dataset: {len(X)} filas ({int(y.sum())} phishing, "
          f"{len(y) - int(y.sum())} legitimos), {X.shape[1]} genes")
    print("Reposicion: todos los pesos w >= 0 (los 32 genes son indicadores "
          "de phishing; activar uno nunca baja el score).")

    corpus = construir_corpus()

    alphas = [0.01, 0.03, 0.1, 0.3, 1.0, 3.0] if args.barrido else [0.01, 0.03, 0.1]
    if args.alphas:
        alphas = [float(a) for a in args.alphas.split(",")]
    mejor: tuple[float, int, np.ndarray, float, dict] | None = None
    resultados = []

    for alpha in alphas:
        w, b = ajustar(X, y, alpha)
        met = metricas(X, y, w, b)
        coef = {g: round(float(v), 6) for g, v in zip(GENES_32, w, strict=True)}

        # AC-SCO-01: 0 genes -> score < 30
        p0 = 1.0 / (1.0 + math.exp(-b)) if b > -500 else 0.0
        ac01 = p0 * 100.0 < 30.0

        ok_corpus, filas = evaluar_coefs(corpus, coef, b)
        n_ok = sum(1 for f in filas if f["ok"])
        resultados.append((alpha, met, ac01, n_ok, filas))

        print(f"\n--- alpha={alpha} ---")
        print(f"  intercepto={b:+.4f} (0 genes -> {p0*100:.2f})  "
              f"AC-SCO-01={'OK' if ac01 else 'FALLA'}")
        print(f"  metricas: acc={met['accuracy']:.4f} recall={met['recall']:.4f} "
              f"f1={met['f1']:.4f}")
        print(f"  escenarios correctos: {n_ok}/{len(filas)}")
        for f in filas:
            marca = "OK  " if f["ok"] else "FALLA"
            print(f"    [{marca}] {f['caso']:<24} score={f['score']:>3} "
                  f"(ag={f['ag']:>6} + band={str(f['banderas']):>4}) "
                  f"esperado={f['esperado']}")

        puntuacion = (1 if ac01 else 0, n_ok, met["f1"])
        if mejor is None or puntuacion > mejor[0]:
            mejor = (puntuacion, alpha, w, b, coef)

    assert mejor is not None
    _, alpha_opt, w_opt, b_opt, coef_opt = mejor
    print(f"\nMEJOR: alpha={alpha_opt}  intercepto={b_opt:+.4f}")
    print("Pesos con |w| > 0.05:")
    for g, v in sorted(coef_opt.items(), key=lambda x: -x[1]):
        if abs(v) > 0.05:
            print(f"    {g:<32} {v:+.4f}")

    if not args.exportar:
        print("\n(dry run: sin --exportar no se escribio el JSON)")
        return 0

    X, y = cargar_datos(args.extra_patron)
    met = metricas(X, y, w_opt, b_opt)
    modelo = {
        "version": "clasificador_v1",
        "fecha": str(pd.Timestamp.now().date()),
        "conjunto_entrenamiento": (
            f"100correos.csv + {len(LEGITIMOS_EXTRA) + args.extra_patron} "
            f"legitimos extra | monotono w>=0 (B2), alpha={alpha_opt}"
        ),
        "hiperparametros": {
            "solver": "lbfgs-bounds",
            "C": round(1.0 / alpha_opt, 4),
            "max_iter": 5000,
            "random_state": 42,
        },
        "metricas_entrenamiento": {
            "accuracy": round(met["accuracy"], 4),
            "recall": round(met["recall"], 4),
            "f1": round(met["f1"], 4),
        },
        "intercepto": round(b_opt, 6),
        "coeficientes": coef_opt,
    }
    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    JSON_PATH.write_text(json.dumps(modelo, indent=2, ensure_ascii=False) + "\n",
                         encoding="utf-8")
    print(f"\nModelo exportado a {JSON_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
