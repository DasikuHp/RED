import sys
import os
import sqlite3
sys.path.insert(0, r"E:\RED")

PASS = []
FAIL = []
WARN = []

def ok(msg): PASS.append(msg); print(f"  OK  {msg}")
def fail(msg): FAIL.append(msg); print(f" FAIL {msg}")
def warn(msg): WARN.append(msg); print(f" WARN {msg}")

print("\n" + "="*50)
print("RED SYSTEM — HEALTH CHECK")
print("="*50)

# ── 1. ESTRUCTURA DE DIRECTORIOS ──────────────────
print("\n[1] Directorios")
dirs = [
    r"E:\RED\01_discovery",
    r"E:\RED\02_scoring",
    r"E:\RED\03_prototype",
    r"E:\RED\04_outreach",
    r"E:\RED\05_followup",
    r"E:\RED\06_seal",
    r"E:\RED\skills",
    r"E:\RED\templates",
    r"E:\RED\logs",
    r"E:\RED\output",
]
for d in dirs:
    if os.path.isdir(d):
        ok(d.split("RED\\")[1])
    else:
        fail(d.split("RED\\")[1])

# ── 2. ARCHIVOS PYTHON ────────────────────────────
print("\n[2] Módulos Python")
files = {
    r"E:\RED\config.py": "config",
    r"E:\RED\db.py": "db",
    r"E:\RED\obsidian_bridge.py": "obsidian_bridge",
    r"E:\RED\01_discovery\browser_factory.py": "browser_factory",
    r"E:\RED\01_discovery\maps_scraper.py": "maps_scraper",
    r"E:\RED\01_discovery\web_verifier.py": "web_verifier",
    r"E:\RED\01_discovery\lead_extractor.py": "lead_extractor",
    r"E:\RED\02_scoring\lead_scorer.py": "lead_scorer",
    r"E:\RED\06_seal\seal_engine.py": "seal_engine",
    r"E:\RED\06_seal\ab_tracker.py": "ab_tracker",
}
for path, name in files.items():
    if os.path.isfile(path):
        size = os.path.getsize(path)
        ok(f"{name}.py ({size} bytes)")
    else:
        fail(f"{name}.py MISSING")

pending = [
    r"E:\RED\03_prototype\prototype_gen.py",
    r"E:\RED\04_outreach\email_gen.py",
    r"E:\RED\04_outreach\email_sender.py",
    r"E:\RED\04_outreach\tracking_server.py",
    r"E:\RED\05_followup\scheduler.py",
    r"E:\RED\main.py",
]
print("\n[2b] Módulos pendientes")
for path in pending:
    name = path.split("\\")[-1]
    if os.path.isfile(path):
        ok(f"{name} (ya existe)")
    else:
        warn(f"{name} — pendiente de crear")

# ── 3. CONFIG ─────────────────────────────────────
print("\n[3] Configuración")
try:
    from config import Config
    munis = Config.MUNICIPALITIES
    assert "Moncada" in munis, "Moncada missing"
    assert "Burjassot" in munis, "Burjassot missing"
    assert len(munis) == 5, f"Expected 5 municipalities, got {len(munis)}"
    ok(f"MUNICIPALITIES: {munis}")
    cats = Config.CATEGORIES
    assert len(cats) == 8, f"Expected 8 categories, got {len(cats)}"
    ok(f"CATEGORIES: {len(cats)} categorías OK")
    ok(f"LLM: {Config.llm_base_url} / {Config.llm_model}")
    ok(f"OBSIDIAN: {Config.obsidian_url}")
    if Config.smtp_host == "pending":
        warn("SMTP: pendiente (credenciales Rubén)")
    else:
        ok(f"SMTP: {Config.smtp_host}")
    if Config.ftp_host == "pending":
        warn("FTP: pendiente (credenciales Rubén)")
    else:
        ok(f"FTP: {Config.ftp_host}")
except Exception as e:
    fail(f"config.py: {e}")

# ── 4. BASE DE DATOS ──────────────────────────────
print("\n[4] Base de datos")
try:
    conn = sqlite3.connect(r"E:\RED\red.db")
    c = conn.cursor()
    expected_tables = [
        "leads", "prototipos", "campaigns",
        "tracking_events", "ab_experiments",
        "seal_insights"
    ]
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing = [r[0] for r in c.fetchall()]
    for t in expected_tables:
        if t in existing:
            c.execute(f"SELECT COUNT(*) FROM {t}")
            n = c.fetchone()[0]
            ok(f"tabla {t} ({n} filas)")
        else:
            fail(f"tabla {t} MISSING")
    expected_cols = {
        "leads": ["id","business_name","category",
                  "municipality","phone","score",
                  "tier","language","email","status"],
        "campaigns": ["id","lead_id","variant",
                      "opened","clicked","replied"],
        "prototipos": ["id","lead_id","demo_url",
                       "html_path","visited"],
    }
    for table, cols in expected_cols.items():
        c.execute(f"PRAGMA table_info({table})")
        existing_cols = [r[1] for r in c.fetchall()]
        missing = [col for col in cols
                   if col not in existing_cols]
        if missing:
            fail(f"{table} missing cols: {missing}")
        else:
            ok(f"{table} schema completo")
    conn.close()
