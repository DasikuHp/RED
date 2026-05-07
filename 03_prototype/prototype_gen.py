import sys
sys.path.insert(0, r"E:\RED")
import sqlite3
import re
import os
import unicodedata
from pathlib import Path
from openai import OpenAI
from config import Config
from loguru import logger

DB_PATH = r"E:\RED\red.db"
TEMPLATES_DIR = Path(r"E:\RED\templates")
OUTPUT_DIR = Path(r"E:\RED\output")
OUTPUT_DIR.mkdir(exist_ok=True)


def generate_slug(name: str) -> str:
    """Converts business name to URL-safe slug."""
    slug = name.lower()
    slug = slug.replace(" ", "-")
    slug = unicodedata.normalize("NFKD", slug)
    slug = slug.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    return slug


def generate_prototype(lead_id: int) -> str:
    """Generates an HTML prototype for a lead. Returns path to generated file."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    try:
        # 1. Load lead from SQLite
        c.execute(
            "SELECT business_name, phone, address, "
            "rating, review_count, category, language "
            "FROM leads WHERE id=?",
            (lead_id,),
        )
        row = c.fetchone()
        if not row:
            raise ValueError(f"Lead {lead_id} not found")
        business_name, phone, address, rating, review_count, category, language = row
        logger.info(f"Loaded lead {lead_id}: {business_name}")

        # 2. Load matching template
        template_path = TEMPLATES_DIR / f"{category}.html"
        if not template_path.exists():
            logger.warning(
                f"Template '{category}.html' not found, using fallback"
            )
            template_path = TEMPLATES_DIR / "restaurante-bar.html"
        html = template_path.read_text(encoding="utf-8")

        # 3. Replace placeholder tokens
        html = html.replace("[NOMBRE_NEGOCIO]", business_name)
        html = html.replace("[TELEFONO]", phone or "")
        html = html.replace("[DIRECCION]", address or "")
        html = html.replace("[RATING]", str(rating or ""))
        html = html.replace("[NUM_REVIEWS]", str(review_count or ""))

        # 4. LLM enhancement — generate tagline
        client = OpenAI(
            base_url=Config.LLM_BASE_URL,
            api_key="not-needed",
        )
        lang_instruction = (
            "Escribe en valenciano."
            if language == "val"
            else "Escribe en español."
        )
        tagline_prompt = (
            f"{lang_instruction} "
            f"Genera un tagline comercial de maximo 8 palabras "
            f"para este negocio: {business_name}, "
            f"categoria {category} en Valencia. "
            f"Solo el tagline, nada mas."
        )
        tagline_response = client.chat.completions.create(
            model=Config.LLM_MODEL,
            messages=[{"role": "user", "content": tagline_prompt}],
        )
        tagline = tagline_response.choices[0].message.content.strip()
        html = html.replace("[TAGLINE]", tagline)
        logger.info(f"Generated tagline: {tagline}")

        # 5. Add tracking pixel before </body>
        tracking_html = (
            f'<img src="{Config.PROTOTYPE_BASE_URL}'
            f'/px/{lead_id}.gif" '
            f'width="1" height="1" alt="" '
            f'style="position:absolute;opacity:0">'
        )
        html = html.replace("</body>", tracking_html + "\n</body>")

        # 6. Generate slug and save
        slug = generate_slug(business_name)
        output_path = OUTPUT_DIR / f"{slug}.html"
        output_path.write_text(html, encoding="utf-8")
        logger.success(f"Saved prototype to {output_path}")

        # 7. Update SQLite prototipos table
        c.execute(
            "INSERT INTO prototipos "
            "(lead_id, html_path, demo_url, generated_at) "
            "VALUES (?, ?, ?, datetime('now'))",
            (
                lead_id,
                str(output_path),
                f"{Config.PROTOTYPE_BASE_URL}/{slug}",
            ),
        )

        # 8. Update leads table
        c.execute(
            "UPDATE leads SET status='prototipo_generado', "
            "updated_at=datetime('now') WHERE id=?",
            (lead_id,),
        )

        conn.commit()
        logger.info(f"Database updated for lead {lead_id}")

        # 9. Return output path
        return str(output_path)

    except Exception as e:
        conn.rollback()
        logger.error(f"Error generating prototype for lead {lead_id}: {e}")
        raise
    finally:
        conn.close()
