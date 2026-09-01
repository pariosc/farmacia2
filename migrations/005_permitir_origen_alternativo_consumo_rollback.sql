\set ON_ERROR_STOP on

BEGIN;

SELECT pg_advisory_xact_lock(hashtext('farmacia:005_permitir_origen_alternativo_consumo'));

-- ADVERTENCIA: si ya existen filas con id_solicitud_insumo NULL (registradas
-- vía id_prescripcion), este rollback fallará al intentar restaurar NOT NULL.
-- Revisar y corregir esas filas manualmente antes de revertir.

ALTER TABLE tf_consumos_internos
    DROP CONSTRAINT IF EXISTS ck_tf_consumos_internos_origen;

ALTER TABLE tf_detalles_consumo
    DROP CONSTRAINT IF EXISTS ck_tf_detalles_consumo_origen;

ALTER TABLE tf_consumos_internos
    ALTER COLUMN id_solicitud_insumo SET NOT NULL;

ALTER TABLE tf_detalles_consumo
    ALTER COLUMN id_detalle_solicitud_consumo SET NOT NULL;

COMMIT;
