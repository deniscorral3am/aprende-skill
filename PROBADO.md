# Qué se ha probado de verdad

Fecha: 08/11/2026 · macOS (Apple Silicon) · Python 3.9.6 del sistema · yt-dlp 2026.10.21 · faster-whisper 1.2.1

## 1. Comprobación de herramientas
```
$ python3 motor/aprende.py comprobar
OK    yt-dlp  (/opt/homebrew/bin/yt-dlp)
OK    ffmpeg  (/opt/homebrew/bin/ffmpeg)
OK    faster-whisper
```

## 2. Dos vídeos reales de YouTube a la vez (ponentes de España)
```
$ python3 motor/aprende.py transcribir https://www.youtube.com/watch?v=Dwgi1PK2ui8 \
    https://www.youtube.com/watch?v=kI01s0CZLF4 --idioma es --salida (transcripciones no incluidas: son de terceros)
[1/2] sin subtítulos: transcribiendo el audio en local con Whisper (small)...
      OK  ¿Cómo responder a la objeción "no me interesa"?  ·  Whisper local (small)  ·  250 palabras
[2/2] OK  Los dos mejores cierres de ventas | César Piqueras  ·  subtítulos automáticos (idioma original)  ·  463 palabras
Listo: 2/2 transcritas.
```
El primero (Alfonso y Christian, 1:33) no tiene subtítulos, así que probó solo el paso a Whisper. Resultado en
`(transcripciones no incluidas: son de terceros)/` (un .md por vídeo con marcas [mm:ss] e `indice.json`).
La primera versión del ejemplo usaba un vídeo con voseo (ponente argentino); se cambió para que todo el ejemplo
sea de España.

### Fallo encontrado y corregido: vídeos con doblaje automático
Con «3 claves para cerrar ventas con clientes indecisos» (José Piquer, LePvhX94fb8) el script cogió los subtítulos
en **árabe**: el vídeo tiene doblaje automático, YouTube marca varias pistas como «-orig» (ar-orig, es-orig,
en-US-orig, pt-BR-orig) y no tenía subtítulos manuales en español. Ahora busca el «-orig» del idioma pedido o del
idioma del vídeo, y si no hay nada fiable transcribe el audio. Repetido: sale en español (708 palabras), con y sin
`--idioma`.

## 3. Sin subtítulos: audio + Whisper local
```
$ python3 motor/aprende.py transcribir https://www.youtube.com/watch?v=kI01s0CZLF4 --forzar-whisper --salida /tmp/...
OK  Los dos mejores cierres de ventas  ·  Whisper local (small)  ·  473 palabras
```
22 s para un vídeo de 2:55. Sale con puntuación (mejor que los subtítulos automáticos de ese vídeo).

## 4. Pódcast / audio local
Un mp3 local de 1:33 (audio de un vídeo de ventas bajado aparte):
- Sin `--idioma`: Whisper detectó gallego («gl», 59 % de seguridad) y la transcripción salió mezclada. El script
  avisa: «idioma detectado 'gl' con poca seguridad (59 %). Si no es ese, repite con --idioma es».
- Con `--idioma es`: transcripción correcta en español, 250 palabras, 8 s.
Por eso la SKILL.md le dice a Claude que pase siempre `--idioma` cuando lo sepa.

## 5. Canal de YouTube
```
$ python3 motor/aprende.py transcribir https://www.youtube.com/@Cesar.Piqueras --max 2 --salida /tmp/...
[1/2] OK  Despertarte a las 5am sin autosabotearte  ·  1782 palabras
[2/2] OK  #116 Una gestión del tiempo saludable  ·  2639 palabras
```
21 s. Fallo encontrado y corregido: con la URL del canal sin pestaña, yt-dlp recorría el canal entero (más de
3 minutos sin terminar). Ahora se añade `/videos` y lista solo los N más recientes (2 s).
También probado `expandir()` con una lista (`playlist?list=`): devuelve los N primeros vídeos.

## 6. Errores
- Vídeo que no existe: `ERROR  [youtube] noexiste123: This video is unavailable`, sigue con las demás, sale con código 1.
- Handle de canal mal escrito: error claro de yt-dlp (404), sin colgarse.

## 7. Generación de la skill de ejemplo
Con las dos transcripciones del punto 2, Claude escribió (siguiendo SKILL.md, pasos 03–04)
`ejemplo/skills/objeciones-y-cierre/SKILL.md`: método en dos partes, reglas, frases literales con su minuto,
ejemplos con las cifras que dan los autores y uno aplicado marcado como «(añadido)», y la fuente.
```
$ python3 motor/aprende.py validar ejemplo/skills/objeciones-y-cierre/SKILL.md
OK  ejemplo/skills/objeciones-y-cierre/SKILL.md
```
Validador probado también con una skill mal hecha (name con espacios, sin description ni fuente): 3 errores,
3 avisos, código 1.

## No probado
- Windows y Linux (los comandos de instalación que imprime `comprobar` no se han ejecutado allí).
- Enlaces de pódcast de plataformas (Apple Podcasts, Ivoox). yt-dlp soporta muchas, pero no se han probado aquí.
- La skill instalada en `~/.claude/skills/aprende` activándose sola por la description (se probó el motor y el
  procedimiento, no el disparo automático en una conversación nueva).
