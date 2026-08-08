#!/usr/bin/env python3
"""
Mundo Motor — genera la galería pública de piezas.

Recorre docs/ y arma un index.html con todas las piezas publicadas: la portada
de cada carrusel, sus láminas y el copy con el que salió. Se regenera en cada
publicación, así que la página siempre refleja lo que hay.

Uso: python galeria.py
"""

import datetime as dt
import html
import json
import pathlib

BASE = pathlib.Path(__file__).parent
DOCS = BASE / "docs"
AMARILLO = "#FDC207"
NEGRO = "#0B0B0B"

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def historial() -> dict:
    f = BASE / "banco" / "historial.json"
    if not f.exists():
        return {}
    datos = json.loads(f.read_text(encoding="utf-8"))
    return {p["slug"]: p for p in datos.get("publicadas", [])}


def bonita(iso: str) -> str:
    try:
        d = dt.date.fromisoformat(iso)
        return f"{d.day} de {MESES[d.month - 1]} de {d.year}"
    except Exception:
        return iso


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def main():
    DOCS.mkdir(exist_ok=True)
    hist = historial()
    piezas = []

    for carpeta in sorted(DOCS.iterdir()):
        if not carpeta.is_dir():
            continue
        laminas = sorted(carpeta.glob("[0-9][0-9].png"))
        if not laminas:
            continue
        slug = carpeta.name
        datos = {"slug": slug, "laminas": [l.name for l in laminas]}
        paq = carpeta / "paquete.json"
        if paq.exists():
            try:
                p = json.loads(paq.read_text(encoding="utf-8"))
                datos["caption"] = p.get("caption", "")
                datos["origen"] = p.get("origen", "")
                datos["alts"] = {i["archivo"]: i.get("alt", "")
                                 for i in p.get("imagenes", [])}
            except json.JSONDecodeError:
                pass
        h = hist.get(slug, {})
        datos["fecha"] = h.get("fecha", "")
        datos["origen"] = datos.get("origen") or h.get("origen", "")
        piezas.append(datos)

    piezas.sort(key=lambda p: p.get("fecha", ""), reverse=True)

    tarjetas = []
    for p in piezas:
        titulo = p["slug"].replace("-", " ").capitalize()
        fecha = f'<span class="fecha">Publicada el {bonita(p["fecha"])}</span>' if p.get("fecha") else \
                '<span class="fecha pendiente">En el banco, sin publicar</span>'
        origen = (f'<a class="origen" href="{esc(p["origen"])}" target="_blank" '
                  f'rel="noopener">Ver el artículo →</a>') if p.get("origen") else ""
        caption = (f'<details><summary>Ver el copy con el que salió</summary>'
                   f'<pre>{esc(p["caption"])}</pre></details>') if p.get("caption") else ""
        alts = p.get("alts", {})
        minis = "".join(
            f'<a href="{p["slug"]}/{l}" target="_blank" rel="noopener">'
            f'<img loading="lazy" src="{p["slug"]}/{l}" '
            f'alt="{esc(alts.get(l, "Lámina " + l[:2]))}"></a>'
            for l in p["laminas"]
        )
        tarjetas.append(f"""
    <article class="pieza">
      <header>
        <h2>{esc(titulo)}</h2>
        <div class="meta">{fecha}<span class="cuenta">{len(p["laminas"])} láminas</span>{origen}</div>
      </header>
      <div class="tira">{minis}</div>
      {caption}
    </article>""")

    total_laminas = sum(len(p["laminas"]) for p in piezas)
    publicadas = sum(1 for p in piezas if p.get("fecha"))

    doc = f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>Mundo Motor — piezas de Instagram</title>
<style>
 *{{margin:0;padding:0;box-sizing:border-box}}
 body{{background:{NEGRO};color:#fff;
   font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif;
   padding:0 20px 80px}}
 .barra{{height:8px;background:{AMARILLO};margin:0 -20px 48px}}
 header.top{{max-width:1100px;margin:0 auto 44px}}
 h1{{font-size:2rem;letter-spacing:-.02em}}
 h1 span{{color:{AMARILLO}}}
 .sub{{color:#9a9a9a;margin-top:8px}}
 main{{max-width:1100px;margin:0 auto;display:flex;flex-direction:column;gap:44px}}
 .pieza{{background:#141414;border:1px solid #242424;border-radius:12px;padding:24px}}
 .pieza h2{{font-size:1.25rem;text-transform:capitalize}}
 .meta{{display:flex;flex-wrap:wrap;gap:8px 18px;align-items:center;
   margin:8px 0 20px;font-size:.87rem;color:#8f8f8f}}
 .fecha{{color:{AMARILLO}}}
 .fecha.pendiente{{color:#8f8f8f}}
 .cuenta::before{{content:"·";margin-right:18px;color:#3a3a3a}}
 .origen{{color:#7fb2ff;text-decoration:none}}
 .origen:hover{{text-decoration:underline}}
 .tira{{display:flex;gap:12px;overflow-x:auto;padding-bottom:10px;
   scroll-snap-type:x mandatory}}
 .tira img{{height:300px;width:auto;border-radius:8px;display:block;
   scroll-snap-align:start;background:#222}}
 .tira a{{flex:none}}
 details{{margin-top:18px;border-top:1px solid #242424;padding-top:14px}}
 summary{{cursor:pointer;color:#9a9a9a;font-size:.9rem}}
 summary:hover{{color:{AMARILLO}}}
 pre{{white-space:pre-wrap;font:14px/1.65 inherit;color:#d2d2d2;
   margin-top:12px;background:#0e0e0e;padding:16px;border-radius:8px}}
 footer{{max-width:1100px;margin:60px auto 0;color:#6d6d6d;font-size:.85rem;
   border-top:1px solid #242424;padding-top:20px}}
 footer a{{color:#8f8f8f}}
 .vacio{{color:#8f8f8f;text-align:center;padding:60px 0}}
 @media(max-width:600px){{ .tira img{{height:210px}} h1{{font-size:1.5rem}} }}
</style>
</head>
<body>
<div class="barra"></div>
<header class="top">
  <h1>Mundo <span>Motor</span> — piezas de Instagram</h1>
  <p class="sub">{publicadas} carrusel(es) publicado(s) · {total_laminas} láminas generadas.
  Cada pieza se arma a partir de un artículo ya publicado y verificado.</p>
</header>
<main>
{"".join(tarjetas) if tarjetas else '<p class="vacio">Todavía no hay piezas generadas.</p>'}
</main>
<footer>
  Las imágenes viven aquí porque Instagram necesita descargarlas desde una URL pública.
  El contenido editorial está en <a href="https://mundomotor.bike/">mundomotor.bike</a>.
</footer>
</body>
</html>
"""
    (DOCS / "index.html").write_text(doc, encoding="utf-8")
    print(f"Galería generada: {len(piezas)} pieza(s), {total_laminas} láminas.")


if __name__ == "__main__":
    main()
