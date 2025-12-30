import os
import time
import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# ================== CONFIGURACIÓN ==================

BASE_URL = "https://ar.computrabajo.com"

BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "..", "data")
buenos_aires_DIR = os.path.join(DATA_DIR, "buenos_aires")
OFERTAS_DIR = os.path.join(DATA_DIR, "ofertas_detalle")

os.makedirs(OFERTAS_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-AR,es;q=0.9,en;q=0.8",
}

REQUEST_DELAY_SECONDS = 2.0  # tiempo entre requests al sitio
MAX_OFERTAS = None           # None = procesa TODOS los links encontrados
MAX_PAGES = 30                # 👈 máximo de páginas buenos_aires_pX.html a procesar


# ========== 1) SACAR LINKS DESDE TUS LISTADOS LOCALES ==========

def es_link_oferta(href: str) -> bool:
    return href and "/ofertas-de-trabajo/oferta-de-trabajo-de-" in href


def obtener_links_desde_listados() -> list[str]:
    """
    Recorre los buenos_aires_pX.html y devuelve una lista
    de links de ofertas únicos (sin el #lc=...).
    """
    urls: list[str] = []
    vistos = set()

    # 👉 armamos la lista de archivos y la cortamos en MAX_PAGES
    archivos_ba = [
        a for a in os.listdir(buenos_aires_DIR)
        if a.startswith("buenos_aires_p") and a.endswith(".html")
    ]
    archivos_ba = sorted(archivos_ba)[:MAX_PAGES]

    for archivo in archivos_ba:
        ruta = os.path.join(buenos_aires_DIR, archivo)
        print(f"📄 Leyendo {archivo}...")
        with open(ruta, "r", encoding="utf-8") as f:
            html = f.read()

        soup = BeautifulSoup(html, "html.parser")

        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if not es_link_oferta(href):
                continue

            href_base = href.split("#")[0]
            if href_base not in vistos:
                vistos.add(href_base)
                urls.append(href_base)

    print(f"✅ Encontradas {len(urls)} ofertas únicas en los listados.")
    return urls



# ========== 2) BAJAR DETALLE Y EXTRAER DESCRIPCIÓN (CON CACHÉ) ==========

def ruta_cache_para_href(href: str) -> str:
    nombre = re.sub(r"[^a-zA-Z0-9_]", "_", href) + ".html"
    return os.path.join(OFERTAS_DIR, nombre)


def descargar_html_detalle(href: str) -> str | None:
    """
    Devuelve el HTML de detalle de una oferta.
    - Si ya fue descargado, lo lee desde disco.
    - Si no, lo baja y lo guarda.
    """
    ruta_archivo = ruta_cache_para_href(href)

    if os.path.exists(ruta_archivo):
        print(f"📁 Usando caché local para {href}")
        with open(ruta_archivo, "r", encoding="utf-8") as f:
            return f.read()

    url = urljoin(BASE_URL, href)
    print(f"⬇️  Descargando detalle: {url}")
    try:
        resp = requests.get(url, headers=HEADERS, timeout=25)
    except requests.RequestException as e:
        print(f"   ❌ Error de red: {e}")
        return None

    if resp.status_code != 200:
        print(f"   ❌ HTTP {resp.status_code}, no guardo.")
        return None

    html = resp.text
    with open(ruta_archivo, "w", encoding="utf-8") as f:
        f.write(html)

    return html


def adivinar_div_descripcion(soup: BeautifulSoup):
    """
    Heurística: buscamos el <div> con más texto que parezca cuerpo de la oferta.
    Así evitamos tocar clases/ids del sitio.
    """
    candidatos = []

    for div in soup.find_all("div"):
        texto = div.get_text(" ", strip=True)
        if len(texto) < 300:
            continue
        tlow = texto.lower()
        if "cookies" in tlow or "política de privacidad" in tlow:
            continue
        candidatos.append((len(texto), div))

    if not candidatos:
        return None

    candidatos.sort(key=lambda x: x[0], reverse=True)
    return candidatos[0][1]


def extraer_descripcion(html_detalle: str) -> str:
    soup = BeautifulSoup(html_detalle, "html.parser")
    div_desc = adivinar_div_descripcion(soup)
    if not div_desc:
        return ""
    return div_desc.get_text("\n", strip=True)


