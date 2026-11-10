"""Conversaciones, historial y chat. Reutiliza `Conversacion` y `Agente`; no duplica lógica del orquestador."""
from fastapi import Depends, Query, Request

from agentflow.agent.conversacion import Conversacion, ConversacionNoEncontrada
from agentflow.api.errors import DemasiadasSolicitudes, ErrorRespuesta, NoEncontrado
from agentflow.api.esquemas import (ConversacionCreada, ConversacionResumen, EjecucionResumen, HerramientaUsada,
                                    Mensaje, NuevoMensaje, RespuestaChat)
from agentflow.api.rutas._comun import (Servicios, limitar_lectura, obtener_servicios, router_privado,
                                        uuid_o_404)

router = router_privado("Conversaciones")
_NO_EXISTE = "Conversación no encontrada."


@router.post("/conversaciones", status_code=201, response_model=ConversacionCreada,
             dependencies=[Depends(limitar_lectura)], summary="Crea una conversación vacía")
def crear(s: Servicios = Depends(obtener_servicios)) -> ConversacionCreada:
    return ConversacionCreada(id=s.historial.crear())


@router.get("/conversaciones", response_model=list[ConversacionResumen], dependencies=[Depends(limitar_lectura)],
            summary="Conversaciones recientes")
def listar(limite: int = Query(20, ge=1, le=50), s: Servicios = Depends(obtener_servicios)):
    return s.historial.listar(limite)


@router.get("/conversaciones/{conversacion_id}/mensajes", response_model=list[Mensaje],
            responses={404: {"model": ErrorRespuesta}}, dependencies=[Depends(limitar_lectura)],
            summary="Historial cronológico (últimos `limite` mensajes)")
def historial(conversacion_id: str, limite: int = Query(50, ge=1, le=100),
              s: Servicios = Depends(obtener_servicios)):
    mensajes = s.historial.cargar(uuid_o_404(conversacion_id, _NO_EXISTE), limite)
    if mensajes is None:
        raise NoEncontrado(_NO_EXISTE)
    return [Mensaje(rol=m["role"], contenido=m["content"]) for m in mensajes]


@router.get("/conversaciones/{conversacion_id}/ejecuciones", response_model=list[EjecucionResumen],
            responses={404: {"model": ErrorRespuesta}}, dependencies=[Depends(limitar_lectura)],
            summary="Ejecuciones del agente en la conversación")
def ejecuciones(conversacion_id: str, limite: int = Query(20, ge=1, le=50),
                s: Servicios = Depends(obtener_servicios)):
    identificador = uuid_o_404(conversacion_id, _NO_EXISTE)
    if s.historial.cargar(identificador, 1) is None:
        raise NoEncontrado(_NO_EXISTE)
    return s.ejecuciones.listar(identificador, limite)


@router.post("/conversaciones/{conversacion_id}/mensajes", response_model=RespuestaChat,
             responses={404: {"model": ErrorRespuesta}, 422: {"model": ErrorRespuesta}},
             summary="Chat: envía un mensaje al agente (consume cuota del modelo)")
def chatear(conversacion_id: str, entrada: NuevoMensaje, request: Request,
            s: Servicios = Depends(obtener_servicios)) -> RespuestaChat:
    limitadores = request.app.state.limitadores
    limitadores.chat.consumir()  # antes de tocar la base o el modelo
    identificador = uuid_o_404(conversacion_id, _NO_EXISTE)
    if not limitadores.chats_activos.acquire(blocking=False):  # tope de chats simultáneos (cuota y hilos)
        raise DemasiadasSolicitudes(5, "Hay otro mensaje en curso. Espera a que termine.")
    try:
        try:
            conversacion = Conversacion.reanudar(s.historial, identificador)
        except ConversacionNoEncontrada:
            raise NoEncontrado(_NO_EXISTE) from None
        r = s.crear_agente().responder(entrada.contenido, conversacion)
    finally:
        limitadores.chats_activos.release()
    return RespuestaChat(
        respuesta=r.respuesta, estado=r.estado, motivo=r.motivo, origen=r.origen,
        herramientas=[HerramientaUsada(nombre=h.nombre, ok=h.ok, codigo_error=h.codigo_error,
                                       duracion_ms=h.duracion_ms) for h in r.herramientas],
        tokens_entrada=r.tokens_entrada, tokens_salida=r.tokens_salida, duracion_ms=r.duracion_ms,
        ejecucion_id=r.ejecucion_id, historial_guardado=conversacion.persistencia_ok)
