"""Graba las frases de prueba con tu voz para el benchmark de STT.

Por cada frase: Enter para empezar a grabar, Enter para terminar.
Después: Enter = siguiente · r = repetir · e = escuchar · q = salir.

Las grabaciones se guardan en <repo>/recordings/voz01/ (ignorada en git; nunca sale de la Mac).
Si vuelves a correr el script, salta las frases ya grabadas (usa --rehacer para regrabarlas).

Uso (desde experiments/voz/):
    .venv/bin/python grabar.py
    .venv/bin/python grabar.py --solo N1 A1    # solo algunas frases
    .venv/bin/python grabar.py --rehacer       # regrabar todo
"""

from __future__ import annotations

import argparse
import queue
import sys
from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf

from frases import FRASES_STT

SR = 16_000  # frecuencia nativa de Whisper
RAIZ_REPO = Path(__file__).resolve().parents[2]
DIR_GRABACIONES = RAIZ_REPO / "recordings" / "voz01"


def grabar() -> np.ndarray:
    """Graba del micrófono hasta que se presione Enter."""
    bloques: queue.Queue[np.ndarray] = queue.Queue()

    def callback(indata, frames, tiempo, status):  # noqa: ARG001
        bloques.put(indata.copy())

    with sd.InputStream(samplerate=SR, channels=1, dtype="float32", callback=callback):
        input("   🔴 Grabando… (Enter para terminar) ")
    partes = []
    while not bloques.empty():
        partes.append(bloques.get())
    return np.concatenate(partes)[:, 0] if partes else np.zeros(0, dtype=np.float32)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--solo", nargs="+", help="IDs de frases a grabar (p. ej. N1 A1)")
    parser.add_argument("--rehacer", action="store_true", help="regrabar aunque ya existan")
    args = parser.parse_args()

    DIR_GRABACIONES.mkdir(parents=True, exist_ok=True)
    frases = [f for f in FRASES_STT if not args.solo or f.id in args.solo]
    entrada = sd.query_devices(kind="input")["name"]
    print(f"Micrófono: {entrada}")
    print(f"Destino: {DIR_GRABACIONES}")
    print("Lee cada frase con naturalidad, como le hablarías a Tessia.\n")

    for i, frase in enumerate(frases, 1):
        archivo = DIR_GRABACIONES / f"{frase.id}.wav"
        if archivo.exists() and not args.rehacer:
            print(f"[{i}/{len(frases)}] {frase.id} ya grabada, se salta.")
            continue
        while True:
            print(f"[{i}/{len(frases)}] {frase.id}  «{frase.texto}»")
            if frase.emocion:
                print(f"   (dila con tono de: {frase.emocion})")
            input("   Enter para grabar ")
            audio = grabar()
            dur = len(audio) / SR
            pico = float(np.abs(audio).max()) if len(audio) else 0.0
            aviso = "  ⚠️ muy bajo, acércate al micrófono" if pico < 0.05 else ""
            print(f"   {dur:.1f} s, nivel máx {pico:.2f}{aviso}")
            opcion = input("   Enter = guardar y seguir · r = repetir · e = escuchar · q = salir: ").strip().lower()
            while opcion == "e":
                sd.play(audio, SR)
                sd.wait()
                opcion = input("   Enter = guardar y seguir · r = repetir · e = escuchar · q = salir: ").strip().lower()
            if opcion == "q":
                print("Saliendo (esta frase no se guardó).")
                return 0
            if opcion == "r":
                continue
            sf.write(archivo, audio, SR)
            print("   ✅ guardada\n")
            break

    print(f"Listo. Grabaciones en {DIR_GRABACIONES}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nInterrumpido.")
        sys.exit(1)
