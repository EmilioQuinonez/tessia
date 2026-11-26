"""Etapa B: agente de voz mínimo con LiveKit Agents en modo consola (micrófono y bocinas de la Mac).

Flujo: Silero VAD → mlx-whisper turbo (+ prompt de vocabulario) → Claude Haiku 5.5 → ElevenLabs v4 Turbo.

Mide por turno (en salidas/agente/):
- Latencia percibida: desde que el VAD detecta que dejaste de hablar hasta que Tessia empieza a hablar.
  (A eso hay que sumar el silencio mínimo del VAD, SILENCIO_VAD_S, para obtener "desde tu última palabra").
- Métricas internas de LiveKit: retraso de fin de turno, STT, TTFT del LLM y TTFB de la TTS.

Uso (desde experiments/voz/):
    .venv/bin/python agente_consola.py download-files   # una vez: modelos del detector de turnos
    .venv/bin/python agente_consola.py console          # conversar (Ctrl+C para terminar)

Variables opcionales:
    DETECTOR=vad            usar solo VAD para fin de turno (por defecto: detector multilingüe de LiveKit)
    PREEMPTIVO=0            desactivar la generación anticipada del LLM
"""

from __future__ import annotations

import os
from pathlib import Path

RAIZ_REPO = Path(__file__).resolve().parents[2]
os.environ.setdefault("HF_HOME", str(RAIZ_REPO / "models" / "huggingface"))

import asyncio
import csv
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from math import gcd

import numpy as np
from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    APIConnectOptions,
    JobContext,
    JobProcess,
    MetricsCollectedEvent,
    cli,
    metrics,
    stt,
)
from livekit.agents.types import NOT_GIVEN, NotGivenOr
from livekit.agents.utils import AudioBuffer, is_given
from livekit.plugins import anthropic, elevenlabs, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel  # debe importarse en el hilo principal

load_dotenv(Path(__file__).parent / ".env")

# --- Configuración del experimento --------------------------------------------
MODELO_LLM = "claude-haiku-5-5"  # único modelo permitido (ver docs §9)
MODELO_STT = "mlx-community/whisper-large-v3-turbo"
MODELO_TTS = "eleven_v4_turbo"
PROMPT_VOCABULARIO = "Tessia, Emilio Santiago López Quiñonez, Apple Music, HomePod, AirPlay, Wi-Fi, Natalia Lafourcade."
SILENCIO_VAD_S = 0.55  # min_silence_duration de Silero (valor por defecto)

INSTRUCCIONES = (
    "Eres Tessia, una asistente de voz de casa. Hablas español mexicano, con calidez y naturalidad. "
    "Tus respuestas se convierten en voz: responde en una o dos oraciones cortas, "
    "sin listas, sin markdown, sin emojis y sin abreviaturas. "
    "Empieza siempre con una frase muy corta (por ejemplo «Claro.» o «Mira,») antes del resto."
)

DIR_SALIDA = Path(__file__).parent / "salidas" / "agente"


# --- STT: mlx-whisper como proveedor de LiveKit --------------------------------


