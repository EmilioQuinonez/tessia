# Experimento 01 — Latencia y naturalidad de la voz (spike)

| Campo | Valor |
|---|---|
| Estado | 🔬 En curso — etapa A |
| Rama | `feature/spikeVoz` |
| Código | `experiments/voz/` |
| Equipo de pruebas | MacBook Pro M3 Pro, 18 GB, macOS — Python 3.11 |
| Fecha de inicio | 2026-11-25 |

## 1. Objetivo

Validar, **antes de construir Tessia**, que la arquitectura propuesta para la v2
(STT local → LLM en la nube → TTS) se siente como un asistente tipo Alexa:

1. **Latencia**: primera palabra hablada en **≤ 1.5 s** (mediana) desde que el usuario termina de hablar.
2. **Naturalidad**: voz femenina en español mexicano que suene natural y pueda expresar emociones.
3. **Viabilidad del esqueleto**: LiveKit Agents permite conectar proveedores propios
   (STT/TTS locales) detrás de interfaces intercambiables.

### Preguntas que debe responder

- ¿Qué STT local es más rápido y preciso en Apple Silicon?
- ¿Claude Haiku responde lo bastante rápido en streaming para conversación?
- ¿Qué TTS da el mejor balance entre naturalidad y tiempo al primer audio?
- ¿Alguna TTS local se acerca a la calidad de ElevenLabs?
- ¿El flujo completo cabe en el presupuesto de 1.5 s?

### Fuera de alcance

Wake word, satélites, app de iPhone, herramientas (música, foco), memoria,
speaker ID y pruebas en la PC con CUDA (experimento aparte).

- **Respaldo sin internet** (router local + LLM pequeño vía Ollama, p. ej. `qwen2.5:3b`): experimento futuro,
  junto con el diseño del router de comandos. Los comandos simples no deberían necesitar un LLM, así que el
  modelo local solo cubriría conversación sin conexión; se evaluarán los modelos pequeños disponibles en ese momento.

## 2. Hipótesis de presupuesto de latencia

Desglose estimado para llegar a la primera palabra. Es una **hipótesis**: el experimento la confirma o la corrige.

| Etapa | Presupuesto estimado |
|---|---|
| Detección de fin de turno (VAD / endpointing) | 300–500 ms |
| STT (transcripción final) | 150–400 ms |
| LLM hasta la primera oración completa | 300–600 ms |
| TTS hasta el primer audio | 150–400 ms |
| **Total** | **~0.9–1.9 s** |

Clave: el LLM y la TTS deben trabajar **en streaming por oración**. La TTS empieza a hablar
con la primera oración mientras el LLM sigue generando.

## 3. Candidatos

### STT (local)

| Motor | Notas |
|---|---|
| `mlx-whisper` | Usa la GPU de Apple Silicon vía MLX |
| `whisper.cpp` | Usa Metal; muy ligero |

Se prueban con el modelo más preciso que dé buena latencia (p. ej. `large-v3-turbo`) y uno más pequeño como referencia.
`faster-whisper` se descarta en la Mac porque no usa la GPU de Apple (en la PC sí sería candidato).

### LLM (nube)

| Modelo | Configuraciones |
|---|---|
| Claude Haiku 5.5 (`claude-haiku-5-5`) | Streaming; thinking deshabilitado vs. adaptive con effort `low` |

Prompt de sistema corto: asistente femenina, español mexicano, respuestas habladas breves.

### TTS

| Motor | Tipo | Voz | Control de emoción |
|---|---|---|---|
| Chatterbox Multilingual | Local (MPS) | Clonada desde un audio de referencia femenino | Parámetro de intensidad/exageración |
| Kokoro | Local | `ef_dora` | Prácticamente nulo |
| Piper | Local | Voz femenina `es_MX` disponible | Nulo |
| ElevenLabs | Nube (plan gratuito) | `EXAVITQu4vr4xnSDxMaL` + una alternativa | Por el texto; etiquetas si el modelo/plan lo permite |

ElevenLabs funciona como **referencia de calidad** ("lo mejor de la nube").

**Voz de referencia para Chatterbox** (decisión):

1. **Ronda 1 — voz por defecto** de Chatterbox: sin trámites, mide latencia y calidad base.
2. **Ronda 2 — clip femenino de español de México con licencia CC0** (p. ej. Mozilla Common Voice,
   filtrando acento México), ~10 s. El acento de la voz clonada depende de la referencia, así que esta
   ronda dice si Chatterbox puede sonar mexicana.

