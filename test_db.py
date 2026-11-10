
from database import obtener_conexion


def probar_conexion():
    """Comprueba la conexión con PostgreSQL."""

    print("Verificando conexion con PostgreSQL...")

    try:
        # 1. Conectar a la base de datos
        with obtener_conexion() as conexion:

            print("Conexion establecida correctamente.")

            # 2. Crear cursor para ejecutar SQL
            with conexion.cursor() as cursor:

                # 3. Comprobar la base de datos actual
                cursor.execute("SELECT current_database()")
                base_datos = cursor.fetchone()[0]

                # 4. Contar los productos
                cursor.execute(
                    "SELECT COUNT(*) FROM public.productos"
                )
                cantidad = cursor.fetchone()[0]

                print(f"Base de datos: {base_datos}")
                print(f"Productos registrados: {cantidad}")

        print("\nPRUEBA COMPLETADA CORRECTAMENTE")

    except Exception as error:
        print("\nERROR DE CONEXION")
        print(f"Tipo: {type(error).__name__}")
        print(f"Detalle: {error}")


if __name__ == "__main__":
    probar_conexion()


