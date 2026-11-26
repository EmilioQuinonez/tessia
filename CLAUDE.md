# Tessia — Contexto del proyecto (v2)

Asistente de voz personal tipo Jarvis/Alexa en **español mexicano**, para uso en casa y familia.
Autor: Emilio. Toda la documentación se escribe en español. Proyecto también pensado como **portafolio**.

## Visión

Un solo asistente ("Tessia") con un **cerebro central** que **sigue al usuario entre dispositivos**
(Mac, iPhone, PC, bocinas/satélites por cuarto) y se adapta a lo que cada uno puede hacer.
Debe hacer lo que hace Alexa (foco/IoT, música, agenda, correo, recordatorios), con **voz natural**
e interacción tan fluida como Alexa (respuesta inmediata, se puede interrumpir).

Ecosistema del usuario: **Apple/iCloud** principalmente (Google ocasional), **Apple Music**, sin IoT todavía
(comprará un foco **Matter**), sin Home Assistant todavía. Uso fuera de casa: **futuro**, no en el MVP.

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
- **Local-first, nube cuando vale la pena.** Wake word, VAD, memoria y control de casa → local.
  Razonamiento → LLM en la nube. **Voz (TTS) → nube** (ElevenLabs; ver experimento 01).
  STT → local o nube según el servidor. La privacidad es *controlada*, no absoluta.
- **Núcleo en Python** con **LiveKit Agents** (self-hosted). Resuelve streaming, VAD, turnos, barge-in y
  cancelación de eco, y permite conectar satélites/teléfono/web al mismo "cuarto".
- **Todo en streaming de punta a punta**; respuestas habladas de 1–2 oraciones que empiezan con una frase corta.
- **TypeScript** solo donde aporte: dashboard y, opcionalmente, servidores MCP.
- **Proveedores intercambiables** detrás de interfaces (validado: adaptador propio de mlx-whisper como `stt.STT` de LiveKit).
- **Herramientas vía MCP** (no un switch gigante).
- **Cada dispositivo expone sus capacidades**: un **agente en la Mac** (cuando está prendida) ofrece Apple Music y Atajos.
  Lo esencial no depende de la Mac: foco vía Home Assistant (Matter), calendario iCloud vía CalDAV, correo vía IMAP,
  **recordatorios propios de Tessia** con avisos push al iPhone. El iPhone es cliente, no ejecutor (iOS no permite agentes en segundo plano).
- **Respuesta hablada corta + detalle en pantalla/teléfono** para respuestas largas (mejor UX y menor costo).
- **Acciones sensibles** (correo, etc.) requieren confirmación y, a futuro, speaker ID.

## Stack (validado en `docs/experimentos/01-latencia-voz.md`)

| Pieza | Elección | Notas |
|---|---|---|
| Orquestación de voz | LiveKit Agents 1.9 (Python) | Self-hosted. El plugin de Anthropic exige SDK `anthropic` 1.x |
| VAD + turnos | Silero VAD (silencio mínimo 0.55 s) + detector de turnos multilingüe | Emilio prefiere no ser interrumpido sobre ganar ~250 ms |
| Wake word | openWakeWord ("Tessia") | Entrenar modelo propio (muestras sintéticas en español) |
| STT | **mlx-whisper large-v3-turbo + prompt de vocabulario** (Apple Silicon) o **ElevenLabs Scribe Realtime** (nube, si el servidor es una Raspberry Pi) | Whisper alucina con audio muy bajo → filtrar |
| LLM | **Claude Haiku 5.5** (`claude-haiku-5-5`), thinking adaptativo, effort `low` | ~580 ms a la primera oración |
| TTS principal | **ElevenLabs v4 Turbo** (`eleven_v4_turbo`), voz `EXAVITQu4vr4xnSDxMaL` | ~240 ms, emociones, etiquetas de audio |
| TTS respaldo | Kokoro `ef_dora` (local) | Modo sin internet; Chatterbox y Piper descartados |
| Herramientas | MCP: Home Assistant, calendario, recordatorios, búsqueda, música, "mándame esto al teléfono" | |
| Memoria | Postgres + pgvector | Memoria por persona + resumen diario |
| Speaker ID | Embeddings de voz (ECAPA / pyannote) | Base para permisos (ABAC) |
| Dashboard | TypeScript (Next.js o similar) | Después |

Latencia medida (etapa B): **~2.0–2.5 s** desde la última palabra; se percibe inmediata. Cuello de botella: fin de turno + STT.

## Hardware

- **Servidor 24/7 (pendiente de comprar)**: recomendado **Raspberry Pi 5 + SSD NVMe** con STT en la nube.
  Alternativa futura: **Mac mini M6** (desde $19,999 MXN) con STT local y acceso nativo a Apple. La Mac mini hoy no es opción por presupuesto.
