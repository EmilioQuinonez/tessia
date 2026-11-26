"""Frases de prueba del experimento 01 (fuente única; ver docs/experimentos/01-latencia-voz.md §4)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Frase:
    id: str
    categoria: str
    texto: str
    emocion: str | None = None  # solo para las frases E1–E7


FRASES: list[Frase] = [
    Frase("C1", "corta", "Listo, apagué la luz de la sala."),
    Frase("C2", "corta_hora", "Tu alarma quedó a las 7:30 de la mañana."),
    Frase("C3", "corta", "Claro, ¿algo más?"),
    Frase("N1", "nombre", "Buenos días, Emilio Santiago López Quiñonez."),
    Frase("N2", "nombre", "Emilio, tienes un mensaje nuevo de tu mamá."),
    Frase("F1", "fecha_numero", "El martes 14 de enero tienes cita a las 4:45 de la tarde."),
    Frase("F2", "numero", "La temperatura es de 23 grados, con 40 % de probabilidad de lluvia."),
    Frase("A1", "anglicismos", "Pongo tu playlist en Apple Music y la mando al HomePod por AirPlay."),
    Frase("A2", "anglicismos", "Se desconectó el Wi-Fi del foco del cuarto."),
    Frase("M1", "modismos", "¡Órale, qué buena onda! Ahorita te lo checo."),
    Frase("M2", "modismos", "No manches, ya casi es la hora de la junta."),
    Frase(
        "L1",
        "mediana",
        "Hoy en la mañana va a estar fresco, alrededor de 15 grados, y en la tarde sube a 24. "
        "Tienes dos pendientes en tu agenda: la llamada con el equipo a las 11 y recoger el paquete antes de las 6.",
    ),
    Frase("E1", "emocion", "¿En serio? ¡No puedo creer que ya sea viernes!", "sorpresa"),
    Frase("E2", "emocion", "¡Qué gusto, Emilio! Me encanta que te haya ido tan bien.", "alegria"),
    Frase("E3", "emocion", "Lo siento mucho… sé que era importante para ti.", "tristeza"),
    Frase("E4", "emocion", "Ay, otra vez se te olvidó sacar la basura, ¿verdad?", "decepcion"),
    Frase("E5", "emocion", "¡Ya te dije tres veces que la puerta está abierta!", "enojo"),
    Frase("E6", "emocion", "Tranquilo, todo está bajo control. Respira.", "calma"),
    Frase("E7", "emocion", "¡Vámonos! Hoy va a ser un gran día.", "entusiasmo"),
]
