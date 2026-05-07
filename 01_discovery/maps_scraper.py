"""
maps_scraper.py — Google Maps lead scraper
Uses undetected-chromedriver via browser_factory.
Extracts business data with CSS selectors + XPath fallbacks.
"""

import re
import sys
import time
import random
import sqlite3
from pathlib import Path

from loguru import logger
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    StaleElementReferenceException,
    ElementClickInterceptedException,
)

# ── Imports internos ─────────────────────────────────────────────
# Add project root to path for db.py access
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from .browser_factory import create_driver, random_delay, clear_driver_cache
except ImportError:
    from browser_factory import create_driver, random_delay, clear_driver_cache

_cache_cleared = False

# ── Regex para redes sociales ────────────────────────────────────
_SOCIAL_RE = re.compile(r"facebook|instagram|tiktok", re.IGNORECASE)

# ── CSS + XPath selector pairs ───────────────────────────────────
SELECTORS = {
    "name": {
        "css": "h1.DUwDvf",
        "xpath": "//h1[contains(@class,'fontHeadlineLarge')]",
    },
    "phone": {
        "css": 'button[data-item-id^="phone"]',
        "xpath": "//button[contains(@aria-label,'Telefono')]",
        "attr": "aria-label",
    },
    "website": {
        "css": 'a[data-item-id="authority"]',
        "xpath": "//a[contains(@aria-label,'Sitio web')]",
        "attr": "href",
    },
    "rating": {
        "css": "span.Aq14fc",
        "xpath": "//span[contains(@aria-label,'estrellas')]",
        "attr": "aria-label",
    },
    "reviews": {
        "css": "span.UY7F9",
        "xpath": "//span[contains(text(),'reseñas') or contains(text(),'resenas')]",
    },
}


# ── Helpers ──────────────────────────────────────────────────────

def _safe_extract(driver, field: str) -> str | None:
    """Try CSS selector first, then XPath fallback.
    Returns text/attribute or None."""
    spec = SELECTORS[field]
    attr = spec.get("attr")

    # 1) CSS attempt
    try:
        el = driver.find_element(By.CSS_SELECTOR, spec["css"])
        value = el.get_attribute(attr) if attr else el.text
        if value and value.strip():
            return value.strip()
    except (NoSuchElementException, StaleElementReferenceException):
        pass

    # 2) XPath fallback
    try:
        el = driver.find_element(By.XPATH, spec["xpath"])
        value = el.get_attribute(attr) if attr else el.text
        if value and value.strip():
            return value.strip()
    except (NoSuchElementException, StaleElementReferenceException):
        pass

    return None


def _parse_rating(raw: str | None) -> float | None:
    """Extract numeric rating from text like '4,5 estrellas'."""
    if not raw:
        return None
    m = re.search(r"(\d[.,]?\d?)", raw)
    if m:
        return float(m.group(1).replace(",", "."))
    return None


def _parse_reviews(raw: str | None) -> int | None:
    """Extract review count from text like '(123)' or '123 reseñas'."""
    if not raw:
        return None
    m = re.search(r"[\d.]+", raw.replace(".", ""))
    if m:
        try:
            return int(m.group(0))
        except ValueError:
            return None
    return None


def _parse_phone(raw: str | None) -> str | None:
    """Extract phone number from aria-label like 'Telefono: 961 234 567'."""
    if not raw:
        return None
    m = re.search(r"[\d\s\+\-]{7,}", raw)
    if m:
        return m.group(0).strip()
    return None


def _human_scroll(driver, panel, scrolls: int = 3):
    """Scroll the results panel in a human-like way."""
    for _ in range(scrolls):
        scroll_amount = random.randint(300, 600)
        driver.execute_script(
            "arguments[0].scrollTop += arguments[1];", panel, scroll_amount
        )
        time.sleep(random.uniform(0.8, 1.5))


# ── Main scraping function ──────────────────────────────────────

