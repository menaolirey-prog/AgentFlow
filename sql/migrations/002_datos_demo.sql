-- Idempotente. Datos FICTICIOS (es_demo = true): 1 venta semanal por producto,
-- 2026-05-04 a 2026-11-02 (27 semanas x 3 productos = 81). Determinista: sin random().
-- El Mouse cae desde octubre. Requiere 001.
-- Doble protección contra duplicados: índice único parcial + inserción condicional.
CREATE UNIQUE INDEX IF NOT EXISTS uq_ventas_demo ON ventas (id_producto, fecha) WHERE es_demo;

INSERT INTO ventas (id_producto, cantidad, fecha, precio_unitario, es_demo)
SELECT p.id_producto,
       GREATEST(1, 2 + ((EXTRACT(week FROM d)::int * p.id_producto) % 5)
                   - CASE WHEN p.nombre = 'Mouse' AND d >= DATE '2026-10-01' THEN 2 ELSE 0 END),
       d + TIME '10:00',
       p.precio,
       true
FROM productos p
CROSS JOIN generate_series(DATE '2026-05-04', DATE '2026-11-02', INTERVAL '7 days') AS d
WHERE NOT EXISTS (SELECT 1 FROM ventas WHERE es_demo);
