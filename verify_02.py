import sys
sys.path.insert(0, r"E:\RED")

errors = []

try:
    import obsidian_bridge as ob
    print("OK: obsidian_bridge importado")
except Exception as e:
    print(f"FAIL: no se pudo importar obsidian_bridge: {e}")
    sys.exit(1)

required_functions = [
    "setup_vault", "crear_lead_note", "mover_lead",
    "actualizar_lead", "escribir_seal_log", "crear_campana"
]
for fn in required_functions:
    if not hasattr(ob, fn):
        errors.append(f"MISSING FUNCTION: {fn}")
    else:
        print(f"OK: {fn} existe")

slug = ob._make_slug("Bar La Peña")
if slug != "bar-la-pena":
    errors.append(f"WRONG SLUG: expected 'bar-la-pena', got '{slug}'")
else:
    print(f"OK: slug generado correctamente: {slug}")

try:
    result = ob.setup_vault()
    print(f"OK: setup_vault() ejecutado, {len(result)} rutas creadas")
except Exception as e:
    errors.append(f"FAIL setup_vault: {e}")

test_lead = {
    "business_name": "Bar Prueba",
    "category": "restaurante-bar",
    "score": 0,
    "status": "sin_verificar",
    "phone": "600000000",
    "email": "",
    "address": "Calle Test 1, Moncada",
    "demo_url": "",
    "language": "es",
    "created_at": "2025-01-01",
    "google_maps_url": "",
}
try:
    path = ob.crear_lead_note(test_lead)
    print(f"OK: nota creada en {path}")
except Exception as e:
    errors.append(f"FAIL crear_lead_note: {e}")

try:
    ob.mover_lead("bar-prueba", "activos", "contactados")
    print("OK: lead movido a contactados")
except Exception as e:
    errors.append(f"FAIL mover_lead: {e}")

if errors:
    for e in errors:
        print(f"FAIL: {e}")
    sys.exit(1)
else:
    print("ALL OK — K-02 complete")
