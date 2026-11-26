# Experimento 01 — Voz (spike)

> ⚠️ **Código experimental y desechable.** No se mantiene ni se importa desde `agent/`.
> Plan, método y resultados: [`docs/experimentos/01-latencia-voz.md`](../../docs/experimentos/01-latencia-voz.md).

## Requisitos (macOS, Apple Silicon)

```bash
brew install ffmpeg portaudio espeak-ng whisper-cpp
```

Python 3.11 (Homebrew: `/opt/homebrew/bin/python3.11`).

## Instalación

Desde esta carpeta (`experiments/voz/`):

```bash
/opt/homebrew/bin/python3.11 -m venv .venv
.venv/bin/pip install -r requirements.lock.txt   # versiones exactas probadas
cp .env.example .env                              # y llena las API keys
```

`requirements.txt` lista las dependencias directas; `requirements.lock.txt` congela las versiones con las que se corrió el experimento.

## Modelos

Se descargan en `models/` en la raíz del repo (ignorada en git, ~7.8 GB):

| Modelo | Uso | Ruta |
|---|---|---|
| `mlx-community/whisper-large-v3-turbo` | STT (mlx-whisper) | `models/huggingface/` |
| `mlx-community/whisper-small-mlx` | STT (referencia pequeña) | `models/huggingface/` |
| `ggml-large-v3-turbo.bin`, `ggml-small.bin` | STT (whisper.cpp) | `models/whisper.cpp/` |
| `hexgrad/Kokoro-82M` (voz `ef_dora`) | TTS | `models/huggingface/` |
| `ResembleAI/chatterbox` (multilingüe) | TTS | `models/huggingface/` |
| `es_MX-claude-high` | TTS (Piper) | `models/piper/` |

Los scripts usan `HF_HOME=<repo>/models/huggingface` para que Hugging Face no descargue en `~/.cache`.

## Estructura

```
experiments/voz/
├── README.md
├── .env.example
├── requirements.txt
├── requirements.lock.txt
└── salidas/             # audios y resultados (ignorado en git)
```

Los scripts de medición (`stt_bench.py`, `llm_bench.py`, `tts_bench.py`, `agente_consola.py`) se agregan en la etapa A y B.
