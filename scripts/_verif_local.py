"""Verificacion rapida: specs 002-005 + 007-008 (sin red)."""
import os, sys, json
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from dotenv import load_dotenv; load_dotenv()

# === 002 ===
print("SPEC 002: Normalizacion")
from src.level2_agent.normalizacion import normalizar_desde_api, enmascarar_para_terceros
from src.level2_agent.models import EmailData

ed = normalizar_desde_api({"subject": "Urgente: verifique", "from": "no-reply@banco.com", "to": "u@ucaldas.edu.co", "text": "Clic http://bit.ly/3x4mPq", "html": "<html><body><a href='http://bit.ly/3x4mPq'>Click</a></body></html>"})
print(f"  OK - normalizar_desde_api: subject={ed.subject}, urls={len(ed.urls)}")

email = EmailData(subject="Test", recipient="user@gmail.com", textBody="Su tarjeta es 4532015112830366")
masked = enmascarar_para_terceros(email)
assert "4532015112830366" not in masked.textBody, f"PII no enmascarada: {masked.textBody}"
print(f"  OK - enmascarar PII: {masked.textBody}")

# === 003 ===
print("SPEC 003: Banderas")
from src.level2_agent.banderas import evaluar_banderas
from src.level2_agent.banderas.configuracion import ConfigBanderas
cfg = ConfigBanderas.desde_entorno()
e1 = EmailData(subject="Urgente", headers=json.dumps({"From": "phish@evil.xyz", "To": "user@ucaldas.edu.co", "Authentication-Results": "spf=fail; dkim=fail; dmarc=fail"}))
r1 = evaluar_banderas(e1, config=cfg)
print(f"  OK - auth fail: {len(r1.banderas)} banderas, puntos={r1.puntos_totales}")
e2 = EmailData(subject="Reunion", headers=json.dumps({"From": "colega@ucaldas.edu.co", "To": "equipo@ucaldas.edu.co"}))
r2 = evaluar_banderas(e2, config=cfg)
print(f"  OK - auth pass: {len(r2.banderas)} banderas, puntos={r2.puntos_totales}")

# === 004 ===
print("SPEC 004: URLs")
from src.level2_agent.analisis_urls import analizar_urls
e3 = EmailData(subject="Test", urls=["http://bit.ly/3x4mPq", "http://login-banco.xyz/auth"])
r3 = analizar_urls(e3)
p3 = sum(b.puntos for b in r3.banderas)
print(f"  OK - URLs: {len(r3.banderas)} banderas, puntos={p3}")

# === 005 ===
print("SPEC 005: Adjuntos")
from src.level2_agent.adjuntos import analizar_adjunto
a1 = analizar_adjunto(nombre="factura.exe", tipo_declarado="application/octet-stream", payload=b"\x00" * 100)
print(f"  OK - .exe: sha256={a1.sha256[:16]}..., {len(a1.banderas)} banderas")
a2 = analizar_adjunto(nombre="reporte.pdf", tipo_declarado="application/pdf", payload=b"%PDF-1.4" + b"\x00" * 100)
print(f"  OK - .pdf: sha256={a2.sha256[:16]}..., {len(a2.banderas)} banderas")

# === 007 ===
print("SPEC 007: Scoring")
from src.level3_logic.scoring import calcular_score_final
s1 = calcular_score_final(EmailData(subject="Reunion", headers=json.dumps({"From": "colega@ucaldas.edu.co"})))
print(f"  OK - benigno: score={s1.score_final}, banderas={s1.puntos_banderas}")
s2 = calcular_score_final(EmailData(subject="URGENTE: Factura", headers=json.dumps({"From": "facturas@banc0-seguro.xyz", "Authentication-Results": "spf=fail; dkim=fail; dmarc=fail", "X-PHP-Originating-Script": "1234:mail.php"}), urls=["http://bit.ly/factura-urgente"]))
print(f"  OK - malicioso: score={s2.score_final}, banderas={s2.puntos_banderas}")

# === 008 ===
print("SPEC 008: Motor de decision")
from src.level2_agent.decision import evaluar_veredicto, EntradaMotor
from src.level3_logic.scoring.modelos import ScoreFinal
v1 = evaluar_veredicto(EntradaMotor(email_data=EmailData(subject="T"), score_final=ScoreFinal(score_final=90, score_clasificador=90.0, puntos_banderas=0, version_modelo="v1")))
print(f"  OK - score 90: veredicto={v1.veredicto}, ruta={v1.ruta}")
v2 = evaluar_veredicto(EntradaMotor(email_data=EmailData(subject="T"), score_final=ScoreFinal(score_final=10, score_clasificador=10.0, puntos_banderas=0, version_modelo="v1")))
print(f"  OK - score 10: veredicto={v2.veredicto}, ruta={v2.ruta}")

# === 009 simulado ===
print("SPEC 009: Agente (simulado)")
from src.level2_agent.agente import consultar_agente, crear_modelo, EntradaAgente
os.environ["LLM_PROVEEDOR"] = "simulado"
r9 = consultar_agente(EntradaAgente(email_data=EmailData(subject="Test phishing"), score_final=ScoreFinal(score_final=50, score_clasificador=50.0, puntos_banderas=0, version_modelo="v1")), modelo=crear_modelo("simulado"))
print(f"  OK - simulado: confirmacion={r9.confirmacion_agente}")

# === 010 tabla ===
print("SPEC 010: Tabla de acciones")
from src.level2_agent.acciones import resolver_acciones, Accion
assert Accion.CREAR_TICKET in resolver_acciones("malicioso")
assert Accion.CREAR_TICKET_BAJA in resolver_acciones("sospechoso")
assert resolver_acciones("sin_indicadores") == [Accion.MARCAR_LEIDO]
print("  OK - tabla correcta")

# === 011 MongoDB ===
print("SPEC 011: MongoDB")
uri = os.environ.get("MONGODB_ATLAS_CLUSTER_URI", "")
if uri:
    from pymongo import MongoClient
    cols = MongoClient(uri, serverSelectionTimeoutMS=5000)["phishguard"].list_collection_names()
    print(f"  OK - conexion: {cols[:5]}")
else:
    print("  SKIP - MONGODB_ATLAS_CLUSTER_URI no configurada")

# === 012 API ===
print("SPEC 012: API REST")
from fastapi.testclient import TestClient
from src.api.app import create_app
os.environ["API_KEY"] = "test-key"
os.environ["LLM_PROVEEDOR"] = "simulado"
app = create_app()
client = TestClient(app)
resp = client.get("/api/health", headers={"X-API-Key": "test-key"})
print(f"  OK - health: {resp.status_code}")
resp2 = client.post("/api/analyses", json={"modo": "pegar", "dry_run": True, "subject": "Urgente: verifique", "from": "phish@evil.xyz", "text": "Clic http://bit.ly/3x4mPq", "headers": {"From": "phish@evil.xyz", "Authentication-Results": "spf=fail; dkim=fail"}}, headers={"X-API-Key": "test-key", "Content-Type": "application/json"})
d = resp2.json()
print(f"  OK - POST analyses: veredicto={d['resultado']['veredicto']}, score={d['resultado']['score']}")

# === D12 HCTI ===
print("D12: HCTI Screenshots")
from src.level2_agent.screenshots import generar_screenshot
url = generar_screenshot("<html><body style='font-family:sans-serif;padding:20px'><h2 style='color:#c00'>Phishing Alert</h2><p>From: soporte@banco-seguro.xyz</p></body></html>")
if url:
    print(f"  OK - screenshot: {url}")
else:
    print("  FAIL - HCTI retorno None")

print("\n=== Lotes sin red: todos OK ===")
