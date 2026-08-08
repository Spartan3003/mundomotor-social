#!/usr/bin/env python3
"""
Mundo Motor — publica el carrusel en Instagram por la API oficial.

Usa la Instagram Platform (Content Publishing). Es gratuita y no necesita
revision de Meta mientras se publique en la cuenta propia.

Flujo oficial de un carrusel:
  1. Un contenedor por imagen  -> POST /{ig_id}/media  (is_carousel_item=true)
  2. Un contenedor del carrusel -> POST /{ig_id}/media  (media_type=CAROUSEL)
  3. Publicar                   -> POST /{ig_id}/media_publish

Requisitos que impone Meta y que aqui se respetan:
  - Las imagenes deben estar en una URL publica: Meta las descarga.
  - JPEG, maximo 8 MB, proporcion entre 4:5 y 1.91:1 (nuestro 1080x1350 = 4:5).
  - El alt text solo se admite en imagenes, no en Reels ni Stories.

Variables de entorno:
  IG_USER_ID     id de la cuenta profesional de Instagram
  IG_TOKEN       token de acceso de larga duracion (caduca a los 60 dias)
  BASE_URL       raiz publica donde viven las imagenes
  GRAPH_VERSION  version de la Graph API (por defecto v21.0)

Uso:
  python publicar_ig.py salida/<slug>/paquete.json           publica
  python publicar_ig.py salida/<slug>/paquete.json --simular  solo comprueba
"""

import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

GRAPH = os.environ.get("GRAPH_VERSION", "v21.0")
API = f"https://graph.instagram.com/{GRAPH}"


def pide(url: str, datos: dict = None, metodo: str = "POST"):
    cuerpo = urllib.parse.urlencode(datos).encode() if datos else None
    req = urllib.request.Request(url, data=cuerpo, method=metodo)
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        detalle = e.read().decode("utf-8", "ignore")
        raise SystemExit(f"\nLa API respondio {e.code}:\n{detalle}\n")


def espera_contenedor(cid: str, token: str, intentos: int = 30):
    """Meta procesa el contenedor de forma asincrona. Hay que esperar a FINISHED."""
    for i in range(intentos):
        r = pide(f"{API}/{cid}?fields=status_code&access_token={token}", metodo="GET")
        estado = r.get("status_code")
        if estado == "FINISHED":
            return True
        if estado == "ERROR":
            raise SystemExit(f"El contenedor {cid} fallo al procesarse: {r}")
        time.sleep(3)
    raise SystemExit(f"El contenedor {cid} no termino de procesarse a tiempo.")


def main() -> int:
    ruta = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "")
    simular = "--simular" in sys.argv
    if not ruta.exists():
        print("Uso: python publicar_ig.py salida/<slug>/paquete.json [--simular]")
        return 1

    paquete = json.loads(ruta.read_text(encoding="utf-8"))
    ig_id = os.environ.get("IG_USER_ID")
    token = os.environ.get("IG_TOKEN")
    base = (os.environ.get("BASE_URL") or "").rstrip("/")

    faltan = [n for n, v in
              (("IG_USER_ID", ig_id), ("IG_TOKEN", token), ("BASE_URL", base)) if not v]
    if faltan and not simular:
        print("Faltan variables de entorno: " + ", ".join(faltan))
        return 1

    slug = paquete["slug"]
    imagenes = paquete["imagenes"]
    caption = paquete["caption"]

    if len(imagenes) > 10:
        print(f"El carrusel trae {len(imagenes)} imagenes y el maximo son 10.")
        return 1

    urls = [f"{base}/{slug}/{im['archivo']}" for im in imagenes]
    print(f"Carrusel '{slug}' — {len(urls)} laminas")
    for u, im in zip(urls, imagenes):
        print(f"  {u}")
        print(f"      alt: {im['alt'][:70]}...")
    print(f"\nCaption: {len(caption)} caracteres")

    if simular:
        print("\n[simulacion] No se publico nada.")
        return 0

    # 1) un contenedor por lamina
    hijos = []
    for u, im in zip(urls, imagenes):
        r = pide(f"{API}/{ig_id}/media", {
            "image_url": u,
            "is_carousel_item": "true",
            "alt_text": im["alt"],
            "access_token": token,
        })
        print(f"  contenedor {r['id']} <- {im['archivo']}")
        hijos.append(r["id"])

    for h in hijos:
        espera_contenedor(h, token)

    # 2) contenedor del carrusel
    padre = pide(f"{API}/{ig_id}/media", {
        "media_type": "CAROUSEL",
        "children": ",".join(hijos),
        "caption": caption,
        "access_token": token,
    })
    espera_contenedor(padre["id"], token)

    # 3) publicar
    pub = pide(f"{API}/{ig_id}/media_publish", {
        "creation_id": padre["id"],
        "access_token": token,
    })
    print(f"\nPUBLICADO. id del post: {pub.get('id')}")

    limite = pide(f"{API}/{ig_id}/content_publishing_limit"
                  f"?fields=quota_usage&access_token={token}", metodo="GET")
    print(f"Cuota usada en 24 h: {limite.get('data', [{}])[0].get('quota_usage', '?')}/100")
    return 0


if __name__ == "__main__":
    sys.exit(main())
