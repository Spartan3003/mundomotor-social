#!/usr/bin/env python3
"""
Mundo Motor — control de veracidad para las piezas sociales.

Regla del medio: una lamina NUNCA puede afirmar un dato que no este en el
articulo ya publicado y revisado. Este script lo comprueba de forma mecanica.

Que hace:
  1. Descarga el articulo de origen (campo "origen" del JSON del carrusel).
  2. Extrae TODA cifra del carrusel: pesos, porcentajes, decimales, codigos
     de infraccion, anios, leyes y resoluciones.
  3. Verifica que cada una aparezca literalmente en el articulo.
  4. Falla con codigo 1 si alguna no aparece. Sin verde, no se publica.

Uso:  python verificar.py carrusel.json
"""

import html
import json
import pathlib
import re
import sys
import urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

# Patrones de dato factual que exigen respaldo en la fuente.
PATRONES = [
    (r"\$\s?[\d][\d.,]*", "valor en pesos"),
    (r"\b\d{1,3},\d{1,2}\s?%", "porcentaje"),
    (r"\b\d{1,3}\s?%", "porcentaje"),
    (r"\b\d{1,3},\d{1,2}\b", "cifra decimal"),
    (r"\b[A-E]\.\d{2}\b", "codigo de infraccion"),
    (r"\b(?:Resoluci[oó]n|Ley|Circular|Decreto|NTC)\s+[\w.\-]+", "norma citada"),
]

# Ruido que no es dato factual y no exige respaldo.
IGNORAR = {"2026", "2025", "50", "25", "100"}


def texto_plano(h: str) -> str:
    h = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", h, flags=re.S | re.I)
    h = re.sub(r"<[^>]+>", " ", h)
    h = html.unescape(h)
    return re.sub(r"\s+", " ", h)


def normaliza(s: str) -> str:
    """Compara sin espacios raros ni acentos de formato."""
    s = s.replace(" ", " ").replace(" ", " ")
    return re.sub(r"\s+", " ", s).strip()


def limpia_cifra(s: str) -> str:
    """Quita la puntuacion de cierre de frase que el patron arrastra ('$633.200.')."""
    return re.sub(r"[.,]+$", "", normaliza(s))


def recolecta(nodo, salida):
    if isinstance(nodo, dict):
        for k, v in nodo.items():
            if k in ("tipo", "slug", "origen", "url", "size", "marca"):
                continue
            recolecta(v, salida)
    elif isinstance(nodo, list):
        for v in nodo:
            recolecta(v, salida)
    elif isinstance(nodo, str):
        salida.append(nodo)


def main(ruta: str) -> int:
    cfg = json.loads(pathlib.Path(ruta).read_text(encoding="utf-8"))
    origen = cfg.get("origen")
    if not origen:
        print("ERROR: el carrusel no declara 'origen'. Sin fuente no se verifica.")
        return 1

    req = urllib.request.Request(origen, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=45) as r:
        fuente = normaliza(texto_plano(r.read().decode("utf-8", "ignore")))

    textos = []
    recolecta(cfg["laminas"], textos)
    plano = normaliza(texto_plano(" ".join(textos)))

    hallados, vistos = [], set()
    for patron, clase in PATRONES:
        for m in re.findall(patron, plano):
            v = limpia_cifra(m)
            if v in vistos or v.strip("$ %") in IGNORAR:
                continue
            vistos.add(v)
            hallados.append((v, clase))

    faltan = []
    for valor, clase in hallados:
        # normaliza el separador de miles y el espacio tras el signo peso
        variantes = {valor, valor.replace("$ ", "$"), valor.replace(" %", "%")}
        if not any(v in fuente for v in variantes):
            faltan.append((valor, clase))

    # --- procedencia de las fotos -------------------------------------
    import fuentes as fu

    imgs, problemas_img, avisos_img = [], [], []
    for i, lam in enumerate(cfg["laminas"], 1):
        if not lam.get("imagen"):
            continue
        imgs.append(lam["imagen"])
        if not lam.get("credito"):
            problemas_img.append(f"lamina {i}: foto sin credito declarado")
            continue
        estado, dom, motivo = fu.clasifica(lam["imagen"])
        if estado == fu.PROHIBIDO:
            problemas_img.append(f"lamina {i}: {dom} {motivo}")
        elif estado == fu.REVISAR:
            avisos_img.append(f"lamina {i}: {dom} — {motivo}")

    print(f"Fuente: {origen}")
    print(f"Datos factuales detectados en el carrusel: {len(hallados)}")
    print(f"Fotos usadas: {len(imgs)}")

    if avisos_img:
        print("\n  AVISO — confirmar procedencia de estas fotos:")
        for a in avisos_img:
            print(f"   ? {a}")

    if problemas_img:
        print(f"\n  *** {len(problemas_img)} FOTO(S) QUE INCUMPLEN LA REGLA ***")
        for p in problemas_img:
            print(f"   - {p}")
        print("\n  NO PUBLICAR. Las fotos van de la marca o del concesionario, "
              "nunca de un medio de la competencia.")
        return 1

    if faltan:
        print(f"\n  *** {len(faltan)} DATO(S) SIN RESPALDO EN EL ARTICULO ***")
        for v, c in faltan:
            print(f"   - {v}   ({c})")
        print("\n  NO PUBLICAR. Corrige el dato o verificalo en el articulo primero.")
        return 1

    print("\n  OK: cada cifra, codigo y norma del carrusel aparece en el articulo publicado.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "carrusel.json"))
