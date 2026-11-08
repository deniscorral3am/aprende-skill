#!/usr/bin/env python3
"""aprende.py · baja la transcripción de vídeos de YouTube, listas, canales o pódcasts.

Uso:
  python3 aprende.py comprobar
  python3 aprende.py transcribir <url|archivo> [<url|archivo> ...] --salida DIR [--max 10]
                     [--idioma es] [--modelo small] [--forzar-whisper]
  python3 aprende.py validar <ruta/a/SKILL.md>

Orden: 1) subtítulos del propio vídeo (manuales y, si no hay, los automáticos del idioma original)
       2) si no hay subtítulos, baja el audio y lo transcribe en tu ordenador con faster-whisper.
Solo librería estándar de Python. Herramientas externas: yt-dlp y ffmpeg (y faster-whisper si hay
que transcribir audio). `comprobar` te dice qué falta y cómo instalarlo.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PARRAFO_SEG = 30  # una marca de tiempo cada ~30 s de transcripción


# ---------------------------------------------------------------- comprobar
def _hay_faster_whisper() -> bool:
    try:
        import importlib.util
        return importlib.util.find_spec("faster_whisper") is not None
    except Exception:
        return False


def comprobar(_args=None) -> int:
    falta = []
    for b in ("yt-dlp", "ffmpeg"):
        ruta = shutil.which(b)
        print(("OK    " if ruta else "FALTA ") + b + (f"  ({ruta})" if ruta else ""))
        if not ruta:
            falta.append(b)
    fw = _hay_faster_whisper()
    print(("OK    " if fw else "AVISO ") + "faster-whisper" +
          ("" if fw else "  (solo hace falta para vídeos sin subtítulos y pódcasts)"))
    if falta or not fw:
        print("\nCómo instalar lo que falta:")
        if falta:
            if sys.platform == "darwin":
                print("  brew install " + " ".join(falta))
            elif os.name == "nt":
                print("  winget install yt-dlp.yt-dlp Gyan.FFmpeg")
            else:
                print("  sudo apt install ffmpeg  &&  python3 -m pip install -U yt-dlp")
        if not fw:
            print("  python3 -m pip install -U faster-whisper")
    return 1 if falta else 0


# ---------------------------------------------------------------- utilidades
def _yt(args, capturar=True):
    cmd = ["yt-dlp", "--no-warnings", "--ignore-config"] + args
    r = subprocess.run(cmd, capture_output=capturar, text=True)
    return r


def _mmss(s: float) -> str:
    s = int(s)
    h, m, s = s // 3600, (s % 3600) // 60, s % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def _slug(t: str, n: int = 60) -> str:
    import unicodedata
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()
    t = re.sub(r"[^a-zA-Z0-9]+", "-", t).strip("-").lower()
    return (t[:n].strip("-")) or "fuente"


def _es_local(f: str) -> bool:
    return not re.match(r"^https?://", f) and Path(f).expanduser().exists()


# ---------------------------------------------------------------- VTT
TS = re.compile(r"(\d+):(\d{2}):(\d{2})[.,](\d{3})\s+-->\s+(\d+):(\d{2}):(\d{2})[.,](\d{3})")
TAG = re.compile(r"<[^>]+>")


def leer_vtt(ruta: str):
    """Devuelve [(segundo, texto)] sin las líneas repetidas de los subtítulos automáticos."""
    lineas = Path(ruta).read_text(encoding="utf-8", errors="ignore").splitlines()
    salida, recientes = [], []
    i = 0
    while i < len(lineas):
        m = TS.search(lineas[i])
        if not m:
            i += 1
            continue
        g = m.groups()
        ini = int(g[0]) * 3600 + int(g[1]) * 60 + int(g[2]) + int(g[3]) / 1000
        i += 1
        while i < len(lineas) and lineas[i].strip():
            t = TAG.sub("", lineas[i]).replace("&nbsp;", " ").replace("&amp;", "&").strip()
            t = re.sub(r"\s+", " ", t)
            if t and t not in recientes:
                salida.append((ini, t))
                recientes = (recientes + [t])[-4:]
            i += 1
    return salida


def a_parrafos(trozos):
    """[(seg, texto)] -> lista de (seg_inicio, párrafo) agrupando cada ~30 s."""
    out, cur, t0 = [], [], None
    for s, t in trozos:
        if t0 is None:
            t0 = s
        cur.append(t)
        if s - t0 >= PARRAFO_SEG and re.search(r"[.?!…]$", t) or (s - t0 >= PARRAFO_SEG * 1.6):
            out.append((t0, " ".join(cur)))
            cur, t0 = [], None
    if cur:
        out.append((t0 or 0, " ".join(cur)))
    return out


# ---------------------------------------------------------------- fuentes
def expandir(fuente: str, maximo: int):
    """Una URL de lista o canal -> URLs de sus vídeos (hasta `maximo`)."""
    if _es_local(fuente):
        return [fuente]
    # canal sin pestaña -> sus vídeos más recientes (si no, yt-dlp recorre todas las pestañas enteras)
    if re.match(r"^https?://(www\.|m\.)?youtube\.com/(@[^/?#]+|channel/[^/?#]+|c/[^/?#]+|user/[^/?#]+)/?$", fuente):
        fuente = fuente.rstrip("/") + "/videos"
    r = _yt(["--flat-playlist", "-J", "--playlist-end", str(maximo), fuente])
    if r.returncode != 0:
        return [fuente]
    try:
        info = json.loads(r.stdout)
    except ValueError:
        return [fuente]
    if info.get("_type") in ("playlist", "multi_video") and info.get("entries"):
        urls = []
        for e in info["entries"]:
            if not e:
                continue
            if e.get("_type") == "playlist" and e.get("url"):  # pestañas de un canal
                urls += expandir(e["url"], maximo - len(urls))
            else:
                u = e.get("url") or e.get("webpage_url") or e.get("id")
                if u and not u.startswith("http"):
                    u = "https://www.youtube.com/watch?v=" + u
                if u:
                    urls.append(u)
            if len(urls) >= maximo:
                break
        return urls[:maximo]
    return [fuente]


def elegir_subtitulo(info: dict, idioma: str | None):
    """Prioridad: manual en tu idioma > manual en el idioma original > automático del idioma original.
    Nunca coge una traducción automática (pierde matices)."""
    manual = info.get("subtitles") or {}
    auto = info.get("automatic_captions") or {}
    manual = {k: v for k, v in manual.items() if k != "live_chat"}
    orig = (info.get("language") or "").split("-")[0]
    pref = [p for p in [idioma, orig] if p]

    def busca(dic, lang):
        for k in dic:
            if k == lang or k.startswith(lang + "-"):
                return k
        return None

    for p in pref:
        k = busca(manual, p)
        if k:
            return k, "subtítulos manuales"
    # automáticos: YouTube marca el idioma original como "xx-orig". Ojo: los vídeos con doblaje
    # automático tienen varios "-orig" (uno por pista de audio), así que se busca el del idioma pedido.
    for p in pref:
        for k in auto:
            if k.endswith("-orig") and (k == p + "-orig" or k.startswith(p + "-")):
                return k, "subtítulos automáticos (idioma original)"
    if not pref:
        origs = [k for k in auto if k.endswith("-orig")]
        if len(origs) == 1:
            return origs[0], "subtítulos automáticos (idioma original)"
        if not origs and len(manual) == 1:
            return next(iter(manual)), "subtítulos manuales"
    # nada fiable (o solo traducciones): mejor transcribir el audio
    return None, None


def transcribir_whisper(audio: str, modelo: str, idioma: str | None):
    if not _hay_faster_whisper():
        raise RuntimeError("Este contenido no tiene subtítulos y falta faster-whisper. "
                           "Instálalo con: python3 -m pip install -U faster-whisper")
    import warnings
    warnings.filterwarnings("ignore")
    from faster_whisper import WhisperModel  # type: ignore
    print(f"      sin subtítulos: transcribiendo el audio en local con Whisper ({modelo})...", flush=True)
    m = WhisperModel(modelo, device="auto", compute_type="int8")
    segs, info = m.transcribe(audio, language=idioma, vad_filter=True, beam_size=1)
    trozos = [(s.start, s.text.strip()) for s in segs if s.text.strip()]
    if not idioma and getattr(info, "language_probability", 1) < 0.9:
        print(f"      AVISO: idioma detectado '{info.language}' con poca seguridad "
              f"({info.language_probability:.0%}). Si no es ese, repite con --idioma es", flush=True)
    return trozos, info.language


def una_fuente(fuente: str, salida: Path, args) -> dict:
    tmp = Path(tempfile.mkdtemp(prefix="aprende-"))
    meta = {"fuente": fuente}
    try:
        if _es_local(fuente):
            p = Path(fuente).expanduser().resolve()
            meta.update(titulo=p.stem, canal="archivo local", url=str(p), id=_slug(p.stem))
            trozos, lang = transcribir_whisper(str(p), args.modelo, args.idioma)
            meta.update(metodo=f"Whisper local ({args.modelo})", idioma=lang)
        else:
            r = _yt(["-J", "--skip-download", "--no-playlist", fuente])
            if r.returncode != 0:
                raise RuntimeError((r.stderr or "yt-dlp no pudo leer la URL").strip().splitlines()[-1])
            info = json.loads(r.stdout)
            meta.update(titulo=info.get("title") or fuente,
                        canal=info.get("channel") or info.get("uploader") or "",
                        url=info.get("webpage_url") or fuente,
                        id=info.get("id") or _slug(fuente),
                        duracion=info.get("duration"),
                        fecha=info.get("upload_date"))
            trozos = None
            if not args.forzar_whisper:
                clave, tipo = elegir_subtitulo(info, args.idioma)
                if clave:
                    _yt(["--skip-download", "--no-playlist", "--write-subs", "--write-auto-subs",
                         "--sub-langs", clave, "--sub-format", "vtt/best", "--convert-subs", "vtt",
                         "-o", str(tmp / "sub.%(ext)s"), fuente])
                    vtts = list(tmp.glob("*.vtt"))
                    if vtts:
                        trozos = leer_vtt(str(vtts[0]))
                        meta.update(metodo=tipo, idioma=clave.replace("-orig", ""))
            if not trozos:
                _yt(["-f", "bestaudio/best", "--no-playlist", "-x", "--audio-format", "mp3",
                     "--audio-quality", "5", "-o", str(tmp / "audio.%(ext)s"), fuente])
                audios = [a for a in tmp.iterdir() if a.suffix in (".mp3", ".m4a", ".webm", ".opus")]
                if not audios:
                    raise RuntimeError("no se pudo bajar el audio")
                trozos, lang = transcribir_whisper(str(audios[0]), args.modelo, args.idioma)
                meta.update(metodo=f"Whisper local ({args.modelo})", idioma=lang)
        if not trozos:
            raise RuntimeError("la transcripción ha salido vacía")
        parr = a_parrafos(trozos)
        palabras = sum(len(t.split()) for _, t in trozos)
        base, ident = _slug(meta["titulo"], 50), _slug(str(meta["id"]), 15)
        nombre = (base if ident == base else f"{base}-{ident}") + ".md"
        cab = [f"# {meta['titulo']}", "",
               f"- Canal / autor: {meta.get('canal', '')}",
               f"- Enlace: {meta.get('url', '')}"]
        if meta.get("duracion"):
            cab.append(f"- Duración: {_mmss(meta['duracion'])}")
        if meta.get("fecha"):
            f = meta["fecha"]
            cab.append(f"- Publicado: {f[6:8]}/{f[4:6]}/{f[0:4]}")
        cab += [f"- Transcripción: {meta['metodo']} · idioma {meta.get('idioma')}",
                f"- Palabras: {palabras}", "", "## Transcripción", ""]
        cuerpo = [f"[{_mmss(s)}] {t}" for s, t in parr]
        (salida / nombre).write_text("\n".join(cab) + "\n" + "\n\n".join(cuerpo) + "\n", encoding="utf-8")
        meta.update(archivo=nombre, palabras=palabras, ok=True)
    except Exception as e:  # una fuente rota no tumba las demás
        meta.update(ok=False, error=str(e))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return meta


def transcribir(args) -> int:
    if not shutil.which("yt-dlp") and not all(_es_local(f) for f in args.fuentes):
        print("Falta yt-dlp. Ejecuta: python3 aprende.py comprobar", file=sys.stderr)
        return 1
    salida = Path(args.salida).expanduser()
    salida.mkdir(parents=True, exist_ok=True)
    urls = []
    for f in args.fuentes:
        urls += expandir(f, args.max)
    urls = list(dict.fromkeys(urls))[: args.max]
    print(f"{len(urls)} fuente(s) para transcribir -> {salida}")
    res = []
    for n, u in enumerate(urls, 1):
        print(f"[{n}/{len(urls)}] {u}", flush=True)
        m = una_fuente(u, salida, args)
        res.append(m)
        if m["ok"]:
            print(f"      OK  {m['titulo']}  ·  {m['metodo']}  ·  {m['palabras']} palabras  ->  {m['archivo']}")
        else:
            print(f"      ERROR  {m['error']}")
    (salida / "indice.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    ok = sum(1 for m in res if m["ok"])
    print(f"\nListo: {ok}/{len(res)} transcritas. Índice en {salida / 'indice.json'}")
    return 0 if ok else 1


# ---------------------------------------------------------------- validar
def validar(args) -> int:
    p = Path(args.skill).expanduser()
    if p.is_dir():
        p = p / "SKILL.md"
    if not p.exists():
        print(f"No existe {p}")
        return 1
    txt = p.read_text(encoding="utf-8")
    errores, avisos = [], []
    m = re.match(r"^---\n(.*?)\n---\n", txt, re.S)
    if not m:
        errores.append("falta el frontmatter (--- name / description ---) al principio")
        fm = ""
    else:
        fm = m.group(1)
    name = re.search(r"^name:\s*(.+)$", fm, re.M)
    desc = re.search(r"^description:\s*(.+)$", fm, re.M)
    if not name:
        errores.append("falta name: en el frontmatter")
    else:
        n = name.group(1).strip().strip('"\'')
        if not re.match(r"^[a-z0-9][a-z0-9-]{0,63}$", n):
            errores.append(f"name '{n}' debe ir en minúsculas, sin espacios ni tildes (usa guiones)")
        if n != p.parent.name:
            avisos.append(f"name '{n}' no coincide con la carpeta '{p.parent.name}'")
    if not desc:
        errores.append("falta description: en el frontmatter")
    else:
        d = desc.group(1)
        if len(d) < 80:
            avisos.append("description muy corta: di qué hace y cuándo usarla (frases que la activan)")
        if "úsala" not in d.lower() and "usala" not in d.lower() and "use" not in d.lower():
            avisos.append("description sin disparadores («Úsala cuando…»)")
    if not re.search(r"^#+\s*fuente", txt, re.M | re.I):
        errores.append("falta la sección «Fuente» con el vídeo o pódcast del que sale")
    if not re.search(r"https?://", txt):
        avisos.append("no hay ningún enlace a la fuente")
    if len(txt.split()) < 150:
        avisos.append("la skill es muy corta; ¿están los pasos, reglas y ejemplos?")
    for e in errores:
        print("ERROR  " + e)
    for a in avisos:
        print("AVISO  " + a)
    if not errores:
        print(f"OK  {p}  ({len(txt.split())} palabras)")
    return 1 if errores else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Transcripciones de YouTube y pódcasts para /aprende")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("comprobar").set_defaults(fn=comprobar)
    t = sub.add_parser("transcribir")
    t.add_argument("fuentes", nargs="+")
    t.add_argument("--salida", required=True)
    t.add_argument("--max", type=int, default=10, help="máximo de vídeos por lista o canal (10)")
    t.add_argument("--idioma", default=None, help="código de idioma preferido, p. ej. es")
    t.add_argument("--modelo", default="small", help="modelo de Whisper local (tiny, base, small, medium, large-v3)")
    t.add_argument("--forzar-whisper", action="store_true", help="ignora los subtítulos y transcribe el audio")
    t.set_defaults(fn=transcribir)
    v = sub.add_parser("validar")
    v.add_argument("skill")
    v.set_defaults(fn=validar)
    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
