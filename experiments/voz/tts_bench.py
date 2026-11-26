"""Benchmark de TTS: latencia y audios para calificar.

Motores:
- chatterbox      Chatterbox Multilingual, local (MPS), voz por defecto (ronda 1)
- kokoro          Kokoro-82M, local, voz ef_dora
- piper           Piper, local, es_MX-claude-high
- elevenlabs      ElevenLabs en la nube (gasta créditos; pide confirmación)

Métricas por frase:
- TTFA: tiempo hasta tener el primer audio reproducible.
  * Locales: se sintetiza oración por oración (como en el flujo real en streaming);
    TTFA = tiempo de la primera oración.
  * ElevenLabs: streaming nativo; TTFA = primer fragmento recibido.
- Total y RTF (tiempo de síntesis ÷ duración del audio; < 1 = más rápido que tiempo real).

Uso (desde experiments/voz/):
    .venv/bin/python tts_bench.py                          # motores locales
    .venv/bin/python tts_bench.py --motores elevenlabs     # solo ElevenLabs (pide confirmación)
    .venv/bin/python tts_bench.py --motores kokoro piper   # algunos
"""

from __future__ import annotations

import os
from pathlib import Path

RAIZ_REPO = Path(__file__).resolve().parents[2]
os.environ.setdefault("HF_HOME", str(RAIZ_REPO / "models" / "huggingface"))  # antes de importar libs de HF

import argparse
import csv
import html
import re
import statistics
import sys
import time
import warnings
from dataclasses import asdict, dataclass
from typing import Callable

import numpy as np
import soundfile as sf
from dotenv import load_dotenv

from frases import FRASES, Frase

warnings.filterwarnings("ignore")

DIR_SALIDA = Path(__file__).parent / "salidas" / "tts"
MOTORES_LOCALES = ["kokoro", "piper", "chatterbox"]
TODOS = MOTORES_LOCALES + ["elevenlabs"]

ELEVEN_MODELOS = ["eleven_flash_v2_5", "eleven_multilingual_v2"]  # rápido vs. calidad (por defecto)
# Otros disponibles: eleven_v4_turbo (tiempo real, emotivo), eleven_v4 (máxima calidad)

SEPARADOR_ORACIONES = re.compile(r"(?<=[.!?…])\s+")


@dataclass
class Medicion:
    motor: str
    frase_id: str
    oraciones: int
    ttfa_ms: int
    total_ms: int
    duracion_audio_s: float
    rtf: float
    archivo: str


# --- Motores locales: cada uno devuelve sintetizar(texto, frase) -> (audio float32, sample_rate) ---

Sintetizador = Callable[[str, Frase], "tuple[np.ndarray, int]"]


def cargar_kokoro() -> Sintetizador:
    from kokoro import KPipeline

    pipe = KPipeline(lang_code="e", repo_id="hexgrad/Kokoro-82M")

    def sintetizar(texto: str, frase: Frase) -> tuple[np.ndarray, int]:
        partes = [np.asarray(audio, dtype=np.float32) for _, _, audio in pipe(texto, voice="ef_dora")]
        return np.concatenate(partes), 24000

    return sintetizar


def cargar_piper() -> Sintetizador:
    from piper import PiperVoice

    modelo = RAIZ_REPO / "models" / "piper" / "es" / "es_MX" / "claude" / "high" / "es_MX-claude-high.onnx"
    voz = PiperVoice.load(str(modelo))

    def sintetizar(texto: str, frase: Frase) -> tuple[np.ndarray, int]:
        chunks = list(voz.synthesize(texto))
        audio = np.concatenate([np.frombuffer(c.audio_int16_bytes, dtype=np.int16) for c in chunks])
        return audio.astype(np.float32) / 32768.0, chunks[0].sample_rate

    return sintetizar


def cargar_chatterbox() -> Sintetizador:
    import torch
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS

    dispositivo = "mps" if torch.backends.mps.is_available() else "cpu"
    modelo = ChatterboxMultilingualTTS.from_pretrained(device=dispositivo)
    print(f"  chatterbox en {dispositivo}")

    def sintetizar(texto: str, frase: Frase) -> tuple[np.ndarray, int]:
        # Emociones: más exageración y menos cfg = más expresivo (recomendación de Chatterbox)
        exag, cfg = (0.8, 0.3) if frase.emocion else (0.5, 0.5)
        wav = modelo.generate(texto, language_id="es", exaggeration=exag, cfg_weight=cfg)
        return wav.squeeze(0).detach().cpu().numpy().astype(np.float32), modelo.sr

    return sintetizar


