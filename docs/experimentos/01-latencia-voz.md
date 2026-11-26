# Experimento 01 — Latencia y naturalidad de la voz (spike)

| Campo | Valor |
|---|---|
| Estado | ✅ Completado (2026-11-26) |
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
| ElevenLabs v4 Turbo | Nube | **240 ms** | 423 ms | — |
| ElevenLabs Multilingual v2 | Nube | **345 ms** | 475 ms | — |
| ElevenLabs v4 | Nube | **590 ms** | 889 ms | — |
| Kokoro `ef_dora` | Local, CPU | **350 ms** | 735 ms | 0.12 |
| Chatterbox Multilingual (voz por defecto) | Local, GPU Mac (MPS) | **14.5 s** | 131 s | 4.14 |

Observaciones:

- **Chatterbox no es viable en la Mac**: ~4× más lento que tiempo real (tarda 4 s por cada segundo de audio).
  Además, en E6 generó 13.7 s de audio para una frase de ~3 s (alucinación/silencio largo, revisar al escuchar).
  Para usarlo en conversación se necesita GPU NVIDIA (la PC) → pendiente medirlo ahí.
  **Implicación de hardware**: una Mac mini como servidor no podría correr Chatterbox en tiempo real.
- **Piper, Kokoro y ElevenLabs (salvo v4) caben en el presupuesto** (150–400 ms).
- **ElevenLabs v4 (590 ms) se sale del presupuesto** para conversación; solo serviría para audio no interactivo.
- v4 Turbo y v4 se agregaron en una segunda corrida tras revisar la lista oficial de modelos
  (precios por 1,000 caracteres: Flash v2.5 y v4 Turbo $0.04; Multilingual v2 y v4 $0.08).
- Los motores locales dependen de la longitud de la primera oración (L1 es el peor caso); ElevenLabs casi no, por su streaming.

### 11.3 TTS — calificaciones de Emilio (2026-11-25)

Escucha de las 19 frases por motor (`salidas/tts/escuchar.html`). Evaluación cualitativa:

| Lugar | Motor | Naturalidad | Pronunciación | Emociones | Comentarios |
|---|---|---|---|---|---|
| 1 | **ElevenLabs v4 Turbo** | Excelente; "suena igual que v4" | Buena | ✅ | "Mil veces mejor que Flash v2.5". **Ganador** |
| 1 | ElevenLabs v4 | Excelente | Buena | ✅ | Igual a v4 Turbo, pero 590 ms y el doble de precio |
| 2 | ElevenLabs Multilingual v2 | Excelente, "increíble" | Buena | ✅ Se notan sin exagerar | La mejor de la primera corrida |
| 3 | ElevenLabs Flash v2.5 | Muy buena | Buena; algunas frases suenan raras | ✅ Se detectan, a veces forzadas o muy marcadas | Muy por encima de los locales |
| 4 | Kokoro `ef_dora` | Buena (voz conocida de la v1) | Buena | ❌ | La mejor local |
| 5 | Piper `es_MX-claude-high` | Aceptable para su velocidad | ❌ Falla en acentos y algunas palabras | ❌ | Útil solo por rapidez |
| 6 | Chatterbox (voz por defecto) | ❌ | ❌ | ❌ | Ruidos de fondo, habla en otro idioma, voz masculina |

Conclusiones:

- **Ninguna TTS local maneja emociones.** Solo ElevenLabs cumple el criterio de emociones (§7).
- **ElevenLabs v4 Turbo es la TTS elegida**: calidad de v4 (la máxima), 240 ms p50, $0.04 por 1,000 caracteres
  (igual que Flash) y soporte de etiquetas de audio para emociones (a probar en la etapa B).
- **Chatterbox se descarta en la Mac** (calidad y latencia). La ronda 2 (clip mexicano CC0) no se corre en la Mac;
  solo tendría sentido en la PC con CUDA, como experimento aparte.
- **Kokoro queda como mejor opción local** (respaldo sin internet / respuestas cortas).

**Implicación importante**: la decisión de la v2 asumía TTS local (Chatterbox) y que el único gasto sería el LLM.
Si la voz principal es ElevenLabs, la voz pasa a ser **un gasto mensual en la nube** y deja de ser local.
Hay que estimar el costo con uso real y considerar un esquema híbrido (ver §12).

### 11.4 STT — Whisper local (2026-11-25)

Script: `experiments/voz/stt_bench.py`. 24 grabaciones de Emilio (19 frases + 5 órdenes), grabadas con **AirPods Pro**
(Bluetooth, 16 kHz; la MacBook estaba cerrada en el dock y su micrófono interno queda apagado).
Modelo precargado en todos los motores; latencia = mediana de 3 repeticiones.