No se clona audio generado por ElevenLabs (sus términos de uso probablemente no lo permiten).
La voz definitiva de Tessia (grabación propia con permiso, voz diseñada, etc.) se decide después del experimento.
También se revisa si existe un finetune de Chatterbox para español latino/mexicano y bajo qué licencia.

## 4. Frases de prueba

### 4.1 Respuestas generales

| ID | Categoría | Frase |
|---|---|---|
| C1 | Corta | Listo, apagué la luz de la sala. |
| C2 | Corta / hora | Tu alarma quedó a las 7:30 de la mañana. |
| C3 | Corta | Claro, ¿algo más? |
| N1 | Nombre | Buenos días, Emilio Santiago López Quiñonez. |
| N2 | Nombre | Emilio, tienes un mensaje nuevo de tu mamá. |
| F1 | Fecha / número | El martes 14 de enero tienes cita a las 4:45 de la tarde. |
| F2 | Número | La temperatura es de 23 grados, con 40 % de probabilidad de lluvia. |
| A1 | Anglicismos | Pongo tu playlist en Apple Music y la mando al HomePod por AirPlay. |
| A2 | Anglicismos | Se desconectó el Wi-Fi del foco del cuarto. |
| M1 | Modismos | ¡Órale, qué buena onda! Ahorita te lo checo. |
| M2 | Modismos | No manches, ya casi es la hora de la junta. |
| L1 | Mediana | Hoy en la mañana va a estar fresco, alrededor de 15 grados, y en la tarde sube a 24. Tienes dos pendientes en tu agenda: la llamada con el equipo a las 11 y recoger el paquete antes de las 6. |

### 4.2 Emociones

| ID | Emoción | Frase |
|---|---|---|
| E1 | Sorpresa | ¿En serio? ¡No puedo creer que ya sea viernes! |
| E2 | Alegría | ¡Qué gusto, Emilio! Me encanta que te haya ido tan bien. |
| E3 | Tristeza | Lo siento mucho… sé que era importante para ti. |
| E4 | Decepción | Ay, otra vez se te olvidó sacar la basura, ¿verdad? |
| E5 | Enojo | ¡Ya te dije tres veces que la puerta está abierta! |
| E6 | Calma | Tranquilo, todo está bajo control. Respira. |
| E7 | Entusiasmo | ¡Vámonos! Hoy va a ser un gran día. |

### 4.3 Frases para STT

Emilio graba las frases C1–M2 y E1–E7 con su voz (además de órdenes típicas como
"Tessia, apaga la luz" o "pon música de Natalia Lafourcade").
Las grabaciones se quedan **solo en local** (`recordings/`, ignorada en git).

## 5. Métricas

| Pieza | Métrica | Definición |
|---|---|---|
| STT | Latencia | Fin del audio → texto final |
| STT | WER | Tasa de error de palabras contra el texto esperado |
| STT | Nombre | ¿Transcribe bien "Emilio Santiago López Quiñonez"? (sí/no) |
| LLM | TTFT | Envío de la petición → primer token |
| LLM | Primera oración | Envío → primera oración completa (lista para TTS) |
| TTS | TTFA | Texto enviado → primer fragmento de audio |
| TTS | RTF | Tiempo de síntesis ÷ duración del audio (< 1 = más rápido que tiempo real) |
| TTS | Naturalidad | Calificación de Emilio, 1–5 |
| TTS | Pronunciación | Calificación 1–5 (nombre, números, anglicismos) |
| TTS | Emoción | Calificación 1–5: ¿se percibe la emoción pedida? |
| E2E | Latencia total | Fin de habla del usuario → primer audio de respuesta |

Cada medición de latencia se repite **10 veces**; se reportan **mediana (p50) y p90**.
La primera ejecución (carga del modelo / calentamiento) se descarta.

## 6. Procedimiento

### Etapa A — Medición por pieza (scripts sueltos, sin LiveKit)

1. Preparar entorno: `ffmpeg`, `portaudio`, entorno virtual con Python 3.11, `.env` con las API keys.
2. **STT**: transcribir las grabaciones con cada motor y medir latencia y WER.
3. **LLM**: enviar preguntas típicas a Haiku en streaming y medir TTFT y tiempo a la primera oración.
4. **TTS**: sintetizar todas las frases con cada motor; medir TTFA y RTF; guardar los audios.
5. **Escucha**: Emilio escucha y califica en una hoja (`calificaciones.csv`).

