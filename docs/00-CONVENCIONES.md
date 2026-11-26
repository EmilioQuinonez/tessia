# 00 — Convenciones de documentación

| Campo | Valor |
|---|---|
| Estado | 📝 Borrador |
| Última actualización | 2026-11-26 |
| Relacionados | [`CLAUDE.md`](../CLAUDE.md) · [plantilla de experimento](experimentos/_plantilla.md) |

Reglas para que todos los documentos de Tessia se vean y se lean igual. Son pocas a propósito:
si una regla estorba más de lo que ayuda, se cambia aquí.

## 1. Qué documentos hay

| Documento | Para qué sirve |
|---|---|
| `00-CONVENCIONES.md` | Este archivo: cómo se escriben los docs |
| `01-VISION.md` | Qué es Tessia, para quién y qué problema resuelve |
| `02-SRS.md` | Requisitos funcionales y no funcionales |
| `03-ARQUITECTURA.md` | Componentes, flujos y decisiones técnicas |
| `04-PLAN-CALIDAD.md` | Cómo se prueba y se mide la calidad |
| `05-SETUP.md` | Cómo instalar y correr el proyecto |
| `06-ROADMAP.md` | Fases y estado |
| `experimentos/NN-nombre.md` | Un experimento (spike): plan, método, resultados y conclusiones |

Además: `CLAUDE.md` (raíz) es el **resumen vivo** del proyecto: visión, stack, estado actual y convenciones.

## 2. Nombres de archivo

- **Documentos principales**: `NN-NOMBRE.md` en mayúsculas, con número de dos dígitos (`03-ARQUITECTURA.md`).
- **Experimentos**: `docs/experimentos/NN-nombre-corto.md` en minúsculas y con guiones (`01-latencia-voz.md`).
  El número es consecutivo y no se reutiliza, aunque un experimento se cancele.
- Archivos auxiliares (plantillas) empiezan con `_` (`_plantilla.md`).

## 3. Encabezado de cada documento

Todo documento empieza con su título y una tabla de metadatos:

```markdown
# NN — Título

| Campo | Valor |
|---|---|
| Estado | 📝 Borrador |
| Última actualización | AAAA-MM-DD |
| Relacionados | enlaces a otros docs, PR o rama |
```

Estados posibles:

| Estado | Significado |
|---|---|
| 📝 Borrador / Planeado | En escritura o aún no empieza |
| 🔬 En curso | Se está trabajando (experimentos) |
| ✅ Vigente / Completado | Refleja la realidad actual |
| 🗄️ Obsoleto | Ya no aplica; indicar qué lo reemplaza |

Los experimentos agregan los campos `Rama`, `Código` y `Equipo de pruebas` (ver la plantilla).

## 4. Cómo se escribe

- **Español**, frases cortas, voz activa. Un término técnico se explica la primera vez que aparece.
- **Fechas absolutas** en formato `AAAA-MM-DD`. Nunca "ayer", "la semana pasada" o "hace poco".
- **Datos externos con fuente y fecha de consulta** (precios, límites, versiones):
  "ElevenLabs v4 Turbo: $0.04 por 1,000 caracteres ([fuente](https://elevenlabs.io/pricing/api), consultado 2026-11-25)".
- **Números con unidad** (`716 ms`, `$6 USD/mes`, `16 GB`). Latencias como mediana (p50) y p90 cuando haya varias mediciones.
- **Tablas para comparar** opciones; listas para pasos; párrafos solo para explicar.
- **Cada decisión con su porqué y las alternativas descartadas.** Un "elegimos X" sin razón no es una decisión documentada.
- **Separar hechos de opiniones**: lo medido va en Resultados; la interpretación, en Observaciones o Conclusiones.
- **Diagramas en Mermaid** dentro del Markdown (GitHub los muestra) o en ASCII si son simples.
- **Bloques de código con lenguaje** (` ```python `, ` ```bash `).
- **El repo es público**: nada de API keys, correos, contraseñas, rutas con datos personales ni grabaciones.

## 5. Cuándo se actualiza cada cosa

| Qué | Cuándo |
|---|---|
| Doc del componente que cambia | En el **mismo PR** que el código (documentation-first: idealmente antes) |
| `CLAUDE.md` | Al cerrar cada tarea grande (experimento, fase, decisión de arquitectura) |
| Campo "Última actualización" | Cada vez que cambia el contenido del documento |
| `06-ROADMAP.md` | Al empezar o terminar una fase |

## 6. Experimentos

1. **Primero el documento**, a partir de [`experimentos/_plantilla.md`](experimentos/_plantilla.md):
   objetivo, candidatos, método, métricas y criterios de éxito. Se revisa antes de escribir código.
2. **Código en `experiments/<nombre>/`** con su README, `.env.example` y `requirements`.
   Es desechable: no se importa desde `agent/` ni se le da mantenimiento.
3. **Gasto controlado**: los scripts que usan APIs de pago muestran llamadas/caracteres y costo estimado, y piden confirmación.
4. **Resultados y conclusiones en el mismo documento**, con la fecha de cada medición.
5. **Al terminar**: estado ✅, código congelado, lo reutilizable se reescribe bien en `agent/` con tests,
   y se actualiza `CLAUDE.md`. Salidas, audios y modelos nunca se suben.

## 7. Variables de entorno (propuesta)

- Cada componente tiene **su propio** `.env.example` junto a su código (`agent/.env.example`, `dashboard/.env.example`,
  `experiments/<nombre>/.env.example`), con **solo** las variables que usa. Así cada pieza tiene únicamente las llaves que necesita.
- `infra/docker-compose.yml` asigna a cada servicio su archivo con `env_file:`.
- Variables en `UPPER_SNAKE_CASE`, sin comillas ni espacios alrededor del `=`. El `.env` real nunca se sube.
