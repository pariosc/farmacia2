-- Fechas operativas por defecto: día actual del servidor PostgreSQL.
-- Ejecutar una sola vez en la base de datos de Farmacia.

ALTER TABLE tf_compras
    ALTER COLUMN fecha_compra SET DEFAULT CURRENT_DATE;

ALTER TABLE tf_dispensaciones
    ALTER COLUMN fecha_dispensacion SET DEFAULT CURRENT_DATE;

ALTER TABLE tf_consumos_internos
    ALTER COLUMN fecha_consumo SET DEFAULT CURRENT_DATE;

ALTER TABLE tf_movimientos_inventario
    ALTER COLUMN fecha_movimiento SET DEFAULT CURRENT_DATE;