CARGADORES: dict[str, Callable[[], Sintetizador]] = {
    "kokoro": cargar_kokoro,
    "piper": cargar_piper,
    "chatterbox": cargar_chatterbox,
}


def medir_local(motor: str, sintetizar: Sintetizador, frase: Frase) -> Medicion:
    oraciones = SEPARADOR_ORACIONES.split(frase.texto)
    audios: list[np.ndarray] = []
    sr = 24000
    ttfa = None
    inicio = time.perf_counter()
    for oracion in oraciones:
        audio, sr = sintetizar(oracion, frase)
        audios.append(audio)
        if ttfa is None:
            ttfa = time.perf_counter() - inicio
        audios.append(np.zeros(int(sr * 0.15), dtype=np.float32))  # pausa breve entre oraciones
    total = time.perf_counter() - inicio
    audio = np.concatenate(audios[:-1])
    archivo = DIR_SALIDA / motor / f"{frase.id}.wav"
    archivo.parent.mkdir(parents=True, exist_ok=True)
    sf.write(archivo, audio, sr)
    dur = len(audio) / sr
    return Medicion(motor, frase.id, len(oraciones), round(ttfa * 1000), round(total * 1000), round(dur, 2), round(total / dur, 3), str(archivo.relative_to(DIR_SALIDA)))


def correr_local(motor: str) -> list[Medicion]:
    print(f"\n▶ {motor}: cargando modelo…")
    t = time.perf_counter()
    sintetizar = CARGADORES[motor]()
    print(f"  cargado en {time.perf_counter() - t:.1f} s; calentando…")
    sintetizar("Hola.", FRASES[0])  # calentamiento, no se cuenta
    resultados = []
    for frase in FRASES:
        m = medir_local(motor, sintetizar, frase)
        resultados.append(m)
        print(f"  {frase.id}: TTFA={m.ttfa_ms} ms  total={m.total_ms} ms  audio={m.duracion_audio_s} s  RTF={m.rtf}")
    return resultados


# --- ElevenLabs ---------------------------------------------------------------


def correr_elevenlabs(confirmar: bool, modelos: list[str]) -> list[Medicion]:
    from elevenlabs.client import ElevenLabs

    voz = os.environ.get("ELEVENLABS_VOICE_ID") or "EXAVITQu4vr4xnSDxMaL"
    caracteres = sum(len(f.texto) for f in FRASES)
    print(f"\n▶ elevenlabs: voz {voz}, modelos {modelos}")
    print(f"  {len(FRASES)} frases × {len(modelos)} modelos = {caracteres * len(modelos)} caracteres (+ calentamiento)")
    print("  Los créditos por carácter dependen del modelo (Flash cuesta menos que Multilingual).")
    if confirmar and input("  ¿Continuar con ElevenLabs? [s/N] ").strip().lower() not in ("s", "si", "sí"):
        print("  ElevenLabs omitido.")
        return []

    cliente = ElevenLabs(api_key=os.environ["ELEVENLABS_API_KEY"])
    resultados = []
    for modelo in modelos:
        motor =f"elevenlabs_{modelo.removeprefix('eleven_')}"
        b"".join(cliente.text_to_speech.stream(voice_id=voz, text="Hola.", model_id=modelo, language_code="es"))  # calentamiento
        for frase in FRASES:
            inicio = time.perf_counter()
            ttfa = None
            datos = bytearray()
            for chunk in cliente.text_to_speech.stream(
                voice_id=voz, text=frase.texto, model_id=modelo, language_code="es", output_format="mp3_44100_128"
            ):
                if chunk and ttfa is None:
                    ttfa = time.perf_counter() - inicio
                datos.extend(chunk)
            total = time.perf_counter() - inicio
            archivo = DIR_SALIDA / motor / f"{frase.id}.mp3"
            archivo.parent.mkdir(parents=True, exist_ok=True)
            archivo.write_bytes(datos)
            try:
                dur = sf.info(str(archivo)).duration
            except Exception:
                dur = float("nan")
            m = Medicion(motor, frase.id, 1, round(ttfa * 1000), round(total * 1000), round(dur, 2), round(total / dur, 3), str(archivo.relative_to(DIR_SALIDA)))
            resultados.append(m)
            print(f"  {modelo} {frase.id}: TTFA={m.ttfa_ms} ms  total={m.total_ms} ms  audio={m.duracion_audio_s} s")
    return resultados


