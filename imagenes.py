#!/usr/bin/env python3
"""
Mundo Motor — buscador de fotos para las piezas.

Orden de preferencia, y el motivo de cada uno:

  1. La biblioteca de medios de mundomotor.bike. Son fotos propias: sin
     licencia que resolver, sin atribución que arrastrar y coherentes con el
     medio. Siempre se mira aquí primero.
  2. Openverse (Flickr, Wikimedia y otros) filtrando por licencias de uso
     comercial. Es el respaldo cuando no hay nada propio. OJO: casi todas
     esas licencias EXIGEN atribución visible, así que la lámina llevará
     crédito obligatorio.

Regla editorial de Nicolás para fotos genéricas (cascos, trámites, taller):
**sin preferencia de marca**. Se descartan las fotos donde una marca sea el
sujeto o su logo domine la imagen. Este script avisa cuando detecta una marca
en el título, pero el juicio final es humano.

Uso:
    python imagenes.py casco
    python imagenes.py "kit de arrastre" --libres
"""

import json
import re
import sys
import urllib.parse
import urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
PROPIA = "https://mundomotor.bike/wp-json/wp/v2/media"
OPENVERSE = "https://api.openverse.org/v1/images/"

# Marcas del sector: si aparecen en el título de una foto que debería ser
# genérica, se avisa para que un humano decida.
MARCAS = [
    "agv", "shoei", "arai", "hjc", "ls2", "bell", "shark", "nolan", "mt helmets",
    "shaft", "ich", "yamaha", "honda", "suzuki", "kawasaki", "ktm", "bajaj",
    "akt", "hero", "tvs", "royal enfield", "ducati", "bmw", "harley", "aprilia",
    "benelli", "cfmoto", "voge", "victory", "vespa", "piaggio", "triumph",
]


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def pedir(url: str, cabeceras: dict = None):
    req = urllib.request.Request(url, headers=cabeceras or {"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.loads(r.read().decode("utf-8"))


def marca_detectada(texto: str):
    t = (texto or "").lower()
    return [m for m in MARCAS if re.search(rf"\b{re.escape(m)}\b", t)]


def biblioteca_propia(termino: str, limite: int = 12) -> list:
    q = urllib.parse.urlencode({
        "search": termino, "media_type": "image", "per_page": limite,
        "_fields": "id,source_url,alt_text,title,media_details",
    })
    try:
        datos = pedir(f"{PROPIA}?{q}")
    except Exception as e:
        print(f"  (no pude consultar la biblioteca propia: {e})")
        return []

    fotos = []
    for m in datos:
        md = m.get("media_details", {})
        ancho, alto = md.get("width", 0), md.get("height", 0)
        if ancho < 900:          # por debajo de eso se ve mal a 1080 px
            continue
        titulo = re.sub("<[^>]+>", "", m["title"]["rendered"])
        fotos.append({
            "url": m["source_url"],
            "titulo": titulo,
            "alt": m.get("alt_text") or titulo,
            "medidas": f"{ancho}x{alto}",
            "origen": "propia",
            "credito": None,                    # es nuestra: no lleva crédito
            "marcas": marca_detectada(titulo),
        })
    return fotos


def bancos_libres(termino: str, limite: int = 8) -> list:
    q = urllib.parse.urlencode({
        "q": termino, "license_type": "commercial",
        "page_size": limite, "mature": "false",
    })
    try:
        datos = pedir(f"{OPENVERSE}?{q}", {"User-Agent": "MundoMotor/1.0"})
    except Exception as e:
        print(f"  (no pude consultar Openverse: {e})")
        return []

    fotos = []
    for r in datos.get("results", []):
        titulo = r.get("title") or "(sin título)"
        autor = r.get("creator") or "autor desconocido"
        lic = f"{r.get('license', '').upper()} {r.get('license_version', '')}".strip()
        fotos.append({
            "url": r.get("url"),
            "titulo": titulo,
            "alt": titulo,
            "medidas": f"{r.get('width', '?')}x{r.get('height', '?')}",
            "origen": r.get("source", "openverse"),
            # Estas licencias obligan a citar autor y licencia en la pieza.
            "credito": f"{autor} / {lic}",
            "marcas": marca_detectada(titulo),
        })
    return fotos


def buscar(termino: str, incluir_libres: bool = False) -> list:
    fotos = biblioteca_propia(termino)
    if not fotos or incluir_libres:
        fotos += bancos_libres(termino)
    return fotos


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    termino = sys.argv[1]
    libres = "--libres" in sys.argv
    fotos = buscar(termino, libres)

    if not fotos:
        print(f"Sin resultados para '{termino}'.")
        return 1

    print(f"\n{len(fotos)} foto(s) para '{termino}':\n")
    for i, f in enumerate(fotos, 1):
        aviso = ""
        if f["marcas"]:
            aviso = f"   [OJO] marca en el titulo: {', '.join(f['marcas'])}"
        credito = f"   crédito obligatorio: {f['credito']}" if f["credito"] else ""
        print(f"{i:2}. [{f['origen']}] {f['medidas']}  {f['titulo'][:58]}{aviso}")
        print(f"    {f['url']}{credito}")
    print("\nLas fotos propias no necesitan crédito. Las de bancos libres, sí.")
    print("Para temas genéricos, descarta las que tengan una marca de protagonista.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
