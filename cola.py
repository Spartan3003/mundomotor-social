#!/usr/bin/env python3
"""
Mundo Motor — banco de piezas y cola de publicacion.

EL PROBLEMA QUE RESUELVE
Si la pieza del dia dependiera del articulo del dia, cualquier semana ocupada
rompe la cadencia. Aqui se separa PRODUCIR de PUBLICAR: se produce cuando hay
material, se publica una al dia. El banco es el colchon.

COMO ELIGE LA PIEZA DEL DIA
  1. Una pieza pendiente cuya vigencia este por vencer (lo perecedero primero).
  2. Si no, la de actualidad mas antigua en el banco.
  3. Si no, un evergreen del archivo que no se haya usado en 180 dias.
  4. Si no hay nada limpio: NO PUBLICA y avisa. Es preferible saltarse un dia
     a publicar un dato caducado.

VIGENCIA (campo "vigencia" del JSON de cada pieza)
  permanente : no caduca (como funciona un kit de arrastre)
  anual      : caduca el 31 de diciembre del anio que declare "anio"
  efimera    : noticia; caduca a los dias que diga "dias_vigencia" (7 por defecto)

Comandos:
  python cola.py estado        informe del banco y dias de autonomia
  python cola.py siguiente     que se publica hoy (no marca nada)
  python cola.py publicada X   registra la pieza X como publicada
  python cola.py candidatos    articulos del archivo aptos para pieza nueva
"""

import datetime as dt
import json
import pathlib
import shutil
import sys
import urllib.parse
import urllib.request

BASE = pathlib.Path(__file__).parent
BANCO = BASE / "banco"
PENDIENTES = BANCO / "pendientes"
PUBLICADAS = BANCO / "publicadas"
HISTORIAL = BANCO / "historial.json"

# Colchon: por debajo de esto hay que producir si o si.
MINIMO_ALERTA = 3
OBJETIVO = 5           # una semana laboral
REPESCA_DIAS = 180     # un evergreen no se repite antes de 6 meses

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
API = "https://mundomotor.bike/wp-json/wp/v2"


def hoy() -> dt.date:
    return dt.date.today()


def asegura_carpetas():
    for c in (PENDIENTES, PUBLICADAS):
        c.mkdir(parents=True, exist_ok=True)
    if not HISTORIAL.exists():
        HISTORIAL.write_text('{"publicadas": []}', encoding="utf-8")


def historial() -> dict:
    asegura_carpetas()
    try:
        datos = json.loads(HISTORIAL.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"  (aviso) historial ilegible ({e}); parto de uno vacio",
              file=sys.stderr)
        return {"publicadas": []}
    datos.setdefault("publicadas", [])
    return datos


def caduca_el(pieza: dict):
    """Devuelve la fecha en que la pieza deja de ser publicable, o None."""
    v = pieza.get("vigencia", "permanente")
    if v == "permanente":
        return None
    if v == "anual":
        anio = int(pieza.get("anio", hoy().year))
        return dt.date(anio, 12, 31)
    if v == "efimera":
        creada = dt.date.fromisoformat(pieza.get("creada", hoy().isoformat()))
        return creada + dt.timedelta(days=int(pieza.get("dias_vigencia", 7)))
    return None


def carga_pendientes() -> list:
    asegura_carpetas()
    piezas = []
    for f in sorted(PENDIENTES.glob("*.json")):
        try:
            p = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"  (aviso) {f.name} no es JSON valido, lo ignoro", file=sys.stderr)
            continue
        p["_archivo"] = f
        piezas.append(p)
    return piezas


def dias_habiles(desde: dt.date, n: int) -> dt.date:
    """Fecha del n-esimo dia habil contando desde 'desde'."""
    d, quedan = desde, n
    while quedan > 0:
        d += dt.timedelta(days=1)
        if d.weekday() < 5:
            quedan -= 1
    return d


def cmd_estado():
    piezas = carga_pendientes()
    vivas, caducadas = [], []
    for p in piezas:
        f = caduca_el(p)
        (caducadas if (f and f < hoy()) else vivas).append((p, f))

    print("BANCO DE PIEZAS")
    print("=" * 58)
    print(f"Listas para publicar : {len(vivas)}")
    print(f"Caducadas            : {len(caducadas)}")
    print(f"Autonomia            : {len(vivas)} dias habiles "
          f"(hasta el {dias_habiles(hoy(), len(vivas)):%d/%m} si se publica una al dia)")
    print()

    if vivas:
        print("En cola:")
        for p, f in ordena(vivas):
            cad = f"caduca {f:%d/%m/%Y}" if f else "no caduca"
            print(f"  - {p.get('slug','(sin slug)'):34} {p.get('vigencia','permanente'):11} {cad}")
    if caducadas:
        print("\nCaducadas (no se publican, revisar o descartar):")
        for p, f in caducadas:
            print(f"  x {p.get('slug','(sin slug)'):34} vencio el {f:%d/%m/%Y}")

    print()
    if len(vivas) == 0:
        print("*** BANCO VACIO: hoy no hay nada que publicar. Produce piezas ya. ***")
    elif len(vivas) < MINIMO_ALERTA:
        print(f"*** COLCHON BAJO ({len(vivas)}/{OBJETIVO}): produce piezas esta semana. ***")
    else:
        print(f"Colchon sano ({len(vivas)}/{OBJETIVO}).")
    return 0


