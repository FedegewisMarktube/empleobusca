#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import math
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

# =========================
# CONFIG
# =========================
BASE_URL = "https://empleobusca.com/"  # sin "/" al final
ROOT_DIR = "."
MAX_URLS_PER_SITEMAP = 45000

EXCLUDE_DIRS = {".git", ".github", "node_modules", "dist", "build", "__pycache__", ".vscode"}
EXCLUDE_EXT = {
    ".css", ".js", ".map", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico",
    ".pdf", ".zip", ".gz", ".woff", ".woff2", ".ttf", ".eot", ".json", ".xml", ".txt"
}
EXCLUDE_CONTAINS = ["/tmp/", "/test/"]

# Si querés excluir secciones enteras:
# EXCLUDE_PREFIXES = ["admin/", "api/"]
EXCLUDE_PREFIXES = []

# =========================
# HELPERS
# =========================
def iso_date_from_mtime(filepath: Path) -> str:
    ts = filepath.stat().st_mtime
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")

def normalize_url(rel_path: str) -> str:
    return urljoin(BASE_URL.rstrip("/") + "/", rel_path.lstrip("/"))

def should_exclude(rel_path: Path) -> bool:
    if any(p in EXCLUDE_DIRS for p in rel_path.parts):
        return True
    if rel_path.suffix.lower() in EXCLUDE_EXT:
        return True
    s = str(rel_path).replace("\\", "/")
    if any(x in s for x in EXCLUDE_CONTAINS):
        return True
    return False

def rel_url_from_file(root: Path, file_path: Path) -> str:
    # Convierte archivos a URL "linda":
    # home/compras/index.html => home/compras
    # index.html => ""
    # algo.html => algo.html (si lo querés así; si no, lo adaptamos)
    rel = str(file_path.relative_to(root)).replace("\\", "/")

    rel_low = rel.lower()

    # Evitar sitemaps previos
    if rel_low.startswith("sitemap"):
        return None

    if rel_low.endswith("/index.html") or rel_low.endswith("\\index.html"):
        rel = rel[:-len("index.html")]
        rel = rel.rstrip("/")  # home/compras/
    elif rel_low == "index.html":
        rel = ""

    # Excluir por prefijo
    for pref in EXCLUDE_PREFIXES:
        if rel.startswith(pref):
            return None

    return rel

def collect_pages(root: Path) -> list[Path]:
    pages = []
    # Incluimos:
    # - index.html en carpetas
    # - .html sueltos (por si hay)
    for p in root.rglob("*.html"):
        rel = p.relative_to(root)
        if should_exclude(rel):
            continue
        pages.append(p)
    return sorted(pages)

def write_urlset(path: Path, urls: list[dict]):
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
        for u in urls:
            f.write("  <url>\n")
            f.write(f"    <loc>{u['loc']}</loc>\n")
            if u.get("lastmod"):
                f.write(f"    <lastmod>{u['lastmod']}</lastmod>\n")
            f.write("  </url>\n")
        f.write("</urlset>\n")

def write_index(path: Path, sitemap_files: list[str]):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
        for sm in sitemap_files:
            f.write("  <sitemap>\n")
            f.write(f"    <loc>{normalize_url(sm)}</loc>\n")
            f.write(f"    <lastmod>{today}</lastmod>\n")
            f.write("  </sitemap>\n")
        f.write("</sitemapindex>\n")

def main():
    root = Path(ROOT_DIR).resolve()
    files = collect_pages(root)

    urls = []
    for fp in files:
        rel = rel_url_from_file(root, fp)
        if rel is None:
            continue
        urls.append({
            "loc": normalize_url(rel),
            "lastmod": iso_date_from_mtime(fp),
        })

    # Deduplicar por si varias rutas apuntan igual
    seen = set()
    dedup = []
    for u in urls:
        if u["loc"] in seen:
            continue
        seen.add(u["loc"])
        dedup.append(u)

    total = len(dedup)
    if total == 0:
        print("❌ No se generaron URLs. Probá revisar la estructura del build.")
        return

    parts = math.ceil(total / MAX_URLS_PER_SITEMAP)

    if parts == 1:
        write_urlset(root / "sitemap_2.xml", dedup)
        print(f"✅ sitemap.xml generado ({total} URLs)")
    else:
        sitemap_files = []
        for i in range(parts):
            chunk = dedup[i * MAX_URLS_PER_SITEMAP:(i + 1) * MAX_URLS_PER_SITEMAP]
            name = f"sitemap-{i+1}.xml"
            write_urlset(root / name, chunk)
            sitemap_files.append(name)
            print(f"✅ {name} ({len(chunk)} URLs)")
        write_index(root / "sitemap_2.xml", sitemap_files)
        print("✅ sitemap.xml (index) generado")
    
SLUGS_FILE = "slugs.txt"  # opcional

def load_slugs(root: Path) -> list[str]:
    p = root / SLUGS_FILE
    if not p.exists():
        return []
    lines = []
    for line in p.read_text(encoding="utf-8").splitlines():
        s = line.strip().lstrip("/")
        if not s or s.startswith("#"):
            continue
        lines.append(s)
    return lines


if __name__ == "__main__":
    main()