| Motor | Latencia p50 | p90 | WER prom. | Exactas | Nombre (N1) |
|---|---|---|---|---|---|
| mlx-whisper large-v3-turbo | **716 ms** | 741 ms | 5.4 % | 16/24 | "Quiñones" |
| mlx-whisper turbo + prompt de vocabulario | 716 ms | 743 ms | **4.9 %** | 16/24 | "Quiñones" |
| whisper.cpp large-v3-turbo (Metal) | 796 ms | 817 ms | 5.4 % | 16/24 | "Quiñones" |
| mlx-whisper small | **224 ms** | 250 ms | 15.7 % | 7/24 | "Quiñones" |
| whisper.cpp small (Metal) | 223 ms | 254 ms | 15.5 % | 6/24 | "Quiñones" |

Observaciones:

- **Turbo es muy preciso**: buena parte de su WER son equivalencias, no errores ("siete y media" vs "7:30",
  "wifi" vs "Wi-Fi"). Errores reales: "tiene" por "tienes", "Recuerda me … el doctor" por "Recuérdame … al doctor",
  "suba 24" por "sube a 24". Entiende "Tessia", "Natalia Lafourcade", "Órale", "Apple Music", "HomePod", "AirPlay".
- **Small no sirve**: falla justo en lo importante ("te si" por "Tessia", "Natalia a la burcade", "ahora le quema la onda" por "Órale…").
- **"Quiñonez" sale "Quiñones" en todos**: en español mexicano suenan igual (seseo); ni el prompt lo corrige.
  No afecta la comprensión del LLM; para nombres escritos (contactos) se debe resolver con búsqueda aproximada.
- **El prompt de vocabulario ayuda poco** (corrigió "Wi-Fi"), sin costo de latencia → se usará.
- **mlx-whisper es ~80 ms más rápido que whisper.cpp** con la misma precisión.
- **⚠️ Latencia fuera de presupuesto (716 ms vs. 150–400 ms)** y casi constante sin importar la duración del audio:
  Whisper procesa siempre una ventana de 30 s. Reducir la ventana en whisper.cpp (`audio_ctx`) lo acelera pero
  destruye la precisión (768 → 401 ms con WER 17.9 %; 512 → 295 ms con WER 92 %). No es viable.

**Estimado E2E con lo medido**: VAD (~300–500 ms) + STT (~720 ms) + LLM primera oración (~580 ms) + TTS (~240 ms)
≈ **1.8–2.0 s**, por encima de la meta de 1.5 s. Opciones a evaluar (ver §12):
transcripción en streaming / generación anticipada en la etapa B, STT en la nube en streaming, o STT en la GPU de la PC.

### 11.5 Etapa B — Conversación completa en LiveKit (2026-11-25)

Script: `experiments/voz/agente_consola.py` (LiveKit Agents 1.9, modo consola, AirPods Pro).
Flujo: Silero VAD (silencio mínimo 0.55 s) + detector de turnos multilingüe → mlx-whisper turbo + prompt de vocabulario
(adaptador propio) → Claude Haiku 5.5 (thinking adaptive, effort low; prompt "empieza con una frase muy corta")
→ ElevenLabs v4 Turbo. Generación anticipada del LLM activada.

| Usuario | Desde la última palabra* | Fin de turno + STT | LLM TTFT | TTS primer audio |
|---|---|---|---|---|
| Dime quién eres | ~2.2 s | 1,275 ms | 449 ms | 242 ms |
| *(hablado muy bajito → alucinación de Whisper)* | ~7.3 s | 6,289 ms | 508 ms | 247 ms |
| Dime un dato curioso *(interrumpida)* | ~2.3 s | 1,307 ms | 459 ms | 245 ms |
| Oye, ¿qué me recomiendas para cenar? | ~2.6 s | 1,351 ms | 482 ms | 195 ms |
| Oye, apaga la luz | ~2.5 s | 1,377 ms | 544 ms | 198 ms |
| Bueno, muchas gracias… | ~2.5 s | 1,408 ms | 537 ms | 238 ms |

\* Tiempo desde que el VAD detecta el fin del habla hasta que Tessia empieza a sonar, más los 0.55 s de silencio mínimo del VAD.

Observaciones:

