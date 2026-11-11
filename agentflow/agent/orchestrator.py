"""Bucle del agente. El modelo propone; el código ejecuta, limita, verifica y decide cuándo parar."""
import time
from dataclasses import dataclass
from datetime import date, datetime
from typing import Callable

from agentflow.agent.conversacion import Conversacion  # noqa: F401  (reexportada: API estable)
from agentflow.agent.prompts import construir_prompt_sistema
from agentflow.agent.render import plantilla_respaldo
from agentflow.agent.verifier import verificar_respuesta
from agentflow.config import ZONA_LIMA, Limites
from agentflow.llm.base import ClienteLLM, ErrorLLM
from agentflow.observability.logging import registrar
from agentflow.tools.registry import RegistroHerramientas, ResultadoHerramienta

AVISOS = {
    "limite_iteraciones": "Alcancé el máximo de pasos permitido para esta consulta.",
    "limite_herramientas": "Alcancé el máximo de consultas a datos permitido para esta solicitud.",
    "limite_tokens": "Alcancé el presupuesto de procesamiento de esta solicitud.",
    "tiempo_agotado": "La consulta tardó más del tiempo permitido.",
    "respuesta_truncada": "La respuesta del modelo quedó incompleta.",
    "respuesta_vacia": "El modelo no produjo una respuesta.",
    "cifras_no_verificadas": "No pude verificar las cifras de la redacción del modelo; te muestro los datos directamente.",
}
MENSAJES_ERROR_LLM = {
    "limite_tasa": "Se alcanzó el límite de uso del servicio de lenguaje. Intenta de nuevo en unos minutos.",
    "conexion": "No pude conectar con el servicio de lenguaje. Intenta de nuevo.",
}
MENSAJE_ERROR_GENERICO = "El servicio de lenguaje no está disponible en este momento."
_CORTES = {"limite_iteraciones", "limite_herramientas", "limite_tokens", "tiempo_agotado",
           "respuesta_truncada", "respuesta_vacia"}


@dataclass
class ResultadoAgente:
    respuesta: str
    estado: str           # ok | degradado | limite | error
    motivo: str | None
    origen: str           # modelo | plantilla | mensaje_error
    herramientas: list[ResultadoHerramienta]
    tokens_entrada: int
    tokens_salida: int
    llamadas_llm: int
    duracion_ms: int
    ejecucion_id: str | None = None


