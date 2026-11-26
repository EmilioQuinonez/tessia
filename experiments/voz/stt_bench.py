"""Benchmark de STT local: latencia y precisión con las grabaciones de Emilio.

Motores (modelo precargado en todos, como lo haría un servicio real):
- mlx_turbo          mlx-whisper, whisper-large-v3-turbo
- mlx_turbo_prompt   igual, con "prompt inicial" de vocabulario (nombres, marcas)
- mlx_small          mlx-whisper, whisper-small (referencia rápida)
- cpp_turbo          whisper.cpp (whisper-server, Metal), large-v3-turbo
- cpp_small          whisper.cpp (whisper-server, Metal), small

Métricas por grabación:
- Latencia: audio completo → texto (mediana de 3 repeticiones, tras calentamiento).
- WER: tasa de error de palabras contra el texto esperado (minúsculas, sin puntuación).
- Nombre: ¿N1 contiene "emilio santiago lópez quiñonez"?

Las grabaciones se leen de <repo>/recordings/voz01/ (ver grabar.py).

Uso (desde experiments/voz/):
    .venv/bin/python stt_bench.py
    .venv/bin/python stt_bench.py --motores mlx_turbo cpp_turbo
"""

from __future__ import annotations

import os
from pathlib import Path

RAIZ_REPO = Path(__file__).resolve().parents[2]
os.environ.setdefault("HF_HOME", str(RAIZ_REPO / "models" / "huggingface"))

import argparse
import csv
import re
import statistics
import subprocess
import sys
import time
import unicodedata
import warnings
from dataclasses import asdict, dataclass
from typing import Callable

import httpx
import jiwer

from frases import FRASES_STT

warnings.filterwarnings("ignore")

DIR_GRABACIONES = RAIZ_REPO / "recordings" / "voz01"
DIR_SALIDA = Path(__file__).parent / "salidas" / "stt"
REPETICIONES = 3

PROMPT_VOCABULARIO = "Tessia, Emilio Santiago López Quiñonez, Apple Music, HomePod, AirPlay, Wi-Fi, Natalia Lafourcade."

MLX_MODELOS = {
    "mlx_turbo": ("mlx-community/whisper-large-v3-turbo", None),
    "mlx_turbo_prompt": ("mlx-community/whisper-large-v3-turbo", PROMPT_VOCABULARIO),
    "mlx_small": ("mlx-community/whisper-small-mlx", None),
}
CPP_MODELOS = {
    "cpp_turbo": RAIZ_REPO / "models" / "whisper.cpp" / "ggml-large-v3-turbo.bin",
    "cpp_small": RAIZ_REPO / "models" / "whisper.cpp" / "ggml-small.bin",
}
TODOS = list(MLX_MODELOS) + list(CPP_MODELOS)

NOMBRE = "emilio santiago lópez quiñonez"


@dataclass
class Medicion:
    motor: str
    frase_id: str
    duracion_audio_s: float
    latencia_ms: int
    rtf: float
    wer: float
    esperado: str
    transcripcion: str