- **Latencia real ≈ 2.0–2.5 s** desde la última palabra (sin contar el turno con alucinación), por encima de la meta de 1.5 s.
- **Experiencia subjetiva de Emilio: "me sorprendió completamente… casi no tarda nada en responderte"**, mucho más rápido
  que la v1. El streaming de punta a punta y la frase inicial corta ("Claro.", "Con gusto.") hacen que se sienta inmediato.
- **Cuello de botella: fin de turno + STT (~1.3 s)** = ~0.55 s de silencio del VAD + ~0.7 s de Whisper.
  LLM (~0.5 s) y TTS (~0.2 s) son rápidos.
- **Barge-in funciona** ✅: al interrumpirla dejó de hablar y atendió la nueva pregunta (sin el detector adaptativo
  de LiveKit Cloud; basta el VAD).
- **Hablar muy bajito provoca alucinaciones de Whisper** ("Neombúas en la tuco, El Arellí", 6.2 s). Tessia respondió
  bien ("Perdón, no te entendí"). Mitigación futura: descartar transcripciones con baja probabilidad de voz.
- **Proveedor propio dentro de LiveKit** ✅: el adaptador de mlx-whisper funcionó detrás de la interfaz `stt.STT`.
- Sin herramientas, ante "apaga la luz" explica que no tiene control → esperado (herramientas MCP en fase 3).

**Decisión: se mantiene el silencio mínimo del VAD en 0.55 s.** Bajarlo a ~0.3 s ahorraría ~250 ms, pero aumenta el
riesgo de que Tessia interrumpa en pausas a media frase; Emilio prefiere que no lo interrumpa y la latencia actual
se siente bien. Queda como ajuste disponible si en el uso diario se percibe lenta.

Notas técnicas para el agente real:

- El plugin de Anthropic de LiveKit exige el SDK `anthropic` 1.x y no expone `thinking`/`effort`
  (se inyectaron con `extra_kwargs` en una subclase).
- `livekit.plugins.turn_detector` y el modo `console` están marcados como obsoletos en 1.9; el detector de
  interrupciones adaptativo requiere LiveKit Cloud.

## 12. Conclusiones y recomendación

**Veredicto: la arquitectura v2 funciona.** Con streaming de punta a punta, Tessia se siente inmediata
("me sorprendió completamente… casi no tarda nada en responderte"), muy por encima de la v1.

### 12.1 Respuestas a las preguntas del objetivo (§1)

| Pregunta | Respuesta |
|---|---|
| ¿Qué STT local es mejor en Apple Silicon? | **mlx-whisper large-v3-turbo + prompt de vocabulario**: 4.9 % WER, ~716 ms. Small es rápido pero no entiende "Tessia". |
| ¿Haiku responde rápido en streaming? | **Sí**: ~580 ms a la primera oración, respuestas cortas y con tono mexicano. Effort `low`; el thinking adaptativo no agrega latencia. |
| ¿Qué TTS da el mejor balance? | **ElevenLabs v4 Turbo**: calidad de v4, ~240 ms, emociones, $0.04 por 1,000 caracteres. |
| ¿Alguna TTS local se acerca a ElevenLabs? | **No.** Ninguna maneja emociones. Kokoro es la mejor local; Chatterbox no es viable en la Mac. |
| ¿El flujo cabe en 1.5 s? | **No en números (~2.0–2.5 s), sí en experiencia.** El cuello de botella es fin de turno + STT (~1.3 s). |

### 12.2 Criterios de éxito (§7)

| Criterio | Resultado |
|---|---|
| Latencia E2E p50 ≤ 1.5 s | ❌ ~2.0–2.5 s (pero se percibe rápida; ver §12.5 para reducirla) |
| Naturalidad ≥ 4/5 | ✅ v4 Turbo, mejor evaluada |
| Pronunciación de nombre y anglicismos | ✅ con ElevenLabs |
| Emociones distinguibles (≥ 4 de 7) | ✅ solo con ElevenLabs |
| Proveedor propio en LiveKit | ✅ adaptador de mlx-whisper |
| Barge-in (extra) | ✅ |

### 12.3 Stack de voz elegido

| Pieza | Elección | Alternativa / respaldo |
|---|---|---|
| VAD + turnos | Silero (silencio mínimo 0.55 s) + detector de turnos multilingüe de LiveKit | Solo VAD si el detector no corre bien en el servidor |
| STT | Depende del servidor (§12.4): mlx-whisper turbo en Apple Silicon, o **ElevenLabs Scribe Realtime** (nube) | — |
| LLM | **Claude Haiku 5.5**, thinking adaptativo, effort `low`, respuestas de 1–2 oraciones que empiezan con una frase corta | — |
| TTS | **ElevenLabs v4 Turbo** | Kokoro `ef_dora` (local) para modo sin internet |
| Orquestación | LiveKit Agents 1.9 | — |

