"""CLI interactiva: python -m agentflow"""
import json
import os
import sys

from dotenv import load_dotenv

from agentflow.agent.orchestrator import Agente, Conversacion
from agentflow.config import MODELO
from agentflow.db.repositories.ventas import RepositorioVentas
from agentflow.llm.groq_client import GroqLLM
from agentflow.observability.logging import configurar_archivo
from agentflow.tools.registry import RegistroHerramientas

AYUDA = ("Comandos: /herramientas (qué usé en la última respuesta), /nueva (reiniciar conversación), "
         "/ayuda, /salir")


def construir_agente(api_key: str) -> Agente:
    return Agente(GroqLLM(api_key), RegistroHerramientas(RepositorioVentas()))


def mostrar_herramientas(conversacion: Conversacion) -> None:
    r = conversacion.ultimo_resultado
    if r is None:
        print("Aún no hay consultas.")
    elif not r.herramientas:
        print("La última respuesta no usó herramientas.")
    for h in r.herramientas if r else []:
        estado = "ok" if h.ok else f"error ({h.codigo_error})"
        print(f"- {h.nombre} {json.dumps(h.argumentos, ensure_ascii=False)} -> {estado}, {h.duracion_ms} ms")


def main() -> int:
    for flujo in (sys.stdout, sys.stderr):  # consola Windows: nunca fallar por un carácter
        flujo.reconfigure(errors="replace")
    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("Falta GROQ_API_KEY en .env")
        return 1
    configurar_archivo("logs/agentflow.jsonl")
    agente, conversacion = construir_agente(api_key), Conversacion()
    print(f"AgentFlow ({MODELO}). Datos ficticios de demostración. {AYUDA}")
    while True:
        try:
            pregunta = input("\nTú> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not pregunta:
            continue
        if pregunta == "/salir":
            return 0
        if pregunta == "/ayuda":
            print(AYUDA)
        elif pregunta == "/nueva":
            conversacion = Conversacion()
            print("Conversación reiniciada.")
        elif pregunta == "/herramientas":
            mostrar_herramientas(conversacion)
        else:
            r = agente.responder(pregunta, conversacion)
            print(f"\n{r.respuesta}")
            print(f"[{r.estado} · {r.origen} · {len(r.herramientas)} herramientas · "
                  f"{r.tokens_entrada + r.tokens_salida} tokens · {r.duracion_ms} ms]")


if __name__ == "__main__":
    sys.exit(main())
