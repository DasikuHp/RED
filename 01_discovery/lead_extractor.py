import sys
import os
import re
import sqlite3
import time
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, r"E:\RED")
from config import Config

# Try to import from the same directory or with absolute path
try:
    from browser_factory import create_driver, random_delay
except ImportError:
    # If called from elsewhere, try to find it in the current directory
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from browser_factory import create_driver, random_delay

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from loguru import logger

DB_PATH = r"E:\RED\red.db"

VALENCIAN_MARKERS = [
    "hui", "dema", "aco", "nosaltres",
    "molt", "pero", "tambe", "perque",
    "hora", "ara", "des de", "gracies",
    "obert", "tancat", "bon dia", "bona vesprada"
]

EMAIL_REGEX = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"

def extract_contact(lead_id: int) -> dict:
    """
    Extracts contact information (email) for a lead and detects its language.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # 1. Load lead from SQLite
    c.execute(
        "SELECT business_name, municipality, social_url FROM leads WHERE id=?",
        (lead_id,)
    )
    lead = c.fetchone()
    if not lead:
        logger.error(f"Lead with ID {lead_id} not found.")
        conn.close()
        return {}

    business_name = lead["business_name"]
    municipality = lead["municipality"]
    social_url = lead["social_url"]
    conn.close()
    
    email = None
    email_status = "not_found"
    collected_text = ""
    language = "es"  # Default language
    driver = None

    try:
        # 2. If lead has social_url (Facebook/Instagram)
        if social_url:
            driver = create_driver(headless=False)
            logger.info(f"Navigating to social URL: {social_url}")
            driver.get(social_url)
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
                pass

            if "facebook.com" in social_url:
                # b. Facebook: find "Acerca de" section, extract email with regex
                # Look for "Acerca de" or "About" or "Información"
                try:
                    # Try to find "Acerca de" or similar
                    about_selectors = [
                        "//span[contains(text(), 'Información')]",
                        "//span[contains(text(), 'Acerca de')]",
                        "//span[contains(text(), 'About')]"
                    ]
                    for selector in about_selectors:
                        try:
                            about_btn = driver.find_element(By.XPATH, selector)
                            about_btn.click()
                            random_delay(2.0, 1.0)
                            break
                        except NoSuchElementException:
                            continue
                except Exception as e:
                    logger.debug(f"Could not find 'About' section: {e}")

                # Extract email and visible text
                page_text = driver.find_element(By.TAG_NAME, "body").text
                collected_text += page_text
                
                emails = re.findall(EMAIL_REGEX, page_text)
                if emails:
                    email = emails[0]
                    email_status = "extracted_facebook"
                    logger.info(f"Found email on Facebook: {email}")

            elif "instagram.com" in social_url:
                # c. Instagram: check bio for email or linktree
                try:
                    bio_el = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, "//header//section"))
                    )
                    bio_text = bio_el.text
                    collected_text += bio_text
                    
                    emails = re.findall(EMAIL_REGEX, bio_text)
                    if emails:
                        email = emails[0]
                        email_status = "extracted_instagram"
                        logger.info(f"Found email in Instagram bio: {email}")
                    else:
                        # Check for linktree or other links
                        links = driver.find_elements(By.XPATH, "//header//section//a")
                        for link in links:
                            href = link.get_attribute("href")
                            if href and ("linktr.ee" in href or "bio.link" in href):
                                logger.info(f"Found linktree/bio link: {href}")
                                # In a real implementation we might follow this, but for now just log it
                                email_status = "linktree_found"
                except Exception as e:
                    logger.debug(f"Error extracting from Instagram: {e}")

        # 3. If no social_url or no email found
        if not email:
            try:
                if not driver or not driver.service.is_connectable():
                    driver = create_driver(headless=False)
                
                logger.info(f"Searching for contact email for: {business_name}")
                query = f"{business_name} {municipality} email contacto"
                driver.get("https://www.google.com/search?q=" + query)
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
                    pass

                # Extract email from result snippets
                search_results = driver.find_element(By.ID, "search").text
                collected_text += search_results
                
                emails = re.findall(EMAIL_REGEX, search_results)
                if emails:
                    email = emails[0]
                    email_status = "extracted_search"
                    logger.info(f"Found email in search results: {email}")
            except Exception as e:
                logger.error(f"Search failed: {e}")

        # 4. Language detection
        text_lower = collected_text.lower()
        marker_count = sum(
            1 for m in VALENCIAN_MARKERS
            if m in text_lower
        )
        language = "val" if marker_count >= 2 else "es"
        logger.info(f"Language detected: {language} (markers found: {marker_count})")

    except Exception as e:
        logger.error(f"Error in extract_contact for lead {lead_id}: {e}")
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
    
    # 5. Update SQLite
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "UPDATE leads SET email=?, language=?, "
            "email_status=?, updated_at=datetime('now') "
            "WHERE id=?",
            (email, language, email_status, lead_id)
        )
        conn.commit()
        conn.close()
        logger.info(f"Updated lead {lead_id} in DB.")
    except Exception as e:
        logger.error(f"Error updating DB for lead {lead_id}: {e}")

    # 6. Return updated lead dict
    return {
        "id": lead_id,
        "business_name": business_name,
        "municipality": municipality,
        "email": email,
        "language": language,
        "email_status": email_status
    }

# Phase 2 stubs
def whatsapp_fallback(lead_id: int): pass
def instagram_dm_fallback(lead_id: int): pass

if __name__ == "__main__":
    # Test if an ID is provided
    if len(sys.argv) > 1:
        try:
            res = extract_contact(int(sys.argv[1]))
            print(res)
        except ValueError:
            print("Usage: python lead_extractor.py <lead_id>")
    else:
        print("Usage: python lead_extractor.py <lead_id>")
