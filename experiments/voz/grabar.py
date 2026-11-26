"""Graba las frases de prueba con tu voz para el benchmark de STT.

Por cada frase: Enter para empezar a grabar, Enter para terminar.
Después: Enter = siguiente · r = repetir · e = escuchar · q = salir.

Las grabaciones se guardan en <repo>/recordings/voz01/ (ignorada en git; nunca sale de la Mac).
Si vuelves a correr el script, salta las frases ya grabadas (usa --rehacer para regrabarlas).

Uso (desde experiments/voz/):
    .venv/bin/python grabar.py
    .venv/bin/python grabar.py --solo N1 A1    # solo algunas frases
    .venv/bin/python grabar.py --rehacer       # regrabar todo
    .venv/bin/python grabar.py --listar        # ver micrófonos
    .venv/bin/python grabar.py --microfono AirPods   # usar otro micrófono (por defecto: el de la MacBook)
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


def elegir_microfono(nombre: str | None) -> int | None:
    """Devuelve el índice del micrófono cuyo nombre contiene `nombre` (None = el del sistema)."""
    if not nombre:
        return None
    for i, d in enumerate(sd.query_devices()):
        if d["max_input_channels"] > 0 and nombre.lower() in d["name"].lower():
            return i
    raise SystemExit(f"No encontré un micrófono que contenga «{nombre}». Usa --listar para ver los disponibles.")


class Microfono:
    """Mantiene el micrófono abierto toda la sesión.

    Los micrófonos Bluetooth (AirPods) tardan en "despertar"; si se abriera el micrófono en cada frase,
    se perdería el inicio de la grabación.
    """

    def __init__(self, dispositivo: int | None) -> None:
        self._bloques: queue.Queue[np.ndarray] = queue.Queue()
        self._grabando = False
        self._stream = sd.InputStream(samplerate=SR, channels=1, dtype="float32", callback=self._callback, device=dispositivo)
        self._stream.start()

    def _callback(self, indata, frames, tiempo, status):  # noqa: ARG002
        if self._grabando:
            self._bloques.put(indata.copy())

    def _vaciar(self) -> np.ndarray:
        partes = []
        while not self._bloques.empty():
            partes.append(self._bloques.get())
        return np.concatenate(partes)[:, 0] if partes else np.zeros(0, dtype=np.float32)

    def nivel(self, segundos: float = 1.0) -> float:
        """Pico de nivel durante `segundos` (para verificar que el micrófono capta algo)."""
        self._grabando = True
        sd.sleep(int(segundos * 1000))
        self._grabando = False
        audio = self._vaciar()
        return float(np.abs(audio).max()) if len(audio) else 0.0

    def grabar(self) -> np.ndarray:
        """Graba hasta que se presione Enter."""
        self._vaciar()
        self._grabando = True
        input("   🔴 Grabando… (Enter para terminar) ")
        self._grabando = False
        return self._vaciar()

    def cerrar(self) -> None:
        self._stream.stop()
        self._stream.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--solo", nargs="+", help="IDs de frases a grabar (p. ej. N1 A1)")
    parser.add_argument("--rehacer", action="store_true", help="regrabar aunque ya existan")
    parser.add_argument("--microfono", default="", help="parte del nombre del micrófono (por defecto: el del sistema)")
    parser.add_argument("--listar", action="store_true", help="mostrar micrófonos disponibles y salir")
    args = parser.parse_args()

    if args.listar:
        for i, d in enumerate(sd.query_devices()):
            if d["max_input_channels"] > 0:
                print(f"{i}: {d['name']}")
        return 0

    dispositivo = elegir_microfono(args.microfono)
    DIR_GRABACIONES.mkdir(parents=True, exist_ok=True)
    frases = [f for f in FRASES_STT if not args.solo or f.id in args.solo]
    entrada = sd.query_devices(dispositivo if dispositivo is not None else sd.default.device[0])["name"]
    print(f"Micrófono: {entrada}")
    print(f"Destino: {DIR_GRABACIONES}")
    mic = Microfono(dispositivo)
    try:
        return grabar_frases(mic, frases, args.rehacer)
    finally:
        mic.cerrar()


def grabar_frases(mic: Microfono, frases: list, rehacer: bool) -> int:
    sd.sleep(1500)  # deja que el micrófono (sobre todo Bluetooth) termine de activarse
    print("Prueba de nivel: di algo durante 2 segundos…")
    pico = mic.nivel(2.0)
    if pico == 0.0:
        print(
            "❌ El micrófono entrega silencio absoluto. Causas comunes:\n"
            "   - MacBook con la tapa cerrada (el micrófono interno se apaga)\n"
            "   - Permiso de micrófono de la app de terminal\n"
            "   Prueba otro con --listar y --microfono <nombre>."
        )
        return 1
    print(f"   nivel máx {pico:.2f} {'✅' if pico >= 0.02 else '⚠️ muy bajo'}")
    print("Lee cada frase con naturalidad, como le hablarías a Tessia.\n")

    for i, frase in enumerate(frases, 1):
        archivo = DIR_GRABACIONES / f"{frase.id}.wav"
        if archivo.exists() and not rehacer:
            print(f"[{i}/{len(frases)}] {frase.id} ya grabada, se salta.")
            continue
        while True:
            print(f"[{i}/{len(frases)}] {frase.id}  «{frase.texto}»")
            if frase.emocion:
                print(f"   (dila con tono de: {frase.emocion})")
            input("   Enter para grabar ")
            audio = mic.grabar()
            dur = len(audio) / SR
            pico = float(np.abs(audio).max()) if len(audio) else 0.0
            aviso = "  ⚠️ casi silencio: revisa el micrófono o el permiso" if pico < 0.02 else ""
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
