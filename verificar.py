#!/usr/bin/env python3
"""
Mundo Motor — control de veracidad para las piezas sociales.

Regla del medio: una lamina NUNCA puede afirmar un dato que no este en el
articulo ya publicado y revisado. Este script lo comprueba de forma mecanica.

Que hace:
  1. Descarga el articulo de origen POR LA API REST y se queda solo con el
     cuerpo del post. Antes se comparaba contra el HTML entero de la pagina,
     que incluye menu, sidebar y notas relacionadas: cualquier cifra de otro
     articulo del sitio servia de coartada.
  2. Extrae TODO dato numerico de la pieza -- laminas y tambien caption y
     alt text, que antes no se miraban -- y comprueba que aparezca en ese
     cuerpo.
  3. Comprueba la procedencia de cada foto, este donde este (fondo, mosaico
     o foto_texto). Lo desconocido bloquea: en un sistema que publica solo,
     un aviso no lo lee nadie.
  4. Comprueba que la vigencia este bien declarada.

Falla con codigo 1 si algo no cuadra. Sin verde, no se publica.

LIMITE CONOCIDO, y es grande: esto verifica CIFRAS, no afirmaciones. Una
frase cualitativa falsa ("la tecnomecanica no es obligatoria el primer ano")
pasa sin que nada la detenga. La unica defensa contra eso hoy es que el
redactor no invente prosa; ver REDACTOR.md.

Uso:  python verificar.py carrusel.json
"""

import html
import json
import pathlib
import re
import sys
import urllib.parse
import urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
DOMINIO_PROPIO = "mundomotor.bike"
API = f"https://{DOMINIO_PROPIO}/wp-json/wp/v2/posts"

# Claves que son metadatos de maquetacion, no contenido que el lector lea.
# OJO: 'marca' NO esta aqui a proposito -- es el badge grande de las listas
# (C.14, 50%, $633.200) y es contenido plenamente visible.
CLAVES_META = {"tipo", "slug", "origen", "url", "size", "imagen", "credito",
               "propia", "vigencia", "anio", "creada", "dias_vigencia",
               "hashtags", "menciones", "ubicacion", "limpio", "plain"}

# Datos que exigen respaldo en el articulo.
PATRONES = [
    (r"\$\s?\d[\d.,]*", "valor en pesos"),
    (r"\b\d{1,3}(?:[.,]\d{1,3})?\s?%", "porcentaje"),
    (r"\b\d{1,3}(?:[.,]\d{1,3})?\s?por\s?ciento", "porcentaje escrito"),
    (r"\b[A-E]\.\d{2}\b", "codigo de infraccion"),
    (r"\b(?:Resoluci[oó]n|Ley|Circular|Decreto|NTC|FMVSS|Sentencia|Acuerdo)"
     r"(?:\s+Externa)?\s+\d[\w.\-]*(?:\s+de\s+\d{4})?", "norma citada"),
    (r"\b\d{1,2}W-\d{2}\b", "viscosidad SAE"),
    (r"\bJASO\s+M[AB]\d?\b", "norma de aceite"),
    # Cilindrada en todas sus formas: 125cc, 125 cc, 125 c.c., 125 cm3.
    # Sin \b final: tras el punto de "c.c." no hay frontera de palabra y el
    # patron no llegaba a disparar nunca.
    (r"\b\d{2,4}\s?(?:c\.c\.|cc\b|cm3\b|cm³)", "cilindrada"),
    (r"\b\d[\d.,]*\s?(?:mm|cm|kg|km|kW|HP|Nm|litros?|pulgadas|"
     r"kil[oó]metros|kilos|a[nñ]os|meses|d[ií]as|horas)\b", "medida o plazo"),
    # Cualquier cifra con separador de miles o decimal: precios, kilometrajes.
    (r"\b\d{1,3}(?:[.,]\d{3})+\b", "cifra con miles"),
    (r"\b\d{1,3},\d{1,2}\b", "cifra decimal"),
    (r"\b(?:19|20)\d{2}\b", "anio"),
]

# Numeracion de las laminas y poco mas. Cualquier otra cifra se comprueba:
# antes se ignoraban 50, 25, 100, 2025 y 2026, y por ahi cabia un descuento
# falso del 50 %, un plazo inventado de 25 dias o una tarifa del ano pasado
# presentada como la de este.
IGNORAR = {f"{n:02d}" for n in range(1, 21)}


