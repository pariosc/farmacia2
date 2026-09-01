\set ON_ERROR_STOP on

BEGIN;

SELECT pg_advisory_xact_lock(hashtext('farmacia:002_operaciones_pendientes'));

ALTER TABLE tf_dispensaciones
    DROP CONSTRAINT IF EXISTS ck_tf_dispensaciones_estado;
ALTER TABLE tf_consumos_internos
    DROP CONSTRAINT IF EXISTS ck_tf_consumos_internos_estado;
ALTER TABLE tf_detalles_dispensacion
    DROP CONSTRAINT IF EXISTS ck_tf_detalles_dispensacion_cantidad;
ALTER TABLE tf_detalles_consumo
    DROP CONSTRAINT IF EXISTS ck_tf_detalles_consumo_cantidad;

COMMIT;
