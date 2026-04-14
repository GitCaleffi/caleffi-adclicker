"""
Script per raccogliere cookies freschi da Google e salvarli in cookies.txt
"""

import json
import time
from pathlib import Path

import undetected_chromedriver as uc

OUTPUT_FILE = Path(__file__).parent / "cookies.txt"

print("=" * 60)
print("  RACCOLTA COOKIES DA GOOGLE")
print("=" * 60)
print()
print("Si aprirà Chrome su google.it")
print("HAI 90 SECONDI per:")
print("  1. Accettare i cookie di Google")
print("  2. Fare login con il tuo account Google (facoltativo ma consigliato)")
print("  3. Fare una ricerca qualsiasi per 'riscaldare' la sessione")
print()
print("I cookies verranno salvati automaticamente alla chiusura.")
print()

options = uc.ChromeOptions()
options.add_argument("--lang=it-IT")
options.add_argument("--no-first-run")
options.add_argument("--no-default-browser-check")

driver = uc.Chrome(options=options)

try:
    driver.get("https://www.google.it")
    print("Browser aperto! Hai 90 secondi...")
    print()

    for remaining in range(90, 0, -10):
        print(f"  Tempo rimanente: {remaining} secondi...")
        time.sleep(10)

    print()
    print("Raccolta cookies in corso...")

    all_cookies = driver.get_cookies()

    # Converti nel formato atteso da cookies.txt
    formatted = []
    for i, c in enumerate(all_cookies):
        formatted.append({
            "domain": c.get("domain", ".google.it"),
            "expirationDate": c.get("expiry", time.time() + 86400 * 365),
            "hostOnly": not c.get("domain", "").startswith("."),
            "httpOnly": c.get("httpOnly", False),
            "name": c.get("name", ""),
            "path": c.get("path", "/"),
            "sameSite": c.get("sameSite", "unspecified"),
            "secure": c.get("secure", False),
            "session": c.get("expiry") is None,
            "storeId": "0",
            "value": c.get("value", ""),
            "id": i + 1
        })

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(formatted, f, indent=4, ensure_ascii=False)

    print(f"✅ Salvati {len(formatted)} cookies in: {OUTPUT_FILE}")

except Exception as e:
    print(f"❌ Errore: {e}")

finally:
    driver.quit()
    print("Browser chiuso.")
