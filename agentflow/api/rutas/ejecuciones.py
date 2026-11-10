"""Detalle de una ejecución del agente (solo metadatos: nunca texto de preguntas ni respuestas)."""
from fastapi import Depends

from agentflow.api.errors import ErrorRespuesta, NoEncontrado
from agentflow.api.esquemas import EjecucionDetalle
from agentflow.api.rutas._comun import Servicios, limitar_lectura, obtener_servicios, router_privado, uuid_o_404

router = router_privado("Ejecuciones")


@router.get("/ejecuciones/{ejecucion_id}", response_model=EjecucionDetalle,
            responses={404: {"model": ErrorRespuesta}}, dependencies=[Depends(limitar_lectura)],
            summary="Detalle de una ejecución con sus herramientas")
def detalle(ejecucion_id: str, s: Servicios = Depends(obtener_servicios)):
    d = s.ejecuciones.detalle(uuid_o_404(ejecucion_id, "Ejecución no encontrada."))
    if d is None:
        raise NoEncontrado("Ejecución no encontrada.")
    return d
