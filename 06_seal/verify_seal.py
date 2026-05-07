import sys
sys.path.insert(0, r"E:\RED")
import sqlite3

DB_PATH = r"E:\RED\red.db"

print("Verificando ab_tracker...")
from ab_tracker import get_variant
v = get_variant(42, "restaurante-bar")
assert v in ["A", "B"], f"Variante inválida: {v}"
print(f"get_variant OK: {v}")
v2 = get_variant(42, "restaurante-bar")
assert v == v2, "No determinista con mismos inputs"
print("Determinismo OK")

print("Verificando seal_engine imports...")
from seal_engine import run_seal_cycle
print("Imports OK")

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
c.execute("SELECT COUNT(*) FROM campaigns WHERE status='sent'")
n = c.fetchone()[0]
conn.close()

if n == 0:
    print(f"Sin campañas enviadas aún — SEAL necesita datos reales")
    print("Estructura verificada OK")
else:
    print(f"Campañas disponibles: {n} — ejecutando ciclo...")
    result = run_seal_cycle()
    print(f"SEAL OK: {result}")

print("K-12 verificación completa")
