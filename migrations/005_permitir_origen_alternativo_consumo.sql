\set ON_ERROR_STOP on

BEGIN;

SELECT pg_advisory_xact_lock(hashtext('farmacia:005_permitir_origen_alternativo_consumo'));

-- Ahora que tf_consumos_internos puede originarse desde id_solicitud_insumo
-- (flujo antiguo) O id_prescripcion (flujo conectado a Internación, migración 003),
-- ninguna de las dos puede ser NOT NULL individualmente. Se agrega un CHECK
-- que exige al menos una de las dos, replicando la validación ya aplicada
-- en el backend (entidades/farmacia_consumo.py).

ALTER TABLE tf_consumos_internos
    ALTER COLUMN id_solicitud_insumo DROP NOT NULL;

ALTER TABLE tf_detalles_consumo
    ALTER COLUMN id_detalle_solicitud_consumo DROP NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'tf_consumos_internos'::regclass
          AND conname = 'ck_tf_consumos_internos_origen'
    ) THEN
        ALTER TABLE tf_consumos_internos
            ADD CONSTRAINT ck_tf_consumos_internos_origen
            CHECK (id_solicitud_insumo IS NOT NULL OR id_prescripcion IS NOT NULL)
            NOT VALID;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'tf_detalles_consumo'::regclass
          AND conname = 'ck_tf_detalles_consumo_origen'
    ) THEN
        ALTER TABLE tf_detalles_consumo
            ADD CONSTRAINT ck_tf_detalles_consumo_origen
            CHECK (id_detalle_solicitud_consumo IS NOT NULL OR id_detalle_prescripcion IS NOT NULL)
            NOT VALID;
    END IF;
END $$;

COMMENT ON COLUMN tf_consumos_internos.id_solicitud_insumo IS
    'Origen legado del consumo. Nullable: puede venir por id_prescripcion en su lugar.';
COMMENT ON COLUMN tf_consumos_internos.id_prescripcion IS
    'Origen desde Internación (ti_prescripciones). Nullable: puede venir por id_solicitud_insumo.';

COMMIT;