def scrape_maps(
    zona: str,
    categoria: str,
    max_results: int = 50,
) -> list[dict]:
    """
    Scrape Google Maps for businesses matching {categoria} in {zona} Valencia.

    Returns a list of dicts with keys:
        business_name, phone, website, rating, review_count,
        tiene_web, social_url, category, municipality
    """
    leads: list[dict] = []
    driver = None

    global _cache_cleared
    try:
        # 0. Clear cache once per session
        if not _cache_cleared:
            clear_driver_cache()
            _cache_cleared = True

        # 1. Launch browser
        driver = create_driver()
        logger.info(f"Buscando: {categoria} {zona} Valencia")

        # 2. Navigate to Google Maps
        driver.get("https://www.google.com/maps/search/" + 
                   f"{categoria}+{zona}+Valencia")

        # ── Saltar página intermedia "Antes de ir a Google Maps" ──
        import time
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        time.sleep(2)
        # Si aparece la página de bienvenida/buscador, hacer clic en el botón de continuar
        try:
            continuar = WebDriverWait(driver, 6).until(
                EC.element_to_be_clickable((By.XPATH,
                    "//button[contains(., 'Continuar') or "
                    "contains(., 'Continue') or "
                    "contains(., 'Aceptar') or "
                    "contains(., 'Accept')]"
                ))
            )
            continuar.click()
            logger.debug("Página intermedia descartada")
            time.sleep(2)
        except Exception:
            logger.debug("Sin página intermedia — continuando")
        random_delay(3.0, 1.5)

        # Accept cookies if dialog appears
        try:
            accept_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(.,'Aceptar todo') or contains(.,'Accept all')]")
                )
            )
            accept_btn.click()
            random_delay(2.0, 1.0)
        except TimeoutException:
            logger.debug("No cookie dialog found — continuing")

        # 3. Search
        search_box = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "searchboxinput"))
        )
        query = f"{categoria} {zona} Valencia"
        search_box.clear()
        # Type like a human: char by char with tiny delays
        for ch in query:
            search_box.send_keys(ch)
            time.sleep(random.uniform(0.03, 0.10))
        random_delay(1.0, 0.5)
        search_box.send_keys(Keys.ENTER)

        # 4. Wait for results panel
        random_delay(4.0, 1.5)

        # Locate the scrollable results container
        results_panel = None
        panel_selectors = [
            "div[role='feed']",
            "div.m6QErb.DxyBCb.kA9KIf.dS8AEf",
            "div.m6QErb",
        ]
        for sel in panel_selectors:
            try:
                results_panel = driver.find_element(By.CSS_SELECTOR, sel)
                break
            except NoSuchElementException:
                continue

        if not results_panel:
            logger.error("No se encontró el panel de resultados")
            return leads

        # 5-7. Iterate through business cards
        seen_names: set[str] = set()
        no_new_results_count = 0
        max_no_new = 5  # stop after 5 scrolls with no new results

        while len(leads) < max_results and no_new_results_count < max_no_new:
            # Find all result cards
            cards = driver.find_elements(By.CSS_SELECTOR, "a.hfpxzc")
            if not cards:
                # Fallback selector
                cards = driver.find_elements(
                    By.XPATH, "//a[contains(@class,'hfpxzc')]"
                )

            new_found = False

            for card in cards:
                if len(leads) >= max_results:
                    break

                # Get card label to check for duplicates
                try:
                    card_label = card.get_attribute("aria-label") or ""
                except StaleElementReferenceException:
                    continue

                if card_label in seen_names:
                    continue

                # 5a. Click to open detail panel
                try:
                    driver.execute_script(
                        "arguments[0].scrollIntoView({block: 'center'});", card
                    )
                    time.sleep(random.uniform(0.3, 0.6))
                    card.click()
                except (
                    ElementClickInterceptedException,
                    StaleElementReferenceException,
                ):
                    logger.debug(f"Click fallido en: {card_label[:40]}")
                    continue

                random_delay(2.5, 1.5)

                # 5b. Extract fields
                name = _safe_extract(driver, "name")
                if not name:
                    logger.debug("Sin nombre — skipping card")
                    # Go back to results
                    try:
                        back_btn = driver.find_element(
                            By.CSS_SELECTOR, "button[aria-label='Atrás']"
                        )
                        back_btn.click()
                    except NoSuchElementException:
                        try:
                            back_btn = driver.find_element(
                                By.XPATH, "//button[contains(@aria-label,'Back') or contains(@aria-label,'Atrás')]"
                            )
                            back_btn.click()
                        except NoSuchElementException:
                            pass
                    random_delay(1.5, 0.5)
                    continue

                if name in seen_names:
                    # Navigate back
                    try:
                        back_btn = driver.find_element(
                            By.CSS_SELECTOR, "button[aria-label='Atrás']"
                        )
                        back_btn.click()
                    except NoSuchElementException:
                        try:
                            back_btn = driver.find_element(
                                By.XPATH, "//button[contains(@aria-label,'Back') or contains(@aria-label,'Atrás')]"
                            )
                            back_btn.click()
                        except NoSuchElementException:
                            pass
                    random_delay(1.5, 0.5)
                    continue

                seen_names.add(name)
                seen_names.add(card_label)
                new_found = True

                phone_raw = _safe_extract(driver, "phone")
                phone = _parse_phone(phone_raw)

                website = _safe_extract(driver, "website")

                rating_raw = _safe_extract(driver, "rating")
                rating = _parse_rating(rating_raw)

                reviews_raw = _safe_extract(driver, "reviews")
                review_count = _parse_reviews(reviews_raw)

                # 5c-5e. Determine tiene_web and social_url
                tiene_web = False
                social_url = None

                if website:
                    if _SOCIAL_RE.search(website):
                        social_url = website
                        tiene_web = False
                    else:
                        tiene_web = True

                lead = {
                    "business_name": name,
                    "phone": phone,
                    "website": website if tiene_web else None,
                    "rating": rating,
                    "review_count": review_count,
                    "tiene_web": tiene_web,
                    "social_url": social_url,
                    "category": categoria,
                    "municipality": zona,
                }
                leads.append(lead)
                logger.info(
                    f"[{len(leads)}/{max_results}] {name} | "
                    f"web={'✓' if tiene_web else '✗'} | ☎ {phone or '—'}"
                )

                # Navigate back to results list
                try:
                    back_btn = driver.find_element(
                        By.CSS_SELECTOR, "button[aria-label='Atrás']"
                    )
                    back_btn.click()
                except NoSuchElementException:
                    try:
                        back_btn = driver.find_element(
                            By.XPATH, "//button[contains(@aria-label,'Back') or contains(@aria-label,'Atrás')]"
                        )
                        back_btn.click()
                    except NoSuchElementException:
                        driver.back()

                random_delay(2.0, 1.0)

            if not new_found:
                no_new_results_count += 1
            else:
                no_new_results_count = 0

            # 6. Scroll results panel to load more
            if len(leads) < max_results:
                # Re-locate the panel (may have gone stale)
                for sel in panel_selectors:
                    try:
                        results_panel = driver.find_element(By.CSS_SELECTOR, sel)
                        break
                    except NoSuchElementException:
                        continue

                if results_panel:
                    _human_scroll(driver, results_panel, scrolls=random.randint(2, 4))
                    random_delay(2.0, 1.0)

                # Check for "end of list" marker
                try:
                    driver.find_element(
                        By.XPATH,
                        "//span[contains(text(),'final de la lista') or "
                        "contains(text(),'end of list') or "
                        "contains(text(),'No hay más resultados')]",
                    )
                    logger.info("Fin de la lista de resultados alcanzado")
                    break
                except NoSuchElementException:
                    pass

    except Exception as e:
        logger.error(f"Error durante el scraping: {e}")
        raise
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

    logger.info(f"Total leads extraídos: {len(leads)}")

    # 8. Save to SQLite
    if leads:
        _save_to_db(leads)

    # 9. Return list of dicts
    return leads


