# Experimento NN — Título corto (spike)

<!--
Cómo usar esta plantilla:
1. Copia este archivo como docs/experimentos/NN-nombre-corto.md (siguiente número libre).
2. Llena las secciones 1–10 ANTES de escribir código y pásalo a revisión.
3. Las secciones 11–12 se llenan con los resultados. Borra estos comentarios al terminar.
Ejemplo completo: 01-latencia-voz.md
-->

| Campo | Valor |
|---|---|
| Estado | 📝 Planeado |
| Rama | `feature/…` |
| Código | `experiments/<nombre>/` |
| Equipo de pruebas | Máquina, sistema, versión de Python |
| Fecha de inicio | AAAA-MM-DD |

## 1. Objetivo

Qué se quiere validar y por qué importa para Tessia (1–3 líneas).

### Preguntas que debe responder

- ¿…?

### Fuera de alcance

- Lo que explícitamente **no** se prueba aquí (y, si aplica, en qué experimento futuro se haría).

## 2. Hipótesis

Lo que esperamos encontrar, con números cuando se pueda (p. ej., un presupuesto de latencia por etapa).
El experimento la confirma o la corrige.

## 3. Candidatos

| Opción | Tipo (local / nube) | Notas (licencia, costo, requisitos) |
|---|---|---|
| | | |

## 4. Datos de prueba

Entradas fijas que se usan con todos los candidatos (frases, grabaciones, preguntas…) y dónde se guardan.
Si incluyen datos personales, se quedan en local y fuera de git.

## 5. Métricas

| Métrica | Definición |
|---|---|
| | |

Repeticiones por medición y qué se descarta (p. ej., la primera ejecución de calentamiento).
Reportar mediana (p50) y p90.

## 6. Procedimiento

1. Preparar el entorno.
2. …

## 7. Criterios de éxito

| Criterio | Umbral |
|---|---|
| | |

Qué se hace si ningún candidato los cumple.

## 8. Organización del código

```
experiments/<nombre>/
├── README.md
├── .env.example
├── requirements.txt
└── salidas/          # resultados (ignorado en git)
```

## 9. Privacidad y costos

- Qué datos salen de la máquina y hacia qué servicios.
- Costo estimado (llamadas × precio) y límites que aplica el código.

## 10. Qué pasa con el experimento al terminar

- Este documento se queda como registro de la decisión.
- El código de `experiments/<nombre>/` se congela; lo reutilizable se reescribe en `agent/` con tests.

## 11. Resultados

### 11.1 Pieza o etapa (AAAA-MM-DD)

Script, condiciones (equipo, red, micrófono…) y tabla de resultados.

Observaciones:

- …

## 12. Conclusiones y recomendación

- **Veredicto** en una línea.
- Respuestas a las preguntas de §1.
- Criterios de éxito: cuáles se cumplieron (✅/❌).
- Decisión tomada, alternativas descartadas y por qué.
- Impacto en `CLAUDE.md` / arquitectura.
- Pendientes y siguientes experimentos.
