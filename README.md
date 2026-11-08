# /aprende · Claude ve vídeos de YouTube por ti y los convierte en skills

Le pasas un vídeo (o una lista, un canal o un pódcast) y le dices: «mira esto, aprende lo que enseña y conviértelo
en una skill que pueda usar siempre». Claude baja la transcripción, se la lee entera, saca el método (pasos, reglas,
frases literales, ejemplos) y te deja una skill nueva en `~/.claude/skills/<nombre>/` con la fuente citada. A partir
de ahí, Claude sabe hacer eso cada vez que se lo pidas.

Puede ver decenas de vídeos a la vez y fusionar lo que aprende de todos en una sola skill (y te dice en qué no están
de acuerdo los autores).

## El prompt exacto

```
Mira este vídeo, aprende lo que enseña y conviértelo en una skill que pueda usar siempre: <url>
```

Más formas de usarla:
```
Mira estos 3 vídeos y júntalo todo en una sola skill de prospección: <url1> <url2> <url3>
Aprende de los últimos 10 vídeos de este canal y hazme una skill: https://www.youtube.com/@canal
Escucha este pódcast y conviértelo en una skill: ~/Descargas/episodio-42.mp3
/aprende https://www.youtube.com/playlist?list=...
```

## Instalación

```bash
git clone https://github.com/deniscorral3am/aprende-skill ~/.claude/skills/aprende
```

Abre Claude Code (o empieza una conversación nueva) y pega el prompt de arriba.

## Qué necesitas

- **Claude Code**.
- **Python 3** (viene con el Mac). El script solo usa la librería estándar.
- **yt-dlp** y **ffmpeg** para bajar subtítulos y audio. En Mac: `brew install yt-dlp ffmpeg`.
  En Windows: `winget install yt-dlp.yt-dlp Gyan.FFmpeg`. En Linux: `sudo apt install ffmpeg` y `pip install yt-dlp`.
- **faster-whisper** (opcional) para vídeos sin subtítulos y pódcasts: `python3 -m pip install -U faster-whisper`.
  Transcribe en tu ordenador, sin claves ni pagar nada. La primera vez baja el modelo (unos 500 MB).

No hace falta ninguna clave de API. La skill comprueba todo esto la primera vez (`python3 motor/aprende.py comprobar`)
y te dice el comando exacto de lo que falte.

## Cómo funciona

1. **Transcripción** (`motor/aprende.py transcribir`): usa los subtítulos del vídeo si los tiene (tarda segundos;
   nunca coge traducciones automáticas). Si no hay, baja el audio y lo transcribe en local con Whisper. Listas y
   canales se expanden en sus vídeos (10 por defecto, `--max` para cambiarlo).
2. **Aprendizaje**: Claude lee cada transcripción entera y saca qué enseña, el método paso a paso, las reglas, las
   frases literales con su minuto, los ejemplos y las cifras que da el autor (sin inventar ninguna).
3. **Skill**: te enseña lo que ha entendido, le pones el visto bueno y la guarda en `~/.claude/skills/<nombre>/SKILL.md`.
   `motor/aprende.py validar` comprueba que está bien formada y que cita la fuente.

## Ejemplo real

En `ejemplo/` tienes una prueba hecha con dos vídeos cortos de ventas de YouTube (Alfonso y Christian, y César
Piqueras):
- `(transcripciones no incluidas: son de terceros)/`: las dos transcripciones tal como las baja el script (una con los subtítulos del vídeo y otra
  con Whisper local, porque ese vídeo no tiene subtítulos).
- `ejemplo/skills/objeciones-y-cierre/SKILL.md`: la skill que salió al fusionar los dos (responder a «no me
  interesa» con dos opciones y cerrar con doble alternativa), con cada paso citado al minuto del vídeo.

## Límites

- Vídeos privados, con restricción de edad o de pago: yt-dlp no puede bajarlos. Descárgalos tú y pásale el archivo.
- Spotify no deja bajar pódcasts. Usa el RSS o el mp3 del episodio, o el vídeo si el pódcast está en YouTube.
- Si el vídeo no enseña un método (una opinión, una noticia), Claude te lo dirá en vez de inventarse una skill.
- Lo que ve es lo que se dice. Si el método está en lo que se enseña en pantalla sin decirlo, pídele que además lo
  vea con capturas.

---

Hecha por Denis Corral · Sell Your AI (https://sellyourai.io) · Licencia MIT
