\set ON_ERROR_STOP on

BEGIN;

SELECT pg_advisory_xact_lock(hashtext('farmacia:003_consumo_prescripciones'));

-- Revierte la conexión de Consumo interno con prescripciones dejando el esquema
-- tal como estaba antes de la migración 003 (solicitud y detalle de solicitud
-- vuelven a ser las únicas referencias). Conserva ti_detalle_prescripciones:
-- esa tabla puede pertenecer al módulo clínico y no debe eliminarse desde aquí.

ALTER TABLE tf_consumos_internos
    DROP CONSTRAINT IF EXISTS fk_tf_consumos_prescripcion;
ALTER TABLE tf_detalles_consumo
    DROP CONSTRAINT IF EXISTS fk_tf_detalles_consumo_detalle_prescripcion;

DROP INDEX IF EXISTS idx_tf_consumos_internos_id_prescripcion;
DROP INDEX IF EXISTS idx_tf_detalles_consumo_id_detalle_prescripcion;

ALTER TABLE tf_consumos_internos
    DROP COLUMN IF EXISTS id_prescripcion;
ALTER TABLE tf_detalles_consumo
    DROP COLUMN IF EXISTS id_detalle_prescripcion;

COMMIT;