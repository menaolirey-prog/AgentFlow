-- Idempotente. Marca como ficticias (es_demo = true) las 3 ventas de prueba del prototipo inicial.
-- Evidencia: ids 1-3, un producto cada una, mismo instante de creación; las demás demo (ids 4-84) ya son es_demo.
-- Solo cambia la columna es_demo; no toca cantidades, precios ni fechas. La doble condición (id + fecha)
-- evita marcar por error una venta real futura que llegara a reutilizar esos IDs.
-- Aplicar como administrador. Reversión: sql/migrations/down/006_marcar_ventas_iniciales_demo.down.sql
UPDATE ventas
SET es_demo = true
WHERE id_venta IN (1, 2, 3)
  AND fecha = TIMESTAMP '2026-11-10 13:12:13.461303'
  AND NOT es_demo;
