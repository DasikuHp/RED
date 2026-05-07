"""
browser_factory.py — undetected Chrome factory
"""
import os
import shutil
import subprocess
import re
import random
from pathlib import Path
import undetected_chromedriver as uc
from loguru import logger

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

def get_chrome_version() -> int:
    """Read major version from Chrome binary via registry or binary."""
    # Método 1: registro de Windows (más fiable)
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Google\Chrome\BLBeacon"
        )
        version_str, _ = winreg.QueryValueEx(key, "version")
        winreg.CloseKey(key)
        major = int(version_str.split(".")[0])
        logger.debug(f"Chrome version from registry: {version_str}")
        return major
    except Exception:
        pass

    # Método 2: subprocess con CREATE_NO_WINDOW
    try:
        result = subprocess.run(
            [CHROME_PATH, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=0x08000000  # CREATE_NO_WINDOW
        )
        match = re.search(r"(\d+)\.\d+\.\d+\.\d+", result.stdout + result.stderr)
        if match:
            return int(match.group(1))
    except Exception:
        pass

    logger.warning("No se pudo detectar versión de Chrome, usando 147")
    return 147

def clear_driver_cache():
    """Clear stale chromedriver cache."""
    cache_dir = Path.home() / "AppData" / "Roaming" / "undetected_chromedriver"
    if cache_dir.exists():
        try:
            shutil.rmtree(cache_dir, ignore_errors=True)
            logger.debug("Cleared undetected_chromedriver cache")
        except Exception as e:
            logger.warning(f"Failed to clear driver cache: {e}")

def create_driver():
    major = get_chrome_version()
    logger.debug(f"Chrome major version detected: {major}")

    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--window-size=1280,900")
    options.add_argument("--lang=es-ES")

    driver = uc.Chrome(
        options=options,
        browser_executable_path=CHROME_PATH,
        version_main=147,       # ← key fix: matches driver to binary
        use_subprocess=True,
        driver_executable_path=None   # force re-download if stale
    )
    return driver

def random_delay(base: float = 3.0, jitter: float = 1.0):
    import time, random
    time.sleep(base + random.uniform(-jitter, jitter))
