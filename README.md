# Ad Clicker – Caleffi Custom Build

Strumento di automazione per il clic su annunci Google, basato su [undetected_chromedriver](https://github.com/ultrafunkamsterdam/undetected-chromedriver). Supporta proxy residenziali con autenticazione, pool persistente di browser indipendenti, riduzione del consumo di banda e rilevamento della soppressione degli annunci da parte di Google.

---

## Requisiti

* Python 3.9 – 3.11
* Chrome (versione più recente)
* Proxy residenziali HTTP(S) con autenticazione `username:password@host:port`

---

## Setup

```bash
python -m venv env
source env/bin/activate          # Linux/Mac
env\Scripts\activate             # Windows
python -m pip install -r requirements.txt
```

Prima del primo avvio reale, eseguire una volta:
```bash
python ad_clicker.py -q test
```
Chiudere con CTRL+C dopo che il browser si apre.

---

## Avvio

| Comando | Descrizione |
|---|---|
| `python run_in_loop.py` | **Avvio principale** – lancia il pool persistente e lo riavvia se termina inaspettatamente |
| `python run_ad_clicker.py` | Avvia N browser in parallelo (singola tornata) |
| `python ad_clicker.py` | Singolo browser, singola esecuzione |
| `python ad_clicker.py --report_clicks` | Report clic del giorno corrente |
| `python ad_clicker.py --report_clicks --date 17-04-2026` | Report per data specifica (formato DD-MM-YYYY) |
| `python ad_clicker.py --report_clicks --excel` | Report con esportazione Excel |

---

## Architettura del pool persistente

Con `multiprocess_style=1` ogni browser gira in un thread indipendente (non in un ProcessPoolExecutor). Ciò significa:

- Ogni browser riavvia la propria sessione non appena termina, senza aspettare gli altri
- Il `loop_wait_time` (secondi di pausa tra una sessione e la successiva) è per-browser
- `run_in_loop.py` monitora `run_ad_clicker.py` e lo riavvia se crasha
- L'intervallo orario (`running_interval_start` / `running_interval_end`) è gestito dentro `run_ad_clicker.py`

---

## Logica di clic – click_order 6

Con `click_order=6` ogni sessione punta a **6 clic totali** su annunci:

1. Vengono cliccati immediatamente gli annunci Shopping in cima alla pagina (fino a 5)
2. Vengono cliccati gli annunci di testo trovati nella ricerca iniziale
3. Se il totale è ancora sotto 6, si apre una nuova scheda con una query diversa e si ripete
4. Condizioni di stop anticipato:
   - `MAX_TAB_RETRIES = 3` – massimo 3 nuove schede aggiuntive per sessione
   - `MAX_CONSECUTIVE_MISS = 2` – se 2 ricerche consecutive restituiscono 0 annunci, la sessione viene tagliata ("Google sta sopprimendo gli annunci")

---

## Riduzione del consumo di banda

Flag Chrome aggiuntivi attivi per default:

| Flag / Impostazione | Risparmio stimato |
|---|---|
| `--disable-background-networking` | ~270 MB/giorno |
| `--disable-sync` | riduce traffico account Google |
| `--disable-component-update` | elimina download aggiornamenti componenti |
| `--no-pings` | elimina ping di navigazione |
| `MediaRouter`, `Prerender2` disabilitati | riduce connessioni inutili |
| `safebrowsing.enabled = false` | elimina chiamate a safebrowsing.googleapis.com (~169 MB/giorno) |
| Immagini bloccate (`managed_default_content_settings.images = 2`) | risparmio significativo su proxy residenziali |

---

## Proxy con tunnel locale (local_proxy.py)

Per proxy che richiedono autenticazione HTTPS (es. IPRoyal), `local_proxy.py` crea un tunnel locale `127.0.0.1:PORTA` verso il proxy remoto iniettando automaticamente l'header `Proxy-Authorization`. In questo modo Chrome non necessita di estensioni per l'autenticazione.

---

## Config (config.json)

```json
{
    "paths": {
        "query_file": "queries general.txt",
        "proxy_file": "proxies.txt",
        "user_agents": "user_agents.txt",
        "filtered_domains": "domains.txt"
    },
    "webdriver": {
        "proxy": "",
        "auth": true,
        "incognito": false,
        "country_domain": false,
        "language_from_proxy": true,
        "ss_on_exception": false,
        "window_size": "",
        "shift_windows": false,
        "use_seleniumbase": false
    },
    "behavior": {
        "query": "",
        "ad_page_min_wait": 10,
        "ad_page_max_wait": 15,
        "nonad_page_min_wait": 15,
        "nonad_page_max_wait": 20,
        "max_scroll_limit": 0,
        "check_shopping_ads": false,
        "excludes": "",
        "random_mouse": false,
        "custom_cookies": true,
        "click_order": 6,
        "browser_count": 7,
        "multiprocess_style": 1,
        "loop_wait_time": 5,
        "wait_factor": 1.0,
        "running_interval_start": "08:00",
        "running_interval_end": "23:59",
        "2captcha_apikey": "",
        "hooks_enabled": false,
        "telegram_enabled": false,
        "send_to_android": false,
        "request_boost": false
    }
}
```

### Parametri principali

* **query_file** – File con le query di ricerca (una per riga). Con `multiprocess_style=1` le query vengono mescolate e ogni browser usa una query diversa.
* **proxy_file** – File con i proxy (formato `user:pass@host:port`).
* **auth** – Proxy con autenticazione username/password.
* **check_shopping_ads** – Abilita il clic sugli annunci Shopping in cima alla pagina (fino a 5).
* **click_order** – Ordine di clic (vedere sezione dedicata sopra per il valore `6`).
* **browser_count** – Numero di browser in parallelo.
* **multiprocess_style** – `1` = query diversa per ogni browser (pool persistente); `2` = stessa query su tutti.
* **loop_wait_time** – Secondi di pausa tra una sessione e la successiva (per browser).
* **running_interval_start / running_interval_end** – Finestra oraria di attivita (formato HH:MM).
* **custom_cookies** – Usa i cookie personalizzati da `cookies.txt`.
* **wait_factor** – Moltiplicatore globale per tutti i tempi di attesa (0.5 = dimezza i tempi).
* **max_scroll_limit** – Numero massimo di scroll sulla pagina dei risultati (0 = fino in fondo).
* **excludes** – Parole chiave per escludere annunci (separate da virgola).
* **random_mouse** – Movimenti random del mouse sulle pagine.
* **2captcha_apikey** – Chiave API per la risoluzione automatica del captcha via 2captcha.
* **hooks_enabled** – Abilita hook personalizzati in `hooks.py`.
* **telegram_enabled** – Notifiche Telegram (configurare `TELEGRAM_TOKEN` come variabile d'ambiente).
* **request_boost** – Invia 10 richieste parallele con IP diversi ad ogni link cliccato.

---

## Report clic

I clic vengono salvati in `clicklogs.db` (SQLite). Colonne: `id`, `click_date` (DD-MM-YYYY), `click_time` (HH:MM:SS), `site_url`, `query`, `category`.

```bash
python ad_clicker.py --report_clicks
python ad_clicker.py --report_clicks --date 14-04-2026
python ad_clicker.py --report_clicks --excel
```

---

## Troubleshooting

### ValueError: max() arg is an empty sequence

1. Eliminare il file `.MULTI_BROWSERS_IN_USE` se esiste.
2. Eseguire `python ad_clicker.py -q test` e chiudere con CTRL+C.
3. Riprendere con `python run_in_loop.py`.

### Chrome version mismatch

Aggiornare Chrome all'ultima versione disponibile, quindi ripetere il punto 2 del troubleshooting precedente.

---

## Notifiche Telegram

1. Creare un bot con [BotFather](https://t.me/BotFather).
2. Impostare la variabile d'ambiente `TELEGRAM_TOKEN` con il token ricevuto.
3. Eseguire `python ad_clicker.py --enable_telegram`.
4. Aprire `https://t.me/<nome_bot>` e inviare `/start`.
5. Chiudere con CTRL+C.
