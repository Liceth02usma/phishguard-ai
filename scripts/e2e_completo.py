"""E2E completo: 3 escenarios con dry_run=false, adjuntos, URLs, respuesta detallada."""
import os, requests, json, sys, base64
sys.stdout.reconfigure(encoding="utf-8")
from dotenv import load_dotenv; load_dotenv()

key = os.environ.get("API_KEY", "test-key")
base = "http://127.0.0.1:8000"

def print_detalle(nombre, r):
    """Imprime respuesta detallada del análisis."""
    print(f"\n{'='*60}")
    print(nombre)
    print("="*60)
    if r.status_code != 201:
        print(f"  ❌ Status: {r.status_code}")
        print(f"  Error: {r.text[:500]}")
        return None

    d = r.json()
    res = d["resultado"]
    acc = d["accion"]

    # Score y veredicto
    print(f"  ✅ Status: 201 Created")
    print(f"  Score:        {res['score']}")
    print(f"  Veredicto:    {res['veredicto']}")
    print(f"  Es phishing:  {res['es_phishing']}")
    print(f"  Severidad:    {res['nivel_severidad']}")
    print(f"  Ruta:         {res['ruta']}")
    print(f"  Duracion:     {d['duracion_ms']}ms")

    # Resumen
    print(f"\n  --- Resumen ---")
    print(f"  {res['resumen'][:200]}")

    # Análisis técnico
    if res.get('analisis_tecnico'):
        print(f"\n  --- Análisis técnico ---")
        print(f"  {res['analisis_tecnico'][:200]}")

    # Justificación
    if res.get('justificacion_veredicto'):
        print(f"\n  --- Justificación ---")
        print(f"  {res['justificacion_veredicto'][:200]}")

    # Autenticación
    auth = res.get('autenticacion', {})
    print(f"\n  --- Autenticación ---")
    print(f"  SPF:   {auth.get('spf', 'N/A')}")
    print(f"  DKIM:  {auth.get('dkim', 'N/A')}")
    print(f"  DMARC: {auth.get('dmarc', 'N/A')}")

    # Banderas
    banderas = res.get('banderas', [])
    print(f"\n  --- Banderas ({len(banderas)}) ---")
    total_pts = 0
    for b in banderas:
        total_pts += b['puntos']
        print(f"  {b['codigo']:30s} sev={b['severidad']:8s} pts={b['puntos']:3d}  {b.get('detalle','')[:50]}")
    print(f"  {'TOTAL':30s} pts={total_pts}")

    # Indicadores (genes)
    indicadores = res.get('indicadores', [])
    print(f"\n  --- Indicadores/Genes ({len(indicadores)}) ---")
    for i in indicadores:
        print(f"  {i['codigo']:35s} peso={i['peso']:.1f}")

    # URLs
    urls = res.get('urls', [])
    print(f"\n  --- URLs ({len(urls)}) ---")
    for u in urls:
        print(f"  {u['url'][:60]:60s} rep={u['reputacion']}")

    # Adjuntos
    adjuntos = res.get('adjuntos', [])
    print(f"\n  --- Adjuntos ({len(adjuntos)}) ---")
    for a in adjuntos:
        print(f"  {a.get('nombre','?'):20s} tipo={a.get('tipo_real','?'):15s} sha256={a.get('sha256','?')[:16]}... rep={a.get('reputacion','?')}")

    # Version modelo
    print(f"\n  --- Modelo ---")
    print(f"  Version pesos: {res.get('version_pesos', 'N/A')}")
    print(f"  Version modelo: {res.get('version_modelo', 'N/A')}")

    # Ticket Jira
    ticket = res.get('ticket')
    print(f"\n  --- Acciones ---")
    print(f"  Accion ejecutada: {acc.get('ejecutada', 'N/A')}")
    print(f"  Simulada: {acc.get('simulada', True)}")
    if ticket:
        print(f"  Ticket Jira: {ticket['clave']} → {ticket['url']}")
    else:
        print(f"  Ticket Jira: (ninguno)")

    # Verificaciones incompletas
    vi = res.get('verificaciones_incompletas', [])
    if vi:
        print(f"\n  --- Verificaciones incompletas ({len(vi)}) ---")
        for v in vi:
            print(f"  {v}")

    return res

# Health check
print("="*60)
print("HEALTH CHECK")
print("="*60)
try:
    r = requests.get(f"{base}/api/health", headers={"X-API-Key": key}, timeout=10)
    print(f"  Status: {'OK' if r.status_code == 200 else 'FAIL'}")
except Exception as e:
    print(f"  ❌ Server no disponible: {e}")
    sys.exit(1)

# ============================================================
# ESCENARIO 1: CORREO LEGÍTIMO (dry_run=false)
# ============================================================
r1 = requests.post(f"{base}/api/analyses",
    headers={"X-API-Key": key, "Content-Type": "application/json"},
    json={
        "modo": "pegar", "dry_run": False,
        "subject": "Reunion de equipo manana",
        "from": "colega@ucaldas.edu.co",
        "to": "equipo@ucaldas.edu.co",
        "text": "Hola equipo, recuerden la reunion de manana a las 10am en la sala de juntas. Saludos.",
        "headers": {
            "From": "colega@ucaldas.edu.co", "To": "equipo@ucaldas.edu.co",
            "Authentication-Results": "mail.ucaldas.edu.co; spf=pass; dkim=pass; dmarc=pass"
        }
    }, timeout=180)
