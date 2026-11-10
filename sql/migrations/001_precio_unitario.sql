-- Idempotente. Guarda el precio de cada venta para que cambiar productos.precio no altere la historia.
ALTER TABLE ventas ADD COLUMN IF NOT EXISTS precio_unitario numeric(12,2);
ALTER TABLE ventas ADD COLUMN IF NOT EXISTS es_demo boolean NOT NULL DEFAULT false;
-- Solo rellena las filas sin precio (las ventas existentes son recientes: sin historia de precios).
UPDATE ventas v SET precio_unitario = p.precio
FROM productos p WHERE p.id_producto = v.id_producto AND v.precio_unitario IS NULL;
ALTER TABLE ventas ALTER COLUMN precio_unitario SET NOT NULL;
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint
                   WHERE conname = 'ventas_precio_unitario_check'
                     AND conrelid = 'public.ventas'::regclass) THEN
        ALTER TABLE ventas ADD CONSTRAINT ventas_precio_unitario_check CHECK (precio_unitario >= 0);
    END IF;
END $$;
CREATE INDEX IF NOT EXISTS idx_ventas_fecha ON ventas (fecha);
