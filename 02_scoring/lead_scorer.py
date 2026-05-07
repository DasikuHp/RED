import sys
sys.path.insert(0, r"E:\RED")
import sqlite3
from openai import OpenAI
from config import Config
from tqdm import tqdm

DB_PATH = r"E:\RED\red.db"

HIGH_VALUE = [
    "restaurante-bar", "horchateria-cafeteria",
    "peluqueria-barberia", "clinica-fisio"
]
MED_VALUE = [
    "taller-mecanico", "academia",
    "tienda-alimentacion", "reformas-servicios"
]

def score_lead(lead_id: int) -> int:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT business_name, category, rating, "
        "review_count, email, language "
        "FROM leads WHERE id=?",
        (lead_id,)
    )
    row = c.fetchone()
    if not row:
        conn.close()
        return 0

    business_name, category, rating, review_count, email, language = row

    # LAYER 1 — Deterministic rules (max 60 pts)
    layer1_score = 0
    if email is not None and email != "":
        layer1_score += 20
    if review_count is not None and review_count >= 20:
        layer1_score += 15
    if rating is not None and rating >= 4.0:
        layer1_score += 10
    if rating is not None and rating >= 4.5:
        layer1_score += 5
    if category in HIGH_VALUE:
        layer1_score += 15
    if category in MED_VALUE:
        layer1_score += 10
    if language == "val":
        layer1_score += 5

    layer1_score = min(60, layer1_score)

    # LAYER 2 — LLM evaluation (max 40 pts)
    client = OpenAI(
        base_url=Config.LLM_BASE_URL,
        api_key="not-needed"
    )
    prompt = (
        f"Rate 0-40 the likelihood that this local "
        f"business in Valencia, Spain would pay for "
        f"a professional website. "
        f"Business: {business_name}, "
        f"Category: {category}, "
        f"{review_count} Google reviews, "
        f"rating {rating}. "
        f"They currently have no website. "
        f"Return ONLY a number between 0 and 40."
    )
    
    try:
        response = client.chat.completions.create(
            model=Config.LLM_MODEL,
            messages=[{"role": "user", "content": prompt}]
        )
        llm_score_text = response.choices[0].message.content.strip()
        try:
            llm_score = max(0, min(40, int(llm_score_text)))
        except ValueError:
            llm_score = 20
    except Exception as e:
        print(f"LLM evaluation failed: {e}")
        llm_score = 20

    total = layer1_score + llm_score

    # Assign tier
    if total >= 70:
        tier = "A"
    elif total >= 50:
        tier = "B"
    else:
        tier = "C"

    # Update SQLite
    c.execute(
        "UPDATE leads SET score=?, tier=?, "
        "updated_at=datetime('now') WHERE id=?",
        (total, tier, lead_id)
    )
    conn.commit()
    conn.close()

    return total

def score_all_verified():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM leads WHERE status='verificado' AND score IS NULL")
    rows = c.fetchall()
    conn.close()
    
    if not rows:
        print("No verified leads pending scoring.")
        return
        
    for row in tqdm(rows, desc="Scoring leads"):
        score_lead(row[0])
        
    # Print leaderboard
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT business_name, category, score, tier "
        "FROM leads WHERE score IS NOT NULL "
        "ORDER BY score DESC LIMIT 10"
    )
    top_leads = c.fetchall()
    conn.close()
    
    print("\n--- TOP 10 LEADS LEADERBOARD ---")
    for lead in top_leads:
        b_name, cat, score, tier = lead
        name_trunc = (b_name[:27] + "...") if len(b_name) > 30 else b_name
        print(f"[{tier}] Score: {score} | {name_trunc:<30} | {cat}")

HIGH_VALUE_CATS = [
    "restaurante-bar", "horchateria-cafeteria",
    "peluqueria-barberia", "clinica-fisio"
]
MED_VALUE_CATS = [
    "taller-mecanico", "academia",
    "tienda-alimentacion", "reformas-servicios"
]

def rule_score(lead: dict) -> int:
    """
    Scoring determinista por reglas. Max 60 puntos.
    Acepta dict con keys: phone, rating, review_count,
    category, language, email
    """
    score = 0
    if lead.get("phone"):                      score += 10
    if lead.get("rating", 0) >= 4.0:           score += 15
    if lead.get("review_count", 0) >= 20:      score += 10
    if lead.get("review_count", 0) >= 50:      score +=  5
    cat = lead.get("category", "")
    if cat in HIGH_VALUE_CATS:                 score += 20
    elif cat in MED_VALUE_CATS:               score += 12
    if lead.get("language") == "val":          score +=  5
    if lead.get("email"):                      score +=  8
    return min(score, 60)