# ── Database persistence ─────────────────────────────────────────

DB_PATH = Path(__file__).resolve().parent.parent / "red.db"


def _save_to_db(leads: list[dict]):
    """Insert scraped leads into the SQLite leads table."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    inserted = 0
    skipped = 0

    for lead in leads:
        # Check for duplicate by business_name + municipality
        cursor.execute(
            "SELECT id FROM leads WHERE business_name = ? AND municipality = ?",
            (lead["business_name"], lead["municipality"]),
        )
        if cursor.fetchone():
            skipped += 1
            logger.debug(f"Duplicado omitido: {lead['business_name']}")
            continue

        cursor.execute(
            """INSERT INTO leads
               (business_name, municipality, phone, listed_website,
                category, rating, review_count, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'sin_verificar')""",
            (
                lead["business_name"],
                lead["municipality"],
                lead["phone"],
                lead["website"],
                lead["category"],
                lead["rating"],
                lead["review_count"],
            ),
        )
        inserted += 1

    conn.commit()
    conn.close()
    logger.info(f"DB: {inserted} insertados, {skipped} duplicados omitidos")


# ── CLI ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import typer

    app = typer.Typer()

    @app.command()
    def main(
        zona: str,
        cat: str,
        max: int = 50,
    ):
        results = scrape_maps(zona, cat, max)
        print(f"Scraped {len(results)} leads")

    app()
