\set ON_ERROR_STOP on

BEGIN TRANSACTION READ ONLY;

SELECT id_tipo_producto, codigo, nombre, activo
FROM tf_tipos_producto
ORDER BY id_tipo_producto;

SELECT p.id_producto,
       p.codigo AS codigo_producto,
       p.tipo_producto AS tipo_legado,
       p.id_tipo_producto,
       t.codigo AS codigo_tipo,
       t.nombre AS nombre_tipo
FROM tf_productos p
JOIN tf_tipos_producto t
  ON t.id_tipo_producto = p.id_tipo_producto
ORDER BY p.id_producto;

SELECT count(*) AS productos_sin_tipo
FROM tf_productos
WHERE id_tipo_producto IS NULL;

SELECT count(*) AS productos_con_tipo_inconsistente
FROM tf_productos p
JOIN tf_tipos_producto t ON t.id_tipo_producto = p.id_tipo_producto
WHERE CASE upper(btrim(p.tipo_producto))
          WHEN 'INSUMO' THEN 'INSUMO_MEDICO'
          WHEN 'DISPOSITIVO' THEN 'DISPOSITIVO_MEDICO'
          ELSE upper(btrim(p.tipo_producto))
      END <> t.codigo;

SELECT c.conname, pg_get_constraintdef(c.oid) AS definicion
FROM pg_constraint c
WHERE c.conrelid IN ('tf_tipos_producto'::regclass, 'tf_productos'::regclass)
  AND c.conname IN (
      'uq_tf_tipos_producto_codigo',
      'uq_tf_tipos_producto_nombre',
      'ck_tf_tipos_producto_codigo_formato',
      'fk_tf_productos_tipo_producto'
  )
ORDER BY c.conname;

SELECT trigger_name, event_manipulation, action_timing
FROM information_schema.triggers
WHERE event_object_schema = 'public'
  AND event_object_table = 'tf_productos'
  AND trigger_name = 'trg_tf_productos_sincronizar_tipo';

ROLLBACK;
