import os
from bs4 import BeautifulSoup

BASE_DIR = os.path.dirname(__file__)

# 👇 ACÁ ELEGÍS LA PROVINCIA
PROV_SLUG = "mendoza"   # ej: "cordoba", luego "mendoza", etc.

DATA_DIR = os.path.join(BASE_DIR, "..", "data", PROV_SLUG)


def limpiar_head_y_scripts(path_html: str):
    with open(path_html, "r", encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")

    head = soup.head
    if head:
        # 1) borrar TODOS los <script> del <head> (ctLytics, etc.)
        for s in head.find_all("script"):
            s.decompose()

        # 2) normalizar los <link> del head:
        for link in list(head.find_all("link")):
            href = (link.get("href") or "").strip()
            rel_list = link.get("rel") or []
            rel = " ".join(rel_list)

            # a) sacamos preconnect, canonical, googletagmanager
            if "preconnect" in rel:
                link.decompose()
                continue
            if "canonical" in rel:
                link.decompose()
                continue
            if "googletagmanager.com" in href:
                link.decompose()
                continue

            # b) fonts remotas -> apuntar a CSS local
            if "CTFont_xs.woff2" in href:
                link["href"] = "../CSS/CTFont_xs.woff2"
                # opcional: limpiar rel para imitar BA
                if "rel" in link.attrs:
                    del link.attrs["rel"]
            elif "ct_regular_font.woff2" in href:
                link["href"] = "../CSS/ct_regular_font.woff2"
                if "rel" in link.attrs:
                    del link.attrs["rel"]
            elif "ct_bold_font.woff2" in href:
                link["href"] = "../CSS/ct_bold_font.woff2"
                if "rel" in link.attrs:
                    del link.attrs["rel"]
            # favicon lo dejamos tal cual:
            # elif "favicon_ct.svg" in href: -> no tocamos

    # 3) borrar el script de webpush extra del body (si existe)
    for s in soup.find_all("script", src=True):
        src = (s.get("src") or "").strip()
        if "webpush.bundle.min.js" in src:
            s.decompose()

    # guardar
    with open(path_html, "w", encoding="utf-8") as f:
        f.write(str(soup))

    print(f"✅ Normalizado: {os.path.basename(path_html)}")


def main():
    if not os.path.isdir(DATA_DIR):
        print(f"❌ No existe la carpeta: {DATA_DIR}")
        return

    prefix = f"{PROV_SLUG}_p"

    archivos = [
        a for a in os.listdir(DATA_DIR)
        if a.startswith(prefix) and a.endswith(".html")
    ]
    archivos = sorted(archivos)

    if not archivos:
        print(f"⚠ No se encontraron archivos {prefix}*.html en {DATA_DIR}")
        return

    for archivo in archivos:
        ruta = os.path.join(DATA_DIR, archivo)
        limpiar_head_y_scripts(ruta)

    print("\n🎉 Listo. Todos los listados de", PROV_SLUG,
          "quedaron con el mismo tipo de limpieza que Buenos Aires.")


if __name__ == "__main__":
    main()
