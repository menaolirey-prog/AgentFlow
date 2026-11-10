from types import SimpleNamespace as NS
from unittest.mock import MagicMock

import groq
import httpx
import pytest

from agentflow.llm.base import ErrorLLM
from agentflow.llm.groq_client import GroqLLM
from agentflow.observability.logging import registrar


def _respuesta(contenido=None, llamadas=None, finish="stop", uso=(10, 5)):
    return NS(choices=[NS(message=NS(content=contenido, tool_calls=llamadas), finish_reason=finish)],
              usage=NS(prompt_tokens=uso[0], completion_tokens=uso[1]))


def _http(codigo):
    return httpx.Response(codigo, request=httpx.Request("POST", "http://x"))


def test_mapea_llamadas_y_tokens():
    cliente = MagicMock()
    tc = NS(id="abc", function=NS(name="ventas_totales", arguments='{"periodo": "este_mes"}'))
    cliente.chat.completions.create.return_value = _respuesta(llamadas=[tc], finish="tool_calls")
    r = GroqLLM(cliente=cliente).chat([{"role": "user", "content": "x"}], [{"t": 1}], "auto")
    assert (r.llamadas[0].id, r.llamadas[0].nombre) == ("abc", "ventas_totales")
    assert (r.tokens_entrada, r.tokens_salida, r.finish_reason) == (10, 5, "tool_calls")
    kw = cliente.chat.completions.create.call_args.kwargs
    assert kw["tools"] == [{"t": 1}] and kw["parallel_tool_calls"] is False and kw["reasoning_effort"] == "low"


def test_tool_choice_none_no_envia_herramientas():
    cliente = MagicMock()
    cliente.chat.completions.create.return_value = _respuesta("hola")
    r = GroqLLM(cliente=cliente).chat([], [{"t": 1}], "none")
    kw = cliente.chat.completions.create.call_args.kwargs
    assert "tools" not in kw and kw["tool_choice"] == "none" and r.contenido == "hola"


def test_uso_ausente_cuenta_cero_tokens():
    cliente = MagicMock()
    cliente.chat.completions.create.return_value = NS(
        choices=[NS(message=NS(content="ok", tool_calls=None), finish_reason="stop")], usage=None)
    r = GroqLLM(cliente=cliente).chat([], [], "auto")
    assert (r.tokens_entrada, r.tokens_salida) == (0, 0)


@pytest.mark.parametrize("excepcion,codigo", [
    (groq.RateLimitError("x", response=_http(429), body=None), "limite_tasa"),
    (groq.APIConnectionError(request=httpx.Request("POST", "http://x")), "conexion"),
    (groq.APITimeoutError(request=httpx.Request("POST", "http://x")), "conexion"),
    (groq.InternalServerError("x", response=_http(500), body=None), "estado_http"),
])
def test_errores_del_sdk_se_traducen(excepcion, codigo):
    cliente = MagicMock()
    cliente.chat.completions.create.side_effect = excepcion
    with pytest.raises(ErrorLLM) as e:
        GroqLLM(cliente=cliente).chat([], [], "auto")
    assert e.value.codigo == codigo


def test_respuesta_malformada_es_error_controlado():
    cliente = MagicMock()
    cliente.chat.completions.create.return_value = NS(choices=[])
    with pytest.raises(ErrorLLM) as e:
        GroqLLM(cliente=cliente).chat([], [], "auto")
    assert e.value.codigo == "respuesta_invalida"


def test_registrar_enmascara_campos_sensibles(caplog):
    with caplog.at_level("INFO", logger="agentflow"):
        registrar("prueba", api_key="gsk_secreta", DB_PASSWORD="x", tokens_entrada=3)
    campos = caplog.records[0].campos
    assert campos == {"api_key": "***", "DB_PASSWORD": "***", "tokens_entrada": 3}