class Agente:
    def __init__(self, llm: ClienteLLM, registro: RegistroHerramientas, limites: Limites = Limites(),
                 hoy: Callable[[], date] = lambda: datetime.now(ZONA_LIMA).date(),
                 reloj: Callable[[], float] = time.monotonic, ejecuciones=None):
        self._llm, self._registro, self._l, self._hoy, self._reloj = llm, registro, limites, hoy, reloj
        self._ejecuciones = ejecuciones  # RegistroEjecuciones o None (sin persistencia)

    def responder(self, pregunta: str, conversacion: Conversacion) -> ResultadoAgente:
        """Una solicitud = una ejecución: se abre 'en_curso' y se cierra con el resultado.
        Si el proceso muere a mitad, la fila queda 'en_curso' (desenlace desconocido), nunca 'ok'."""
        ejecucion_id = self._abrir_ejecucion(conversacion, len(pregunta))
        resultado = self._responder(pregunta, conversacion)
        resultado.ejecucion_id = ejecucion_id
        self._cerrar_ejecucion(ejecucion_id, resultado)
        registrar("respuesta", ejecucion_id=ejecucion_id, estado=resultado.estado, motivo=resultado.motivo,
                  origen=resultado.origen, herramientas=len(resultado.herramientas),
                  tokens_entrada=resultado.tokens_entrada, tokens_salida=resultado.tokens_salida,
                  llamadas_llm=resultado.llamadas_llm, duracion_ms=resultado.duracion_ms)
        return resultado

    def _abrir_ejecucion(self, conversacion: Conversacion, pregunta_chars: int) -> str | None:
        if self._ejecuciones is None:
            return None
        try:
            return self._ejecuciones.iniciar(conversacion.id, pregunta_chars)
        except Exception as error:  # la observabilidad nunca debe impedir responder
            registrar("error_ejecuciones", fase="iniciar", tipo=type(error).__name__)
            return None

    def _cerrar_ejecucion(self, ejecucion_id: str | None, r: ResultadoAgente) -> None:
        if self._ejecuciones is None or ejecucion_id is None:
            return
        herramientas = [{"nombre": h.nombre, "argumentos": h.argumentos, "ok": h.ok,
                         "codigo_error": h.codigo_error, "duracion_ms": h.duracion_ms} for h in r.herramientas]
        try:
            self._ejecuciones.finalizar(ejecucion_id, r.estado, r.motivo, r.origen, r.tokens_entrada,
                                        r.tokens_salida, r.llamadas_llm, r.duracion_ms, herramientas)
        except Exception as error:
            registrar("error_ejecuciones", fase="finalizar", tipo=type(error).__name__)

    def _responder(self, pregunta: str, conversacion: Conversacion) -> ResultadoAgente:
        t0, hoy = self._reloj(), self._hoy()
        l = self._l
        mensajes = [{"role": "system", "content": construir_prompt_sistema(hoy)},
                    *conversacion.recientes(l.max_historial_mensajes),
                    {"role": "user", "content": pregunta}]
        ejecutadas: list[ResultadoHerramienta] = []
        t_in = t_out = llamadas_llm = 0
        motivo: str | None = None
        texto: str | None = None
        registrar("solicitud", pregunta_chars=len(pregunta))

        try:
            for i in range(l.max_iteraciones):
                if self._reloj() - t0 > l.timeout_total_s:
                    motivo = "tiempo_agotado"; break
                if t_in + t_out >= l.max_tokens_total:
                    motivo = "limite_tokens"; break
                ultima = i == l.max_iteraciones - 1  # en la última vuelta se obliga a redactar
                t_llm = self._reloj()
                r = self._llm.chat(mensajes, self._registro.esquemas(), "none" if ultima else "auto")
                llamadas_llm += 1
                t_in, t_out = t_in + r.tokens_entrada, t_out + r.tokens_salida
                registrar("llm_llamada", iteracion=i + 1, finish_reason=r.finish_reason,
                          tokens_entrada=r.tokens_entrada, tokens_salida=r.tokens_salida,
                          duracion_ms=int((self._reloj() - t_llm) * 1000))
                if r.finish_reason == "length":
                    motivo = "respuesta_truncada"; break
                if not r.llamadas:
                    if r.contenido and r.contenido.strip():
                        texto = r.contenido.strip()
                    else:
                        motivo = "respuesta_vacia"
                    break
                if ultima:  # pidió herramientas cuando ya no se permiten
                    motivo = "limite_iteraciones"; break
                if len(ejecutadas) + len(r.llamadas) > l.max_llamadas_herramienta:
                    motivo = "limite_herramientas"; break
                mensajes.append({"role": "assistant", **({"content": r.contenido} if r.contenido else {}),
                                 "tool_calls": [{"id": c.id, "type": "function",
                                                 "function": {"name": c.nombre, "arguments": c.argumentos}}
                                                for c in r.llamadas]})
                for c in r.llamadas:
                    res = self._registro.ejecutar(c.nombre, c.argumentos, hoy)
                    ejecutadas.append(res)
                    registrar("herramienta", herramienta=res.nombre, argumentos=res.argumentos, ok=res.ok,
                              codigo_error=res.codigo_error, duracion_ms=res.duracion_ms)
                    mensajes.append({"role": "tool", "tool_call_id": c.id, "name": c.nombre,
                                     "content": res.contenido()})
        except ErrorLLM as error:
            registrar("error_llm", codigo=error.codigo, detalle=error.detalle)
            return self._cerrar(conversacion, pregunta, t0, ejecutadas, t_in, t_out, llamadas_llm,
                                estado="error", motivo=error.codigo, origen="mensaje_error",
                                respuesta=MENSAJES_ERROR_LLM.get(error.codigo, MENSAJE_ERROR_GENERICO))
        else:
            if texto is None and motivo is None:
                motivo = "limite_iteraciones"  # el bucle terminó sin respuesta

        datos = [{"argumentos": e.argumentos, "datos": e.datos} for e in ejecutadas if e.ok]  # cifras permitidas
        if texto is not None:
            veredicto = verificar_respuesta(texto, datos, hoy)
            if veredicto.ok:
                return self._cerrar(conversacion, pregunta, t0, ejecutadas, t_in, t_out, llamadas_llm,
                                    estado="ok", motivo=None, origen="modelo", respuesta=texto)
            registrar("verificacion_fallida", cifras_no_respaldadas=len(veredicto.no_respaldadas))
            motivo = "cifras_no_verificadas"
        estado = "limite" if motivo in _CORTES else "degradado"
        respuesta = f"{AVISOS[motivo]}\n\n{plantilla_respaldo(ejecutadas)}"
        return self._cerrar(conversacion, pregunta, t0, ejecutadas, t_in, t_out, llamadas_llm,
                            estado=estado, motivo=motivo, origen="plantilla", respuesta=respuesta)

    def _cerrar(self, conversacion, pregunta, t0, ejecutadas, t_in, t_out, llamadas_llm,
                *, estado, motivo, origen, respuesta) -> ResultadoAgente:
        resultado = ResultadoAgente(respuesta, estado, motivo, origen, ejecutadas, t_in, t_out, llamadas_llm,
                                    int((self._reloj() - t0) * 1000))
        if estado != "error":  # un fallo del proveedor no deja rastro en el historial
            conversacion.registrar_turno(pregunta, respuesta)
        conversacion.ultimo_resultado = resultado
        return resultado
