"""Requiere la migración 005 aplicada. Una sola transacción que se revierte: el rol de la app no puede borrar."""
import psycopg
import pytest

from agentflow.db.connection import obtener_conexion_escritura
from agentflow.db.repositories.ejecuciones import RegistroEjecuciones
from agentflow.db.repositories.historial import HistorialPostgres

pytestmark = pytest.mark.integration


class _SinCommit:
    def __init__(self, c):
        self._c = c

    def __enter__(self):
        return self._c

    def __exit__(self, *a):
        return False


@pytest.fixture
def conexion():
    c = obtener_conexion_escritura()
    if c.execute("SELECT to_regclass('public.ejecuciones')").fetchone()[0] is None:
        c.close()
        pytest.skip("migración 005 sin aplicar")
    yield c
    c.rollback()
    c.close()


HERR = [{"nombre": "ventas_totales", "argumentos": {"periodo": "este_mes"}, "ok": True,
         "codigo_error": None, "duracion_ms": 9},
        {"nombre": "ejecutar_sql", "argumentos": None, "ok": False,
         "codigo_error": "herramienta_no_autorizada", "duracion_ms": 0}]


def test_ciclo_iniciar_finalizar_y_listar_por_sesion(conexion):
    f = lambda: _SinCommit(conexion)  # noqa: E731
    sesion = HistorialPostgres(f).crear()
    repo = RegistroEjecuciones(f)
    ejec = repo.iniciar(sesion, 30)
    assert repo.listar(sesion)[0]["estado"] == "en_curso"
    repo.finalizar(ejec, "ok", None, "modelo", 150, 30, 2, 800, HERR)
    fila = repo.listar(sesion)[0]
    assert (fila["id"], fila["estado"], fila["tokens"], fila["herramientas"]) == (ejec, "ok", 180, 2)
    with pytest.raises(LookupError):                       # ya finalizada
        repo.finalizar(ejec, "error", None, "modelo", 0, 0, 0, 0, [])


def test_sesion_ajena_no_aparece(conexion):
    f = lambda: _SinCommit(conexion)  # noqa: E731
    a, b = HistorialPostgres(f).crear(), HistorialPostgres(f).crear()
    repo = RegistroEjecuciones(f)
    repo.iniciar(a, 1)
    assert repo.listar(b) == []


def test_ejecucion_finalizada_es_inmutable_y_la_app_no_puede_borrar(conexion):
    f = lambda: _SinCommit(conexion)  # noqa: E731
    repo = RegistroEjecuciones(f)
    ejec = repo.iniciar(None, 1)
    repo.finalizar(ejec, "ok", None, "modelo", 1, 1, 1, 1, [])
    for sql, params in [("UPDATE ejecuciones SET estado = 'error' WHERE id = %s", (ejec,)),   # trigger
                        ("UPDATE ejecuciones SET pregunta_chars = 0 WHERE id = %s", (ejec,)),  # sin permiso de columna
                        ("DELETE FROM ejecuciones WHERE id = %s", (ejec,))]:
        with pytest.raises(psycopg.Error):
            conexion.execute(sql, params)
        conexion.rollback()
        ejec = RegistroEjecuciones(f).iniciar(None, 1)
        RegistroEjecuciones(f).finalizar(ejec, "ok", None, "modelo", 1, 1, 1, 1, [])


def test_checks_rechazan_estado_invalido(conexion):
    with pytest.raises(psycopg.errors.CheckViolation):
        conexion.execute("INSERT INTO ejecuciones (estado, pregunta_chars) VALUES ('hecho', 1)")


def test_detalle_devuelve_ejecucion_con_herramientas_y_none_si_no_existe(conexion):
    f = lambda: _SinCommit(conexion)  # noqa: E731
    repo = RegistroEjecuciones(f)
    ejec = repo.iniciar(None, 30)
    repo.finalizar(ejec, "ok", None, "modelo", 150, 30, 2, 800, HERR)
    d = repo.detalle(ejec)
    assert (d["id"], d["estado"], d["tokens_entrada"], d["conversacion_id"]) == (ejec, "ok", 150, None)
    assert [h["herramienta"] for h in d["herramientas"]] == ["ventas_totales", "ejecutar_sql"]
    assert d["herramientas"][0]["argumentos"] == {"periodo": "este_mes"} and d["herramientas"][1]["ok"] is False
    assert repo.detalle("00000000-0000-0000-0000-000000000000") is None
