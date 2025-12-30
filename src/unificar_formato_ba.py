import os
from bs4 import BeautifulSoup

# Carpeta base del repo (src/)
BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "..", "data")
BA_DIR = os.path.join(DATA_DIR, "buenos_aires")

def transformar_archivo(path: str) -> None:
    with open(path, "r", encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")

    # Recorro todas las cards de ofertas
    for card in soup.select("article.box_offer"):
        h2 = card.find("h2")
        if not h2:
            continue

        # Si YA tiene la clase fs18 (formato Córdoba), no lo toco
        if "fs18" in (h2.get("class") or []):
            continue

        # Me guardo la descripción scrapeada para volver a ponerla al final
        desc_div = card.find("div", class_="descripcion_scrapeada")
        if desc_div:
            desc_div.extract()  # la saco del DOM temporalmente

        # Sólo los <p> directos del article (no los de la descripción)
        p_children = [p for p in card.find_all("p", recursive=False)]

        company = p_children[0].get_text(strip=True) if len(p_children) >= 1 else ""
        extra   = p_children[1].get_text(strip=True) if len(p_children) >= 2 else ""

        # Link y título
        link_tag = card.find("a", href=True)
        href = link_tag["href"].strip() if link_tag else "#"
        title = h2.get_text(strip=True)

        # Limpio el artículo completo
        card.clear()

        # ----- Armo estructura tipo Córdoba -----

        # (1) Tira superior (puede ir vacía, sólo para mantener diseño)
        list_dot = soup.new_tag("div", attrs={"class": "list_dot mb15"})
        card.append(list_dot)

        # (2) Título con enlace y tags
        h2_new = soup.new_tag("h2", attrs={"class": "fs18 fwB prB"})
        a_new = soup.new_tag("a", attrs={"class": "js-o-link fc_base", "href": href})
        a_new.string = title
        h2_new.append(a_new)

        tags_div = soup.new_tag("div", attrs={"class": "tags"})
        span_post = soup.new_tag("span", attrs={"class": "tag postulated hide", "applied-offer-tag": ""})
        span_post.string = "Postulado"
        span_view = soup.new_tag("span", attrs={"class": "tag hide", "viewed-offer-tag": ""})
        span_view.string = "Vista"
        tags_div.append(span_post)
        tags_div.append(span_view)

        h2_new.append(tags_div)
        card.append(h2_new)

        # (3) Línea de empresa
        p_company = soup.new_tag("p", attrs={"class": "dFlex vm_fx fs16 fc_base mt5"})
        p_company.string = company
        card.append(p_company)

        # (4) Línea “extra” (ahí hoy tenés algo tipo “4,2 Dos Argentina”)
        p_extra = soup.new_tag("p", attrs={"class": "fs16 fc_base mt5"})
        span_ex = soup.new_tag("span", attrs={"class": "mr10"})
        span_ex.string = extra
        p_extra.append(span_ex)
        card.append(p_extra)

        # (5) Línea de fecha vacía (para respetar espacios)
        p_time = soup.new_tag("p", attrs={"class": "fs13 fc_aux mt15"})
        card.append(p_time)

        # (6) Contenedor de los tres puntitos (sin funcionalidad, sólo layout)
        opt_dots = soup.new_tag("div", attrs={"class": "opt_dots"})
        card.append(opt_dots)

        # (7) Vuelvo a poner la descripción oculta al final
        if desc_div:
            card.append(desc_div)

    # Guardo el archivo transformado
    with open(path, "w", encoding="utf-8") as f:
        f.write(str(soup))


def main():
    for fname in sorted(os.listdir(BA_DIR)):
        if not fname.startswith("buenos_aires_p") or not fname.endswith(".html"):
            continue

        full_path = os.path.join(BA_DIR, fname)
        print(f"Transformando {fname}...")
        transformar_archivo(full_path)

    print("✅ Listo: todas las páginas de Buenos Aires ahora usan el formato visual tipo Córdoba.")


if __name__ == "__main__":
    main()
