#!/usr/bin/env python3
"""
Mundo Motor — generador de carruseles para Instagram.

Lee un JSON con las laminas y produce PNG 1080x1350 (4:5) con la identidad
de la marca: negro, amarillo #FDC207, Anton para titulares y Poppins para texto.

Reglas de diseno (v2, orientada a retencion):
  - El contenido SIEMPRE llena el lienzo: nada de tercios muertos.
  - Barra de progreso segmentada: el lector ve cuanto falta y sigue deslizando.
  - Una idea por lamina, con un unico foco visual.
  - La fuente vive en su propia franja, nunca encima del pie.

Uso:  python build.py carrusel.json
Salida: ./salida/<slug>/01.png, 02.png, ...
"""

import base64
import html
import json
import pathlib
import shutil
import subprocess
import sys

BASE = pathlib.Path(__file__).parent
FONTS = BASE / "fonts"
BRAND = BASE / "brand"
def busca_chrome() -> str:
    """Chrome en Windows (equipo de Nicolas) o en Linux (runner de la nube)."""
    import os
    import shutil

    if os.environ.get("CHROME_BIN"):
        return os.environ["CHROME_BIN"]
    candidatos = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium-browser",
        "/usr/bin/chromium",
    ]
    for c in candidatos:
        if pathlib.Path(c).exists():
            return c
    for nombre in ("google-chrome", "chromium", "chrome"):
        ruta = shutil.which(nombre)
        if ruta:
            return ruta
    raise SystemExit("No encuentro Chrome. Instalalo o define CHROME_BIN.")


CHROME = busca_chrome()

W, H = 1080, 1350

AMARILLO = "#FDC207"
NEGRO = "#0B0B0B"
BLANCO = "#FFFFFF"


UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

# Regla de Nicolas: las fotos de motos salen de la marca o del concesionario
# que la vende. NUNCA de un medio de la competencia. Ver fuentes.py.
CACHE_IMG = BASE / "imagenes"


def b64(path: pathlib.Path) -> str:
    return base64.b64encode(path.read_bytes()).decode()


def imagen_b64(spec: str) -> str:
    """Acepta una URL o una ruta local y devuelve la imagen en base64.
    Las descargas quedan cacheadas para no volver a pedirlas."""
    import hashlib
    import urllib.request

    if not spec.startswith("http"):
        p = pathlib.Path(spec)
        if not p.is_absolute():
            p = BASE / spec
        return b64(p)

    CACHE_IMG.mkdir(exist_ok=True)
    destino = CACHE_IMG / (hashlib.sha1(spec.encode()).hexdigest()[:16] + ".img")
    if not destino.exists():
        req = urllib.request.Request(spec, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=45) as r:
            destino.write_bytes(r.read())
    return b64(destino)


def esc(s) -> str:
    return html.escape(str(s), quote=False)


def face(name: str, file: str, weight: int) -> str:
    return (
        f"@font-face{{font-family:'{name}';font-weight:{weight};font-style:normal;"
        f"src:url(data:font/ttf;base64,{b64(FONTS / file)}) format('truetype');}}"
    )


