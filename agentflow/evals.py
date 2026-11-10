"""Evaluación de selección de herramientas: ¿elige la herramienta y los argumentos esperados?

Se ejecuta con cualquier ClienteLLM. En pruebas unitarias se usa un LLM simulado; contra Groq real
solo con autorización explícita (consume cuota).
"""
from dataclasses import dataclass, field
from datetime import date

from agentflow.agent.prompts import construir_prompt_sistema
from agentflow.tools.registry import RegistroHerramientas


@dataclass(frozen=True)
class Caso:
    pregunta: str
    herramienta: str
    argumentos: dict  # ya normalizados (valores por defecto incluidos)


@dataclass
class InformeSeleccion:
    total: int = 0
    herramienta_correcta: int = 0
    argumentos_correctos: int = 0
    fallos: list[str] = field(default_factory=list)


def evaluar_seleccion(llm, registro: RegistroHerramientas, casos: list[Caso], hoy: date) -> InformeSeleccion:
    informe = InformeSeleccion(total=len(casos))
    for caso in casos:
        mensajes = [{"role": "system", "content": construir_prompt_sistema(hoy)},
                    {"role": "user", "content": caso.pregunta}]
        r = llm.chat(mensajes, registro.esquemas(), "auto")
        if not r.llamadas or r.llamadas[0].nombre != caso.herramienta:
            elegida = r.llamadas[0].nombre if r.llamadas else "ninguna"
            informe.fallos.append(f"{caso.pregunta!r}: esperaba {caso.herramienta}, eligió {elegida}")
            continue
        informe.herramienta_correcta += 1
        res = registro.ejecutar(r.llamadas[0].nombre, r.llamadas[0].argumentos, hoy)
        if res.ok and res.argumentos == caso.argumentos:
            informe.argumentos_correctos += 1
        else:
            informe.fallos.append(f"{caso.pregunta!r}: argumentos {res.argumentos or res.datos} != {caso.argumentos}")
    return informe
