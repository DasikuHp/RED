"""
obsidian_bridge.py — K-02
Puente con la Obsidian Local REST API.
Usa httpx (sincrono) con retry (3 intentos, esperas 1/2/4s).
"""

import time
import re
import unicodedata

import httpx
from loguru import logger

from config import Config

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

BASE = Config.obsidian_url.rstrip("/")
RETRY_DELAYS = [1, 2, 4]


def _headers() -> dict:
    """Retorna cabeceras de autorizacion para la API de Obsidian."""
    return {"Authorization": f"Bearer {Config.obsidian_api_key}"}


def _retry_request(method: str, url: str, **kwargs) -> httpx.Response:
    """
    Intenta la peticion hasta 3 veces.
    Esperas entre intentos: 1s, 2s, 4s.
    Lanza excepcion si los 3 fallan.
    """
    last_exc = None
    for attempt, delay in enumerate(RETRY_DELAYS, start=1):
        try:
            resp = httpx.request(method, url, headers=_headers(), timeout=15, **kwargs)
            resp.raise_for_status()
            return resp
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            last_exc = exc
            logger.warning(
                f"Obsidian API intento {attempt}/3 fallido: {exc}"
            )
            if attempt < len(RETRY_DELAYS):
                time.sleep(delay)
    raise last_exc  # type: ignore[misc]


# ──────────────────────────────────────────────
# 3. setup_vault
# ──────────────────────────────────────────────

_VAULT_FILES: list[tuple[str, str]] = [
    (
        "00_sistema/config.md",
        "---\nversion: \"1.0\"\nzones: valencia\n---\n",
    ),
    (
        "00_sistema/README.md",
        "# RED System\nDocumentacion del sistema RED.",
    ),
    ("01_leads/activos/.gitkeep", ""),
    ("01_leads/contactados/.gitkeep", ""),
    ("01_leads/frios/.gitkeep", ""),
    ("01_leads/convertidos/.gitkeep", ""),
    ("02_prototipos/templates/.gitkeep", ""),
    ("02_prototipos/generados/.gitkeep", ""),
    ("03_campanas/.gitkeep", ""),
    ("04_seal_logs/.gitkeep", ""),
    (
        "05_social_fallback/README.md",
        "Phase 2 - WhatsApp/IG automation pending",
    ),
]


def setup_vault() -> list[str]:
    """Crea la estructura de carpetas/archivos en el vault de Obsidian."""
    created: list[str] = []
    for path, content in _VAULT_FILES:
        url = f"{BASE}/vault/{path}"
        _retry_request("PUT", url, content=content, headers={**_headers(), "Content-Type": "text/markdown"})
        logger.info(f"Vault: creado {path}")
        created.append(path)
    return created


# ──────────────────────────────────────────────
# 4. _make_slug
# ──────────────────────────────────────────────

def _make_slug(business_name: str) -> str:
    """
    Convierte nombre a slug:
    - minusculas
    - espacios a guiones
    - elimina acentos (NFKD + ascii ignore)
    - elimina caracteres no alfanumericos excepto guiones
    """
    name = business_name.lower().strip()
    # Eliminar acentos
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    # Espacios a guiones
    name = name.replace(" ", "-")
    # Solo alfanumericos y guiones
    name = re.sub(r"[^a-z0-9-]", "", name)
    # Colapsar guiones multiples
    name = re.sub(r"-+", "-", name)
    return name.strip("-")


# ──────────────────────────────────────────────
# 5. crear_lead_note
# ──────────────────────────────────────────────

def crear_lead_note(lead: dict) -> str:
    """
    Crea nota de lead en 01_leads/activos/{slug}.md con frontmatter YAML.
    Retorna la ruta de la nota.
    """
    slug = _make_slug(lead.get("business_name", "sin-nombre"))
    path = f"01_leads/activos/{slug}.md"

    frontmatter = (
        "---\n"
        f"nombre: \"{lead.get('business_name', '')}\"\n"
        f"categoria: \"{lead.get('category', '')}\"\n"
        f"score: {lead.get('score', 0)}\n"
        f"status: \"{lead.get('status', 'sin_verificar')}\"\n"
        f"telefono: \"{lead.get('phone', '')}\"\n"
        f"email: \"{lead.get('email', '')}\"\n"
        f"direccion: \"{lead.get('address', '')}\"\n"
        f"demo_url: \"{lead.get('demo_url', '')}\"\n"
        f"idioma: \"{lead.get('language', 'es')}\"\n"
        f"fecha_scraping: \"{lead.get('created_at', '')}\"\n"
        f"maps_url: \"{lead.get('google_maps_url', '')}\"\n"
        "---\n"
    )
    body = "## Notas\n\n## Historial\n"
    content = frontmatter + "\n" + body

    url = f"{BASE}/vault/{path}"
    _retry_request("PUT", url, content=content, headers={**_headers(), "Content-Type": "text/markdown"})
    logger.info(f"Lead note creada: {path}")
    return path