# --- Salidas -----------------------------------------------------------------


def guardar(resultados: list[Medicion]) -> None:
    marca = time.strftime("%Y%m%d-%H%M%S")
    with open(DIR_SALIDA / f"mediciones-{marca}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(asdict(resultados[0]).keys()))
        w.writeheader()
        w.writerows(asdict(m) for m in resultados)

    # Hoja de calificaciones: se crea una nueva por corrida para no pisar calificaciones ya hechas.
    frases = {f.id: f for f in FRASES}
    with open(DIR_SALIDA / f"calificaciones-{marca}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["frase_id", "emocion_pedida", "motor", "archivo", "naturalidad_1a5", "pronunciacion_1a5", "emocion_1a5", "comentarios"])
        for m in sorted(resultados, key=lambda m: (m.frase_id, m.motor)):
            w.writerow([m.frase_id, frases[m.frase_id].emocion or "", m.motor, m.archivo, "", "", "", ""])

    print("\n=== Resumen (ms) ===")
    for motor in dict.fromkeys(m.motor for m in resultados):
        ms = [m for m in resultados if m.motor == motor]
        ttfa = [m.ttfa_ms for m in ms]
        rtf = [m.rtf for m in ms if m.rtf == m.rtf]
        print(f"{motor:30} TTFA p50={statistics.median(ttfa):.0f} max={max(ttfa)} | RTF p50={statistics.median(rtf):.2f}")


def generar_pagina() -> None:
    """Página local para escuchar y comparar: una fila por frase, una columna por motor."""
    motores = sorted(p.name for p in DIR_SALIDA.iterdir() if p.is_dir())
    filas = []
    for frase in FRASES:
        celdas = []
        for motor in motores:
            archivo = next((p for p in (DIR_SALIDA / motor).glob(f"{frase.id}.*")), None)
            celdas.append(f'<td><audio controls preload="none" src="{motor}/{archivo.name}"></audio></td>' if archivo else "<td>—</td>")
        emocion = f" <em>({frase.emocion})</em>" if frase.emocion else ""
        filas.append(f"<tr><th>{frase.id}</th><td class='t'>{html.escape(frase.texto)}{emocion}</td>{''.join(celdas)}</tr>")
    cabecera = "".join(f"<th>{m}</th>" for m in motores)
    pagina = f"""<!doctype html><html lang="es"><meta charset="utf-8"><title>Tessia — comparación de voces</title>
<style>body{{font-family:system-ui;margin:2rem}}table{{border-collapse:collapse}}td,th{{border:1px solid #ccc;padding:.4rem;vertical-align:middle}}
.t{{max-width:22rem}}audio{{width:180px}}</style>
<h1>Tessia — comparación de voces</h1><p>Califica en <code>calificaciones-*.csv</code> (1–5).</p>
<table><tr><th>ID</th><th>Frase</th>{cabecera}</tr>{''.join(filas)}</table></html>"""
    (DIR_SALIDA / "escuchar.html").write_text(pagina, encoding="utf-8")
    print(f"Página para escuchar: {DIR_SALIDA / 'escuchar.html'}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--motores", nargs="+", choices=TODOS, default=MOTORES_LOCALES)
    parser.add_argument("--si", action="store_true", help="no pedir confirmación para ElevenLabs")
    parser.add_argument("--modelos-eleven", nargs="+", default=ELEVEN_MODELOS, help="model_id de ElevenLabs a probar")
    args = parser.parse_args()
    load_dotenv(Path(__file__).parent / ".env")
    DIR_SALIDA.mkdir(parents=True, exist_ok=True)

    resultados: list[Medicion] = []
    for motor in args.motores:
        if motor == "elevenlabs":
            resultados += correr_elevenlabs(confirmar=not args.si, modelos=args.modelos_eleven)
        else:
            resultados += correr_local(motor)
    if resultados:
        guardar(resultados)
    generar_pagina()
    return 0


if __name__ == "__main__":
    sys.exit(main())
