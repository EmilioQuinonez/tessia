"""Benchmark de latencia del LLM (Claude Haiku 5.5) en streaming.

Mide, por llamada:
- TTFT: tiempo hasta el primer token de texto.
- Primera oración: tiempo hasta tener una oración completa (lo que la TTS necesita para empezar).
- Total: tiempo hasta terminar la respuesta.

Compara dos configuraciones:
- "sin_thinking": razonamiento interno apagado, effort low.
- "thinking_low": razonamiento adaptativo (por defecto en Haiku 5.5), effort low.

Uso (desde experiments/voz/):
    .venv/bin/python llm_bench.py          # pide confirmación antes de gastar
    .venv/bin/python llm_bench.py --si     # sin confirmación
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import anthropic
from dotenv import load_dotenv

# --- Restricción del experimento: único modelo permitido -----------------------
MODELO = "claude-haiku-5-5"
PRECIO_ENTRADA_USD_POR_MTOK = 0.10
PRECIO_SALIDA_USD_POR_MTOK = 0.50

MAX_TOKENS = 400  # respuestas habladas cortas; incluye el razonamiento si está activo
REPETICIONES = 10

CONFIGURACIONES: dict[str, dict] = {
    "sin_thinking": {"thinking": {"type": "disabled"}, "output_config": {"effort": "low"}},
    "thinking_low": {"thinking": {"type": "adaptive"}, "output_config": {"effort": "low"}},
}

SISTEMA = (
    "Eres Tessia, una asistente de voz de casa. Hablas español mexicano, con calidez y naturalidad. "
    "Tus respuestas se convierten en voz: responde en una o dos oraciones cortas, "
    "sin listas, sin markdown, sin emojis y sin abreviaturas."
)

PREGUNTAS = [
    "¿Qué me recomiendas cenar hoy si tengo pollo y arroz?",
    "Explícame en pocas palabras qué es un agujero negro.",
    "¿Cuál es la capital de Australia y cuántas horas de diferencia hay con México?",
    "Estoy cansado, cuéntame algo que me anime.",
    "¿Cómo le digo a mi jefe que necesito el viernes libre sin que suene mal?",
]

# Fin de oración: . ! ? … seguido de espacio (o fin del texto al cerrar el stream)
FIN_ORACION = re.compile(r"[.!?…](\s|$)")

DIR_SALIDA = Path(__file__).parent / "salidas" / "llm"


@dataclass
class Medicion:
    config: str
    pregunta_id: int
    repeticion: int
    ttft_ms: float | None
    primera_oracion_ms: float | None
    total_ms: float
    tokens_entrada: int
    tokens_salida: int
    stop_reason: str | None
    respuesta: str


def medir(cliente: anthropic.Anthropic, config: str, pregunta: str) -> tuple[float | None, float | None, float, anthropic.types.Message]:
    """Hace una llamada en streaming y devuelve (ttft, primera_oracion, total, mensaje_final)."""
    ttft = primera = None
    texto = ""
    inicio = time.perf_counter()
    with cliente.messages.stream(
        model=MODELO,
        max_tokens=MAX_TOKENS,
        system=SISTEMA,
        messages=[{"role": "user", "content": pregunta}],
        **CONFIGURACIONES[config],
    ) as stream:
        for fragmento in stream.text_stream:
            ahora = time.perf_counter()
            if ttft is None and fragmento:
                ttft = ahora - inicio
            texto += fragmento
            if primera is None and FIN_ORACION.search(texto):
                primera = ahora - inicio
        mensaje = stream.get_final_message()
    total = time.perf_counter() - inicio
    if primera is None and texto:
        primera = total  # respuesta de una sola oración sin espacio final
    return ttft, primera, total, mensaje


def percentil(valores: list[float], p: float) -> float:
    ordenados = sorted(valores)
    k = (len(ordenados) - 1) * p
    i = int(k)
    j = min(i + 1, len(ordenados) - 1)
    return ordenados[i] + (ordenados[j] - ordenados[i]) * (k - i)


def resumir(mediciones: list[Medicion]) -> dict:
    resumen = {}
    for config in CONFIGURACIONES:
        ms = [m for m in mediciones if m.config == config]
        fila = {"llamadas": len(ms)}
        for campo in ("ttft_ms", "primera_oracion_ms", "total_ms"):
            vals = [getattr(m, campo) for m in ms if getattr(m, campo) is not None]
            fila[campo] = {
                "p50": round(statistics.median(vals)) if vals else None,
                "p90": round(percentil(vals, 0.9)) if vals else None,
            }
        fila["tokens_salida_prom"] = round(statistics.mean(m.tokens_salida for m in ms)) if ms else 0
        resumen[config] = fila
    return resumen


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--si", action="store_true", help="no pedir confirmación")
    args = parser.parse_args()

    load_dotenv(Path(__file__).parent / ".env")

    llamadas = len(CONFIGURACIONES) * (1 + len(PREGUNTAS) * REPETICIONES)  # +1 calentamiento por config
    peor_caso = llamadas * (300 * PRECIO_ENTRADA_USD_POR_MTOK + MAX_TOKENS * PRECIO_SALIDA_USD_POR_MTOK) / 1e6
    print(f"Modelo: {MODELO}")
    print(f"Llamadas: {llamadas} ({len(CONFIGURACIONES)} configs × {len(PREGUNTAS)} preguntas × {REPETICIONES} reps + calentamiento)")
    print(f"Costo máximo estimado: ${peor_caso:.3f} USD (si todas las respuestas usaran {MAX_TOKENS} tokens)")
    if not args.si and input("¿Continuar? [s/N] ").strip().lower() not in ("s", "si", "sí"):
        print("Cancelado.")
        return 1

    cliente = anthropic.Anthropic()
    mediciones: list[Medicion] = []
    costo = 0.0

    try:
        # Calentamiento: abre la conexión TLS; no se cuenta.
        for config in CONFIGURACIONES:
            medir(cliente, config, "Hola")

        for rep in range(REPETICIONES):
            for pid, pregunta in enumerate(PREGUNTAS):
                for config in CONFIGURACIONES:  # intercalado para no sesgar por hora/red
                    ttft, primera, total, msg = medir(cliente, config, pregunta)
                    if msg.stop_reason == "refusal":
                        print(f"  ⚠️ rechazo en pregunta {pid} ({config})")
                    texto = "".join(b.text for b in msg.content if b.type == "text")
                    m = Medicion(
                        config=config,
                        pregunta_id=pid,
                        repeticion=rep,
                        ttft_ms=round(ttft * 1000) if ttft is not None else None,
                        primera_oracion_ms=round(primera * 1000) if primera is not None else None,
                        total_ms=round(total * 1000),
                        tokens_entrada=msg.usage.input_tokens,
                        tokens_salida=msg.usage.output_tokens,
                        stop_reason=msg.stop_reason,
                        respuesta=texto,
                    )
                    mediciones.append(m)
                    costo += (m.tokens_entrada * PRECIO_ENTRADA_USD_POR_MTOK + m.tokens_salida * PRECIO_SALIDA_USD_POR_MTOK) / 1e6
                    print(f"rep {rep + 1:2}/{REPETICIONES} P{pid} {config:13} ttft={m.ttft_ms}ms  1a_oración={m.primera_oracion_ms}ms  total={m.total_ms}ms")
    except anthropic.AuthenticationError:
        print("❌ API key inválida. Revisa ANTHROPIC_API_KEY en .env")
        return 2
    except anthropic.RateLimitError:
        print("❌ Límite de uso alcanzado; se guardan las mediciones hechas hasta ahora.")
    except anthropic.APIStatusError as e:
        print(f"❌ Error de la API ({e.status_code}): {e.message}")
        if not mediciones:
            return 2
    except anthropic.APIConnectionError:
        print("❌ Sin conexión con la API.")
        if not mediciones:
            return 2

    DIR_SALIDA.mkdir(parents=True, exist_ok=True)
    marca = time.strftime("%Y%m%d-%H%M%S")
    with open(DIR_SALIDA / f"mediciones-{marca}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(asdict(mediciones[0]).keys()))
        w.writeheader()
        w.writerows(asdict(m) for m in mediciones)
    resumen = resumir(mediciones)
    (DIR_SALIDA / f"resumen-{marca}.json").write_text(json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n=== Resumen (ms) ===")
    for config, fila in resumen.items():
        print(
            f"{config:13} TTFT p50={fila['ttft_ms']['p50']} p90={fila['ttft_ms']['p90']} | "
            f"1a oración p50={fila['primera_oracion_ms']['p50']} p90={fila['primera_oracion_ms']['p90']} | "
            f"total p50={fila['total_ms']['p50']} | tokens salida prom={fila['tokens_salida_prom']}"
        )
    print(f"\nCosto real aproximado: ${costo:.4f} USD")
    print(f"Archivos en {DIR_SALIDA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
