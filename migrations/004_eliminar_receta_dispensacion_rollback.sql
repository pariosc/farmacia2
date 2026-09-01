\set ON_ERROR_STOP on

BEGIN;

SELECT pg_advisory_xact_lock(hashtext('farmacia:004_eliminar_receta_dispensacion'));

-- ADVERTENCIA: este rollback restaura la ESTRUCTURA de las columnas
-- (nullable, sin backfill), no los datos originales de id_receta /
-- id_detalle_receta, que ya se perdieron al hacer DROP COLUMN.
-- Solo usar si la migración 004 debe revertirse inmediatamente después
-- de aplicarse y antes de que se registren dispensaciones nuevas.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'tf_dispensaciones' AND column_name = 'id_receta'
    ) THEN
        ALTER TABLE tf_dispensaciones ADD COLUMN id_receta integer;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'tf_detalles_dispensacion' AND column_name = 'id_detalle_receta'
    ) THEN
        ALTER TABLE tf_detalles_dispensacion ADD COLUMN id_detalle_receta integer;
    END IF;
END $$;

COMMIT;