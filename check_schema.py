import sqlite3

def check_table_schema(table_name):
    c = sqlite3.connect('red.db').cursor()
    c.execute(f'PRAGMA table_info({table_name})')
    cols = [r[1] for r in c.fetchall()]
    print(f'{table_name}: {cols}')
    c.close()

check_table_schema('leads')
check_table_schema('prototipos')
check_table_schema('campaigns')
check_table_schema('ab_experiments')
check_table_schema('seal_insights')
check_table_schema('tracking_events')