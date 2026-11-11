"""Verifica las migraciones desde cero en una base TEMPORAL y aislada; nunca toca la base de la aplicación.

Uso (conexión de administrador por variables estándar de libpq; la contraseña no va en el código):
    PGHOST=localhost PGPORT=5432 PGUSER=<admin> PGPASSWORD=<...> python scripts/verificar_migraciones.py

Crea una base `agentflow_verif_<aleatorio>`, aplica sql/migrations/000..006 (dos veces: idempotencia), comprueba
esquema, datos demo y permisos del rol agentflow_app, y borra la base al terminar. Si el rol agentflow_app no existe
en el servidor lo crea sin contraseña (NOLOGIN) y lo elimina al final; si ya existe, no lo modifica.
"""
import secrets
import sys
from pathlib import Path

import psycopg
from psycopg import sql

RAIZ = Path(__file__).resolve().parent.parent
MIGRACIONES = sorted((RAIZ / "sql" / "migrations").glob("[0-9][0-9][0-9]_*.sql"))

COLUMNAS_ESPERADAS = {
    "productos": [("id_producto", "integer", "NO"), ("nombre", "character varying", "NO"), ("precio", "numeric", "NO")],
    "ventas": [("id_venta", "integer", "NO"), ("id_producto", "integer", "NO"), ("cantidad", "integer", "NO"),
               ("fecha", "timestamp without time zone", "NO"), ("precio_unitario", "numeric", "NO"),
               ("es_demo", "boolean", "NO")],
}


def comprobar(condicion: bool, mensaje: str) -> None:
    print(("  OK  " if condicion else "  FALLA ") + mensaje)
    if not condicion:
        raise SystemExit(1)


def aplicar_todas(dsn_base: dict, nombre_db: str) -> None:
    with psycopg.connect(dbname=nombre_db, **dsn_base, autocommit=False) as con:
        for archivo in MIGRACIONES:
            con.execute(archivo.read_text(encoding="utf-8"))
            con.commit()


def main() -> int:
    if not MIGRACIONES or MIGRACIONES[0].name[:3] != "000":
        print("No se encontró sql/migrations/000_*.sql")
        return 2
    nombre_db = f"agentflow_verif_{secrets.token_hex(4)}"
    rol_creado = False
    with psycopg.connect(dbname="postgres", autocommit=True) as admin:
        if not admin.execute("SELECT 1 FROM pg_roles WHERE rolname='agentflow_app'").fetchone():
            admin.execute("CREATE ROLE agentflow_app NOLOGIN")
            rol_creado = True
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(nombre_db)))
        print(f"Base temporal: {nombre_db}")
        try:
            aplicar_todas({}, nombre_db)
            print("Migraciones aplicadas:", ", ".join(m.name[:3] for m in MIGRACIONES))
            with psycopg.connect(dbname=nombre_db) as con:
                snap1 = con.execute("SELECT (SELECT count(*) FROM ventas), (SELECT count(*) FROM productos)").fetchone()
            aplicar_todas({}, nombre_db)  # segunda pasada: todas son idempotentes
            with psycopg.connect(dbname=nombre_db) as con:
                snap2 = con.execute("SELECT (SELECT count(*) FROM ventas), (SELECT count(*) FROM productos)").fetchone()
                comprobar(snap1 == snap2, f"idempotencia: dos pasadas dejan los mismos conteos {snap2}")
                for tabla, esperadas in COLUMNAS_ESPERADAS.items():
                    cols = con.execute(
                        "SELECT column_name, data_type, is_nullable FROM information_schema.columns "
                        "WHERE table_schema='public' AND table_name=%s ORDER BY ordinal_position", (tabla,)).fetchall()
                    comprobar(cols == esperadas, f"columnas de {tabla}")
                productos = con.execute("SELECT id_producto, nombre, precio FROM productos ORDER BY 1").fetchall()
                comprobar([p[:2] for p in productos] == [(1, "Laptop"), (2, "Mouse"), (3, "Monitor")], "productos 1-3")
                n, n_demo = con.execute("SELECT count(*), count(*) FILTER (WHERE es_demo) FROM ventas").fetchone()
                comprobar((n, n_demo) == (81, 81), f"ventas: {n} filas, {n_demo} demo (todas ficticias, ninguna real)")
                for tabla in ("conversaciones", "mensajes", "ejecuciones", "ejecucion_herramientas"):
                    existe = con.execute("SELECT to_regclass(%s)", (f"public.{tabla}",)).fetchone()[0]
                    comprobar(existe is not None, f"tabla {tabla}")
                privs = lambda t: {p for (p,) in con.execute(  # noqa: E731
                    "SELECT privilege_type FROM information_schema.role_table_grants "
                    "WHERE grantee='agentflow_app' AND table_name=%s", (t,))}
                comprobar(privs("ventas") == {"SELECT"} and privs("productos") == {"SELECT"},
                          "agentflow_app: solo SELECT en ventas y productos")
                comprobar(privs("mensajes") == {"SELECT", "INSERT"}, "agentflow_app: SELECT+INSERT en mensajes")
                comprobar(all(privs(t) <= {"SELECT", "INSERT"} for t in ("ventas", "productos", "mensajes", "conversaciones")),
                          "agentflow_app: nunca UPDATE, DELETE ni DDL en datos de negocio e historial")
            print("RESULTADO: migraciones verificadas desde cero")
            return 0
        finally:
            admin.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(nombre_db)))
            if rol_creado:
                admin.execute("DROP ROLE IF EXISTS agentflow_app")
            print(f"Base temporal {nombre_db} eliminada")


if __name__ == "__main__":
    sys.exit(main())
