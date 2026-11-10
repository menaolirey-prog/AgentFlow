"""Valida el dataset de casos y el arnés de evaluación con un LLM simulado (sin red)."""
import json

from agentflow.evals import evaluar_seleccion
from agentflow.llm.base import LlamadaModelo, RespuestaLLM
from agentflow.tools.registry import RegistroHerramientas
from tests.evals.casos_seleccion import CASOS
from tests.fakes import HOY, RepoFalso


class LLMOraculo:
    """Responde siempre con la llamada esperada del caso: comprueba que el dataset es válido."""

    def chat(self, mensajes, herramientas, tool_choice):
        caso = next(c for c in CASOS if c.pregunta == mensajes[-1]["content"])
        return RespuestaLLM(llamadas=[LlamadaModelo("1", caso.herramienta, json.dumps(caso.argumentos))])


class LLMTorpe:
    def chat(self, mensajes, herramientas, tool_choice):
        return RespuestaLLM(llamadas=[LlamadaModelo("1", "ventas_totales", '{"periodo": "este_mes"}')])


def test_dataset_tiene_al_menos_12_casos_y_cubre_las_5_herramientas():
    assert len(CASOS) >= 12
    assert {c.herramienta for c in CASOS} == {"ventas_totales", "ventas_por_producto",
                                              "comparar_periodos", "productos_en_caida", "reporte_ventas"}


def test_todos_los_casos_esperados_son_validos_para_el_registro():
    informe = evaluar_seleccion(LLMOraculo(), RegistroHerramientas(RepoFalso()), CASOS, HOY)
    assert informe.herramienta_correcta == informe.argumentos_correctos == informe.total, informe.fallos


def test_el_arnes_detecta_selecciones_incorrectas():
    informe = evaluar_seleccion(LLMTorpe(), RegistroHerramientas(RepoFalso()), CASOS, HOY)
    assert 0 < informe.herramienta_correcta < informe.total
    assert informe.argumentos_correctos < informe.total and informe.fallos
