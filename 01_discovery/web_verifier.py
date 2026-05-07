import sys
sys.path.insert(0, r"E:\RED")

import sqlite3
from config import Config
import httpx
from urllib.parse import urlparse
from tqdm import tqdm

DB_PATH = r"E:\RED\red.db"

AGGREGATOR_LIST = [
    "facebook.com",
    "instagram.com",
    "tripadvisor.com",
    "yelp.com",
    "11870.com",
    "paginasamarillas.es",
    "infobel.com",
    "foursquare.com",
    "google.com",
    "mapquest.com",
    "bing.com",
    "yelp.es",
    "cylex.es",
    "einforma.com",
    "axesor.es"
]

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"


def extract_domain(url: str) -> str:
    """Extract domain from URL."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        # Remove www. prefix if present
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return ""


def google_search(query: str) -> list:
    """
    Perform Google search and return top 5 result URLs.
    
    Args:
        query: Search query string
        
    Returns:
        List of URLs from search results
    """
    try:
        headers = {"User-Agent": USER_AGENT}
        url = f"https://www.google.com/search?q={query}"
        
        response = httpx.get(url, headers=headers, timeout=10.0)
        response.raise_for_status()
        
        # Parse search results - extract URLs from href attributes
        import re
        # Google search results have URLs in href="/url?q=..." format
        pattern = r'href="(/url\?q=([^&]+)&|https?://[^"]+)"'
        matches = re.findall(pattern, response.text)
        
        urls = []
        for match in matches:
            if match[1]:  # URL from /url?q= format
                try:
                    url_decoded = match[1]
                    if url_decoded.startswith("http"):
                        urls.append(url_decoded)
                except Exception:
                    pass
            elif match[0].startswith("http"):  # Direct URL
                urls.append(match[0])
            
            if len(urls) >= 5:
                break
        
        return urls[:5]
    
    except Exception as e:
        print(f"Error during Google search: {e}")
        return []


def verify_lead(lead_id: int) -> bool:
    """
    Verify if a lead has a real website or only aggregator presence.
    
    Args:
        lead_id: ID of the lead to verify
        
    Returns:
        True if lead is verified (no real website), False otherwise
    """
    # Step 1: Load lead from SQLite
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "SELECT business_name, listed_website, website_status FROM leads WHERE id=?",
            (lead_id,)
        )
        row = c.fetchone()
        conn.close()

        if not row:
            return False

        business_name, listed_website, website_status = row
    except Exception as e:
        print(f"Error loading lead {lead_id}: {e}")
        return False
    
    # New verification logic
    if listed_website in [None, ""]:
        new_website_status, new_status = "sin_web", "verificado"
    elif any(agg in listed_website for agg in AGGREGATOR_LIST):
        new_website_status, new_status = "social_or_directory", "verificado"
    else:
        try:
            r = httpx.HEAD(
                listed_website,
                follow_redirects=True,
                timeout=8
            )
            final_domain = urlparse(r.url).netloc
            if r.status_code >= 400:
                new_website_status, new_status = "dead", "verificado"
            elif any(agg in final_domain for agg in AGGREGATOR_LIST):
                new_website_status, new_status = "social_or_directory", "verificado"
            else:
                new_website_status, new_status = "owned", "descartado"
        except:
            new_website_status, new_status = "unknown", "verificado"

    # Update SQLite
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "UPDATE leads SET website_status=?, status=?, updated_at=datetime('now') WHERE id=?",
            (new_website_status, new_status, lead_id)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error updating lead {lead_id}: {e}")
        return False

    return new_status == "verificado"


def verify_all_pending() -> None:
    """
    Verify all leads with status='sin_verificar'.
    Shows progress bar using tqdm.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Get all pending leads
        c.execute("SELECT id FROM leads WHERE status='sin_verificar'")
        pending_leads = [row[0] for row in c.fetchall()]
        conn.close()
        
        if not pending_leads:
            print("No pending leads to verify.")
            return
        
        print(f"Verifying {len(pending_leads)} pending leads...")
        
        # Process each lead with progress bar
        verified_count = 0
        for lead_id in tqdm(pending_leads, desc="Verifying leads"):
            if verify_lead(lead_id):
                verified_count += 1
        
        print(f"\nVerification complete: {verified_count}/{len(pending_leads)} leads verified")
    
    except Exception as e:
        print(f"Error during batch verification: {e}")


if __name__ == "__main__":
    # Example usage
    verify_all_pending()

def classify_url(url: str) -> str:
    """
    Alias público para el health check y módulos externos.
    Clasifica una URL como: none|social|directory|owned|dead
    """
    if not url or url.strip() == "":
        return "none"
    SOCIAL = [
        "facebook.com","instagram.com","tiktok.com",
        "twitter.com","linkedin.com","youtube.com"
    ]
    DIRECTORY = [
        "yelp.com","tripadvisor.com","paginasamarillas.es",
        "google.com","bing.com","foursquare.com",
        "11870.com","infobel.com","mapquest.com",
        "einforma.com","axesor.es","empresite.es"
    ]
    from urllib.parse import urlparse
    try:
        domain = urlparse(url).netloc.lower().replace("www.","")
        if any(s in domain for s in SOCIAL):
            return "social"
        if any(d in domain for d in DIRECTORY):
            return "directory"
        import httpx
        resp = httpx.head(url, follow_redirects=True, timeout=8)
        if resp.status_code >= 400:
            return "dead"
        final = urlparse(str(resp.url)).netloc.lower()
        if any(s in final for s in SOCIAL):
            return "social"
        if any(d in final for d in DIRECTORY):
            return "directory"
        return "owned"
    except Exception:
        return "dead"