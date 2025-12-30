import os
import time
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

BASE_URL = "https://ar.computrabajo.com"
BA_LIST_URL = f"{BASE_URL}/empleos-en-buenos_aires"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-AR,es;q=0.9,en;q=0.8",
}

# base del repo
BASE_DIR = os.path.dirname(__file__)
HTML_DIR = os.path.join(BASE_DIR, "..", "data", "buenos_aires")

# 👇 lo dejo igual que vos: una carpeta CSS común
CSS_DIR = os.path.join(BASE_DIR, "..", "data", "CSS")


def ensure_dirs():
    os.makedirs(HTML_DIR, exist_ok=True)
    os.makedirs(CSS_DIR, exist_ok=True)


def get_html(url: str) -> str | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
    except requests.RequestException as e:
        print(f"[ERROR RED] {url}: {e}")
        return None

    if resp.status_code != 200:
        print(f"[ERROR HTTP {resp.status_code}] {url}")
        return None

    return resp.text


def save_html(content: str, filename: str) -> None:
    path = os.path.join(HTML_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[HTML] Guardado {path}")


def sanitize_filename(name: str) -> str:
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in name)


def download_css_from_html(html: str, page_url: str, downloaded: set) -> None:
    soup = BeautifulSoup(html, "html.parser")
    links = soup.find_all("link", rel="stylesheet")

    for link in links:
        href = link.get("href")
        if not href:
            continue

        css_url = urljoin(page_url, href)
        if css_url in downloaded:
            continue

        print(f"[CSS] Descargando {css_url}")
        try:
            r = requests.get(css_url, headers=HEADERS, timeout=20)
            if r.status_code != 200:
                print(f"   -> Error HTTP {r.status_code} en CSS")
                continue
        except requests.RequestException as e:
            print(f"   -> Error red CSS: {e}")
            continue

        parsed = urlparse(css_url)
        filename = sanitize_filename(os.path.basename(parsed.path) or "style.css")
        path = os.path.join(CSS_DIR, filename)

        with open(path, "wb") as f:
            f.write(r.content)
        print(f"   -> Guardado {path}")

        downloaded.add(css_url)


def scrape_home(downloaded_css: set) -> None:
    print("\n=== HOME ===")
    url = BASE_URL
    html = get_html(url)
    if not html:
        print("No se pudo descargar el home.")
        return

    save_html(html, "home.html")
    download_css_from_html(html, url, downloaded_css)


def scrape_buenos_aires_pages(downloaded_css: set, delay: float = 2.0, max_pages: int | None = None) -> None:
    print("\n=== PÁGINAS buenos_aires ===")
    page = 1

    while True:
        if max_pages is not None and page > max_pages:
            print("Max de páginas alcanzado, corto.")
            break

        url = f"{BA_LIST_URL}?p={page}"
        print(f"\n[PAGE] {page} -> {url}")
        html = get_html(url)
        if not html:
            print("No se pudo descargar la página, corto.")
            break

        save_html(html, f"buenos_aires_p{page}.html")
        download_css_from_html(html, url, downloaded_css)

        soup = BeautifulSoup(html, "html.parser")
        job_cards = soup.find_all("article")
        if not job_cards:
            print("No se encontraron más avisos (no hay <article>), corto.")
            break

        page += 1
        time.sleep(delay)


if __name__ == "__main__":
    ensure_dirs()
    downloaded_css = set()

    scrape_home(downloaded_css)
    scrape_buenos_aires_pages(downloaded_css, delay=2.0, max_pages=30)

    # ✅ CAMBIO: este print queda adentro del main
    print(f"\nListo. HTML en '{HTML_DIR}' y CSS en '{CSS_DIR}'.")