except Exception as e:
    fail(f"SQLite: {e}")

# ── 5. IMPORTS DE MÓDULOS ─────────────────────────
print("\n[5] Imports")
module_tests = [
    ("config", "from config import Config"),
    ("obsidian_bridge",
     "from obsidian_bridge import crear_lead_note"),
    ("browser_factory",
     "import sys; sys.path.insert(0,r'E:\\RED\\01_discovery');"
     "from browser_factory import create_driver"),
    ("web_verifier",
     "import sys; sys.path.insert(0,r'E:\\RED\\01_discovery');"
     "from web_verifier import classify_url"),
    ("lead_scorer",
     "import sys; sys.path.insert(0,r'E:\\RED\\02_scoring');"
     "from lead_scorer import rule_score"),
    ("seal_engine",
     "import sys; sys.path.insert(0,r'E:\\RED\\06_seal');"
     "from seal_engine import run_seal_cycle"),
    ("ab_tracker",
     "import sys; sys.path.insert(0,r'E:\\RED\\06_seal');"
     "from ab_tracker import get_variant"),
]
for name, stmt in module_tests:
    try:
        exec(stmt)
        ok(f"import {name}")
    except Exception as e:
        fail(f"import {name}: {e}")

# ── 6. CONECTIVIDAD ───────────────────────────────
print("\n[6] Conectividad")
import httpx

try:
    r = httpx.get(
        "http://127.0.0.1:27123/",
        timeout=3,
        headers={"Authorization":
            f"Bearer {Config.obsidian_api_key}"}
    )
    ok(f"Obsidian REST API: HTTP {r.status_code}")
except Exception as e:
    fail(f"Obsidian REST API: {e}")

try:
    r = httpx.get(
        "http://localhost:1234/v1/models",
        timeout=3
    )
    ok(f"LM Studio: HTTP {r.status_code}")
except Exception as e:
    warn(f"LM Studio: no disponible ({e.__class__.__name__})"
         " — normal si no está corriendo")

# ── 7. FUNCIONES CRÍTICAS ─────────────────────────
print("\n[7] Funciones críticas")

try:
    sys.path.insert(0, r"E:\RED\01_discovery")
    from web_verifier import classify_url
    assert classify_url("") == "none"
    assert classify_url("https://www.facebook.com/bar") == "social"
    ok("classify_url() lógica correcta")
except Exception as e:
    fail(f"classify_url: {e}")

try:
    sys.path.insert(0, r"E:\RED\02_scoring")
    from lead_scorer import rule_score
    test_lead = {
        "phone": "961000000",
        "rating": 4.5,
        "review_count": 35,
        "category": "restaurante-bar",
        "language": "es",
        "email": ""
    }
    score = rule_score(test_lead)
    assert 0 < score <= 60, f"Score fuera de rango: {score}"
    ok(f"rule_score() = {score}/60")
except Exception as e:
    fail(f"rule_score: {e}")

try:
    sys.path.insert(0, r"E:\RED\06_seal")
    from ab_tracker import get_variant
    v1 = get_variant(42, "restaurante-bar")
    v2 = get_variant(42, "restaurante-bar")
    assert v1 in ["A","B"]
    assert v1 == v2
    ok(f"get_variant() determinista: {v1}")
except Exception as e:
    fail(f"get_variant: {e}")

# ── 8. TEMPLATES ──────────────────────────────────
print("\n[8] Templates HTML")
categories = [
    "restaurante-bar", "horchateria-cafeteria",
    "peluqueria-barberia", "taller-mecanico",
    "tienda-alimentacion", "clinica-fisio",
    "academia", "reformas-servicios"
]
for cat in categories:
    path = rf"E:\RED\templates\{cat}.html"
    if os.path.isfile(path):
        size = os.path.getsize(path)
        ok(f"{cat}.html ({size} bytes)")
    else:
        warn(f"{cat}.html — PENDIENTE (K-07b)")

# ── RESUMEN FINAL ─────────────────────────────────
print("\n" + "="*50)
print("RESUMEN")
print("="*50)
print(f"  PASS: {len(PASS)}")
print(f"  WARN: {len(WARN)} (pendientes o no críticos)")
print(f"  FAIL: {len(FAIL)}")

if FAIL:
    print("\nProblemas a resolver:")
    for f in FAIL:
        print(f"  ✗ {f}")

if len(FAIL) == 0:
    print("\nSistema listo para continuar con K-07a")
else:
    print(f"\nResolver {len(FAIL)} FAILs antes de continuar")
