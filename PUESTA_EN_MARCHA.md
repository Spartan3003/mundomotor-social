# Puesta en marcha

Todo lo que sigue son cosas que solo puedes hacer tú, porque exigen tus
credenciales. Están en orden y ninguna toma más de veinte minutos.

---

## 1. Subir el repositorio (5 minutos)

GitHub CLI ya está instalado en el equipo. Desde `C:\Users\nicol\MundoMotor\social`:

```
gh auth login
```

Elige **GitHub.com** → **HTTPS** → **Yes** (autenticar Git) → **Login with a web
browser**. Copia el código que te muestra, pégalo en el navegador y listo. La
credencial queda guardada en tu equipo.

Después, crea el repositorio y súbelo:

```
gh repo create mundomotor-social --public --source=. --remote=origin --push
```

**Público, no privado.** Dos motivos: GitHub Pages necesita repositorio público
para servir las imágenes en el plan gratuito, y GitHub Actions no consume
minutos de cuota en repos públicos. El repositorio solo contiene el generador y
los textos de las piezas: nada sensible. Los tokens van en *secrets*, que no se
publican nunca.

## 2. Activar GitHub Pages (2 minutos)

En el repositorio: **Settings → Pages**. En *Source* elige **Deploy from a
branch**, rama `main`, carpeta `/docs`. Guarda.

A los pocos minutos tendrás la URL, que será:

```
https://spartan3003.github.io/mundomotor-social
```

Esa es la raíz pública desde donde Instagram descargará las imágenes.

Guárdala como variable del repositorio en **Settings → Secrets and variables →
Actions → Variables → New repository variable**:

- Nombre: `BASE_URL`
- Valor: `https://spartan3003.github.io/mundomotor-social`

Y una segunda variable, que fija la versión de la API de Meta:

- Nombre: `GRAPH_VERSION`
- Valor: `v21.0`

## 3. Crear la app de Meta (20 minutos)

Esto es lo único tedioso, y se hace una sola vez.

**Antes de empezar**, confirma que la cuenta `@mundomotor.bike` es **profesional**
(Business o Creator). Si es personal, cámbiala en Configuración → Tipo de cuenta.

1. Entra a [developers.facebook.com](https://developers.facebook.com) con tu
   cuenta y crea una app.
2. Añade el producto **Instagram** y configura **Instagram API with Instagram
   Login** (la variante que **no** exige vincular una página de Facebook).
3. En los permisos, pide `instagram_business_basic` e
   `instagram_business_content_publish`.
4. **No necesitas revisión de Meta.** Como vas a publicar solo en tu propia
   cuenta, basta el *Standard Access*, que se concede automáticamente siempre
   que añadas la cuenta de Instagram como usuaria con rol en la app.
5. Genera un **token de larga duración** y anota también el **ID de la cuenta**
   de Instagram.

La documentación oficial del flujo está en
`developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login`.
Los menús de Meta cambian cada pocos meses, así que si algo no coincide con
estos pasos, avísame y lo revisamos juntos sobre la pantalla.

Guarda las dos credenciales como **secrets** (no como variables) en
**Settings → Secrets and variables → Actions → Secrets**:

- `IG_USER_ID` — el identificador de la cuenta
- `IG_TOKEN` — el token de larga duración

⚠️ **El token caduca a los 60 días.** El actual se emitió el 7 de agosto de
2026, así que vence alrededor del **6 de octubre**; un workflow te avisa unos
quince días antes. Renovarlo es generar otro, reemplazar el secret y poner la
fecha nueva en `banco/token_emitido.txt`.

## 3 bis. Avisos por WhatsApp (2 minutos)

Los avisos importantes —publicación fallida, banco vacío, token por caducar—
llegan por WhatsApp además de por issue, usando CallMebot, el mismo servicio
del radar de empleo.

`CALLMEBOT_PHONE` ya está configurado. Falta añadir un secret más:

- `CALLMEBOT_APIKEY` — la clave de CallMebot

Sin ese dato el sistema funciona igual, pero solo avisa por GitHub.

## 4. Probar sin publicar (2 minutos)

En la pestaña **Actions** del repositorio, abre *Publicar carrusel en Instagram*
y pulsa **Run workflow** dejando `simular` en **true**.

Eso verifica los datos, genera las nueve imágenes, arma el copy y te muestra
exactamente qué se publicaría, **sin publicar nada**. Las imágenes quedan
descargables como artefacto del run.

Cuando el resultado te convenza, vuelve a lanzarlo con `simular` en **false** y
saldrá de verdad.

## 5. A partir de ahí

El workflow corre solo de lunes a viernes en las franjas configuradas. Tú solo
tienes que vigilar que el banco no se vacíe: cuando baje de tres piezas, el
propio run te lo avisa en el log.

---

## Cosas que conviene revisar en Instagram esta semana

**Estado de la cuenta** (Configuración → Cuenta). Desde el 30 de abril de 2026
Instagram penaliza el contenido no original también en fotos y carruseles.
Confirma que la cuenta está limpia antes de invertir en esto.

**Indexación en buscadores** (Configuración → Privacidad de la cuenta). Google
indexa el contenido público de las cuentas profesionales desde julio de 2025 y
viene activado por defecto; verifica que sigue encendido.

**Search Console.** Desde el 29 de julio de 2026 puedes dar de alta la cuenta de
Instagram como *platform property* y ver qué consultas de Google traen tráfico a
tus publicaciones. Para ti, que vives del SEO, es medición gratis de un canal
que hasta ahora era una caja negra.

**Horas más activas** (Instagram Insights → Tu audiencia). Ese dato de tu propia
cuenta vale más que cualquier estudio global: si contradice el calendario que
programamos, mandan tus datos y ajustamos los cron.