def construir_diccionario_descripciones(links: list[str]) -> dict[str, str]:
    """
    Devuelve un dict {href_base: descripcion}.
    Si MAX_OFERTAS es None, procesa todos los links.
    """
    descripciones: dict[str, str] = {}

    links_a_procesar = links
    if MAX_OFERTAS is not None:
        links_a_procesar = links[:MAX_OFERTAS]

    total = len(links_a_procesar)
    for i, href in enumerate(links_a_procesar, start=1):
        print(f"\n[{i}/{total}] Procesando {href}...")
        html_detalle = descargar_html_detalle(href)
        if not html_detalle:
            continue

        desc = extraer_descripcion(html_detalle)
        if desc:
            print(f"   ✅ Descripción encontrada ({len(desc)} caracteres).")
        else:
            print("   ⚠ Sin descripción (heurística no encontró nada).")

        descripciones[href] = desc

        time.sleep(REQUEST_DELAY_SECONDS)

    return descripciones


# ========== 3) INYECTAR .descripcion_scrapeada + CSS + JS ==========

def limpiar_inyecciones_previas(soup: BeautifulSoup) -> None:
    """
    Limpia cosas que hayamos metido en pasadas anteriores:
    - <style> con data-custom-ofertas="1"
    - <script> con data-custom-ofertas="1"
    - div.aviso_sin_descripcion

    NO borra div.descripcion_scrapeada para poder detectar
    qué ofertas ya están procesadas y no reprocesarlas.
    """
    for style in soup.find_all("style", attrs={"data-custom-ofertas": True}):
        style.decompose()

    for script in soup.find_all("script", attrs={"data-custom-ofertas": True}):
        script.decompose()

    for aviso in soup.select("div.aviso_sin_descripcion"):
        aviso.decompose()


def agregar_css_personalizado(soup: BeautifulSoup) -> None:
    head = soup.head
    if not head:
        return

    css = """
.descripcion_scrapeada {
    display: none !important;
    font-weight: normal;
    line-height: 1.4;
    white-space: pre-line;
}

/* cartel rojo en la card de la izquierda cuando no hay descripción real */
.aviso_sin_descripcion {
    font-size: 12px;
    color: #b3261e;
    font-weight: bold;
    margin-bottom: 6px;
}

[data-offers-grid-loading-container] {
    display: none !important;
}
    """.strip()

    style_tag = soup.new_tag("style", attrs={"data-custom-ofertas": "1"})
    style_tag.string = css
    head.append(style_tag)


def agregar_script_personalizado(soup: BeautifulSoup) -> None:
    body = soup.body
    if not body:
        return

    # JS simplificado: solo arma párrafos y bullets.
    js = r"""
document.addEventListener('DOMContentLoaded', function () {

    const offers = document.querySelectorAll('.box_offer');
    const detailBox = document.querySelector('[data-offers-grid-box-detail]');
    if (!detailBox) return;

    const detailContainer = detailBox.querySelector('[data-offers-grid-detail-container]');
    if (!detailContainer) return;

    offers.forEach(offer => {
        offer.addEventListener('click', () => {

            // marcar oferta seleccionada en la lista
            document.querySelectorAll('.box_offer.sel').forEach(o => o.classList.remove('sel'));
            offer.classList.add('sel');

            const title   = (offer.querySelector('h2') || {}).innerText || '';
            const company = (offer.querySelector('p:nth-of-type(1)') || {}).innerText || '';
            const place   = (offer.querySelector('p:nth-of-type(2)') || {}).innerText || '';
            const descDiv = offer.querySelector('.descripcion_scrapeada');

            if (!descDiv) return;

            const lines = Array.from(descDiv.querySelectorAll('p'))
                .map(p => p.innerText.trim())
                .filter(p => p.length > 0);

            let html = "";

            lines.forEach(line => {
                // bullets con - o *
                if (/^\s*[-*]\s+/.test(line)) {
                    const txt = line.replace(/^\s*[-*]\s+/, "");
                    html += `<p style="margin:0 0 8px 0;">• ${txt}</p>`;
                } else {
                    // párrafo normal
                    html += `<p style="margin:0 0 10px 0;">${line}</p>`;
                }
            });

            detailContainer.classList.remove('hide');

            detailContainer.innerHTML = `
                <div class="box_border" style="padding:20px;">

                    <h1 class="fs22 fwB" style="margin-bottom:5px;">
                        ${title}
                    </h1>

                    <p class="fwB" style="margin:0;">${company}</p>
                    <p style="margin:0 0 15px 0;">${place}</p>

                    <div style="margin:15px 0;">
                        <button style="
                            background:#0D3878;
                            color:#fff;
                            padding:10px 20px;
                            border-radius:25px;
                            border:none;
                            font-weight:bold;
                            cursor:pointer;">
                            Postularme
                        </button>
                    </div>

                    <div style="font-size:15px; line-height:1.5;">
                        ${html}
                    </div>

                </div>
            `;
        });
    });

    // dispara la primera oferta al cargar
    if (offers.length > 0) {
        offers[0].click();
    }
});
    """.strip()

    script_tag = soup.new_tag("script", attrs={"data-custom-ofertas": "1"})
    script_tag.string = js
    body.append(script_tag)


