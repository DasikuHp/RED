import sys
sys.path.insert(0, r"E:\RED")
import sqlite3
import random
from datetime import date, datetime
from loguru import logger
from config import Config

DB_PATH = r"E:\RED\red.db"

def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def _query_performance() -> list:
    conn = _get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT l.category AS categoria,
               c.variant,
               COUNT(*) AS total,
               ROUND(AVG(CAST(c.opened AS FLOAT)), 3) AS open_rate,
               ROUND(AVG(CAST(c.clicked AS FLOAT)), 3) AS click_rate,
               ROUND(AVG(CAST(c.replied AS FLOAT)), 3) AS reply_rate
        FROM campaigns c
        JOIN leads l ON c.lead_id = l.id
        WHERE c.status = 'sent'
        GROUP BY l.category, c.variant
        HAVING COUNT(*) >= 5
    """)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def _llm_suggestion(categoria: str, open_rate: float, reply_rate: float) -> str:
    try:
        from openai import OpenAI
        client = OpenAI(base_url=Config.llm_base_url, api_key="local")
        prompt = (f"Eres experto en email marketing para negocios "
                  f"locales en Valencia, España.\n"
                  f"Categoría: {categoria}\n"
                  f"Tasa apertura actual: {open_rate:.0%}\n"
                  f"Tasa respuesta actual: {reply_rate:.0%}\n"
                  f"El rendimiento es bajo. Genera UN asunto de email "
                  f"mejorado (máx 60 caracteres) para captar la atención "
                  f"del dueño de un negocio sin web.\n"
                  f"Responde SOLO con el asunto, sin comillas ni explicación.")
        resp = client.chat.completions.create(model=Config.llm_model,
                                              messages=[{"role": "user", "content": prompt}],
                                              max_tokens=80, temperature=0.7)
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.warning(f"LLM suggestion fallback: {e}")
        return f"Su negocio merece una web profesional — RBN Informática"

def _save_insight(categoria: str, metric: str, value: float, suggestion: str):
    conn = _get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO seal_insights(run_date, segment_type, segment_value,
                                  metric_name, metric_value, suggestion, applied)
        VALUES (?, 'category', ?, ?, ?, ?, 0)
    """, (date.today().isoformat(), categoria, metric, value, suggestion))
    conn.commit()
    conn.close()

def _write_report(today: str, stats: dict, low_performers: list, suggestions: list) -> str:
    lines = [
        f"# SEAL Report — {today}\n",
        "## Resumen\n",
        f"- Campañas analizadas: {stats.get('total', 0)}",
        f"- Bajo rendimiento (<20% apertura): {stats.get('low_performers', 0)}",
        f"- Sugerencias generadas: {len(suggestions)}\n",
        "## Bajo rendimiento\n",
    ]
    for lp in low_performers:
        lines.append(f"- **{lp['categoria']}** variante {lp['variant']}: "
                     f"apertura {lp['open_rate']:.0%}, respuesta {lp['reply_rate']:.0%}")
    lines.append("\n## Sugerencias de mejora\n")
    for s in suggestions:
        lines.append(f"- [{s['categoria']}] Nuevo asunto: *{s['suggestion']}*")
    return "\n".join(lines)

def run_seal_cycle() -> dict:
    today = date.today().isoformat()
    logger.info(f"SEAL cycle iniciado: {today}")
    
    # FASE 1 — Análisis
    performance = _query_performance()
    low_performers = [r for r in performance if r["open_rate"] < 0.20]
    logger.info(f"Analizados: {len(performance)}, bajo rendimiento: {len(low_performers)}")
    
    # FASE 2 — Mejoras
    suggestions = []
    for lp in low_performers:
        suggestion = _llm_suggestion(lp["categoria"], lp["open_rate"], lp["reply_rate"])
        _save_insight(lp["categoria"], "open_rate", lp["open_rate"], suggestion)
        suggestions.append({"categoria": lp["categoria"], "suggestion": suggestion})
        logger.info(f"Sugerencia [{lp['categoria']}]: {suggestion}")
    
    # FASE 3 — Reporte
    stats = {"total": len(performance), "low_performers": len(low_performers)}
    report = _write_report(today, stats, low_performers, suggestions)
    written = False
    
    try:
        sys.path.insert(0, r"E:\RED")
        from obsidian_bridge import escribir_seal_log
        escribir_seal_log(today, report)
        report_path = f"04_seal_logs/seal_{today}.md"
        written = True
        logger.info(f"Reporte Obsidian: {report_path}")
    except Exception as e:
        logger.warning(f"Obsidian no disponible: {e}")
    
    if not written:
        import os
        os.makedirs(r"E:\RED\logs", exist_ok=True)
        report_path = rf"E:\RED\logs\seal_{today}.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        logger.info(f"Reporte local: {report_path}")
    
    return {
        "run_date": today,
        "analyzed_campaigns": len(performance),
        "low_performers": len(low_performers),
        "suggestions_generated": len(suggestions),
        "report_path": report_path,
        "summary_stats": stats
    }

if __name__ == "__main__":
    result = run_seal_cycle()
    print(f"SEAL completado: {result}")
