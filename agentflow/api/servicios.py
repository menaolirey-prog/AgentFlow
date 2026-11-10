"""Contenedor de dependencias de la API. Los routers reciben `Servicios`; las pruebas lo sustituyen por dobles."""
import os
from dataclasses import dataclass
from typing import Any, Callable

from fastapi import Request

from agentflow.agent.orchestrator import Agente
from agentflow.api.errors import ServicioNoDisponible
from agentflow.db.repositories.ejecuciones import RegistroEjecuciones
from agentflow.db.repositories.historial import HistorialPostgres
from agentflow.db.repositories.ventas import RepositorioVentas
from agentflow.llm.groq_client import GroqLLM
from agentflow.tools.registry import RegistroHerramientas


@dataclass
class Servicios:
    historial: Any                      # HistorialPostgres o doble
    ejecuciones: Any                    # RegistroEjecuciones o doble
    ventas: Any                         # RepositorioVentas o doble
    crear_agente: Callable[[], Agente]  # perezoso: el cliente de Groq solo se crea al chatear


def servicios_por_defecto() -> Servicios:
    historial, ejecuciones, ventas = HistorialPostgres(), RegistroEjecuciones(), RepositorioVentas()

    def crear_agente() -> Agente:
        clave = os.getenv("GROQ_API_KEY")
        if not clave:
            raise ServicioNoDisponible("llm_no_configurado", "El servicio de lenguaje no está configurado.")
        return Agente(GroqLLM(clave), RegistroHerramientas(ventas), ejecuciones=ejecuciones)

    return Servicios(historial, ejecuciones, ventas, crear_agente)


def obtener_servicios(request: Request) -> Servicios:
    return request.app.state.servicios
