import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import gspread
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials

def get_gsheet_client():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        os.environ["GOOGLE_SHEET_CREDS_JSON"],
        scope
    )
    return gspread.authorize(creds)

def get_urls_from_config(sheet_id):
    client = get_gsheet_client()
    sheet = client.open_by_key(sheet_id).worksheet("Config - URL")
    all_rows = sheet.get_all_values()
    rows = all_rows[1:]  # skip header

    urls_to_fetch = []
    for idx, row in enumerate(rows, start=2):
        product_id = row[0] if len(row) > 0 else ""
        url = row[1] if len(row) > 1 else ""
        flag = row[2] if len(row) > 2 else ""
        if url and flag.strip() == "1":
            urls_to_fetch.append((product_id, url))
        print(f"Řádek {idx}: id={product_id} | url={url} | fetch={flag}")

    print(f"Celkem vybráno {len(urls_to_fetch)} URL ke stažení.")
    return urls_to_fetch

def get_domain(url):
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    if domain.startswith("www."):
        domain = domain[4:]
    return domain

def parse_price_jedishop(html):
    m = re.search(r'<meta\s+itemprop="price"\s+content="([\d\.]+)"', html)
    if m:
        cena = m.group(1)
        if "." in cena:
            cena = cena.split(".")[0]
        return cena
    return "N/A"

def parse_price_svetkomiksu(html):
    m = re.search(r'<meta\s+property="product:price:amount"\s+content="([\d\.]+)"', html)
    if m:
        cena = m.group(1)
        if "." in cena:
            cena = cena.split(".")[0]
        return cena
    return "N/A"

def parse_price_fategate(html):
    m = re.search(r'<em>cena:</em>\s*<strong>([\d\s]+),?-&nbsp;Kč</strong>', html)
    if m:
        return m.group(1).replace(" ", "")
    return "N/A"

def parse_price_statue(html):
    m = re.search(r'<meta\s+itemprop="price"\s+content="([\d\.]+)"', html)
    if m:
        cena = m.group(1)
        if "." in cena:
            cena = cena.split(".")[0]
        return cena
    return "N/A"

def parse_price_figurkybrno(html):
    m = re.search(r'c2009.*?([\d\s]+),?- Kč</span>', html)
    if m:
        return m.group(1).replace(" ", "")
    return "N/A"

def parse_price_figures(html):
    m = re.search(r'white-space:nowrap;">([\d\s]+)K', html)
    if m:
        return m.group(1).replace(" ", "")
    return "N/A"

def fetch_price(url):
    try:
        resp = requests.get(url, timeout=15)
        html = resp.text
        domain = get_domain(url)
        if "jedishop.cz" in domain:
            price = parse_price_jedishop(html)
        elif "svetkomiksu.cz" in domain:
            price = parse_price_svetkomiksu(html)
        elif "fategate.com" in domain:
            price = parse_price_fategate(html)
        elif "statuecollectibles.cz" in domain:
            price = parse_price_statue(html)
        elif "figurky-brno.cz" in domain:
            price = parse_price_figurkybrno(html)
        elif "figures.cz" in domain:
            price = parse_price_figures(html)
        else:
            price = "N/A"
        return price, domain
    except Exception as e:
        return f"Error: {str(e)}", get_domain(url)

def write_prices_to_python_data(sheet_id, data):
    client = get_gsheet_client()
    try:
        sheet = client.open_by_key(sheet_id).worksheet("python-data")
    except Exception as e:
        print("Chyba při otevírání záložky 'python-data':", e)
        raise

    # Pokud je sheet prázdný, přidej hlavičku
    if len(sheet.get_all_values()) == 0:
        sheet.append_row(["Date", "URL", "Price", "Product ID", "Domain"])

    if data:
        sheet.append_rows(data)
        print(f"Přidáno {len(data)} řádků do záložky 'python-data'.")
    else:
        print("Nebyla nalezena žádná data ke zapsání.")

def main():
    print("== Spouštím price checker ==")
    SHEET_ID = os.environ["SOURCE_SHEET_ID"]  # pro čtení i zápis
    urls = get_urls_from_config(SHEET_ID)
    results = []
    now = datetime.now().strftime("%Y-%m-%d")
    for product_id, url in urls:
        price, domain = fetch_price(url)
        # Vynucený int nebo N/A
        try:
            price_int = int(float(price))
        except:
            price_int = "N/A"
        results.append([now, url, price_int, product_id, domain])
        print(f"{url} ➜ {price_int} (ID: {product_id}) | Domain: {domain}")
    write_prices_to_python_data(SHEET_ID, results)
    print("== Hotovo, zkontrolujte Google Sheet! ==")

if __name__ == "__main__":
    main()
