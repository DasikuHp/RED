import sys
sys.path.insert(0, r"E:\RED")
import sqlite3
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from loguru import logger
from config import Config

DB_PATH = r"E:\RED\red.db"

db_path_forward = DB_PATH.replace("\\", "/")
jobstore_url = f"sqlite:///{db_path_forward}"

jobstores = {
    "default": SQLAlchemyJobStore(url=jobstore_url)
}
scheduler = BackgroundScheduler(jobstores=jobstores)


def check_and_resend(lead_id: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("SELECT id, business_name, municipality, category, language, email, phone FROM leads WHERE id=?", (lead_id,))
    lead_row = c.fetchone()
    
    if not lead_row:
        logger.error(f"check_and_resend: Lead {lead_id} not found.")
        conn.close()
        return

    lead = {
        "id": lead_row[0],
        "business_name": lead_row[1],
        "municipality": lead_row[2],
        "category": lead_row[3],
        "language": lead_row[4],
        "email": lead_row[5],
        "phone": lead_row[6]
    }
    
    c.execute("SELECT status FROM campaigns WHERE lead_id=? ORDER BY sent_at DESC LIMIT 1", (lead_id,))
    campaign_row = c.fetchone()
    
    if campaign_row and campaign_row[0] == 'opened':
        logger.info(f"Lead {lead_id} already opened email, no resend needed.")
        conn.close()
        return

    subject = f"{lead['business_name']} — su web ya esta lista"
    logger.info(f"Resending email to lead {lead_id} with subject: {subject}")
    
    c.execute("SELECT demo_url FROM prototipos WHERE lead_id=? ORDER BY generated_at DESC LIMIT 1", (lead_id,))
    proto_row = c.fetchone()
    demo_url = proto_row[0] if proto_row else ""

    sys.path.insert(0, r"E:\RED\06_seal")
    import ab_tracker
    from email_gen import generate_email
    import smtplib
    import hashlib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    variant = ab_tracker.get_variant(lead_id, lead["category"])
    email_data = generate_email(lead, variant, demo_url)
    
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = Config.SMTP_USER
    msg["To"] = lead["email"]
    
    html_body = email_data["body"].replace("\n", "<br>")
    msg.attach(MIMEText(html_body, "html"))
    
    try:
        with smtplib.SMTP(Config.SMTP_HOST, int(Config.SMTP_PORT)) as server:
            server.starttls()
            server.login(Config.SMTP_USER, Config.SMTP_PASS)
            server.sendmail(Config.SMTP_USER, lead["email"], msg.as_string())
    except Exception as e:
        logger.error(f"SMTP error resending for lead {lead_id}: {e}")
        conn.close()
        return

    body_hash = hashlib.md5(html_body.encode()).hexdigest()
    c.execute(
        "INSERT INTO campaigns (lead_id, email_subject, email_body_hash, variant, sent_at, status, sequence_step) "
        "VALUES (?, ?, ?, ?, datetime('now'), 'sent', 1)",
        (lead_id, subject, body_hash, variant)
    )
    
    conn.commit()
    conn.close()


def log_pending_whatsapp(lead_id: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT business_name, phone FROM leads WHERE id=?", (lead_id,))
    row = c.fetchone()
    conn.close()
    
    if not row:
        logger.error(f"log_pending_whatsapp: Lead {lead_id} not found.")
        return
        
    business_name = row[0]
    phone = row[1]
    
    log_path = r"E:\RED\logs\pending_social.log"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"PENDING_WHATSAPP: {lead_id},{phone},{business_name}\n")
        
    logger.info(f"WhatsApp fallback logged: {lead_id}")


def archive_cold_lead(lead_id: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE leads SET status='frio' WHERE id=?", (lead_id,))
    conn.commit()
    conn.close()
    
    logger.info(f"Lead {lead_id} archived as cold")
    
    try:
        sys.path.insert(0, r"E:\RED\02_knowledge")
        import obsidian_bridge
        if hasattr(obsidian_bridge, 'mover_lead'):
            obsidian_bridge.mover_lead(lead_id)
    except Exception as e:
        logger.debug(f"obsidian_bridge.mover_lead not called: {e}")


def schedule_followup_sequence(lead_id: int):
    scheduler.add_job(
        check_and_resend,
        "date",
        run_date=datetime.now() + timedelta(days=3),
        args=[lead_id],
        id=f"resend_{lead_id}",
        replace_existing=True
    )

    scheduler.add_job(
        log_pending_whatsapp,
        "date",
        run_date=datetime.now() + timedelta(days=5),
        args=[lead_id],
        id=f"whatsapp_{lead_id}",
        replace_existing=True
    )

    scheduler.add_job(
        archive_cold_lead,
        "date",
        run_date=datetime.now() + timedelta(days=10),
        args=[lead_id],
        id=f"archive_{lead_id}",
        replace_existing=True
    )

    logger.info(f"Follow-up sequence scheduled: lead {lead_id}")


def start_scheduler():
    scheduler.start()
    logger.info("APScheduler started, pending jobs restored")
