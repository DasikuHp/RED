import sqlite3
c = sqlite3.connect('red.db')
cur = c.cursor()
cur.execute('SELECT name FROM sqlite_master WHERE type="table"')
print([r[0] for r in cur.fetchall()])
c.close()