def css() -> str:
    return f"""
{face('Anton', 'Anton-Regular.ttf', 400)}
{face('Poppins', 'Poppins-Regular.ttf', 400)}
{face('Poppins', 'Poppins-SemiBold.ttf', 600)}
{face('Poppins', 'Poppins-Bold.ttf', 700)}

*{{margin:0;padding:0;box-sizing:border-box;}}
html,body{{width:{W}px;height:{H}px;overflow:hidden;}}
body{{font-family:'Poppins',sans-serif;background:{NEGRO};color:{BLANCO};
  -webkit-font-smoothing:antialiased;text-rendering:geometricPrecision;}}

/* ============ lienzo ============ */
.slide{{
  position:relative;width:{W}px;height:{H}px;overflow:hidden;
  display:flex;flex-direction:column;
  background:
    repeating-linear-gradient(115deg, rgba(255,255,255,.016) 0 2px, transparent 2px 26px),
    radial-gradient(135% 95% at 88% -8%, #232323 0%, {NEGRO} 58%),
    {NEGRO};
}}
/* cuna angular de marca, anclada a la esquina inferior derecha */
.cuna{{
  position:absolute;right:0;bottom:0;width:520px;height:430px;z-index:1;
  background:{AMARILLO};
  clip-path:polygon(100% 0, 100% 100%, 0 100%);
  opacity:.10;
}}
.cuna.solida{{opacity:1;}}
.slide.limpio .cuna{{display:none;}}

.barra-top{{position:absolute;top:0;left:0;width:100%;height:14px;background:{AMARILLO};z-index:6;}}

.contenido{{
  position:relative;z-index:4;flex:1;display:flex;flex-direction:column;
  padding:92px 78px 0 78px;min-height:0;
}}
.bloque-centro{{flex:1;display:flex;flex-direction:column;justify-content:center;min-height:0;}}
.bloque-fin{{flex:1;display:flex;flex-direction:column;justify-content:flex-end;min-height:0;}}

/* ============ tipografia ============ */
.kicker{{
  font-weight:700;font-size:25px;letter-spacing:.18em;text-transform:uppercase;
  color:{AMARILLO};display:flex;align-items:center;gap:16px;
}}
.kicker::after{{content:'';flex:1;height:3px;background:{AMARILLO};opacity:.4;max-width:170px;}}

.etiqueta{{
  display:inline-block;background:{AMARILLO};color:{NEGRO};
  font-weight:700;font-size:26px;letter-spacing:.06em;text-transform:uppercase;
  padding:12px 22px;border-radius:4px;align-self:flex-start;
}}

h1{{
  font-family:'Anton',sans-serif;font-weight:400;font-size:122px;line-height:.92;
  text-transform:uppercase;letter-spacing:.004em;
}}
h1.mediano{{font-size:100px;}}
h1.chico{{font-size:84px;}}

h2{{
  font-family:'Anton',sans-serif;font-weight:400;font-size:66px;line-height:1.0;
  text-transform:uppercase;letter-spacing:.005em;
}}
h2.chico{{font-size:56px;}}

em{{font-style:normal;color:{AMARILLO};}}
mark{{background:{AMARILLO};color:{NEGRO};padding:0 12px;}}

p.bajada{{font-size:33px;line-height:1.45;color:#DEDEDE;max-width:880px;}}
p.bajada strong{{color:{BLANCO};font-weight:700;}}
.sep{{height:34px;flex:none;}}
.sep.chico{{height:22px;}}

/* ============ cifra ============ */
.cifra{{font-family:'Anton',sans-serif;font-size:250px;line-height:.84;color:{AMARILLO};
  letter-spacing:-.025em;}}
.cifra.larga{{font-size:186px;}}
.cifra-nota{{font-size:31px;font-weight:700;color:#B4B4B4;text-transform:uppercase;
  letter-spacing:.12em;margin-top:14px;}}

/* ============ tabla ============ */
table{{width:100%;border-collapse:collapse;}}
th{{font-size:22px;font-weight:700;text-transform:uppercase;letter-spacing:.1em;
  color:{NEGRO};background:{AMARILLO};padding:19px 24px;text-align:left;}}
th:last-child{{text-align:right;}}
td{{font-size:34px;padding:26px 24px;border-bottom:2px solid #262626;}}
tr:last-child td{{border-bottom:none;}}
tr td:first-child{{font-family:'Anton';font-size:40px;width:120px;color:{BLANCO};}}
tr td:last-child{{font-weight:700;color:{AMARILLO};text-align:right;white-space:nowrap;}}
tr.destaca td{{background:rgba(253,194,7,.09);}}

/* ============ lista ============ */
ul.items{{list-style:none;}}
ul.items li{{display:flex;gap:28px;align-items:flex-start;padding:28px 0;
  border-bottom:2px solid #232323;}}
ul.items li:last-child{{border-bottom:none;}}
.num{{font-family:'Anton';font-size:46px;color:{AMARILLO};line-height:1.05;min-width:112px;}}
.item-txt{{font-size:31px;line-height:1.36;color:#C9C9C9;}}
.item-txt b{{color:{BLANCO};font-weight:700;display:block;font-size:36px;
  line-height:1.22;margin-bottom:7px;}}

/* ============ comparativa VS ============ */
.vs{{display:flex;align-items:stretch;gap:0;}}
.vs .col{{flex:1;padding:34px 30px;}}
.vs .col:first-child{{border-right:4px solid {AMARILLO};}}
.vs .col h3{{font-family:'Anton';font-size:46px;text-transform:uppercase;
  margin-bottom:26px;line-height:1;}}
.vs .col .dato{{font-size:30px;line-height:1.5;color:#D2D2D2;margin-bottom:14px;}}
.vs .col .dato b{{color:{AMARILLO};font-weight:700;}}

/* ============ caja destacada ============ */
.caja{{background:{AMARILLO};color:{NEGRO};border-radius:8px;padding:46px 48px;}}
.caja .et{{font-family:'Anton';font-size:76px;line-height:1;text-transform:uppercase;
  margin-bottom:18px;}}
.caja .et.chica{{font-size:48px;}}
.caja p{{font-size:33px;line-height:1.4;font-weight:600;}}

.nota{{border-left:9px solid {AMARILLO};padding:4px 0 4px 28px;font-size:29px;
  line-height:1.42;color:#BEBEBE;}}

/* ============ pie ============ */
.fuente{{position:relative;z-index:4;font-size:21px;color:#6F6F6F;line-height:1.35;
  padding:0 78px 18px 78px;}}
.progreso{{position:relative;z-index:4;display:flex;gap:7px;padding:0 78px 22px 78px;}}
.progreso i{{flex:1;height:7px;background:#333;border-radius:99px;}}
.progreso i.on{{background:{AMARILLO};}}
.pie{{position:relative;z-index:5;display:flex;align-items:center;
  justify-content:space-between;padding:0 78px 54px 78px;}}
.pie img{{height:76px;}}
.pie .handle{{font-size:26px;font-weight:700;color:#8A8A8A;letter-spacing:.04em;}}

.desliza{{display:flex;align-items:center;gap:14px;font-size:28px;font-weight:700;
  color:{AMARILLO};text-transform:uppercase;letter-spacing:.12em;}}
.desliza .flecha{{font-family:'Anton';font-size:38px;line-height:1;}}

/* ============ lamina con foto real ============ */
.foto-fondo{{position:absolute;inset:0;z-index:0;overflow:hidden;}}
.foto-fondo img{{width:100%;height:100%;object-fit:cover;}}
.velo{{position:absolute;inset:0;z-index:1;
  background:linear-gradient(180deg, rgba(11,11,11,.34) 0%, rgba(11,11,11,.10) 30%,
    rgba(11,11,11,.82) 68%, rgba(11,11,11,.97) 100%);}}
.slide.con-foto .contenido{{justify-content:flex-end;padding-bottom:34px;}}
.slide.con-foto .bloque-centro{{justify-content:flex-end;flex:1;}}
.slide.con-foto .cuna{{display:none;}}
.credito{{position:absolute;top:38px;right:40px;z-index:5;font-size:19px;
  color:rgba(255,255,255,.72);background:rgba(0,0,0,.45);padding:8px 16px;
  border-radius:4px;letter-spacing:.03em;}}

/* ============ galeria de fotos del tema ============ */
.mosaico{{display:grid;gap:16px;}}
.mosaico.n2{{grid-template-columns:1fr 1fr;}}
.mosaico.n3{{grid-template-columns:1fr 1fr;}}
.mosaico.n3 .celda:first-child{{grid-column:1 / -1;}}
.mosaico.n4{{grid-template-columns:1fr 1fr;}}
.celda{{position:relative;border-radius:8px;overflow:hidden;background:#1a1a1a;
  border:3px solid #202020;}}
.celda img{{width:100%;height:100%;object-fit:cover;display:block;}}
.mosaico.n2 .celda{{height:660px;}}
.mosaico.n3 .celda{{height:330px;}}
.mosaico.n3 .celda:first-child{{height:380px;}}
.mosaico.n4 .celda{{height:340px;}}
.celda .pie-foto{{position:absolute;left:0;bottom:0;width:100%;
  background:linear-gradient(180deg,transparent,rgba(0,0,0,.9));
  color:#fff;font-size:24px;font-weight:700;padding:44px 20px 16px;}}
.celda .pie-foto b{{color:{AMARILLO};display:block;font-family:'Anton';
  font-size:30px;font-weight:400;text-transform:uppercase;line-height:1.1;}}

/* ============ foto + texto ============ */
.dupla{{display:grid;grid-template-columns:1fr 1fr;gap:26px;align-items:center;}}
.dupla .marco{{border-radius:8px;overflow:hidden;height:480px;background:#1a1a1a;
  border:3px solid #202020;}}
.dupla .marco img{{width:100%;height:100%;object-fit:cover;display:block;}}
.dupla .texto p{{font-size:31px;line-height:1.45;color:#DEDEDE;}}
.dupla .texto p + p{{margin-top:18px;}}

/* ============ cierre ============ */
.cierre{{flex:1;display:flex;flex-direction:column;align-items:center;
  justify-content:center;text-align:center;}}
.cierre img{{height:210px;margin-bottom:54px;}}
.cierre h2{{font-size:78px;margin-bottom:28px;text-wrap:balance;max-width:900px;}}
.cierre p{{font-size:33px;color:#D2D2D2;line-height:1.45;max-width:790px;}}
.cierre .url{{margin-top:50px;background:{AMARILLO};color:{NEGRO};font-family:'Anton';
  font-size:42px;padding:22px 48px;border-radius:6px;}}
.acciones{{display:flex;gap:26px;margin-top:46px;}}
.acciones div{{border:3px solid #3A3A3A;border-radius:99px;padding:16px 30px;
  font-size:26px;font-weight:700;color:#CFCFCF;}}
.acciones div b{{color:{AMARILLO};}}
"""


