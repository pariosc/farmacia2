\set ON_ERROR_STOP on

BEGIN;

-- Este rollback conserva tipo_producto, por lo que el backend anterior sigue
-- teniendo toda la información. Se niega a borrar el catálogo si otra tabla
-- llegó a referenciarlo.
DROP TRIGGER IF EXISTS trg_tf_productos_sincronizar_tipo ON tf_productos;
DROP FUNCTION IF EXISTS tf_sincronizar_tipo_producto();

ALTER TABLE tf_productos
    DROP CONSTRAINT IF EXISTS fk_tf_productos_tipo_producto;

DROP INDEX IF EXISTS idx_tf_productos_id_tipo_producto;

ALTER TABLE tf_productos
    DROP COLUMN IF EXISTS id_tipo_producto;

DROP TABLE IF EXISTS tf_tipos_producto;

COMMIT;
