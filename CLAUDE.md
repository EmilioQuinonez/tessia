# Tessia — Contexto del proyecto (v2)

Asistente de voz personal tipo Jarvis/Alexa en **español mexicano**, para uso en casa y familia.
Autor: Emilio. Toda la documentación se escribe en español.

## Historia: por qué existe la v2

La v1 (repo `orion`, archivado con tag `v1.0-mvp1`) funcionaba de punta a punta:
cliente Python (WebRTC VAD → Vosk wake word → faster-whisper → ElevenLabs/Kokoro) +
backend Express/TypeScript (Ollama qwen3.5:9b, 29 comandos macOS vía osascript, Prisma/Postgres, 72 tests).

Llegó a un tope de **arquitectura**, no de calidad de código:

1. **Dos llamadas al LLM por turno** (`detectIntent` en JSON + `generateResponse`) → el doble de latencia y JSON frágil.
2. **El streaming no se aprovechaba**: el backend mandaba tokens, pero el cliente esperaba la respuesta completa y el TTS sintetizaba todo antes de reproducir.
3. **Wake word con Vosk como ASR completo + matching difuso** ("decía", "te decía") → falsos positivos.
4. **Half-duplex**: reproducción bloqueante, sin barge-in (no se puede interrumpir).
5. **Comandos amarrados a la Mac** (osascript) y hardcodeados en prompt + whitelist + switch → no escala.
6. **Inteligencia limitada**: modelo local de 9B, 10 mensajes de historial, un solo usuario, sin memoria.
7. **Dos lenguajes sin beneficio**: la voz ya vivía en Python; el backend TS era solo un proxy.

## Decisiones de la v2

- **Ya no es 100% local ni solo TypeScript.** Prioridades: que sea **inteligente** y que la **voz suene natural**.
- **Local-first, nube cuando vale la pena**: voz, wake word, STT, speaker ID, memoria y control de casa → local.
  Razonamiento y conversación → LLM en la nube. La privacidad es *controlada*, no absoluta.
- **Núcleo en Python** con **LiveKit Agents** (self-hosted). Resuelve streaming, VAD, turnos, barge-in y
  cancelación de eco, y permite conectar satélites/teléfono/web al mismo "cuarto".
- **TypeScript** solo donde aporte: dashboard y, opcionalmente, servidores MCP.
- **Proveedores intercambiables** detrás de interfaces: `LlmProvider`, `SttProvider`, `TtsProvider`.
- **Herramientas vía MCP** (no un switch gigante). Los comandos `osascript` de la v1 pueden volverse un servidor MCP `mac-control`.
- **Respuesta hablada corta + detalle en pantalla/teléfono** para respuestas largas (mejor UX y menor costo).

## Stack objetivo

| Pieza | Elección | Notas |
|---|---|---|
| Orquestación de voz | LiveKit Agents (Python) | Self-hosted en la PC |
| VAD | Silero VAD | |
| Wake word | openWakeWord ("Tessia") | Entrenar modelo propio |
| STT | faster-whisper en GPU (CUDA) | |
| TTS principal | Chatterbox Multilingual — finetune `es-mx-latam` | MIT, local, clonación de voz, control de emoción |
| TTS rápido | Piper (voces es_MX) | Confirmaciones cortas |
| LLM | Nube (Gemini Flash / Claude Haiku / Sonnet) + Ollama de respaldo | Router: comandos simples sin LLM o con modelo pequeño |
| Herramientas | MCP: Home Assistant, calendario, recordatorios, búsqueda, música, "mándame esto al teléfono" | |
| Memoria | Postgres + pgvector | Memoria por persona + resumen diario |
| Speaker ID | Embeddings de voz (ECAPA / pyannote) | Base para permisos (ABAC) |
| Dashboard | TypeScript (Next.js o similar) | Después |

## Hardware

- **Servidor**: PC de escritorio — Ryzen 5 5600X, 32 GB RAM, RTX 3070 Ti (**8 GB VRAM**).
  Whisper + Chatterbox caben; un LLM local de 8B además llena la VRAM → por eso el cerebro va en la nube.
- **Desarrollo**: MacBook Pro M3 Pro (18 GB).
- **Satélites** (futuro): ESP32-S3 o Raspberry Pi por cuarto; iPhone/Watch como clientes.

## Costos estimados (uso personal)

- Con TTS local (Chatterbox/Piper), el único gasto es el LLM en la nube: ~$10–25 USD/mes aunque se use mucho.
- Capa gratuita de Gemini sirve para prototipar, pero sus datos pueden usarse para mejorar productos de Google → para uso familiar real, capa de pago.
- Claude Pro (suscripción) **no** incluye API; la API se paga aparte por uso.

## Roadmap v2

1. **Agente básico**: hablar desde el navegador → LLM en la nube + Chatterbox. Validar que *se sienta* bien (latencia < ~1.5 s a la primera palabra).
2. Wake word + un satélite en un cuarto.
3. Herramientas MCP: Home Assistant, timers, calendario.
4. Memoria + speaker ID + perfiles de familia.
5. App de teléfono + proactividad (brief matutino, avisos, rutinas).

## Estructura del repo

```
tessia/
├── agent/        # Python: LiveKit Agents (voz + cerebro)
├── tools/        # servidores MCP (Python o TS)
├── dashboard/    # TypeScript (después)
├── docs/         # 01-VISION, 02-SRS, 03-ARQUITECTURA, 04-PLAN-CALIDAD, 05-SETUP, 06-ROADMAP
└── infra/        # docker-compose: LiveKit, Postgres, etc.
```

## Convenciones

- **Documentation-first**: escribir/actualizar docs antes o junto con el código.
- **Git**: Conventional Commits (`feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `style`);
  ramas `main` ← `develop` ← `feature/…` / `fix/…` (nombres en camelCase, ej. `feature/wakeWordTessia`).
- **Python**: PEP 8 (`snake_case`), type hints, tests con pytest.
- **TypeScript**: `camelCase`; tablas y columnas de BD en `snake_case`.
- **`.env`**: variables en `UPPER_SNAKE_CASE`; nunca subir `.env`, API keys, modelos ni grabaciones de audio.
- Licencia Apache 2.0.

## Cómo trabajar conmigo (Emilio)

- Prefiero dialogar las decisiones de arquitectura antes de aceptarlas; señala trade-offs y no asumas.
- Siguiente paso pendiente: escribir `docs/03-ARQUITECTURA.md` de la v2 antes de tocar código.