def _pie(logo: str, idx: int, total: int, con_desliza: bool) -> str:
    barras = "".join(f'<i class="{"on" if k <= idx else ""}"></i>' for k in range(1, total + 1))
    der = (
        '<div class="desliza">Desliza <span class="flecha">&rsaquo;&rsaquo;</span></div>'
        if con_desliza else '<div class="handle">@mundomotor.bike</div>'
    )
    return (
        f'<div class="progreso">{barras}</div>'
        f'<div class="pie"><img src="data:image/png;base64,{logo}">{der}</div>'
    )


def render_slide(s: dict, idx: int, total: int, logo: str) -> str:
    tipo = s.get("tipo", "texto")
    clases = ["slide"] + (["limpio"] if s.get("limpio") else [])
    cuna = '<div class="cuna"></div>'
    cuerpo = ""

    # Foto real de la moto. Exige credito: sin fuente declarada no se monta.
    fondo = ""
    if s.get("imagen"):
        if not s.get("credito"):
            raise SystemExit(
                f"Lamina {idx}: lleva imagen pero no declara 'credito'. "
                "Toda foto debe citar de donde salio."
            )
        clases.append("con-foto")
        fondo = (
            f'<div class="foto-fondo"><img src="data:image;base64,{imagen_b64(s["imagen"])}">'
            f'</div><div class="velo"></div>'
            f'<div class="credito">Foto: {esc(s["credito"])}</div>'
        )

    if tipo in ("portada", "foto"):
        cuerpo = (
            (f'<div class="kicker">{esc(s["kicker"])}</div>' if s.get("kicker") else "")
            + '<div class="bloque-centro">'
            + (f'<div class="etiqueta">{esc(s["etiqueta"])}</div><div class="sep"></div>'
               if s.get("etiqueta") else "")
            + f'<h1 class="{s.get("size","")}">{s["titulo"]}</h1>'
            + (f'<div class="sep"></div><p class="bajada">{s["bajada"]}</p>'
               if s.get("bajada") else "")
            + "</div>"
        )

    elif tipo == "cifra":
        cls = "cifra larga" if len(str(s["cifra"])) > 8 else "cifra"
        cuerpo = (
            (f'<div class="kicker">{esc(s["kicker"])}</div>' if s.get("kicker") else "")
            + '<div class="bloque-centro">'
            + f'<div class="{cls}">{esc(s["cifra"])}</div>'
            + (f'<div class="cifra-nota">{esc(s["nota"])}</div>' if s.get("nota") else "")
            + (f'<div class="sep"></div><p class="bajada">{s["bajada"]}</p>'
               if s.get("bajada") else "")
            + "</div>"
        )

    elif tipo == "tabla":
        filas = ""
        for f in s["filas"]:
            cls = ' class="destaca"' if isinstance(f, dict) else ""
            celdas = f["celdas"] if isinstance(f, dict) else f
            filas += f"<tr{cls}>" + "".join(f"<td>{esc(c)}</td>" for c in celdas) + "</tr>"
        cuerpo = (
            f'<h2>{s["titulo"]}</h2><div class="sep"></div>'
            + '<div class="bloque-centro"><table><thead><tr>'
            + "".join(f"<th>{esc(c)}</th>" for c in s["columnas"])
            + f"</tr></thead><tbody>{filas}</tbody></table>"
            + (f'<div class="sep"></div><div class="nota">{s["nota"]}</div>'
               if s.get("nota") else "")
            + "</div>"
        )

    elif tipo == "lista":
        items = ""
        for i, it in enumerate(s["items"], 1):
            marca = it.get("marca") or f"{i:02d}"
            t = f"<b>{it['titulo']}</b>" if it.get("titulo") else ""
            items += (f'<li><div class="num">{esc(marca)}</div>'
                      f'<div class="item-txt">{t}{it.get("texto","")}</div></li>')
        cuerpo = (
            f'<h2 class="{s.get("size","")}">{s["titulo"]}</h2><div class="sep"></div>'
            + f'<div class="bloque-centro"><ul class="items">{items}</ul>'
            + (f'<div class="sep"></div><div class="nota">{s["nota"]}</div>'
               if s.get("nota") else "")
            + "</div>"
        )

    elif tipo == "destacado":
        et_cls = "et chica" if len(str(s["caja_titulo"])) > 22 else "et"
        cuerpo = (
            f'<h2 class="{s.get("size","")}">{s["titulo"]}</h2>'
            + '<div class="bloque-centro">'
            + f'<div class="caja"><div class="{et_cls}">{s["caja_titulo"]}</div>'
            + f'<p>{s["caja_texto"]}</p></div>'
            + (f'<div class="sep"></div><p class="bajada">{s["bajada"]}</p>'
               if s.get("bajada") else "")
            + "</div>"
        )

    elif tipo == "comparativa":
        cols = ""
        for c in s["columnas"]:
            datos = "".join(f'<div class="dato">{d}</div>' for d in c["datos"])
            cols += f'<div class="col"><h3>{c["titulo"]}</h3>{datos}</div>'
        cuerpo = (
            f'<h2>{s["titulo"]}</h2><div class="sep"></div>'
            + f'<div class="bloque-centro"><div class="vs">{cols}</div>'
            + (f'<div class="sep"></div><div class="nota">{s["nota"]}</div>'
               if s.get("nota") else "")
            + "</div>"
        )

    elif tipo == "galeria":
        # Fotos del tema. Cada una obliga a declarar su procedencia: las
        # propias del medio no llevan credito, las de bancos libres si.
        celdas = ""
        for f in s["fotos"]:
            if not f.get("propia") and not f.get("credito"):
                raise SystemExit(
                    f"Lamina {idx}: la foto {f.get('imagen')} no es propia y no "
                    "declara credito."
                )
            pie = ""
            if f.get("titulo") or f.get("nota"):
                pie = (f'<div class="pie-foto">'
                       f'{f"<b>{f['titulo']}</b>" if f.get("titulo") else ""}'
                       f'{f.get("nota", "")}</div>')
            celdas += (f'<div class="celda"><img src="data:image;base64,'
                       f'{imagen_b64(f["imagen"])}">{pie}</div>')
        n = min(len(s["fotos"]), 4)
        cuerpo = (
            f'<h2 class="{s.get("size","")}">{s["titulo"]}</h2><div class="sep"></div>'
            + f'<div class="bloque-centro"><div class="mosaico n{n}">{celdas}</div>'
            + (f'<div class="sep"></div><div class="nota">{s["nota"]}</div>'
               if s.get("nota") else "")
            + "</div>"
        )

    elif tipo == "foto_texto":
        f = s["foto"]
        if not f.get("propia") and not f.get("credito"):
            raise SystemExit(f"Lamina {idx}: foto sin credito declarado.")
        parrafos = "".join(f"<p>{p}</p>" for p in s["parrafos"])
        cuerpo = (
            f'<h2 class="{s.get("size","")}">{s["titulo"]}</h2><div class="sep"></div>'
            + '<div class="bloque-centro"><div class="dupla">'
            + f'<div class="marco"><img src="data:image;base64,{imagen_b64(f["imagen"])}"></div>'
            + f'<div class="texto">{parrafos}</div></div>'
            + (f'<div class="sep"></div><div class="nota">{s["nota"]}</div>'
               if s.get("nota") else "")
            + "</div>"
        )

    elif tipo == "cierre":
        acciones = ""
        if s.get("acciones"):
            acciones = '<div class="acciones">' + "".join(
                f"<div>{a}</div>" for a in s["acciones"]) + "</div>"
        cuerpo = (
            f'<div class="cierre"><img src="data:image/png;base64,{logo}">'
            f'<h2>{s["titulo"]}</h2><p>{s["texto"]}</p>'
            f'<div class="url">{esc(s.get("url","mundomotor.bike"))}</div>{acciones}</div>'
        )
        cuna = '<div class="cuna"></div>'

    else:  # texto
        cuerpo = (
            f'<h2>{s["titulo"]}</h2>'
            + f'<div class="bloque-centro"><p class="bajada">{s.get("bajada","")}</p></div>'
        )

    fuente = f'<div class="fuente">{esc(s["fuente"])}</div>' if s.get("fuente") else ""
    pie = "" if tipo == "cierre" else _pie(logo, idx, total, idx == 1)
    if tipo == "cierre":
        pie = '<div class="pie"><div class="handle">@mundomotor.bike</div></div>'

    return (
        f'<div class="{" ".join(clases)}">{fondo}{cuna}<div class="barra-top"></div>'
        f'<div class="contenido">{cuerpo}</div>{fuente}{pie}</div>'
    )


