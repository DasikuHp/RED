import sqlite3

def recreate_all_tables():
    conn = sqlite3.connect('red.db')
    c = conn.cursor()
    
    # Drop all tables in proper order to respect foreign keys
    for table in ['seal_insights', 'tracking_events', 'ab_experiments', 'campaigns', 'prototipos', 'leads']:
        try:
            c.execute(f'DROP TABLE IF EXISTS {table}')
            print(f'Dropped {table}')
        except Exception as e:
            print(f'Error dropping {table}: {e}')
    
    # Recreate leads table
    c.execute('''CREATE TABLE leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        business_name TEXT,
        address TEXT,
        municipality TEXT,
        phone TEXT,
        google_maps_url TEXT,
        listed_website TEXT,
        website_status TEXT,
        category TEXT,
        rating REAL,
        review_count INTEGER,
        opening_hours TEXT,
        score INTEGER,
        tier TEXT,
        language TEXT,
        status TEXT DEFAULT "sin_verificar",
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    print('Created leads table')

    # Recreate prototipos table
    c.execute('''CREATE TABLE prototipos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lead_id INTEGER,
        version INTEGER DEFAULT 1,
        html_path TEXT,
        demo_url TEXT,
        generated_at DATETIME,
        deployed_at DATETIME,
        visited INTEGER DEFAULT 0,
        visit_count INTEGER DEFAULT 0,
        FOREIGN KEY (lead_id) REFERENCES leads(id)
    )''')
    print('Created prototipos table')

    # Recreate campaigns table
    c.execute('''CREATE TABLE campaigns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lead_id INTEGER,
        email_subject TEXT,
        email_body_hash TEXT,
        variant TEXT,
        sent_at DATETIME,
        message_id TEXT,
        sequence_step INTEGER,
        opened INTEGER DEFAULT 0,
        opened_at DATETIME,
        clicked INTEGER DEFAULT 0,
        clicked_at DATETIME,
        replied INTEGER DEFAULT 0,
        replied_at DATETIME,
        status TEXT DEFAULT "pending",
        FOREIGN KEY (lead_id) REFERENCES leads(id)
    )''')
    print('Created campaigns table')

    # Recreate tracking_events table
    c.execute('''CREATE TABLE tracking_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        campaign_id INTEGER,
        lead_id INTEGER,
        event_type TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        ip_address TEXT,
        user_agent TEXT,
        FOREIGN KEY (campaign_id) REFERENCES campaigns(id),
        FOREIGN KEY (lead_id) REFERENCES leads(id)
    )''')
    print('Created tracking_events table')

    # Recreate ab_experiments table
    c.execute('''CREATE TABLE ab_experiments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        categoria TEXT,
        template_version TEXT,
        variant TEXT,
        total_sent INTEGER DEFAULT 0,
        opens INTEGER DEFAULT 0,
        clicks INTEGER DEFAULT 0,
        replies INTEGER DEFAULT 0,
        conversions INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    print('Created ab_experiments table')

    # Recreate seal_insights table
    c.execute('''CREATE TABLE seal_insights (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_date DATE,
        segment_type TEXT,
        segment_value TEXT,
        metric_name TEXT,
        metric_value REAL,
        suggestion TEXT,
        applied INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    print('Created seal_insights table')

    # Version table
    c.execute('CREATE TABLE IF NOT EXISTS version (version INTEGER NOT NULL)')
    c.execute('INSERT OR IGNORE INTO version (version) VALUES (1)')
    print('Created version table')

    conn.commit()
    conn.close()
    print('All tables recreated successfully')

if __name__ == '__main__':
    recreate_all_tables()