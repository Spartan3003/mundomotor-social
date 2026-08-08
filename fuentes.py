#!/usr/bin/env python3
"""
Mundo Motor — procedencia permitida de las fotos.

Regla de Nicolas (7-ago-2026): las imagenes de motos se toman del fabricante
o del concesionario que vende esa moto. NUNCA de un medio de comunicacion
de la competencia.

Este modulo clasifica el dominio de una imagen en:
  PROHIBIDO  -> medio de la competencia u otro medio. Bloquea la publicacion.
  OFICIAL    -> web de marca o distribuidor oficial. Permitido.
  REVISAR    -> desconocido. Puede ser un concesionario legitimo; lo decide
                un humano antes de publicar.
"""

from urllib.parse import urlparse

# Medios: la competencia directa (radar editorial) y prensa en general.
COMPETENCIA = {
    "motociclismo.es", "demotos.com.co", "motosan.es", "lamoto.com.ar",
    "publimotos.com", "motorpasionmoto.com", "motorpasion.com", "mundomotero.com",
    "revistamoto.com", "rushlane.com", "bikewale.com", "motorcyclenews.com",
    "rideapart.com", "visordown.com", "motorbikemag.es", "todocircuito.com",
    "soymotero.net", "motor.com.co", "lifestyle.fyi", "elcarrocolombiano.com",
    "cycleworld.com", "motorcycle.com", "motorbit.com", "autobild.es", "km77.com",
    "eltiempo.com", "semana.com", "elespectador.com", "infobae.com", "larepublica.co",
    "portafolio.co", "caracol.com.co", "rcnradio.com", "wradio.com.co", "pulzo.com",
    "eluniversal.com.co", "elcolombiano.com", "elheraldo.co", "bikedekho.com",
    "zigwheels.com", "autocarindia.com", "webbikeworld.com", "asphaltandrubber.com",
}

# Marcas y distribuidores oficiales presentes en Colombia y la region.
OFICIALES = {
    "incolmotos-yamaha.com.co", "yamaha-motor.com.co", "yamaha-motor.com",
    "honda.com.co", "hondamotos.com.co", "honda.com", "powersports.honda.com",
    "suzukimotor.com.co", "globalsuzuki.com", "suzukicycles.com",
    "kawasaki.com.co", "kawasaki.com", "kawasaki.es",
    "aktmotos.com", "auteco.com.co", "automotoresauteco.com",
    "bajaj.com.co", "bajajauto.com", "heromotocorp.com", "heromotos.com.co",
    "tvsmotor.com", "tvsmotor.com.co", "ktm.com", "royalenfield.com",
    "cfmoto.com", "cfmotocolombia.com", "vogemoto.com", "voge.com",
    "benelli.com", "qjmotor.com", "ducati.com", "bmw-motorrad.com",
    "bmw-motorrad.com.co", "triumphmotorcycles.com", "harley-davidson.com",
    "aprilia.com", "piaggio.com", "vespa.com", "husqvarna-motorcycles.com",
    "zontes.com", "italika.com.mx", "victorymotos.com.co", "starmotos.com.co",
    "yamahamotorcolombia.com", "suzuki.com.co",
}

PROHIBIDO, OFICIAL, REVISAR = "PROHIBIDO", "OFICIAL", "REVISAR"


def dominio(url: str) -> str:
    d = (urlparse(url).netloc or url).lower()
    return d[4:] if d.startswith("www.") else d


def clasifica(url: str):
    """Devuelve (estado, dominio, explicacion)."""
    d = dominio(url)
    for mal in COMPETENCIA:
        if d == mal or d.endswith("." + mal):
            return PROHIBIDO, d, "es un medio de comunicacion; la regla lo prohibe"
    for ok in OFICIALES:
        if d == ok or d.endswith("." + ok):
            return OFICIAL, d, "web oficial de marca o distribuidor"
    return REVISAR, d, "origen desconocido: confirmar que sea marca o concesionario"


if __name__ == "__main__":
    import sys
    for u in sys.argv[1:]:
        estado, d, motivo = clasifica(u)
        print(f"{estado:9} {d:34} {motivo}")