def build(config_path: str):
    cfg = json.loads(pathlib.Path(config_path).read_text(encoding="utf-8"))
    logo = b64(BRAND / "logo_0.png")
    slides, slug = cfg["laminas"], cfg["slug"]
    total = len(slides)

    out = BASE / "salida" / slug
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    tmp = BASE / "_tmp"
    tmp.mkdir(exist_ok=True)

    hoja = css()
    for i, s in enumerate(slides, 1):
        doc = ("<!doctype html><html lang='es'><head><meta charset='utf-8'>"
               f"<style>{hoja}</style></head><body>"
               f"{render_slide(s, i, total, logo)}</body></html>")
        f = tmp / f"{slug}_{i:02d}.html"
        f.write_text(doc, encoding="utf-8")

        png = out / f"{i:02d}.png"
        subprocess.run(
            [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
             "--no-sandbox", "--disable-dev-shm-usage",
             "--force-device-scale-factor=1", f"--window-size={W},{H}",
             "--default-background-color=0B0B0BFF", "--virtual-time-budget=2500",
             f"--screenshot={png}", f"file:///{f.as_posix()}"],
            capture_output=True, timeout=120,
        )
        print(f"  [{'OK' if png.exists() else 'FALLO'}] {png.name}  {s.get('tipo')}")

    print(f"\nCarrusel listo: {out}")
    return out


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else str(BASE / "carrusel.json"))