def normalizar(texto: str) -> str:
    """Minúsculas, sin puntuación; conserva acentos y ñ. '7:30' → '7 30', '%' → 'por ciento'."""
    t = unicodedata.normalize("NFC", texto.lower())
    t = t.replace("%", " por ciento ").replace("-", " ")
    t = re.sub(r"(\d)[:.](\d)", r"\1 \2", t)
    t = re.sub(r"[^\w\sáéíóúüñ]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


# --- Motores: cada cargador devuelve transcribir(ruta) -> texto, y una función para cerrar ---

Transcriptor = Callable[[Path], str]


def cargar_mlx(repo: str, prompt: str | None) -> tuple[Transcriptor, Callable[[], None]]:
    import mlx_whisper

    def transcribir(ruta: Path) -> str:
        r = mlx_whisper.transcribe(str(ruta), path_or_hf_repo=repo, language="es", initial_prompt=prompt, verbose=None)
        return r["text"].strip()

    return transcribir, lambda: None


def cargar_cpp(modelo: Path, puerto: int) -> tuple[Transcriptor, Callable[[], None]]:
    proceso = subprocess.Popen(
        ["whisper-server", "-m", str(modelo), "-l", "es", "--port", str(puerto), "--host", "127.0.0.1"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    cliente = httpx.Client(base_url=f"http://127.0.0.1:{puerto}", timeout=120)
    for _ in range(120):  # espera a que el servidor cargue el modelo
        try:
            cliente.get("/")
            break
        except httpx.TransportError:
            time.sleep(0.5)
    else:
        proceso.kill()
        raise RuntimeError("whisper-server no arrancó")

    def transcribir(ruta: Path) -> str:
        with open(ruta, "rb") as f:
            r = cliente.post("/inference", files={"file": (ruta.name, f, "audio/wav")}, data={"response_format": "json", "language": "es", "temperature": "0"})
        r.raise_for_status()
        return r.json()["text"].strip()

    def cerrar() -> None:
        cliente.close()
        proceso.terminate()
        proceso.wait()

    return transcribir, cerrar


def cargar(motor: str) -> tuple[Transcriptor, Callable[[], None]]:
    if motor in MLX_MODELOS:
        return cargar_mlx(*MLX_MODELOS[motor])
    return cargar_cpp(CPP_MODELOS[motor], puerto=8178 + list(CPP_MODELOS).index(motor))


def correr(motor: str, grabaciones: list[tuple]) -> list[Medicion]:
    import soundfile as sf

    print(f"\n▶ {motor}: cargando…")
    t = time.perf_counter()
    transcribir, cerrar = cargar(motor)
    transcribir(grabaciones[0][1])  # calentamiento (en mlx también carga el modelo)
    print(f"  listo en {time.perf_counter() - t:.1f} s")
    resultados = []
    try:
        for frase, ruta in grabaciones:
            tiempos, texto = [], ""
            for _ in range(REPETICIONES):
                inicio = time.perf_counter()
                texto = transcribir(ruta)
                tiempos.append(time.perf_counter() - inicio)
            lat = statistics.median(tiempos)
            dur = sf.info(str(ruta)).duration
            esperado = normalizar(frase.texto)
            wer = jiwer.wer(esperado, normalizar(texto) or "∅")
            m = Medicion(motor, frase.id, round(dur, 2), round(lat * 1000), round(lat / dur, 3), round(wer, 3), frase.texto, texto)
            resultados.append(m)
            marca = "✅" if wer == 0 else "  "
            print(f"  {marca} {frase.id}: {m.latencia_ms:5} ms  WER={m.wer:.2f}  «{texto}»")
    finally:
        cerrar()
    return resultados


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--motores", nargs="+", choices=TODOS, default=TODOS)
    args = parser.parse_args()

    grabaciones = [(f, DIR_GRABACIONES / f"{f.id}.wav") for f in FRASES_STT if (DIR_GRABACIONES / f"{f.id}.wav").exists()]
    if not grabaciones:
        print(f"No hay grabaciones en {DIR_GRABACIONES}. Corre grabar.py primero.")
        return 1
    print(f"{len(grabaciones)} grabaciones · {REPETICIONES} repeticiones por grabación")

    resultados: list[Medicion] = []
    for motor in args.motores:
        resultados += correr(motor, grabaciones)

    DIR_SALIDA.mkdir(parents=True, exist_ok=True)
    marca = time.strftime("%Y%m%d-%H%M%S")
    with open(DIR_SALIDA / f"mediciones-{marca}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(asdict(resultados[0]).keys()))
        w.writeheader()
        w.writerows(asdict(m) for m in resultados)

    print("\n=== Resumen ===")
    print(f"{'motor':18} {'lat p50':>8} {'lat p90':>8} {'RTF':>6} {'WER prom':>9} {'exactas':>8}  nombre")
    for motor in args.motores:
        ms = [m for m in resultados if m.motor == motor]
        lats = sorted(m.latencia_ms for m in ms)
        p90 = lats[int(0.9 * (len(lats) - 1))]
        wer_prom = statistics.mean(m.wer for m in ms)
        exactas = sum(m.wer == 0 for m in ms)
        n1 = next((m for m in ms if m.frase_id == "N1"), None)
        nombre = "✅" if n1 and NOMBRE in normalizar(n1.transcripcion) else f"❌ «{n1.transcripcion if n1 else '—'}»"
        rtf = statistics.median(m.rtf for m in ms)
        print(f"{motor:18} {statistics.median(lats):7.0f}ms {p90:7}ms {rtf:6.3f} {wer_prom:9.1%} {exactas:4}/{len(ms)}  {nombre}")
    print(f"\nDetalle en {DIR_SALIDA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
