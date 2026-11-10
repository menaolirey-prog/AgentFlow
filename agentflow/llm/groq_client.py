"""Adaptador de Groq. Conserva los parámetros del prototipo que ya funcionaron."""
import groq
from groq import Groq

from agentflow.config import MODELO, Limites
from agentflow.llm.base import ErrorLLM, LlamadaModelo, RespuestaLLM


class GroqLLM:
    def __init__(self, api_key: str | None = None, modelo: str = MODELO,
                 limites: Limites = Limites(), cliente=None):
        # Sin reintentos automáticos: los reintentos los decide el orquestador, con límites.
        self._cliente = cliente or Groq(api_key=api_key, max_retries=0, timeout=limites.timeout_llm_s)
        self._modelo = modelo
        self._max_tokens = limites.max_tokens_respuesta

    def chat(self, mensajes: list[dict], herramientas: list[dict], tool_choice: str) -> RespuestaLLM:
        params = dict(model=self._modelo, messages=mensajes, tool_choice=tool_choice,
                      reasoning_effort="low", max_completion_tokens=self._max_tokens)
        if tool_choice != "none":  # igual que el prototipo: la respuesta final se pide sin herramientas
            params.update(tools=herramientas, parallel_tool_calls=False)
        try:
            r = self._cliente.chat.completions.create(**params)
        except groq.RateLimitError:
            raise ErrorLLM("limite_tasa") from None
        except groq.APIConnectionError:  # incluye timeouts
            raise ErrorLLM("conexion") from None
        except groq.APIStatusError as error:
            raise ErrorLLM("estado_http", str(error.status_code)) from None
        try:
            eleccion = r.choices[0]
            mensaje = eleccion.message
            llamadas = [LlamadaModelo(c.id, c.function.name, c.function.arguments)
                        for c in (mensaje.tool_calls or [])]
            uso = r.usage
            return RespuestaLLM(mensaje.content, llamadas, eleccion.finish_reason or "stop",
                                getattr(uso, "prompt_tokens", 0) or 0,
                                getattr(uso, "completion_tokens", 0) or 0)
        except (AttributeError, IndexError, TypeError):
            raise ErrorLLM("respuesta_invalida") from None