- **PC de escritorio**: Ryzen 5 5600X, 32 GB, RTX 3070 Ti (8 GB VRAM). **No puede estar prendida 24/7.**
- **Desarrollo**: MacBook Pro M3 Pro (18 GB), normalmente **cerrada en un dock** con monitor externo
  → su micrófono interno está apagado; para audio se usan **AirPods Pro**.
- **Satélites** (futuro): ESP32-S3 o Raspberry Pi por cuarto; iPhone/Watch como clientes.

## Costos estimados (precios consultados el 2026-11-25; detalle en experimento 01 §12.5)

- La **voz es ~85 % del costo**. ElevenLabs: todos los planes incluyen API; v4 Turbo a $0.04 por 1,000 caracteres.
  Free (20k caracteres v4 Turbo/mes, sin licencia comercial) para desarrollar → **Starter $6/mes** (150k, licencia comercial) para uso diario.
- Claude Haiku 5.5: $0.10 / $0.50 por millón de tokens; caché a $0.01 → centavos al mes.
- Total: **~$0 en desarrollo · ~$6/mes uso ligero · ~$25/mes familia intensa.**
- Claude Pro (suscripción) **no** incluye API; la API se paga aparte por uso.

## Roadmap v2

1. **Agente básico** — ✅ validado con el experimento 01 (consola en la Mac). Falta: agente real en `agent/` y cliente web/navegador.
2. Wake word + un satélite en un cuarto.
3. Herramientas MCP: Home Assistant, timers, calendario.
4. Memoria + speaker ID + perfiles de familia.
5. App de teléfono + proactividad (brief matutino, avisos, rutinas).

## Estado actual (actualizar al cerrar cada tarea grande)

- **Experimento 01 (voz) completado** en la rama `feature/spikeVoz` (pendiente PR a `develop`).
  Código desechable en `experiments/voz/`; resultados y conclusiones en `docs/experimentos/01-latencia-voz.md`.
- **Siguientes pasos**: experimento 02 (Scribe Realtime en español), experimento 03 (agente en Raspberry Pi),
  y escribir `docs/03-ARQUITECTURA.md` de la v2 antes del código de `agent/`.
- Aún no existen: `agent/`, `tools/`, `dashboard/`, `infra/`, ni los docs 01–06.

## Estructura del repo

```
tessia/
├── agent/        # Python: LiveKit Agents (voz + cerebro) — por crear
├── tools/        # servidores MCP (Python o TS) — por crear
├── dashboard/    # TypeScript (después)
├── experiments/  # spikes desechables (código congelado al terminar; no se importa desde agent/)
├── docs/         # 01-VISION, 02-SRS, 03-ARQUITECTURA, 04-PLAN-CALIDAD, 05-SETUP, 06-ROADMAP
│   └── experimentos/   # NN-nombre.md: plan, método, resultados y conclusiones de cada experimento
├── models/       # modelos descargados (ignorado en git)
├── recordings/   # grabaciones de voz (ignorado en git; nunca salen de la máquina)
└── infra/        # docker-compose: LiveKit, Postgres, etc. — por crear
```

## Convenciones

- **Documentation-first**: escribir/actualizar docs antes o junto con el código.
- **Experimentos**: primero el documento (objetivo, método, métricas, criterios), luego el código en `experiments/`;
  resultados y conclusiones van al mismo documento. Lo reutilizable se reescribe bien en `agent/` con tests.
- **Git**: Conventional Commits (`feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `style`);
  ramas `main` ← `develop` ← `feature/…` / `fix/…` / `chore/…` (nombres en camelCase, ej. `feature/wakeWordTessia`).
- **Integración siempre por Pull Request** (nunca merge directo), llenando `.github/pull_request_template.md`.
  Emilio hace el merge.
- **Python**: PEP 8 (`snake_case`), type hints, tests con pytest. Entornos con Python 3.11 de Homebrew.
- **TypeScript**: `camelCase`; tablas y columnas de BD en `snake_case`.
- **`.env`**: variables en `UPPER_SNAKE_CASE`, sin comillas; nunca subir `.env`, API keys, modelos ni grabaciones de audio.
- **Gasto en APIs**: los scripts muestran número de llamadas/caracteres y costo estimado y piden confirmación antes de gastar.
- Licencia Apache 2.0.

## Cómo trabajar conmigo (Emilio)

- Prefiero dialogar las decisiones de arquitectura antes de aceptarlas; señala trade-offs y no asumas.
- No empezar a implementar sin mi confirmación cuando todavía estamos definiendo.
- Antes de escribir conclusiones con costos, avisarme para investigar precios a detalle.