def ordena(vivas: list) -> list:
    """Lo perecedero primero; entre iguales, lo mas antiguo."""
    def clave(par):
        p, f = par
        return (f or dt.date(2999, 12, 31), p.get("creada", "9999-99-99"))
    return sorted(vivas, key=clave)


def cmd_siguiente():
    """Con --slug imprime solo el slug, para que lo consuma el automatismo."""
    solo_slug = "--slug" in sys.argv
    piezas = carga_pendientes()
    vivas = [(p, caduca_el(p)) for p in piezas]
    vivas = [(p, f) for p, f in vivas if not (f and f < hoy())]

    if solo_slug:
        if not vivas:
            return 1
        print(ordena(vivas)[0][0].get("slug", ""))
        return 0

    if not vivas:
        print("No hay ninguna pieza publicable hoy.")
        print("NO se publica nada: es preferible saltar un dia a sacar un dato caducado.")
        print("Corre 'python cola.py candidatos' para ver que articulos del archivo sirven.")
        return 1

    p, f = ordena(vivas)[0]
    print(f"Hoy se publica: {p.get('slug')}")
    print(f"  origen   : {p.get('origen')}")
    print(f"  vigencia : {p.get('vigencia','permanente')}"
          + (f" (caduca {f:%d/%m/%Y})" if f else ""))
    print(f"  archivo  : {p['_archivo']}")
    if len(vivas) - 1 < MINIMO_ALERTA:
        print(f"\n  AVISO: quedarian {len(vivas)-1} piezas en el banco.")
    return 0


def cmd_publicada(slug: str):
    h = historial()
    piezas = [p for p in carga_pendientes() if p.get("slug") == slug]
    if not piezas:
        print(f"No encuentro '{slug}' entre las pendientes.")
        return 1
    p = piezas[0]
    origen = p.get("origen", "")
    h["publicadas"].append({
        "slug": slug,
        "origen": origen,
        "post_id": id_de_url(origen),
        "fecha": hoy().isoformat(),
    })
    HISTORIAL.write_text(json.dumps(h, ensure_ascii=False, indent=2), encoding="utf-8")
    destino = PUBLICADAS / p["_archivo"].name
    if destino.exists():
        destino = PUBLICADAS / f"{destino.stem}-{hoy():%Y%m%d}{destino.suffix}"
    shutil.move(str(p["_archivo"]), str(destino))
    print(f"Registrada '{slug}' como publicada el {hoy():%d/%m/%Y}.")
    print(f"Movida a {destino}")
    return 0


def id_de_url(url: str) -> str:
    return urllib.parse.urlparse(url).path.rstrip("/").split("/")[-1] if url else ""


def cmd_candidatos():
    """Articulos evergreen del archivo que aun no se han convertido en pieza."""
    h = historial()
    usados = {x.get("post_id") for x in h["publicadas"]}
    usados |= {id_de_url(p.get("origen", "")) for p in carga_pendientes()}
    limite = hoy() - dt.timedelta(days=REPESCA_DIAS)
    for x in h["publicadas"]:
        if dt.date.fromisoformat(x["fecha"]) < limite:
            usados.discard(x.get("post_id"))  # ya se puede repescar

    url = (f"{API}/categories?slug=moto-tips&_fields=id,name,count")
    cat = pedir(url)
    if not cat:
        print("No pude consultar las categorias del sitio.")
        return 1
    cid, total = cat[0]["id"], cat[0]["count"]
    print(f"Archivo evergreen: categoria '{cat[0]['name']}' con {total} articulos.\n")

    posts = pedir(f"{API}/posts?categories={cid}&per_page=30&orderby=date&order=desc"
                  f"&_fields=id,date,title,link") or []
    libres = [p for p in posts if id_de_url(p["link"]) not in usados]

    print(f"Candidatos sin usar (de los {len(posts)} mas recientes):")
    for p in libres[:15]:
        titulo = p["title"]["rendered"]
        print(f"  [{p['date'][:10]}] {titulo[:64]}")
        print(f"              {p['link']}")
    if not libres:
        print("  (ninguno: todos los recientes ya se usaron; amplia la busqueda "
              "o espera a la repesca de 180 dias)")
    return 0


def pedir(url: str):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=45) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        print(f"  (error consultando el sitio: {e})", file=sys.stderr)
        return None


COMANDOS = {"estado": cmd_estado, "siguiente": cmd_siguiente, "candidatos": cmd_candidatos}

if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "estado"
    if arg == "publicada":
        sys.exit(cmd_publicada(sys.argv[2]) if len(sys.argv) > 2
                 else print("Falta el slug: python cola.py publicada <slug>") or 1)
    sys.exit(COMANDOS.get(arg, cmd_estado)())
