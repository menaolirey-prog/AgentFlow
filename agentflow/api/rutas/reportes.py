"""Reportes de ventas (deterministas, sin IA). Reutiliza `construir_reporte` y `escribir_csv`; el CSV va en memoria."""
import io
from datetime import datetime
from typing import Literal

from fastapi import Depends, Query
from fastapi.responses import Response

from agentflow.api.errors import ErrorAPI, ErrorRespuesta
from agentflow.api.rutas._comun import Servicios, limitar_lectura, obtener_servicios, router_privado
from agentflow.config import ZONA_LIMA
from agentflow.tools.reportes import construir_reporte, escribir_csv

router = router_privado("Reportes")
_ERR = {422: {"model": ErrorRespuesta}}


class _Parametros:
    def __init__(self,
                 periodo: str = Query(..., min_length=1, max_length=40, description="Preset o AAAA-MM-DD/AAAA-MM-DD"),
                 comparar_con: str | None = Query(None, min_length=1, max_length=40),
                 origen: Literal["todos", "real", "demo"] = "todos"):
        self.periodo, self.comparar_con, self.origen = periodo, comparar_con, origen


def _reporte(p: _Parametros, s: Servicios) -> dict:
    try:
        return construir_reporte(s.ventas, p.periodo, p.comparar_con, p.origen, datetime.now(ZONA_LIMA).date())
    except ValueError as error:  # mensajes de periodos.py: fijos, salvo la lista de presets; no ecoan la entrada
        raise ErrorAPI(422, "periodo_invalido", str(error)) from None


@router.get("/reportes/ventas", responses=_ERR, dependencies=[Depends(limitar_lectura)],
            summary="Reporte de ventas (real y demo por separado)")
def reporte_json(p: _Parametros = Depends(), s: Servicios = Depends(obtener_servicios)) -> dict:
    return _reporte(p, s)


@router.get("/reportes/ventas.csv", responses=_ERR, dependencies=[Depends(limitar_lectura)],
            response_class=Response, summary="Mismo reporte en CSV (generado en memoria)")
def reporte_csv(p: _Parametros = Depends(), s: Servicios = Depends(obtener_servicios)) -> Response:
    buffer = io.StringIO()
    buffer.write("﻿")  # BOM para que Excel lea bien los acentos
    escribir_csv(_reporte(p, s), buffer)
    return Response(buffer.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="reporte_ventas.csv"'})