def texto_plano(h: str) -> str:
    h = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", h, flags=re.S | re.I)
    h = re.sub(r"<[^>]+>", " ", h)
    h = html.unescape(h)
    return re.sub(r"\s+", " ", h)


def normaliza(s: str) -> str:
    s = s.replace(" ", " ").replace(" ", " ")
    return re.sub(r"\s+", " ", s).strip()


def limpia_cifra(s: str) -> str:
    """Quita la puntuacion de cierre de frase que el patron arrastra."""
    return re.sub(r"[.,]+$", "", normaliza(s))


# El articulo escribe los numeros pequenos con letra ("cinco dias habiles") y
# la pieza los escribe en cifra. Es el mismo dato: hay que casarlos.
EN_LETRA = {
    1: "un", 2: "dos", 3: "tres", 4: "cuatro", 5: "cinco", 6: "seis",
    7: "siete", 8: "ocho", 9: "nueve", 10: "diez", 11: "once", 12: "doce",
    13: "trece", 14: "catorce", 15: "quince", 16: "diecis[eé]is",
    17: "diecisiete", 18: "dieciocho", 19: "diecinueve", 20: "veinte",
    21: "veintiun", 24: "veinticuatro", 25: "veinticinco", 30: "treinta",
    50: "cincuenta", 100: "cien",
}


def variantes(v: str) -> set:
    """Formas equivalentes de escribir el mismo dato."""
    base = {v, v.replace("$ ", "$"), v.replace(" %", "%"), v.replace("%", " %"),
            v.replace(" ", "")}
    # 125 c.c. == 125 cc == 125cc
    sin_puntos = re.sub(r"c\.c\.", "cc", v)
    base |= {sin_puntos, sin_puntos.replace(" ", "")}
    return {b for b in base if b}


def respaldado(v: str, fuente: str) -> bool:
    if any(x in fuente for x in variantes(v)):
        return True
    # "5 dias" contra "cinco dias": se compara el numero escrito con letra
    # junto a la misma unidad.
    m = re.match(r"^(\d{1,3})\s*(.*)$", v)
    if m:
        num, resto = int(m.group(1)), m.group(2).strip()
        letra = EN_LETRA.get(num)
        if letra:
            patron = letra + (r"\s+" + re.escape(resto) if resto else "")
            if re.search(patron, fuente, re.I):
                return True
    return False


def cuerpo_del_articulo(origen: str) -> str:
    """Solo el cuerpo del post, pedido por la API. Nada de sidebar ni menu."""
    partes = urllib.parse.urlparse(origen)
    if not partes.netloc.endswith(DOMINIO_PROPIO):
        raise SystemExit(
            f"ERROR: el origen no es un articulo de {DOMINIO_PROPIO} ({origen}).\n"
            "Una pieza solo puede apoyarse en contenido propio ya publicado."
        )
    slug = partes.path.rstrip("/").split("/")[-1]
    if not slug or slug == DOMINIO_PROPIO:
        raise SystemExit(
            "ERROR: el origen debe ser un articulo concreto, no la portada ni "
            "una categoria. Apuntar a la home valida cualquier cifra del sitio."
        )
    url = f"{API}?slug={urllib.parse.quote(slug)}&_fields=title,content,link"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            datos = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        raise SystemExit(f"ERROR: no pude leer el articulo de origen: {e}")
    if not datos:
        raise SystemExit(
            f"ERROR: no existe ningun articulo publicado con el slug '{slug}'.\n"
            "Puede que se haya despublicado o cambiado de direccion."
        )
    post = datos[0]
    return normaliza(texto_plano(
        post["title"]["rendered"] + " " + post["content"]["rendered"]))


def recolecta(nodo, salida):
    if isinstance(nodo, dict):
        for k, v in nodo.items():
            if k in CLAVES_META:
                continue
            recolecta(v, salida)
    elif isinstance(nodo, list):
        for v in nodo:
            recolecta(v, salida)
    elif isinstance(nodo, str):
        salida.append(nodo)