### Etapa B — Flujo completo (LiveKit Agents, modo consola)

1. Agente mínimo: Silero VAD → STT → Claude Haiku → TTS, con la mejor combinación de la etapa A.
2. Si gana un motor local, escribir su adaptador (plugin) para LiveKit.
3. Conversación real en la Mac (micrófono y bocinas): medir latencia E2E.
4. Probar barge-in: interrumpir a Tessia mientras habla.

## 7. Criterios de éxito

| Criterio | Umbral |
|---|---|
| Latencia E2E (p50) | ≤ 1.5 s (deseable ≤ 1.2 s) |
| Naturalidad de la TTS elegida | ≥ 4 / 5 |
| Pronunciación del nombre y anglicismos | Correcta en la TTS elegida |
| Emociones | Distinguibles en al menos 4 de 7 |
| Integración en LiveKit | Proveedor propio funcionando detrás de la interfaz del plugin |

Si ninguna combinación local cumple, se documenta la brecha y las alternativas
(TTS en la nube, probar en la PC con CUDA, otro hardware).

## 8. Organización del código

```
experiments/voz/
├── README.md            # cómo correr el experimento
├── .env.example         # ANTHROPIC_API_KEY, ELEVENLABS_API_KEY
├── frases.py            # frases de prueba (fuente única)
├── stt_bench.py
├── llm_bench.py
├── tts_bench.py
├── agente_consola.py    # etapa B
└── salidas/             # audios y resultados (ignorado en git)
```

## 9. Privacidad y costos

- Las frases con el nombre de Emilio se envían a **Anthropic** y **ElevenLabs**; las grabaciones de voz **no** salen de la Mac.
- ElevenLabs: el set de frases cabe en el límite mensual del plan gratuito.
- Anthropic: **único modelo permitido `claude-haiku-5-5`** (Claude Haiku 5.5, $0.10 / $0.50 por millón de tokens de entrada/salida).
  - El ID va fijo en una constante; los scripts no aceptan otro modelo.
  - `max_tokens` limitado (respuestas habladas cortas) y número de llamadas fijo.
  - Cada script muestra el número de llamadas y el costo estimado **antes** de ejecutar y pide confirmación.
  - Estimado de la etapa A: ~100 llamadas → **menos de $0.05 USD**.

## 10. Qué pasa con el experimento al terminar

- **Este documento se queda para siempre**: registra por qué se eligió cada pieza de voz.
- **El código de `experiments/voz/` se congela**: no se mantiene ni se importa desde `agent/`.
  Su README indicará que es histórico.
- Lo que sirva (p. ej. un adaptador de STT/TTS) **se reescribe bien en `agent/`**, con tests, en su propia rama `feature/…`.
- Si más adelante el código estorba, se borra; queda en el historial de git (y opcionalmente un tag `spike-voz`).

## 11. Resultados

### 11.1 LLM — Claude Haiku 5.5 (2026-11-25)

Script: `experiments/voz/llm_bench.py`. 5 preguntas × 10 repeticiones × 2 configuraciones (100 llamadas + 2 de calentamiento),
`max_tokens=400`, streaming, desde la red de casa en la Mac. Costo real: **$0.006 USD** (13,130 tokens de entrada / 9,598 de salida).

| Configuración | TTFT p50 / p90 | Primera oración p50 / p90 | Total p50 / p90 | Tokens de salida (prom.) |
|---|---|---|---|---|
| `sin_thinking` (thinking deshabilitado, effort low) | 362 / 644 ms | 600 / 990 ms | 960 / 1250 ms | 93 |
| `thinking_low` (adaptive, effort low) | 358 / 608 ms | 578 / 817 ms | 828 / 1433 ms | 99 |

Observaciones:

- **Ambas configuraciones rinden igual** en la mediana: con effort `low`, el razonamiento adaptativo casi no se activa en preguntas sencillas.
  La diferencia entre preguntas (480–980 ms) es mayor que la diferencia entre configuraciones.
- **Primera oración ≈ 600 ms (p50)**: en el límite alto del presupuesto estimado (300–600 ms).
- **Respuestas con primera oración larga tardan más** (p. ej. la receta: ~980 ms). Idea para la etapa B: pedir en el prompt
  una primera frase corta ("Claro, …") y/o cortar para la TTS también en comas y dos puntos.
