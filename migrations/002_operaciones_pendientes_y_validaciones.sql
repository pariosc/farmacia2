\set ON_ERROR_STOP on

BEGIN;

SELECT pg_advisory_xact_lock(hashtext('farmacia:002_operaciones_pendientes'));

-- PENDIENTE no descuenta existencias. La confirmación transaccional del backend
-- cambia al estado final y genera la salida de inventario.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'tf_dispensaciones'::regclass
          AND conname = 'ck_tf_dispensaciones_estado'
    ) THEN
        ALTER TABLE tf_dispensaciones
            ADD CONSTRAINT ck_tf_dispensaciones_estado
            CHECK (estado IN ('PENDIENTE', 'ENTREGADA', 'ANULADA')) NOT VALID;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'tf_consumos_internos'::regclass
          AND conname = 'ck_tf_consumos_internos_estado'
    ) THEN
        ALTER TABLE tf_consumos_internos
            ADD CONSTRAINT ck_tf_consumos_internos_estado
            CHECK (estado IN ('PENDIENTE', 'REGISTRADO', 'ANULADO')) NOT VALID;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'tf_detalles_dispensacion'::regclass
          AND conname = 'ck_tf_detalles_dispensacion_cantidad'
    ) THEN
        ALTER TABLE tf_detalles_dispensacion
            ADD CONSTRAINT ck_tf_detalles_dispensacion_cantidad
            CHECK (cantidad_entregada > 0) NOT VALID;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'tf_detalles_consumo'::regclass
          AND conname = 'ck_tf_detalles_consumo_cantidad'
    ) THEN
        ALTER TABLE tf_detalles_consumo
            ADD CONSTRAINT ck_tf_detalles_consumo_cantidad
            CHECK (cantidad_entregada > 0) NOT VALID;
    END IF;
END $$;

COMMIT;
