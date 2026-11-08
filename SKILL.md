---
name: aprende
description: Claude ve vídeos de YouTube (uno, varios, una lista o un canal) o escucha pódcasts, aprende lo que enseñan y lo convierte en una skill nueva que puede usar siempre, con los pasos, las reglas, los ejemplos y la fuente citada. Si le pasas varios a la vez, fusiona lo que aprende de todos en una sola skill. Úsala cuando digan /aprende, «comenta APRENDE», «mira este vídeo y aprende», «aprende lo que enseña este vídeo», «conviértelo en una skill», «hazme una skill con este vídeo», «aprende de este canal», «escucha este pódcast y aprende» o peguen un enlace de YouTube o de un pódcast pidiendo que lo aprenda.
---

# /aprende · de un vídeo (o cincuenta) a una skill que Claude usa siempre

El trabajo tiene tres partes: **bajar la transcripción** (lo hace el script), **entender el método** (lo haces tú,
Claude, leyendo la transcripción entera) y **escribir la skill** (tú, con la plantilla de abajo). La skill nueva tiene
que servir sin volver a ver el vídeo: pasos concretos, reglas, ejemplos y de dónde sale.

`M` = carpeta de esta skill + `/motor` (normalmente `~/.claude/skills/aprende/motor`).

## 01 · Comprobar herramientas (solo la primera vez)
```bash
python3 $M/aprende.py comprobar
```
- Si falta `yt-dlp` o `ffmpeg`, enséñale el comando que imprime (`brew install yt-dlp ffmpeg` en Mac) y pídele
  permiso para ejecutarlo. Sin ellos no se puede seguir.
- `faster-whisper` solo hace falta para vídeos sin subtítulos y pódcasts. Si falta y se necesita:
  `python3 -m pip install -U faster-whisper` (la primera vez baja el modelo, unos 500 MB el `small`).

## 02 · Bajar las transcripciones
Carpeta de trabajo: `~/.claude/aprende/<tema>/fuentes/` (crea `<tema>` en minúsculas con guiones).
```bash
python3 $M/aprende.py transcribir <url1> [<url2> ...] --salida ~/.claude/aprende/<tema>/fuentes --idioma es
```
- Acepta: vídeo de YouTube, lista (`playlist?list=`), canal (`@canal`, coge los más recientes), archivo de audio o
  vídeo local (mp3, m4a, wav, mp4…) y enlaces de pódcast que yt-dlp entienda (mp3 directo, Spotify no).
- `--max N` limita los vídeos por lista o canal (10 por defecto). Si piden «todo el canal», pregunta cuántos: cada
  vídeo largo sin subtítulos tarda minutos en transcribirse.
- Pon `--idioma` con el idioma en el que habla el vídeo (`es`, `en`…). Si no lo sabes, quítalo; si el script avisa
  de que ha detectado un idioma con poca seguridad, repite con el correcto.
- Primero usa los subtítulos del vídeo (segundos). Si no hay, baja el audio y lo transcribe en local con Whisper.
  `--forzar-whisper` ignora los subtítulos (úsalo si los automáticos salen sin puntuación y el método depende de matices).
- Deja un `.md` por fuente (título, autor, enlace, duración, cómo se transcribió y el texto con marcas `[mm:ss]`) y un
  `indice.json`. Si una fuente falla, sigue con las demás: dile cuál falló y por qué.

## 03 · Leer y sacar el método
Lee **cada transcripción entera** (con Read, por partes si es larga). No resumas de memoria ni por el título.
Apunta para ti:
1. **Qué enseña** en una frase y **para quién**.
2. **El método**: los pasos en orden, tal como el autor los aplica.
3. **Reglas**: lo que hay que hacer siempre y lo que no hay que hacer nunca.
4. **Frases, guiones o plantillas** que da literalmente (cópialas con su marca `[mm:ss]`).
5. **Ejemplos** que pone y **números** que da (solo los que dice él; si no da cifras, no las inventes).
6. **Lo que no queda claro** o depende de contexto.

Con varias fuentes: une lo que coincide, quita lo repetido, y cuando dos autores se contradicen, ponlo en una sección
«Dónde no están de acuerdo» con quién dice qué. Cada regla o paso lleva entre paréntesis de qué fuente sale.

Ignora la paja: saludos, «suscríbete», patrocinios, anécdotas que no enseñan nada.

## 04 · Escribir la skill
Antes de escribir, enséñale en 5–8 líneas lo que has entendido (qué enseña, pasos, nombre propuesto de la skill)
y pregunta si lo guardas así. Luego crea `~/.claude/skills/<nombre>/SKILL.md` (si ya existe una skill con ese nombre,
no la pises: pregunta si actualizarla o usar otro nombre).

- `<nombre>`: minúsculas, sin tildes, con guiones, que diga lo que hace (`objeciones-de-precio`, no `video-tino`).
- Escribe en el idioma del usuario, aunque el vídeo esté en otro. En español de España: tú, nunca vos.
- La skill es para que tú (Claude) la uses: instrucciones en imperativo, concretas, aplicables al caso del usuario.

Plantilla:
```markdown
---
name: <nombre>
description: <qué hace en una frase>. Úsala cuando <situaciones y frases que la activan, entre comillas>.
---

# <Título>

<Para qué sirve y cuándo usarla, 2–3 líneas.>

## Método
1. <Paso> — <cómo se hace, en concreto> (fuente 1, [mm:ss])
2. ...

## Reglas
- Siempre: ...
- Nunca: ...

## Guiones y frases (literales de la fuente)
> «...» (fuente 1, [mm:ss])

## Ejemplos
<Ejemplo del vídeo y, si ayuda, uno aplicado al negocio del usuario.>

## Cómo usarla
<Qué le pides al usuario (datos de entrada) y qué le devuelves.>

## Dónde no están de acuerdo   ← solo si hay varias fuentes y chocan

## Fuente
- <Título> · <autor> · <enlace> · visto el <fecha de hoy>
```
Si la transcripción es útil como referencia, cópiala a `~/.claude/skills/<nombre>/fuentes/` y enlázala desde la skill.

## 05 · Comprobar y entregar
```bash
python3 $M/aprende.py validar ~/.claude/skills/<nombre>/SKILL.md
```
Corrige todo lo que salga como ERROR. Luego dile:
- dónde está la skill y cómo se activa (`/<nombre>` o las frases de la description),
- 3–5 líneas de lo que ha aprendido,
- que funciona desde la próxima conversación de Claude Code.

Ofrece probarla en el momento con un caso suyo.

## Reglas
- Nunca inventes pasos, cifras ni frases que no estén en la fuente. Si algo lo añades tú para que se entienda,
  márcalo como «(añadido)».
- Cita siempre la fuente con enlace. La skill es un resumen de estudio, no una copia: no pegues la transcripción
  entera dentro de SKILL.md.
- Si el vídeo no enseña un método (opinión, noticia, vlog), díselo y propón guardarlo como notas, no como skill.
- Vídeos privados, con edad o de pago: yt-dlp fallará. Pide el archivo descargado y pásalo como ruta local.
- No subas nada a internet ni compartas la skill sin que te lo pida.