def inyectar_descripciones_y_script(descripciones: dict[str, str]) -> None:
    """
    Para cada buenos_aires_pX.html:
    - Detecta cuántas ofertas ya están procesadas (tienen .descripcion_scrapeada)
      y cuántas no.
    - NO toca las ofertas ya procesadas.
    - Añade un div.descripcion_scrapeada solo a las ofertas que falten,
      usando el dict de descripciones (o descargando en el momento).
    - Añade el CSS y el script personalizados.
    """
    # 🔹 NUEVO: armar lista de archivos y cortarla en 30
    archivos_ba = [
        a for a in os.listdir(buenos_aires_DIR)
        if a.startswith("buenos_aires_p") and a.endswith(".html")
    ]
    archivos_ba = sorted(archivos_ba)[:30]   # 👈 acá está el límite a 30 páginas

    for archivo in archivos_ba:
        ruta = os.path.join(buenos_aires_DIR, archivo)
        print(f"\n🛠 Analizando {archivo}...")
        with open(ruta, "r", encoding="utf-8") as f:
            html = f.read()

        soup = BeautifulSoup(html, "html.parser")

        # Todas las cards de ofertas
        cards = soup.select("article.box_offer")

        total_cards = len(cards)
        ya_procesadas = 0
        pendientes = 0

        # Contar procesadas vs pendientes
        for card in cards:
            if card.select_one("div.descripcion_scrapeada"):
                ya_procesadas += 1
            else:
                pendientes += 1

        print(f"   👉 Ofertas totales: {total_cards}")
        print(f"   ✅ Ya procesadas : {ya_procesadas}")
        print(f"   ⏳ Pendientes     : {pendientes}")

        # Limpiar SOLO CSS/JS viejo y avisos, no las descripciones
        limpiar_inyecciones_previas(soup)

        # Procesar solo las ofertas pendientes
        for card in cards:
            # si ya tiene descripcion_scrapeada, la dejamos como está
            if card.select_one("div.descripcion_scrapeada"):
                continue

            link_tag = card.find("a", href=True)
            if not link_tag:
                continue

            href = link_tag["href"].strip().split("#")[0]

            # Intentamos obtener la descripción "real"
            desc = descripciones.get(href)
            placeholder = False

            if not desc:
                # si no la tenemos en el dict, la descargamos ahora
                html_detalle = descargar_html_detalle(href)
                if html_detalle:
                    desc = extraer_descripcion(html_detalle)
                    if desc:
                        descripciones[href] = desc

            # Si sigue sin descripción (ej: HTTP 404), usamos placeholder
            if not desc:
                placeholder = True
                desc = (
                    "Descripción no disponible. "
                    "Esta oferta ya no existe en el sitio original de Computrabajo."
                )

            desc = desc.strip()
            if not desc:
                # caso ultra extremo, no hacemos nada
                continue

            # crear el contenedor de descripción
            desc_div = soup.new_tag("div", attrs={"class": "descripcion_scrapeada"})

            # separar en párrafos por líneas en blanco
            paragraphs = re.split(r"\n\s*\n+", desc)
            if not paragraphs:
                paragraphs = [desc]

            for par in paragraphs:
                par = par.strip()
                if not par:
                    continue
                p_tag = soup.new_tag("p")
                p_tag.string = par
                desc_div.append(p_tag)

            # si es placeholder, agregamos también un cartel en la card de la izquierda
            if placeholder:
                aviso_div = soup.new_tag("div", attrs={"class": "aviso_sin_descripcion"})
                aviso_div.string = "Esta oferta ya no tiene descripción disponible (detalle 404)."
                card.insert(0, aviso_div)

            # lo agregamos al final de la card
            card.append(desc_div)

        # CSS y JS personalizados (se aplican igual para todo el archivo)
        agregar_css_personalizado(soup)
        agregar_script_personalizado(soup)

        # guardar cambios
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(str(soup))

        print("   ✅ Archivo actualizado con CSS/JS nuevos y ofertas pendientes completadas.")

# ========== MAIN ==========

def main():
    print("1️⃣ Buscando links de ofertas en tus páginas locales...")
    links = obtener_links_desde_listados()

    print("\n2️⃣ Descargando y extrayendo descripciones (todas las ofertas únicas)...")
    descripciones = construir_diccionario_descripciones(links)

    print("\n3️⃣ Inyectando descripciones, CSS y JS en cada buenos_aires_pX.html...")
    inyectar_descripciones_y_script(descripciones)

    print("\n🎉 Listo. Revisá tus archivos buenos_aires_pX.html en la carpeta data/.")


if __name__ == "__main__":
    main()
