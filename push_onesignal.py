#!/usr/bin/env python3
"""
Mundo Motor — manda la notificacion push del dia por OneSignal.

POR QUE EXISTE
El plugin de WordPress disparaba un push por CADA articulo publicado: 3 a 5
al dia sobre los mismos ~87 suscriptores. Resultado medido el 8-ago-2026:
CTR global del 0,37 % y una caida del 6,45 % de suscriptores en 30 dias.
Aqui se manda UNO al dia, elegido y redactado.

QUE MANDA
La misma pieza que ese dia sale en Instagram, porque ya pasa el control de
veracidad y ya tiene un gancho escrito para enganchar. Pero el push NO
apunta a Instagram: apunta al ARTICULO de mundomotor.bike, que es a donde
queremos llevar el trafico.

EL CRITERIO EDITORIAL, QUE SALE DE LOS DATOS PROPIOS
Los unicos envios con CTR por encima de cero fueron de servicio -- licencia
A1/A2 (2,30 %), casco certificado (1,16 %) --, mientras que MotoGP, Ducati,
Triumph, Royal Enfield y los lanzamientos internacionales dieron 0,00 %
sin excepcion. Un push interrumpe a alguien en el celular: se reserva para
lo que le ahorra plata, tiempo o un problema legal.

Variables de entorno:
  ONESIGNAL_APP_ID   identificador de la app (no es secreto)
  ONESIGNAL_API_KEY  clave REST de OneSignal
  BASE_URL           raiz publica de las imagenes (para la miniatura)

Uso:
  python push_onesignal.py banco/pendientes/<slug>.json            envia
  python push_onesignal.py banco/pendientes/<slug>.json --simular  solo muestra
"""

import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.request

BASE = pathlib.Path(__file__).parent
API = "https://api.onesignal.com/notifications"
API_SEGMENTOS = "https://api.onesignal.com/apps/{app_id}/segments?limit=100"

# Nombres de segmento que OneSignal ha usado como "todo el mundo" segun la
# epoca en que se creo la app. El 10-ago-2026 el push fallo con
# "All included players are not subscribed" porque el script mandaba al
# segmento "Subscribed Users", que en esta app NO existe (las apps recientes
# lo llaman "Total Subscriptions"). Por eso ahora los segmentos se LEEN de la
# API y esta lista solo define el orden de preferencia / el plan B.
SEGMENTOS_CONOCIDOS = [
    "Total Subscriptions",
    "Subscribed Users",
    "Active Subscriptions",
    "Active Users",
]

# Lo que Chrome muestra antes de cortar. No son limites duros de la API:
# son los limites de lo que la persona llega a leer.
MAX_TITULO = 60
MAX_TEXTO = 120


def limpia(s: str) -> str:
    """Quita el marcado de las laminas: en un push no se ve nada de eso."""
    s = re.sub(r"<[^>]+>", "", s or "")
    return re.sub(r"\s+", " ", s).strip()


def peticion(url: str, api_key: str, datos=None):
    """GET (o POST si hay datos) contra OneSignal, probando los dos esquemas
    de Authorization: las claves nuevas usan `Key ...` y las Legacy -- como la
    del plugin de WordPress -- usan `Basic ...`.

    Devuelve (respuesta_json, None) si funciono, o (None, detalle_del_error).
    """
    ultimo = ""
    for esquema in ("Key", "Basic"):
        req = urllib.request.Request(
            url,
            data=json.dumps(datos).encode("utf-8") if datos is not None else None,
            headers={"Authorization": f"{esquema} {api_key}",
                     "Content-Type": "application/json"},
            method="POST" if datos is not None else "GET")
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode()), None
        except urllib.error.HTTPError as e:
            detalle = e.read().decode("utf-8", "ignore")
            ultimo = f"{e.code}: {detalle}"
            if e.code in (401, 403):
                continue  # la clave no vale con este esquema: probar el otro
            return None, ultimo
        except Exception as e:
            return None, str(e)
    return None, ultimo


def segmentos_a_probar(app_id: str, api_key: str):
    """Lee de la API los segmentos REALES de la app y los devuelve en orden
    de preferencia. Si la lectura falla, devuelve los nombres conocidos.

    Leerlos en vez de fijarlos es lo que evita que esto vuelva a romperse si
    OneSignal renombra sus segmentos por defecto o alguien los edita en el
    panel.
    """
    resp, err = peticion(API_SEGMENTOS.format(app_id=app_id), api_key)
    if not resp or not resp.get("segments"):
        print(f"  (aviso) no pude listar los segmentos ({err or 'respuesta vacia'}); "
              f"pruebo los nombres estandar.")
        return list(SEGMENTOS_CONOCIDOS)
    nombres = [s.get("name") for s in resp["segments"] if s.get("name")]
    print(f"Segmentos reales de la app: {nombres}")
    preferidos = [n for n in SEGMENTOS_CONOCIDOS if n in nombres]
    resto = [n for n in nombres if n not in SEGMENTOS_CONOCIDOS]
    return preferidos + resto


