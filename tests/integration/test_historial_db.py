"""Requiere la migración 004 aplicada. Todo se ejecuta en UNA transacción que se revierte al final:
el rol de la aplicación no puede borrar, y las pruebas no deben dejar filas."""
import pytest

from agentflow.db.connection import obtener_conexion_escritura
from agentflow.db.repositories.historial import HistorialPostgres

pytestmark = pytest.mark.integration


class _SinCommit:
    def __init__(self, conexion):
        self._c = conexion

    def __enter__(self):
        return self._c

    def __exit__(self, *a):
        return False  # ni commit ni cierre


@pytest.fixture
def conexion():
    c = obtener_conexion_escritura()
    if c.execute("SELECT to_regclass('public.conversaciones')").fetchone()[0] is None:
        c.close()
        pytest.skip("migración 004 sin aplicar")
    yield c
    c.rollback()
    c.close()


def test_ciclo_completo_y_separacion_por_sesion(conexion):
    repo = HistorialPostgres(lambda: _SinCommit(conexion))
    a, b = repo.crear(), repo.crear()
    repo.agregar(a, [("user", "¿Cuánto vendimos?"), ("assistant", "S/ 100.00")])
    repo.agregar(b, [("user", "otra sesión")])
    assert [m["content"] for m in repo.cargar(a, 10)] == ["¿Cuánto vendimos?", "S/ 100.00"]
    assert [m["content"] for m in repo.cargar(b, 10)] == ["otra sesión"]
    assert repo.cargar("00000000-0000-0000-0000-000000000000", 10) is None
    assert {f["id"] for f in repo.listar(50)} >= {a, b}


def test_la_base_rechaza_roles_y_contenido_invalidos(conexion):
    import psycopg
    cid = HistorialPostgres(lambda: _SinCommit(conexion)).crear()
    for rol, contenido in [("system", "x"), ("user", "")]:
        with pytest.raises(psycopg.errors.CheckViolation):
            conexion.execute("INSERT INTO mensajes (conversacion_id, rol, contenido) VALUES (%s, %s, %s)",
                             (cid, rol, contenido))
        conexion.rollback()
        cid = HistorialPostgres(lambda: _SinCommit(conexion)).crear()


def test_el_rol_de_la_aplicacion_no_puede_borrar_ni_modificar(conexion):
    import psycopg
    cid = HistorialPostgres(lambda: _SinCommit(conexion)).crear()
    for sql in ("DELETE FROM mensajes", "UPDATE mensajes SET contenido = 'x'", "DROP TABLE mensajes"):
        with pytest.raises(psycopg.Error):
            conexion.execute(sql)
        conexion.rollback()
        cid = HistorialPostgres(lambda: _SinCommit(conexion)).crear()
