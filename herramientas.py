
from database import obtener_conexion


def consultar_ventas() -> dict:
    """Consulta las ventas en PostgreSQL y calcula indicadores."""

    print("[TOOL] Consultando ventas en PostgreSQL...")

    # 1. Consulta SQL
    sql = """
        SELECT
            p.nombre AS producto,
            SUM(v.cantidad) AS unidades,
            SUM(v.cantidad * v.precio_unitario) AS ingresos
        FROM ventas v
        JOIN productos p
            ON v.id_producto = p.id_producto
        GROUP BY p.id_producto, p.nombre
        ORDER BY ingresos DESC;
    """

    # 2. Conectar con PostgreSQL
    with obtener_conexion() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(sql)
            resultados = cursor.fetchall()

    # 3. Controlar el caso de una base sin ventas
    if not resultados:
        return {
            "moneda": "PEN",
            "ingresos_totales": 0,
            "producto_lider": None,
            "ingresos_por_producto": {}
        }

    # 4. Organizar los ingresos por producto
    ingresos_por_producto = {
        producto: float(ingreso)
        for producto, unidades, ingreso in resultados
    }

    # 5. Calcular ingresos totales
    ingresos_totales = sum(
        ingresos_por_producto.values()
    )

    # 6. Identificar el producto líder
    producto_lider = max(
        ingresos_por_producto,
        key=ingresos_por_producto.get
    )

    # 7. Devolver los resultados
    return {
        "moneda": "PEN",
        "ingresos_totales": ingresos_totales,
        "producto_lider": producto_lider,
        "ingresos_por_producto": ingresos_por_producto
    }


if __name__ == "__main__":
    print(consultar_ventas())

