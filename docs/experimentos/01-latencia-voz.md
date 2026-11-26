# Experimento 01 — Latencia y naturalidad de la voz (spike)

| Campo | Valor |
|---|---|
| Estado | 📝 Planeado |
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
- Anthropic: Haiku con respuestas cortas; costo estimado de centavos de dólar para todo el experimento.

## 10. Qué pasa con el experimento al terminar

- **Este documento se queda para siempre**: registra por qué se eligió cada pieza de voz.
- **El código de `experiments/voz/` se congela**: no se mantiene ni se importa desde `agent/`.
  Su README indicará que es histórico.
- Lo que sirva (p. ej. un adaptador de STT/TTS) **se reescribe bien en `agent/`**, con tests, en su propia rama `feature/…`.
- Si más adelante el código estorba, se borra; queda en el historial de git (y opcionalmente un tag `spike-voz`).

## 11. Resultados

_Pendiente._

## 12. Conclusiones y recomendación

_Pendiente._
