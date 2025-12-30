import os
from bs4 import BeautifulSoup

BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "..", "data")

def es_link_oferta(href: str) -> bool:
    return href and "/ofertas-de-trabajo/oferta-de-trabajo-de-" in href

def procesar_archivo(path_html: str):
    with open(path_html, "r", encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")

    # buscamos todas las <a> que sean de oferta
    enlaces = [a for a in soup.find_all("a", href=True) if es_link_oferta(a["href"])]

    # para no procesar dos veces la misma card
    procesadas = set()

    for a in enlaces:
        # tarjeta contenedora
        card = a.find_parent("article") or a.find_parent("div")
        if not card:
            continue

        # evitamos repetir si ya tocamos esa card
        if id(card) in procesadas:
            continue
        procesadas.add(id(card))

        # ----------- sacar datos ----------- #
        titulo = a.get_text(strip=True)

        # empresa: alguna <a> distinta dentro de la card
        empresa = ""
        for link in card.find_all("a", href=True):
            if link is a:
                continue
            texto_link = link.get_text(strip=True)
            if texto_link:
                empresa = texto_link
                break

        # ubicación: primer span/p/div con coma
        ubicacion = ""
        for tag in card.find_all(["span", "p", "div"]):
            txt = tag.get_text(" ", strip=True)
            if "," in txt and len(txt) <= 80:
                ubicacion = txt
                break

        href_rel = a["href"].strip()

        # ----------- reemplazar contenido de la card ----------- #
        card.clear()  # vaciamos la tarjeta

        # armamos contenido simple
        h2 = soup.new_tag("h2")
        h2.string = titulo
        card.append(h2)

        if empresa:
            p_emp = soup.new_tag("p")
            p_emp.string = empresa
            card.append(p_emp)

        if ubicacion:
            p_ubi = soup.new_tag("p")
            p_ubi.string = ubicacion
            card.append(p_ubi)

        p_link = soup.new_tag("p")
        link_tag = soup.new_tag("a", href=href_rel)
        link_tag.string = "Ver oferta"
        p_link.append(link_tag)
        card.append(p_link)

    # guardar cambios
    with open(path_html, "w", encoding="utf-8") as f:
        f.write(str(soup))

    print(f"✅ Actualizado: {os.path.basename(path_html)}")


def main():
    for archivo in os.listdir(DATA_DIR):
        if archivo.startswith("buenos_aires_p") and archivo.endswith(".html"):
            ruta = os.path.join(DATA_DIR, archivo)
            procesar_archivo(ruta)

if __name__ == "__main__":
    main()
    print("\n🎉 Listo: se rellenaron todas las tarjetas en todas las páginas.")
