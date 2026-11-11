-- Idempotente. Esquema base (productos y ventas) para construir la base desde cero.
-- Reproduce la estructura del prototipo original; 001 añade precio_unitario y es_demo, y 002 genera los datos demo.
-- En una base que ya tiene estas tablas no cambia nada (IF NOT EXISTS / ON CONFLICT DO NOTHING).
-- Los 3 productos son ficticios; sus ids (1 Laptop, 2 Mouse, 3 Monitor) los espera la lógica de 002.
-- Aplicar como administrador, antes de 001. No hay reversión automática (borraría datos).
CREATE TABLE IF NOT EXISTS productos (
    id_producto integer       GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre      varchar(100)  NOT NULL UNIQUE,
    precio      numeric(10,2) NOT NULL CHECK (precio >= 0)
);

CREATE TABLE IF NOT EXISTS ventas (
    id_venta    integer   GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_producto integer   NOT NULL,
    cantidad    integer   NOT NULL CHECK (cantidad > 0),
    fecha       timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_producto FOREIGN KEY (id_producto) REFERENCES productos (id_producto)
);

INSERT INTO productos (nombre, precio)
VALUES ('Laptop', 2500.00), ('Mouse', 50.00), ('Monitor', 800.00)
ON CONFLICT (nombre) DO NOTHING;
