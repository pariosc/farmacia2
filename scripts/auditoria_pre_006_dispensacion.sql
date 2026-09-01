\set ON_ERROR_STOP on
\pset pager off

\echo '=== Columnas actuales ==='
SELECT table_name, column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN ('tf_productos', 'tf_dispensaciones', 'tf_detalles_dispensacion')
ORDER BY table_name, ordinal_position;

\echo '=== Estados existentes (todos deben ser reconocidos por la migración) ==='
SELECT estado, count(*)
FROM tf_dispensaciones
GROUP BY estado
ORDER BY estado;

\echo '=== Facturas repetidas (debe devolver cero filas) ==='
SELECT id_factura, count(*) AS dispensaciones
FROM tf_dispensaciones
WHERE id_factura IS NOT NULL
GROUP BY id_factura
HAVING count(*) > 1;

\echo '=== Detalles huérfanos de lote/producto (debe devolver cero filas) ==='
SELECT d.id_detalle_dispensacion, d.id_lote
FROM tf_detalles_dispensacion d
LEFT JOIN tf_lotes l ON l.id_lote = d.id_lote
WHERE d.id_lote IS NULL OR l.id_lote IS NULL;

\echo '=== Cantidades históricas inválidas (debe devolver cero filas) ==='
SELECT id_detalle_dispensacion, cantidad_entregada
FROM tf_detalles_dispensacion
WHERE cantidad_entregada IS NULL OR cantidad_entregada <= 0;

\echo '=== Stock negativo (debe devolver cero filas) ==='
SELECT id_lote, id_producto, stock_actual
FROM tf_lotes
WHERE stock_actual < 0;

\echo '=== Resumen previo ==='
SELECT
    (SELECT count(*) FROM tf_productos) AS productos,
    (SELECT count(*) FROM tf_lotes) AS lotes,
    (SELECT count(*) FROM tf_dispensaciones) AS dispensaciones,
    (SELECT count(*) FROM tf_detalles_dispensacion) AS detalles;
