import sys
sys.path.insert(0, r"E:\RED")
sys.path.insert(0, r"E:\RED\06_seal")
import sqlite3, smtplib, hashlib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from loguru import logger
from config import Config
from email_gen import generate_email
import ab_tracker

DB_PATH = r"E:\RED\red.db"
NO_EMAIL_LOG = r"E:\RED\logs\no_email.log"

def send_email(lead_id: int) -> bool:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 1. Load lead from SQLite
    c.execute(
        "SELECT id, business_name, municipality, "
        "category, language, email, phone "
        "FROM leads WHERE id=?",
        (lead_id,)
    )
    row = c.fetchone()
    if not row:
        logger.error(f"Lead {lead_id} not found in database.")
        conn.close()
        return False
        
    lead = {
        "id": row[0],
        "business_name": row[1],
        "municipality": row[2],
        "category": row[3],
        "language": row[4],
        "email": row[5],
        "phone": row[6]
    }

    # 2. Check email exists
    if lead["email"] is None or lead["email"] == "":
        with open(NO_EMAIL_LOG, "a", encoding="utf-8") as f:
            f.write(
                f"{lead_id},"
                f"{lead['business_name']},"
                f"{lead['phone']}\n"
            )
        logger.warning(
            f"No email for lead {lead_id}, "
            f"logged to no_email.log"
        )
        conn.close()
        return False

    # 3. Get demo_url from prototipos table
    c.execute(
        "SELECT demo_url FROM prototipos "
        "WHERE lead_id=? ORDER BY generated_at "
        "DESC LIMIT 1",
        (lead_id,)
    )
    proto_row = c.fetchone()
    demo_url = proto_row[0] if proto_row else ""

    # 4. Get A/B variant
    variant = ab_tracker.get_variant(
        lead_id, lead["category"]
    )

    # 5. Generate email content
    email_data = generate_email(lead, variant, demo_url)

    # 6. Build MIME message
    msg = MIMEMultipart("alternative")
    msg["Subject"] = email_data["subject"]
    msg["From"] = Config.SMTP_USER
    msg["To"] = lead["email"]
    html_body = email_data["body"].replace(
        "\n", "<br>"
    )
    msg.attach(MIMEText(html_body, "html"))

    # 7. Send via SMTP
    try:
        with smtplib.SMTP(
            Config.SMTP_HOST, int(Config.SMTP_PORT)
        ) as server:
            server.starttls()
            server.login(Config.SMTP_USER, Config.SMTP_PASS)
            server.sendmail(
                Config.SMTP_USER,
                lead["email"],
                msg.as_string()
            )
    except Exception as e:
        logger.error(f"SMTP error for lead {lead_id}: {e}")
        conn.close()
        return False

    # 8. Record in campaigns table
    body_hash = hashlib.md5(
        email_data["body"].encode()
    ).hexdigest()
    c.execute(
        "INSERT INTO campaigns "
        "(lead_id, email_subject, email_body_hash, "
        "variant, sent_at, status, sequence_step) "
        "VALUES (?, ?, ?, ?, datetime('now'), 'sent', 0)",
        (lead_id, email_data["subject"],
         body_hash, variant)
    )

    # 9. Update lead status
    c.execute(
        "UPDATE leads SET status='contactado', "
        "updated_at=datetime('now') WHERE id=?",
        (lead_id,)
    )
    
    conn.commit()
    conn.close()

    # 10. Log success
    logger.info(
        f"Email sent to lead {lead_id} "
        f"({lead['business_name']}), variant {variant}"
    )
    return True
