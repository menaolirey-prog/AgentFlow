-- Reversión de 006: devuelve las 3 ventas iniciales a es_demo = false. Aplicar como administrador.
UPDATE ventas
SET es_demo = false
WHERE id_venta IN (1, 2, 3)
  AND fecha = TIMESTAMP '2026-11-10 13:12:13.461303'
  AND es_demo;
