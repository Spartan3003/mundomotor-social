#!/usr/bin/env python3
"""
Mundo Motor — arma el paquete de publicacion de Instagram.

Una pieza no es solo la imagen. Este modulo produce, a partir del mismo JSON:
  - publicacion.txt : el caption listo para pegar (o para la API)
  - paquete.json    : caption + alt text por lamina + rutas de imagen,
                      que es lo que consumira el publicador automatico
  - revision.txt    : checklist de buenas practicas, con lo que falla marcado

Regla del medio: el caption tampoco puede afirmar nada que no este en el
articulo de origen. verificar.py revisa el JSON entero, caption incluido.

Uso:  python paquete.py carrusel.json
"""

import json
import pathlib
import re
import sys

BASE = pathlib.Path(__file__).parent

# La API de Instagram corta el caption en 2.200 caracteres.
MAX_CAPTION = 2200
# Socialinsider (9,1M posts) midio que el caption corto rinde mejor, y que
# carrusel + caption corto es la combinacion con mas engagement. Como nosotros
# ademas necesitamos texto para la busqueda interna y para Google, el limite
# operativo es un punto medio: unas 90 palabras.
RECOMENDADO_CAPTION = 620
# Lo visible antes del "... mas" ronda los 125 caracteres. Instagram no publica
# la cifra exacta; en la practica son unas dos lineas.
MAX_GANCHO = 125
MAX_ALT = 1000
# Instagram limito los hashtags a 5 por publicacion en diciembre de 2025.
TOPE_HASHTAGS = 5


def construye_caption(p: dict) -> str:
    partes = [p["gancho"].strip(), ""]
    partes += [b.strip() for b in p.get("cuerpo", [])]
    if p.get("cta"):
        partes += ["", p["cta"].strip()]
    if p.get("fuente_texto"):
        partes += ["", p["fuente_texto"].strip()]
    if p.get("menciones"):
        partes += ["", " ".join(p["menciones"])]
    if p.get("hashtags"):
        partes += ["", " ".join(p["hashtags"])]
    return "\n".join(partes).strip()


def revisa(cfg: dict, caption: str) -> list:
    """Devuelve la lista de incumplimientos. Vacia = todo en orden."""
    p = cfg["publicacion"]
    laminas = cfg["laminas"]
    fallos = []

    # Se mide solo el copy: la atribucion de fuentes y los hashtags no cuentan,
    # porque son obligacion editorial y la regla no debe empujar a quitarlos.
    copy = " ".join([p["gancho"]] + p.get("cuerpo", []) + [p.get("cta", "")])
    if len(caption) > MAX_CAPTION:
        fallos.append(f"El caption tiene {len(caption)} caracteres; el maximo es {MAX_CAPTION}.")
    elif len(copy) > RECOMENDADO_CAPTION:
        fallos.append(
            f"El copy tiene {len(copy)} caracteres ({len(copy.split())} palabras), sin contar "
            f"fuentes ni hashtags. Por encima de {RECOMENDADO_CAPTION} rinde peor en carrusel: "
            "el detalle va en las laminas, no en el texto."
        )
    if len(p["gancho"]) > MAX_GANCHO:
        fallos.append(
            f"El gancho tiene {len(p['gancho'])} caracteres. Por encima de {MAX_GANCHO} "
            "se corta antes del '... mas' y se pierde."
        )
    if p["gancho"].rstrip().endswith(":"):
        fallos.append("El gancho termina en dos puntos: obliga a abrir para entenderlo.")

    alt = p.get("alt", [])
    if len(alt) != len(laminas):
        fallos.append(f"Hay {len(alt)} textos alternativos para {len(laminas)} laminas.")
    for i, a in enumerate(alt, 1):
        if len(a) > MAX_ALT:
            fallos.append(f"El alt de la lamina {i} supera {MAX_ALT} caracteres.")
        if len(a) < 25:
            fallos.append(f"El alt de la lamina {i} es demasiado corto para describir la imagen.")

    if not p.get("cta"):
        fallos.append("Falta la llamada a la accion (guardar o compartir).")

    # Hashtags: Metricool midio sobre 24M posts que su uso acompana -31,7% de
    # vistas y -33,9% de interacciones. Se usan pocos y solo si aportan contexto.
    n_tags = len(p.get("hashtags", []))
    if n_tags > TOPE_HASHTAGS:
        fallos.append(
            f"Lleva {n_tags} hashtags y desde diciembre de 2025 Instagram solo admite "
            f"{TOPE_HASHTAGS}. Mosseri ya aclaro que no dan alcance: sirven para "
            "describir el tema y para la busqueda interna."
        )
    if n_tags > 3:
        fallos.append(
            f"Lleva {n_tags} hashtags. Con 3 hiperrelevantes basta; mas no aporta."
        )

    # Una pregunta al cierre multiplica los comentarios (+36,7% segun Metricool).
    if not re.search(r"\?\s*$", (p.get("cta") or "").strip()) and \
       not any("?" in b for b in p.get("cuerpo", [])):
        fallos.append(
            "El caption no plantea ninguna pregunta. Cerrar con una pregunta real "
            "sube los comentarios de forma consistente."
        )

    # Cebo de interaccion: pedir interaccion a cambio de algo. Instagram lo castiga.
    # Ojo: preguntar de verdad NO es cebo; lo es condicionar o regalar.
    cebos = [r"comenta\s+[\"']?\w+[\"']?\s+(y|para)\s+te\s+(mando|env[ií]o)",
             r"etiqueta a \d+", r"dale like si", r"sigueme para",
             r"comparte para participar", r"comenta para recibir"]
    for c in cebos:
        if re.search(c, caption, re.I):
            fallos.append(f"El caption contiene cebo de interaccion ('{c}'): Instagram lo castiga.")

    if len(laminas) < 3:
        fallos.append("Un carrusel de menos de 3 laminas no aprovecha el formato.")

    return fallos


def main(ruta: str) -> int:
    cfg = json.loads(pathlib.Path(ruta).read_text(encoding="utf-8"))
    if "publicacion" not in cfg:
        print("ERROR: el JSON no trae bloque 'publicacion'. Sin copy no hay pieza.")
        return 1

    p = cfg["publicacion"]
    caption = construye_caption(p)
    destino = BASE / "salida" / cfg["slug"]
    destino.mkdir(parents=True, exist_ok=True)

    (destino / "publicacion.txt").write_text(caption, encoding="utf-8")

    imgs = sorted(destino.glob("[0-9][0-9].png"))
    (destino / "paquete.json").write_text(json.dumps({
        "slug": cfg["slug"],
        "origen": cfg["origen"],
        "caption": caption,
        "ubicacion": p.get("ubicacion"),
        "imagenes": [{"archivo": f.name, "alt": a}
                     for f, a in zip(imgs, p.get("alt", []))],
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    fallos = revisa(cfg, caption)
    informe = ["REVISION DE LA PUBLICACION", "=" * 40,
               f"Laminas: {len(cfg['laminas'])}   Imagenes generadas: {len(imgs)}",
               f"Caption: {len(caption)} caracteres",
               f"Gancho: {len(p['gancho'])} caracteres",
               f"Hashtags: {len(p.get('hashtags', []))}", ""]
    if fallos:
        informe.append(f"*** {len(fallos)} PUNTO(S) A CORREGIR ***")
        informe += [f" - {f}" for f in fallos]
    else:
        informe.append("OK: la publicacion cumple el checklist.")
    texto = "\n".join(informe)
    (destino / "revision.txt").write_text(texto, encoding="utf-8")
    print(texto)
    print(f"\nPaquete en: {destino}")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else str(BASE / "carrusel.json")))