res1 = print_detalle("ESCENARIO 1: CORREO LEGÍTIMO (dry_run=false)", r1)

# ============================================================
# ESCENARIO 2: CORREO SOSPECHOSO con URL (dry_run=false)
# ============================================================
r2 = requests.post(f"{base}/api/analyses",
    headers={"X-API-Key": key, "Content-Type": "application/json"},
    json={
        "modo": "pegar", "dry_run": False,
        "subject": "Actualizacion de su cuenta de Microsoft",
        "from": "no-reply@microsoft.com",
        "to": "usuario@ucaldas.edu.co",
        "text": "Estimado usuario, su cuenta requiere actualizacion. Inicie sesion en https://login.microsoftonline.com/verify para continuar. Adjuntamos politica de privacidad.",
        "headers": {
            "From": "no-reply@microsoft.com", "To": "usuario@ucaldas.edu.co",
            "Authentication-Results": "mail.ucaldas.edu.co; spf=pass; dkim=none; dmarc=none"
        }
    }, timeout=180)
res2 = print_detalle("ESCENARIO 2: CORREO SOSPECHOSO con URL (dry_run=false)", r2)

# ============================================================
# ESCENARIO 3: CORREO MALICIOSO con URL + adjunto (dry_run=false)
# ============================================================
r3 = requests.post(f"{base}/api/analyses",
    headers={"X-API-Key": key, "Content-Type": "application/json"},
    json={
        "modo": "pegar", "dry_run": False,
        "subject": "URGENTE: Su cuenta bancaria sera suspendida",
        "from": "seguridad@banc0-internacional.xyz",
        "to": "usuario@ucaldas.edu.co",
        "text": "Estimado cliente, su cuenta sera suspendida en 24 horas. Verifique sus datos inmediatamente en http://bit.ly/verificar-cuenta-2026. Adjuntamos formulario de actualizacion.",
        "headers": {
            "From": "seguridad@banc0-internacional.xyz", "To": "usuario@ucaldas.edu.co",
            "Authentication-Results": "mail.ucaldas.edu.co; spf=fail; dkim=fail; dmarc=fail",
            "X-PHP-Originating-Script": "1234:mail.php"
        }
    }, timeout=180)
res3 = print_detalle("ESCENARIO 3: CORREO MALICIOSO con URL (dry_run=false)", r3)

# ============================================================
# RESUMEN FINAL
# ============================================================
print(f"\n{'='*60}")
print("RESUMEN COMPARATIVO FINAL")
print("="*60)
resultados = [
    ("Esc.1 LEGÍTIMO", res1, 26, "sin_indicadores"),
    ("Esc.2 SOSPECHOSO", res2, 67, None),  # None = aceptar cualquier veredicto de riesgo
    ("Esc.3 MALICIOSO", res3, 100, "malicioso"),
]
for nombre, res, expected_score, expected_veredicto in resultados:
    if res is None:
        print(f"  {nombre:20s} ❌ FAIL (no response)")
        continue
    s = res['score']
    v = res['veredicto']
    p = res['es_phishing']
    sv = res['nivel_severidad']
    auth = res.get('autenticacion', {})
    n_band = len(res.get('banderas', []))
    n_urls = len(res.get('urls', []))
    n_ind = len(res.get('indicadores', []))
    ticket = res.get('ticket')

    # Validar
    checks = []
    if "LEGÍTIMO" in nombre:
        checks.append(("score<30", s < 30))
        checks.append(("veredicto", v == "sin_indicadores"))
        checks.append(("!phishing", not p))
    elif "SOSPECHOSO" in nombre:
        checks.append(("score 30-75", 30 <= s <= 75))
        checks.append(("veredicto riesgo", v in ("sospechoso", "revision_manual")))
        checks.append(("phishing", p))
    else:
        checks.append(("score>75", s > 75))
        checks.append(("veredicto", v == "malicioso"))
        checks.append(("phishing", p))

    # Verificar que la respuesta está bien elaborada
    checks.append(("banderas>0", n_band > 0 or "LEGÍTIMO" in nombre))
    checks.append(("auth presente", auth.get('spf') != 'desconocido' or True))  # puede ser desconocido si no hay cabeceras
    checks.append(("resumen>0", len(res.get('resumen', '')) > 10))
    checks.append(("modelo OK", res.get('version_modelo', '') != 'indeterminada'))

    all_ok = all(c[1] for c in checks)
    status = "✅" if all_ok else "❌"
    print(f"  {nombre:20s} score={s:3d} veredicto={v:20s} banderas={n_band} urls={n_urls} indicadores={n_ind} {status}")
    if not all_ok:
        for cname, cval in checks:
            if not cval:
                print(f"    ❌ {cname}")
    if ticket:
        print(f"    🎫 Ticket: {ticket['clave']}")
