# Mundo Motor — máquina de contenido para Instagram

Genera carruseles 1080×1350 (4:5) con la identidad del medio, su copy y su
texto alternativo, a partir de un artículo **ya publicado y revisado**.

## Cómo se usa

```
python producir.py carrusel.json
```

Eso encadena tres pasos y se detiene ante el primer problema:

1. **`verificar.py`** — comprueba que cada cifra, código de infracción y norma
   citada en el carrusel **aparezca literalmente en el artículo de origen**, y
   que las fotos no vengan de un medio de la competencia. Si algo falla, no se
   genera nada.
2. **`build.py`** — renderiza las láminas a PNG con Chrome headless.
3. **`paquete.py`** — arma el caption, el alt text de cada lámina y una
   revisión con el checklist de buenas prácticas.

La salida queda en `salida/<slug>/`: las imágenes numeradas, `publicacion.txt`
(el copy listo para pegar), `paquete.json` (lo que consumirá el publicador
automático) y `revision.txt`.

## Las dos reglas que el código hace cumplir

**Veracidad.** Una lámina nunca puede afirmar un dato que no esté en el
artículo publicado. La automatización redistribuye lo ya verificado por un
humano; no genera hechos nuevos. Por eso el verificador corre *antes* que el
diseño y no después.

**Procedencia de las fotos.** Las imágenes de motos se toman del fabricante o
del concesionario que vende esa moto. Nunca de un medio de la competencia.
`fuentes.py` clasifica cada dominio en PROHIBIDO, OFICIAL o REVISAR; lo
prohibido bloquea la publicación y lo desconocido pide confirmación humana.

## Estructura del JSON

Dos bloques: `laminas` (lo que se ve) y `publicacion` (lo que se lee).

Tipos de lámina disponibles: `portada`, `foto`, `cifra`, `tabla`, `lista`,
`destacado`, `comparativa` (el VS de dos motos), `texto` y `cierre`.

En los textos se puede usar `<em>` para pintar una palabra en amarillo y
`<mark>` para resaltarla con fondo amarillo.

Una lámina con `imagen` **obliga** a declarar `credito`; si falta, el
generador se niega a montarla.

## Identidad

Negro `#0B0B0B`, amarillo `#FDC207`, **Anton** para titulares y **Poppins**
para texto. Las fuentes y el logo van embebidos en base64, así que el render
es idéntico siempre y funciona sin conexión.

## Requisitos

Chrome instalado y Python 3. Nada más: no hay dependencias externas ni
servicios de pago.