### 12.4 Cambios respecto al plan original de la v2

1. **La voz principal pasa a la nube.** El plan asumía Chatterbox local; en la Mac es ~4× más lento que tiempo real,
   con ruidos y alucinaciones, y ninguna TTS local maneja emociones. → ElevenLabs v4 Turbo.
2. **La voz deja de ser gratis.** El supuesto "el único gasto es el LLM" ya no aplica: la TTS es ~85 % del costo.
3. **El servidor ya no necesita GPU NVIDIA.** Al salir la TTS de lo local, lo único pesado es el STT.
   - **Recomendado ahora: Raspberry Pi 5** (24/7, barato, bajo consumo) con **STT en la nube (Scribe Realtime)**,
     porque Whisper turbo sería demasiado lento en la Pi. Ventaja extra: el STT en streaming bajaría ~500 ms la latencia.
     Contra: la voz del usuario sale de casa (privacidad controlada, coherente con la v2).
   - **Alternativa futura: Mac mini** (desde $19,999 MXN): STT local y acceso nativo a Apple Music, Recordatorios y Atajos.
4. **Funciones de Apple vía un agente en la Mac.** Música y Atajos solo están disponibles cuando la Mac está prendida;
   lo esencial no debe depender de ella: foco por Home Assistant (Matter), calendario por CalDAV, correo por IMAP,
   y **recordatorios propios de Tessia** con avisos push al iPhone. El iPhone actúa como cliente, no como ejecutor
   (iOS no permite agentes permanentes en segundo plano).

### 12.5 Costos estimados (precios consultados el 2026-11-25)

Fuentes: [ElevenLabs](https://elevenlabs.io/pricing/api), [Anthropic](https://platform.claude.com/docs/en/about-claude/pricing),
[Apple México](https://www.apple.com/mx/shop/buy-mac/mac-mini).

- **ElevenLabs**: todos los planes incluyen API; v4 Turbo consume la mitad de créditos que v4 (rinde el doble de caracteres).
  Free: 20,000 caracteres de v4 Turbo al mes (sin licencia comercial) · **Starter $6/mes: 150,000** (con licencia comercial)
  · Creator $22/mes: 550,000. Pago por uso equivalente: $0.04 por 1,000 caracteres.
  Scribe Realtime (STT): $0.22 por hora de audio, solo mientras se le habla (nunca transmitir 24/7: ~$160/mes).
- **Claude Haiku 5.5**: $0.10 / $0.50 por millón de tokens (entrada/salida); caché del prompt a $0.01 por millón
  → ~$0.0003 por turno con caché.

Supuesto: ~120 caracteres hablados por respuesta.

| Escenario | Voz | LLM (con caché) | STT nube | **Total al mes** |
|---|---|---|---|---|
| Desarrollo | Free | ~$0.10 | incluido en Free | **~$0** |
| Ligero (~20 respuestas/día) | Starter $6 | ~$0.20 | ~$0.10 | **~$6** |
| Medio (~50/día) | $7–22 | ~$0.50 | ~$0.30 | **~$8–23** |
| Familia intenso (~150/día) | Creator $22 | ~$1.50 | ~$1 | **~$25** |

Compra única: Raspberry Pi 5 + SSD (por cotizar) o Mac mini M6 16 GB/256 GB ($19,999 MXN · $899 USD).
Pendiente verificar en el panel de ElevenLabs los caracteres reales por plan (su página es inconsistente entre créditos y caracteres).

### 12.6 Pendientes y siguientes pasos

- **Experimento 02 (corto)**: Scribe Realtime en español con las grabaciones de §11.4 (latencia, WER, nombre). Cabe en las horas gratuitas.
- **Experimento 03**: el agente corriendo en una Raspberry Pi 5 (VAD, detector de turnos, LiveKit, consumo).
- **Filtrar alucinaciones de Whisper** con audio débil (probabilidad de "no voz"); en Scribe, revisar su equivalente.
- **Etiquetas de emoción** de v4 Turbo: probar que el LLM marque la emoción por oración (`[alegre] …`) sin romper el streaming.
- **Migrar lo obsoleto de LiveKit 1.9** en el agente real: modo `console` → `lk agent console`;
  `livekit.plugins.turn_detector` → `livekit.agents.inference.TurnDetector`.
- **Actualizar `CLAUDE.md`** (tabla del stack, costos, hardware) y escribir `docs/03-ARQUITECTURA.md` con estas decisiones.