- **Formato correcto**: 100/100 terminaron en `end_turn`, sin markdown ni listas, 2.2 oraciones en promedio (máx. 3).
  Tono mexicano natural ("jitomate", "Ay, qué bueno que me lo pides").
- **Precisión**: la diferencia horaria con Australia fue aproximada/imprecisa → datos que cambian (hora, clima, agenda)
  deben venir de herramientas, no del conocimiento del modelo.

**Decisión preliminar**: usar `thinking_low` (adaptive, effort `low`). Misma latencia y deja margen para razonar cuando
haya herramientas. Se revalida en la etapa B.

### 11.2 TTS — latencia (2026-11-25)

Script: `experiments/voz/tts_bench.py`. 19 frases por motor, una corrida cada una (tras calentamiento).
Locales: síntesis oración por oración, TTFA = primera oración. ElevenLabs: streaming nativo, TTFA = primer fragmento.

| Motor | Dónde corre | TTFA p50 | TTFA máx. | RTF p50 |
|---|---|---|---|---|
| Piper `es_MX-claude-high` | Local, CPU | **62 ms** | 130 ms | 0.02 |
| ElevenLabs Flash v2.5 | Nube | **179 ms** | 399 ms | — |
| ElevenLabs Multilingual v2 | Nube | **345 ms** | 475 ms | — |
| Kokoro `ef_dora` | Local, CPU | **350 ms** | 735 ms | 0.12 |
| Chatterbox Multilingual (voz por defecto) | Local, GPU Mac (MPS) | **14.5 s** | 131 s | 4.14 |

Observaciones:

- **Chatterbox no es viable en la Mac**: ~4× más lento que tiempo real (tarda 4 s por cada segundo de audio).
  Además, en E6 generó 13.7 s de audio para una frase de ~3 s (alucinación/silencio largo, revisar al escuchar).
  Para usarlo en conversación se necesita GPU NVIDIA (la PC) → pendiente medirlo ahí.
  **Implicación de hardware**: una Mac mini como servidor no podría correr Chatterbox en tiempo real.
- **Piper, Kokoro y ElevenLabs caben en el presupuesto** (150–400 ms).
- Los motores locales dependen de la longitud de la primera oración (L1 es el peor caso); ElevenLabs casi no, por su streaming.

### 11.3 TTS — calificaciones de Emilio (2026-11-25)

Escucha de las 19 frases por motor (`salidas/tts/escuchar.html`). Evaluación cualitativa:

| Lugar | Motor | Naturalidad | Pronunciación | Emociones | Comentarios |
|---|---|---|---|---|---|
| 1 | ElevenLabs Multilingual v2 | Excelente, "increíble" | Buena | ✅ Se notan sin exagerar | La mejor en general |
| 2 | ElevenLabs Flash v2.5 | Muy buena | Buena; algunas frases suenan raras | ✅ Se detectan, a veces forzadas o muy marcadas | Muy por encima de los locales |
| 3 | Kokoro `ef_dora` | Buena (voz conocida de la v1) | Buena | ❌ | La mejor local |
| 4 | Piper `es_MX-claude-high` | Aceptable para su velocidad | ❌ Falla en acentos y algunas palabras | ❌ | Útil solo por rapidez |
| 5 | Chatterbox (voz por defecto) | ❌ | ❌ | ❌ | Ruidos de fondo, habla en otro idioma, voz masculina |

Conclusiones:

- **Ninguna TTS local maneja emociones.** Solo ElevenLabs cumple el criterio de emociones (§7).
- **ElevenLabs Multilingual v2 es la mejor voz** y aun así cabe en el presupuesto de latencia (345 ms p50);
  Flash v2.5 es la alternativa rápida (179 ms) con algo menos de naturalidad.
- **Chatterbox se descarta en la Mac** (calidad y latencia). La ronda 2 (clip mexicano CC0) no se corre en la Mac;
  solo tendría sentido en la PC con CUDA, como experimento aparte.
- **Kokoro queda como mejor opción local** (respaldo sin internet / respuestas cortas).

**Implicación importante**: la decisión de la v2 asumía TTS local (Chatterbox) y que el único gasto sería el LLM.
Si la voz principal es ElevenLabs, la voz pasa a ser **un gasto mensual en la nube** y deja de ser local.
Hay que estimar el costo con uso real y considerar un esquema híbrido (ver §12).

## 12. Conclusiones y recomendación

_Pendiente._