def arma_push(cfg: dict):
    """Devuelve el push declarado en la pieza, o None si no lo lleva.

    El push es OPT-IN a proposito. Interrumpir a alguien en el celular tiene
    que ser una decision consciente del redactor, no el efecto colateral de
    haber publicado algo. Ese fue exactamente el problema del plugin: mandaba
    por defecto, y por defecto se manda todo.
    """
    p = cfg.get("publicacion", {})
    push = p.get("push")
    if not push or not push.get("titulo") or not push.get("texto"):
        return None
    return {"titulo": limpia(push["titulo"]), "texto": limpia(push["texto"])}


def main() -> int:
    ruta = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "")
    simular = "--simular" in sys.argv
    if not ruta.exists():
        print("Uso: python push_onesignal.py banco/pendientes/<slug>.json [--simular]")
        return 1

    cfg = json.loads(ruta.read_text(encoding="utf-8"))
    app_id = os.environ.get("ONESIGNAL_APP_ID")
    api_key = os.environ.get("ONESIGNAL_API_KEY")
    base_url = (os.environ.get("BASE_URL") or "").rstrip("/")

    destino = cfg.get("origen")
    if not destino:
        print("La pieza no declara 'origen': sin articulo al que llevar el clic.")
        return 1

    p = arma_push(cfg)
    if p is None:
        print(f"La pieza '{cfg['slug']}' no declara bloque 'push'.")
        print("No se envia notificacion: el push es opt-in y esta pieza no lo pidio.")
        return 0

    imagen = f"{base_url}/{cfg['slug']}/01.jpg" if base_url else None

    print(f"Pieza    : {cfg['slug']}")
    print(f"Titulo   : {p['titulo']}  ({len(p['titulo'])} caracteres)")
    print(f"Texto    : {p['texto']}  ({len(p['texto'])} caracteres)")
    print(f"Destino  : {destino}")
    print(f"Imagen   : {imagen}")
    if len(p["titulo"]) > MAX_TITULO:
        print(f"  (aviso) el titulo se cortara en pantalla (>{MAX_TITULO}).")
    if len(p["texto"]) > MAX_TEXTO:
        print(f"  (aviso) el texto se cortara en pantalla (>{MAX_TEXTO}).")

    if simular:
        print("\n[simulacion] No se envio nada.")
        return 0

    faltan = [n for n, v in (("ONESIGNAL_APP_ID", app_id),
                             ("ONESIGNAL_API_KEY", api_key)) if not v]
    if faltan:
        print("Faltan variables de entorno: " + ", ".join(faltan))
        return 1

    cuerpo = {
        "app_id": app_id,
        "headings": {"en": p["titulo"], "es": p["titulo"]},
        "contents": {"en": p["texto"], "es": p["texto"]},
        "url": destino,
    }
    if imagen:
        # chrome_web_image es el que aplica al push web, que es el canal real
        # aqui; big_picture se manda por si algun dia hay app.
        cuerpo["chrome_web_image"] = imagen
        cuerpo["big_picture"] = imagen

    # Se intenta segmento por segmento. Si OneSignal responde que el segmento
    # no tiene suscriptores (el error del 10-ago-2026), se pasa al siguiente;
    # cualquier otro error corta. Solo puede haber UN envio: al primer exito
    # se termina.
    ultimo_error = ""
    for segmento in segmentos_a_probar(app_id, api_key):
        cuerpo["included_segments"] = [segmento]
        resp, err = peticion(API, api_key, cuerpo)
        if resp is None:
            print(f"\nOneSignal no acepto la peticion: {err}")
            return 1
        errores = resp.get("errors") or []
        if not errores:
            print(f"\nPUSH ENVIADO. segmento: {segmento}   id: {resp.get('id')}   "
                  f"destinatarios: {resp.get('recipients', '?')}")
            return 0
        ultimo_error = f"[{segmento}] {errores}"
        texto_err = " ".join(str(e) for e in errores).lower()
        if "not subscribed" in texto_err or "segment" in texto_err:
            print(f"  (el segmento '{segmento}' no sirvio: {errores}; pruebo el siguiente)")
            continue
        break  # error de otra naturaleza: reintentar no lo arregla

    print(f"\nOneSignal devolvio errores: {ultimo_error}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
