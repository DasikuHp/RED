import sys
sys.path.insert(0, r"E:\RED")

import sqlite3
import threading
import io
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.responses import Response, RedirectResponse
from PIL import Image
import uvicorn
from loguru import logger

from config import Config

DB_PATH = r"E:\RED\red.db"

app = FastAPI()


def get_transparent_gif() -> bytes:
    img = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_most_recent_campaign(lead_id: int):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "SELECT id FROM campaigns "
        "WHERE lead_id=? AND status='sent' "
        "ORDER BY sent_at DESC LIMIT 1",
        (lead_id,)
    )
    result = c.fetchone()
    conn.close()
    return result


@app.get("/px/{lead_id}.gif")
async def track_open(lead_id: int, request: Request):
    campaign = get_most_recent_campaign(lead_id)
    if not campaign:
        logger.warning(f"No campaign found for lead {lead_id}")
        return Response(content=get_transparent_gif(), media_type="image/png")

    campaign_id = campaign["id"]

    conn = get_db_connection()
    c = conn.cursor()
    
    # Update campaign opened status
    c.execute(
        "UPDATE campaigns SET opened=1, opened_at=datetime('now') WHERE id=?",
        (campaign_id,)
    )
    
    # Insert tracking event
    c.execute(
        "INSERT INTO tracking_events "
        "(campaign_id, lead_id, event_type, timestamp, ip_address, user_agent) "
        "VALUES (?, ?, 'open', datetime('now'), ?, ?)",
        (campaign_id, lead_id, request.client.host, request.headers.get("user-agent", ""))
    )
    
    conn.commit()
    conn.close()

    logger.info(f"Open tracked: lead {lead_id}")
    return Response(content=get_transparent_gif(), media_type="image/png")


@app.get("/click/{lead_id}")
async def track_click(lead_id: int, request: Request):
    campaign = get_most_recent_campaign(lead_id)
    if not campaign:
        logger.warning(f"No campaign found for lead {lead_id}")
        return RedirectResponse(url=Config.prototype_base_url)

    campaign_id = campaign["id"]

    conn = get_db_connection()
    c = conn.cursor()
    
    # Update campaign clicked status
    c.execute(
        "UPDATE campaigns SET clicked=1, clicked_at=datetime('now') WHERE id=?",
        (campaign_id,)
    )
    
    # Insert tracking event
    c.execute(
        "INSERT INTO tracking_events "
        "(campaign_id, lead_id, event_type, timestamp, ip_address, user_agent) "
        "VALUES (?, ?, 'click', datetime('now'), ?, ?)",
        (campaign_id, lead_id, request.client.host, request.headers.get("user-agent", ""))
    )
    
    # Get demo URL
    c.execute(
        "SELECT demo_url FROM prototipos "
        "WHERE lead_id=? ORDER BY generated_at DESC LIMIT 1",
        (lead_id,)
    )
    demo_result = c.fetchone()
    demo_url = demo_result["demo_url"] if demo_result else Config.prototype_base_url
    
    conn.commit()
    conn.close()

    logger.info(f"Click tracked: lead {lead_id}")
    return RedirectResponse(url=demo_url)


@app.get("/health")
async def health_check():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Count total leads
    c.execute("SELECT COUNT(*) as count FROM leads")
    total_leads = c.fetchone()["count"]
    
    # Count total opens
    c.execute("SELECT COUNT(*) as count FROM campaigns WHERE opened=1")
    total_opens = c.fetchone()["count"]
    
    # Count total clicks
    c.execute("SELECT COUNT(*) as count FROM campaigns WHERE clicked=1")
    total_clicks = c.fetchone()["count"]
    
    # Count total replies
    c.execute("SELECT COUNT(*) as count FROM campaigns WHERE replied=1")
    total_replies = c.fetchone()["count"]
    
    conn.close()

    return {
        "status": "ok",
        "total_leads": total_leads,
        "total_opens": total_opens,
        "total_clicks": total_clicks,
        "total_replies": total_replies
    }


def start_tracking_server() -> str:
    if Config.ngrok_enabled:
        from pyngrok import ngrok
        public_url = ngrok.connect(Config.tracking_port).public_url
        logger.info(f"Tracking public URL: {public_url}")
    else:
        public_url = f"http://localhost:{Config.tracking_port}"

    threading.Thread(
        target=uvicorn.run,
        args=(app,),
        kwargs={
            "host": "0.0.0.0",
            "port": Config.tracking_port,
            "log_level": "warning"
        },
        daemon=True
    ).start()

    logger.info("Tracking server started")
    return public_url
