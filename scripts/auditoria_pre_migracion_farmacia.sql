\set ON_ERROR_STOP on

BEGIN TRANSACTION READ ONLY;

-- Ejecutar primero en cada una de las siete bases y conservar la salida.
SELECT current_database() AS base,
       current_user AS usuario,
       current_timestamp AS fecha_auditoria,
       version() AS version_postgresql;

SELECT 'tf_categorias_producto' AS tabla, count(*) AS registros FROM tf_categorias_producto
UNION ALL SELECT 'tf_productos', count(*) FROM tf_productos
UNION ALL SELECT 'tf_proveedores', count(*) FROM tf_proveedores
UNION ALL SELECT 'tf_compras', count(*) FROM tf_compras
UNION ALL SELECT 'tf_detalles_compra', count(*) FROM tf_detalles_compra
UNION ALL SELECT 'tf_lotes', count(*) FROM tf_lotes
UNION ALL SELECT 'tf_dispensaciones', count(*) FROM tf_dispensaciones
UNION ALL SELECT 'tf_detalles_dispensacion', count(*) FROM tf_detalles_dispensacion
UNION ALL SELECT 'tf_consumos_internos', count(*) FROM tf_consumos_internos
UNION ALL SELECT 'tf_detalles_consumo', count(*) FROM tf_detalles_consumo
UNION ALL SELECT 'tf_movimientos_inventario', count(*) FROM tf_movimientos_inventario;

SELECT tipo_producto, count(*) AS registros
FROM tf_productos
GROUP BY tipo_producto
ORDER BY tipo_producto;

SELECT 'tf_compras' AS tabla, estado, count(*) AS registros FROM tf_compras GROUP BY estado
UNION ALL SELECT 'tf_dispensaciones', estado, count(*) FROM tf_dispensaciones GROUP BY estado
UNION ALL SELECT 'tf_consumos_internos', estado, count(*) FROM tf_consumos_internos GROUP BY estado
UNION ALL SELECT 'tf_lotes', estado, count(*) FROM tf_lotes GROUP BY estado
ORDER BY tabla, estado;

SELECT 'stock_minimo_negativo' AS prueba, count(*) AS hallazgos FROM tf_productos WHERE stock_minimo < 0
UNION ALL SELECT 'stock_actual_negativo', count(*) FROM tf_lotes WHERE stock_actual < 0
UNION ALL SELECT 'compra_cantidad_no_positiva', count(*) FROM tf_detalles_compra WHERE cantidad <= 0
UNION ALL SELECT 'compra_costo_negativo', count(*) FROM tf_detalles_compra WHERE costo_unitario < 0
UNION ALL SELECT 'dispensacion_cantidad_no_positiva', count(*) FROM tf_detalles_dispensacion WHERE cantidad_entregada <= 0
UNION ALL SELECT 'consumo_cantidad_no_positiva', count(*) FROM tf_detalles_consumo WHERE cantidad_entregada <= 0
UNION ALL SELECT 'movimiento_cantidad_cero', count(*) FROM tf_movimientos_inventario WHERE cantidad = 0
UNION ALL SELECT 'movimiento_tipo_invalido', count(*) FROM tf_movimientos_inventario WHERE tipo_movimiento NOT IN ('ENTRADA','SALIDA','AJUSTE');

WITH referencias AS (
    SELECT m.*,
           num_nonnulls(id_detalle_compra,
                        id_detalle_dispensacion,
                        id_detalle_consumo) AS cantidad_origenes
    FROM tf_movimientos_inventario m
)
SELECT 'movimientos_multiples_origenes' AS prueba, count(*) AS hallazgos
FROM referencias WHERE cantidad_origenes > 1
UNION ALL
SELECT 'entradas_sin_compra', count(*)
FROM referencias WHERE tipo_movimiento = 'ENTRADA' AND id_detalle_compra IS NULL
UNION ALL
SELECT 'salidas_sin_origen', count(*)
FROM referencias
WHERE tipo_movimiento = 'SALIDA'
  AND id_detalle_dispensacion IS NULL
  AND id_detalle_consumo IS NULL
UNION ALL
SELECT 'ajustes_con_origen_operativo', count(*)
FROM referencias WHERE tipo_movimiento = 'AJUSTE' AND cantidad_origenes > 0;

WITH stock_calculado AS (
    SELECT l.id_lote,
           l.numero_lote,
           l.stock_actual,
           coalesce(sum(CASE
               WHEN m.tipo_movimiento = 'ENTRADA' THEN m.cantidad
               WHEN m.tipo_movimiento = 'SALIDA' THEN -m.cantidad
               WHEN m.tipo_movimiento = 'AJUSTE' THEN m.cantidad
               ELSE 0
           END), 0) AS stock_por_movimientos
    FROM tf_lotes l
    LEFT JOIN tf_movimientos_inventario m ON m.id_lote = l.id_lote
    GROUP BY l.id_lote, l.numero_lote, l.stock_actual
)
SELECT *, stock_actual - stock_por_movimientos AS diferencia
FROM stock_calculado
WHERE stock_actual <> stock_por_movimientos
ORDER BY id_lote;

SELECT id_lote, numero_lote, fecha_vencimiento, stock_actual, estado
FROM tf_lotes
WHERE (fecha_vencimiento < CURRENT_DATE AND estado <> 'VENCIDO')
   OR (stock_actual <= 0 AND estado <> 'AGOTADO')
   OR (stock_actual > 0 AND estado = 'AGOTADO')
ORDER BY id_lote;

SELECT id_detalle_receta,
       count(*) AS repeticiones,
       sum(cantidad_entregada) AS total_entregado
FROM tf_detalles_dispensacion
GROUP BY id_detalle_receta
HAVING count(*) > 1;

SELECT id_detalle_solicitud_consumo,
       count(*) AS repeticiones,
       sum(cantidad_entregada) AS total_entregado
FROM tf_detalles_consumo
GROUP BY id_detalle_solicitud_consumo
HAVING count(*) > 1;

SELECT m.id_movimiento,
       m.tipo_movimiento,
       m.cantidad,
       m.id_lote,
       coalesce(c.estado, d.estado, ci.estado, 'AJUSTE') AS estado_origen
FROM tf_movimientos_inventario m
LEFT JOIN tf_detalles_compra dc ON dc.id_detalle_compra = m.id_detalle_compra
LEFT JOIN tf_compras c ON c.id_compra = dc.id_compra
LEFT JOIN tf_detalles_dispensacion dd
       ON dd.id_detalle_dispensacion = m.id_detalle_dispensacion
LEFT JOIN tf_dispensaciones d ON d.id_dispensacion = dd.id_dispensacion
LEFT JOIN tf_detalles_consumo dci ON dci.id_detalle_consumo = m.id_detalle_consumo
LEFT JOIN tf_consumos_internos ci ON ci.id_consumo = dci.id_consumo
WHERE c.estado = 'ANULADA'
   OR d.estado = 'ANULADA'
   OR ci.estado = 'ANULADO'
ORDER BY m.id_movimiento;

ROLLBACK;
