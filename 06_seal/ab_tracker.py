import sys
sys.path.insert(0, r"E:\RED")
import sqlite3
import random
from loguru import logger

DB_PATH = r"E:\RED\red.db"

def _variant_scores(categoria: str) -> dict:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT c.variant,
               COUNT(*) AS total,
               AVG(CAST(c.opened AS FLOAT)) AS open_r,
               AVG(CAST(c.clicked AS FLOAT)) AS click_r,
               AVG(CAST(c.replied AS FLOAT)) AS reply_r
        FROM campaigns c
        JOIN leads l ON c.lead_id = l.id
        WHERE l.category = ? AND c.status = 'sent'
        GROUP BY c.variant
        HAVING COUNT(*) >= 10
    """, (categoria,))
    rows = c.fetchall()
    conn.close()
    
    scores = {}
    for row in rows:
        variant, total, o, cl, r = row
        o = o or 0.0
        cl = cl or 0.0
        r = r or 0.0
        score = (o * 0.5) + (cl * 0.3) + (r * 0.2)
        scores[variant] = {"score": score, "total": total}
    return scores

def get_variant(lead_id: int, categoria: str) -> str:
    scores = _variant_scores(categoria)
    
    if not scores:
        random.seed(lead_id)
        variant = random.choice(["A", "B"])
        logger.debug(f"Lead {lead_id} [{categoria}]: sin datos → variante aleatoria {variant}")
        return variant
    
    if len(scores) == 2:
        variant = max(scores, key=lambda v: scores[v]["score"])
        logger.debug(f"Lead {lead_id} [{categoria}]: variante ganadora {variant} (score={scores[variant]['score']:.3f})")
        return variant
    
    variant = list(scores.keys())[0]
    logger.debug(f"Lead {lead_id} [{categoria}]: solo variante disponible {variant}")
    return variant

def update_experiment(categoria: str, variant: str, sent: int = 0, opens: int = 0, clicks: int = 0, replies: int = 0):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM ab_experiments WHERE categoria=? AND variant=?", (categoria, variant))
    row = c.fetchone()
    
    if row:
        c.execute("""
            UPDATE ab_experiments SET
                total_sent = total_sent + ?,
                opens = opens + ?,
                clicks = clicks + ?,
                replies = replies + ?,
                updated_at = datetime('now')
            WHERE categoria=? AND variant=?
        """, (sent, opens, clicks, replies, categoria, variant))
    else:
        c.execute("""
            INSERT INTO ab_experiments(categoria, variant, total_sent, opens, clicks, replies)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (categoria, variant, sent, opens, clicks, replies))
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    test = get_variant(1, "restaurante-bar")
    print(f"Variante para lead 1, restaurante-bar: {test}")
    assert test in ["A", "B"]
    print("ab_tracker.py OK")
