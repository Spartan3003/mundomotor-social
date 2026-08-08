#!/usr/bin/env python3
"""
Mundo Motor — produce la pieza completa de Instagram en un solo paso.

    python producir.py carrusel.json

Encadena, en este orden y frenando ante el primer fallo:
  1. verificar.py : que cada cifra este en el articulo publicado y que las
                    fotos vengan de la marca, no de la competencia.
  2. build.py     : las laminas en PNG 1080x1350.
  3. paquete.py   : caption, alt text y checklist de buenas practicas.

Si el paso 1 falla, no se genera nada. Esa es la idea: en un medio serio, el
control de veracidad va antes que el diseno, no despues.
"""

import pathlib
import subprocess
import sys

BASE = pathlib.Path(__file__).parent
PASOS = [
    ("verificar.py", "Comprobando datos y procedencia de fotos"),
    ("build.py", "Generando las laminas"),
    ("paquete.py", "Armando copy, alt text y revision"),
]


def main() -> int:
    cfg = sys.argv[1] if len(sys.argv) > 1 else "carrusel.json"
    ruta = pathlib.Path(cfg)
    if not ruta.is_absolute():
        ruta = BASE / cfg
    if not ruta.exists():
        print(f"No encuentro {ruta}")
        return 1

    for script, titulo in PASOS:
        print(f"\n=== {titulo} " + "=" * max(0, 52 - len(titulo)))
        r = subprocess.run([sys.executable, str(BASE / script), str(ruta)])
        if r.returncode != 0:
            if script == "verificar.py":
                print("\nDETENIDO: no se genera la pieza hasta corregir lo anterior.")
                return 1
            print("\nLa pieza se genero, pero revisa los puntos marcados antes de publicar.")
            return 1

    print("\n" + "=" * 60)
    print("PIEZA LISTA. Revisa las imagenes y el archivo publicacion.txt")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
