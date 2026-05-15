import sqlite3
import datetime

con = sqlite3.connect("clicklogs.db")
cur = con.cursor()

today = datetime.date.today().strftime("%d-%m-%Y")
yesterday = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%d-%m-%Y")

def report(date_str, label):
    cur.execute("SELECT COUNT(*) FROM clicklogs WHERE click_date=?", (date_str,))
    total = cur.fetchone()[0]
    cur.execute("SELECT category, COUNT(*) FROM clicklogs WHERE click_date=? GROUP BY category ORDER BY COUNT(*) DESC", (date_str,))
    cats = cur.fetchall()
    cur.execute("SELECT COUNT(DISTINCT site_url) FROM clicklogs WHERE click_date=?", (date_str,))
    unique = cur.fetchone()[0]
    print(f"=== {label} ({date_str}) ===")
    print(f"  TOTALE: {total} | URL unici: {unique}")
    for cat, cnt in cats:
        print(f"  {cat}: {cnt}")
    print()
    return total, dict(cats), unique

t_oggi, cats_oggi, u_oggi = report(today, "OGGI")
t_ieri, cats_ieri, u_ieri = report(yesterday, "IERI")

print("=== DELTA ===")
delta = t_oggi - t_ieri
s = "+" if delta >= 0 else ""
print(f"  Totale: {t_ieri} -> {t_oggi}  ({s}{delta})")
for cat in sorted(set(cats_oggi) | set(cats_ieri)):
    a = cats_ieri.get(cat, 0)
    b = cats_oggi.get(cat, 0)
    d = b - a
    print(f"  {cat}: {a} -> {b}  ({'+' if d >= 0 else ''}{d})")
print(f"  URL unici: {u_ieri} -> {u_oggi}  ({'+' if (u_oggi-u_ieri) >= 0 else ''}{u_oggi-u_ieri})")

con.close()