# ──────────────────────────────────────────────
# 6. mover_lead
# ──────────────────────────────────────────────

_VALID_FOLDERS = {"activos", "contactados", "frios", "convertidos"}


def mover_lead(slug: str, origen: str, destino: str) -> None:
    """
    Mueve un lead de una carpeta a otra dentro de 01_leads/.
    Flujo: GET contenido -> PUT en destino -> DELETE origen.
    """
    if origen not in _VALID_FOLDERS:
        raise ValueError(f"Carpeta origen invalida: '{origen}'. Validas: {_VALID_FOLDERS}")
    if destino not in _VALID_FOLDERS:
        raise ValueError(f"Carpeta destino invalida: '{destino}'. Validas: {_VALID_FOLDERS}")

    src_path = f"01_leads/{origen}/{slug}.md"
    dst_path = f"01_leads/{destino}/{slug}.md"

    # GET contenido del origen
    src_url = f"{BASE}/vault/{src_path}"
    resp = _retry_request("GET", src_url)
    content = resp.text

    # PUT en destino
    dst_url = f"{BASE}/vault/{dst_path}"
    _retry_request("PUT", dst_url, content=content, headers={**_headers(), "Content-Type": "text/markdown"})

    # DELETE origen
    _retry_request("DELETE", src_url)

    logger.info(f"Lead movido: {src_path} -> {dst_path}")


# ──────────────────────────────────────────────
# 7. actualizar_lead
# ──────────────────────────────────────────────

def actualizar_lead(slug: str, carpeta: str, updates: dict) -> None:
    """
    GET nota actual, actualiza campos en frontmatter, PUT de vuelta.
    """
    path = f"01_leads/{carpeta}/{slug}.md"
    url = f"{BASE}/vault/{path}"

    # GET nota actual
    resp = _retry_request("GET", url)
    content = resp.text

    # Parsear frontmatter
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            fm_text = parts[1]
            body = parts[2]
        else:
            fm_text = ""
            body = content
    else:
        fm_text = ""
        body = content

    # Actualizar campos
    fm_lines = fm_text.strip().split("\n") if fm_text.strip() else []
    updated_keys = set()
    new_lines = []
    for line in fm_lines:
        if ":" in line:
            key = line.split(":", 1)[0].strip()
            if key in updates:
                value = updates[key]
                if isinstance(value, (int, float)):
                    new_lines.append(f"{key}: {value}")
                else:
                    new_lines.append(f'{key}: "{value}"')
                updated_keys.add(key)
                continue
        new_lines.append(line)

    # Agregar campos nuevos
    for key, value in updates.items():
        if key not in updated_keys:
            if isinstance(value, (int, float)):
                new_lines.append(f"{key}: {value}")
            else:
                new_lines.append(f'{key}: "{value}"')

    new_content = "---\n" + "\n".join(new_lines) + "\n---" + body

    _retry_request("PUT", url, content=new_content, headers={**_headers(), "Content-Type": "text/markdown"})
    logger.info(f"Lead actualizado: {path}")


# ──────────────────────────────────────────────
# 8. escribir_seal_log
# ──────────────────────────────────────────────

def escribir_seal_log(fecha: str, contenido: str) -> None:
    """PUT a 04_seal_logs/seal_{fecha}.md"""
    path = f"04_seal_logs/seal_{fecha}.md"
    url = f"{BASE}/vault/{path}"
    _retry_request("PUT", url, content=contenido, headers={**_headers(), "Content-Type": "text/markdown"})
    logger.info(f"SEAL log escrito: {path}")


# ──────────────────────────────────────────────
# 9. crear_campana
# ──────────────────────────────────────────────

def crear_campana(nombre: str, lead_slugs: list) -> str:
    """
    Crea 03_campanas/{nombre}.md con lista de leads y un bloque Dataview.
    Retorna la ruta creada.
    """
    path = f"03_campanas/{nombre}.md"

    lines = [
        f"# Campaña: {nombre}\n",
        "## Leads incluidos\n",
    ]
    for slug in lead_slugs:
        lines.append(f"- [[01_leads/activos/{slug}]]")

    lines.append("\n## Dataview\n")
    lines.append("```dataview")
    lines.append("TABLE nombre, categoria, score, status")
    lines.append("FROM \"01_leads\"")
    lines.append(f"WHERE contains(file.name, \"{'\" OR contains(file.name, \"'.join(lead_slugs)}\")")
    lines.append("SORT score DESC")
    lines.append("```\n")

    content = "\n".join(lines)

    url = f"{BASE}/vault/{path}"
    _retry_request("PUT", url, content=content, headers={**_headers(), "Content-Type": "text/markdown"})
    logger.info(f"Campaña creada: {path}")
    return path