def revisa_vigencia(cfg: dict) -> list:
    """Una vigencia mal declarada hace que la pieza no caduque nunca."""
    fallos = []
    v = cfg.get("vigencia")
    if v not in ("permanente", "anual", "efimera"):
        fallos.append(
            f"vigencia '{v}' no es valida: debe ser permanente, anual o efimera."
        )
        return fallos
    if v == "anual" and not cfg.get("anio"):
        fallos.append(
            "vigencia anual sin campo 'anio': la caducidad se recalcularia cada "
            "ano y la pieza no moriria nunca."
        )
    if v == "efimera" and not cfg.get("creada"):
        fallos.append(
            "vigencia efimera sin campo 'creada': la caducidad huiria hacia "
            "adelante un dia tras otro."
        )
    return fallos


def main(ruta: str) -> int:
    cfg = json.loads(pathlib.Path(ruta).read_text(encoding="utf-8"))
    origen = cfg.get("origen")
    if not origen:
        print("ERROR: el carrusel no declara 'origen'. Sin fuente no se verifica.")
        return 1

    fuente = cuerpo_del_articulo(origen)

    # --- procedencia de las fotos --------------------------------------
    import fuentes as fu

    imgs, problemas_img = [], []
    for i, lam in enumerate(cfg["laminas"], 1):
        candidatas = []
        if lam.get("imagen"):
            candidatas.append(lam)
        if lam.get("foto"):
            candidatas.append(lam["foto"])
        candidatas += lam.get("fotos", [])

        for f in candidatas:
            url = f.get("imagen")
            if not url:
                continue
            imgs.append(url)
            if not str(url).lower().startswith(("http://", "https://")):
                problemas_img.append(
                    f"lamina {i}: '{url}' es una ruta local; una foto tiene que "
                    "venir de una URL para poder comprobar de donde sale")
                continue
            if not f.get("propia") and not f.get("credito"):
                problemas_img.append(f"lamina {i}: foto sin credito declarado")
                continue
            estado, dom, motivo = fu.clasifica(url)
            if estado == fu.PROHIBIDO:
                problemas_img.append(f"lamina {i}: {dom} {motivo}")
            elif estado == fu.REVISAR:
                # En un sistema desatendido un aviso no lo lee nadie.
                problemas_img.append(
                    f"lamina {i}: {dom} no esta entre las fuentes admitidas "
                    "(biblioteca propia, marca o concesionario)")

    # --- datos factuales ------------------------------------------------
    textos = []
    recolecta(cfg["laminas"], textos)
    recolecta(cfg.get("publicacion", {}), textos)   # el caption y los alt tambien
    plano = normaliza(texto_plano(" ".join(textos)))

    hallados, vistos = [], set()
    for patron, clase in PATRONES:
        for m in re.findall(patron, plano, re.I):
            v = limpia_cifra(m if isinstance(m, str) else m[0])
            if not v or v in vistos or v.strip("$ %") in IGNORAR:
                continue
            vistos.add(v)
            hallados.append((v, clase))

    faltan = [(v, c) for v, c in hallados if not respaldado(v, fuente)]

    problemas_vig = revisa_vigencia(cfg)

    print(f"Fuente: {origen}")
    print(f"Cuerpo del articulo: {len(fuente)} caracteres")
    print(f"Datos factuales detectados: {len(hallados)}   Fotos: {len(imgs)}")

    if problemas_vig:
        print(f"\n  *** VIGENCIA MAL DECLARADA ***")
        for p in problemas_vig:
            print(f"   - {p}")

    if problemas_img:
        print(f"\n  *** {len(problemas_img)} FOTO(S) QUE INCUMPLEN LA REGLA ***")
        for p in problemas_img:
            print(f"   - {p}")

    if faltan:
        print(f"\n  *** {len(faltan)} DATO(S) SIN RESPALDO EN EL ARTICULO ***")
        for v, c in faltan:
            print(f"   - {v}   ({c})")

    if not hallados:
        print("\n  AVISO: no se detecto ningun dato factual. Revisa a mano que "
              "no se haya colado una afirmacion sin respaldo.")

    if faltan or problemas_img or problemas_vig:
        print("\n  NO PUBLICAR. Corrige lo anterior antes de seguir.")
        return 1

    print("\n  OK: cada cifra, codigo y norma de la pieza aparece en el articulo.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "carrusel.json"))