class MlxWhisperSTT(stt.STT):
    """Adaptador de mlx-whisper (no streaming) para LiveKit.

    MLX corre en un hilo dedicado para no bloquear el audio; el modelo se precarga en ese mismo hilo.
    """

    def __init__(self, repo: str, prompt: str | None) -> None:
        super().__init__(capabilities=stt.STTCapabilities(streaming=False, interim_results=False))
        self._repo = repo
        self._prompt = prompt
        self._hilo = ThreadPoolExecutor(max_workers=1, thread_name_prefix="mlx-whisper")
        self._hilo.submit(self._transcribir, np.zeros(16_000, dtype=np.float32)).result()  # precarga

    @property
    def model(self) -> str:
        return self._repo

    @property
    def provider(self) -> str:
        return "mlx-whisper"

    def _transcribir(self, audio: np.ndarray) -> str:
        import mlx_whisper

        r = mlx_whisper.transcribe(audio, path_or_hf_repo=self._repo, language="es", initial_prompt=self._prompt, verbose=None)
        return r["text"].strip()

    async def _recognize_impl(
        self,
        buffer: AudioBuffer,
        *,
        language: NotGivenOr[str] = NOT_GIVEN,
        conn_options: APIConnectOptions,
    ) -> stt.SpeechEvent:
        frame = rtc.combine_audio_frames(buffer)
        audio = np.frombuffer(frame.data, dtype=np.int16).astype(np.float32) / 32768.0
        if frame.num_channels > 1:
            audio = audio.reshape(-1, frame.num_channels).mean(axis=1)
        if frame.sample_rate != 16_000:
            from scipy.signal import resample_poly

            g = gcd(16_000, frame.sample_rate)
            audio = resample_poly(audio, 16_000 // g, frame.sample_rate // g).astype(np.float32)
        texto = await asyncio.get_running_loop().run_in_executor(self._hilo, self._transcribir, audio)
        return stt.SpeechEvent(
            type=stt.SpeechEventType.FINAL_TRANSCRIPT,
            alternatives=[stt.SpeechData(language="es", text=texto)],
        )


# --- LLM: Haiku 5.5 con thinking adaptativo y effort low (lo medido en la etapa A) ---


class HaikuLLM(anthropic.LLM):
    def __init__(self) -> None:
        super().__init__(model=MODELO_LLM, max_tokens=400)

    def chat(self, *args, extra_kwargs: NotGivenOr[dict] = NOT_GIVEN, **kwargs):  # type: ignore[override]
        extra = dict(extra_kwargs) if is_given(extra_kwargs) else {}
        extra.setdefault("thinking", {"type": "adaptive"})
        extra.setdefault("output_config", {"effort": "low"})
        return super().chat(*args, extra_kwargs=extra, **kwargs)


# --- Registro de latencias por turno -------------------------------------------


class Registro:
    def __init__(self) -> None:
        self.turnos: list[dict] = []
        self._fin_usuario: float | None = None
        self._actual: dict = {}

    def usuario_dejo_de_hablar(self) -> None:
        self._fin_usuario = time.perf_counter()
        self._actual = {}

    def tessia_empezo_a_hablar(self) -> None:
        if self._fin_usuario is None:
            return  # saludo inicial u otra respuesta sin turno del usuario
        lat = time.perf_counter() - self._fin_usuario
        self._fin_usuario = None
        self._actual["latencia_percibida_ms"] = round(lat * 1000)
        self._actual["desde_ultima_palabra_ms"] = round((lat + SILENCIO_VAD_S) * 1000)
        self.turnos.append(self._actual)
        print(f"\n⏱  Tessia empezó a hablar {self._actual['latencia_percibida_ms']} ms después del fin de turno "
              f"(≈ {self._actual['desde_ultima_palabra_ms']} ms desde tu última palabra)\n")

    def metrica(self, m: metrics.AgentMetrics) -> None:
        destino = self.turnos[-1] if self._fin_usuario is None and self.turnos else self._actual
        if isinstance(m, metrics.EOUMetrics):
            destino["fin_turno_ms"] = round(m.end_of_utterance_delay * 1000)
            destino["stt_ms"] = round(m.transcription_delay * 1000)
        elif isinstance(m, metrics.LLMMetrics):
            destino.setdefault("llm_ttft_ms", round(m.ttft * 1000))
        elif isinstance(m, metrics.TTSMetrics):
            destino.setdefault("tts_ttfb_ms", round(m.ttfb * 1000))

    def texto(self, rol: str, contenido: str) -> None:
        destino = self.turnos[-1] if rol == "assistant" and self.turnos and self._fin_usuario is None else self._actual
        destino["usuario" if rol == "user" else "tessia"] = contenido

    def guardar(self) -> None:
        if not self.turnos:
            return
        DIR_SALIDA.mkdir(parents=True, exist_ok=True)
        marca = time.strftime("%Y%m%d-%H%M%S")
        campos = ["latencia_percibida_ms", "desde_ultima_palabra_ms", "fin_turno_ms", "stt_ms", "llm_ttft_ms", "tts_ttfb_ms", "usuario", "tessia"]
        with open(DIR_SALIDA / f"turnos-{marca}.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=campos, extrasaction="ignore")
            w.writeheader()
            w.writerows(self.turnos)
        lats = [t["desde_ultima_palabra_ms"] for t in self.turnos]
        print(f"\n=== {len(lats)} turnos · desde tu última palabra: p50={statistics.median(lats):.0f} ms, máx={max(lats)} ms ===")
        print(f"Guardado en {DIR_SALIDA}")


# --- Agente --------------------------------------------------------------------


def prewarm(proc: JobProcess) -> None:
    proc.userdata["vad"] = silero.VAD.load(min_silence_duration=SILENCIO_VAD_S)
    proc.userdata["stt"] = MlxWhisperSTT(MODELO_STT, PROMPT_VOCABULARIO)  # precarga fuera del loop del agente


server = AgentServer(setup_fnc=prewarm)


@server.rtc_session()
async def entrypoint(ctx: JobContext) -> None:
    registro = Registro()

    turnos: dict = {
        "preemptive_generation": {"enabled": os.environ.get("PREEMPTIVO", "1") != "0"},
    }
    if os.environ.get("DETECTOR", "multilingual") == "vad":
        turnos["turn_detection"] = "vad"
    else:
        turnos["turn_detection"] = MultilingualModel()

    session = AgentSession(
        vad=ctx.proc.userdata["vad"],
        stt=ctx.proc.userdata["stt"],
        llm=HaikuLLM(),
        tts=elevenlabs.TTS(
            voice_id=os.environ.get("ELEVENLABS_VOICE_ID") or "EXAVITQu4vr4xnSDxMaL",
            model=MODELO_TTS,
            language="es",
            api_key=os.environ["ELEVENLABS_API_KEY"],
        ),
        turn_handling=turnos,
    )

    @session.on("user_state_changed")
    def _usuario(ev) -> None:
        if ev.old_state == "speaking" and ev.new_state == "listening":
            registro.usuario_dejo_de_hablar()

    @session.on("agent_state_changed")
    def _agente(ev) -> None:
        if ev.new_state == "speaking":
            registro.tessia_empezo_a_hablar()

    @session.on("metrics_collected")
    def _metricas(ev: MetricsCollectedEvent) -> None:
        registro.metrica(ev.metrics)

    @session.on("conversation_item_added")
    def _texto(ev) -> None:
        item = ev.item
        if getattr(item, "role", None) in ("user", "assistant") and getattr(item, "text_content", None):
            registro.texto(item.role, item.text_content)

    async def al_terminar() -> None:
        registro.guardar()

    ctx.add_shutdown_callback(al_terminar)

    await session.start(agent=Agent(instructions=INSTRUCCIONES), room=ctx.room)
    await session.say("Hola, soy Tessia. ¿En qué te ayudo?")


if __name__ == "__main__":
    cli.run_app(server)
