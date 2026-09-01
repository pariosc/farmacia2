\set ON_ERROR_STOP on

BEGIN;

SELECT pg_advisory_xact_lock(hashtext('farmacia:006_dispensacion_integrada'));

-- El rollback es intencionalmente conservador: se detiene si ya existen datos
-- creados con el flujo integrado, porque borrarlos sería pérdida de información.
DO $$
BEGIN
    IF to_regclass('public.tf_reservas_dispensacion') IS NOT NULL
       AND EXISTS (SELECT 1 FROM tf_reservas_dispensacion) THEN
        RAISE EXCEPTION 'Rollback rechazado: existen reservas. Migre o respalde esos datos primero.';
    END IF;
    IF EXISTS (
        SELECT 1 FROM tf_dispensaciones
        WHERE estado IN ('PENDIENTE_PAGO', 'PAGADA', 'VENCIDA', 'ANULACION_SOLICITADA')
           OR id_receta_externa IS NOT NULL
           OR id_paciente_externo IS NOT NULL
    ) THEN
        RAISE EXCEPTION 'Rollback rechazado: existen dispensaciones del flujo integrado.';
    END IF;
END $$;

DROP TRIGGER IF EXISTS trg_tf_detalles_recalcular_total ON tf_detalles_dispensacion;
DROP FUNCTION IF EXISTS farmacia_recalcular_total_dispensacion();
DROP TRIGGER IF EXISTS trg_tf_reservas_validar_producto ON tf_reservas_dispensacion;
DROP FUNCTION IF EXISTS farmacia_validar_reserva_producto();
DROP TABLE IF EXISTS tf_reservas_dispensacion;

DROP INDEX IF EXISTS uq_tf_detalles_dispensacion_prescripcion;
DROP INDEX IF EXISTS idx_tf_detalles_dispensacion_producto;
DROP INDEX IF EXISTS idx_tf_detalles_dispensacion_prescripcion;
ALTER TABLE tf_detalles_dispensacion
    DROP CONSTRAINT IF EXISTS fk_tf_detalles_dispensacion_producto,
    DROP CONSTRAINT IF EXISTS ck_tf_detalles_dispensacion_prescrita,
    DROP CONSTRAINT IF EXISTS ck_tf_detalles_dispensacion_solicitada,
    DROP CONSTRAINT IF EXISTS ck_tf_detalles_dispensacion_precio,
    DROP CONSTRAINT IF EXISTS ck_tf_detalles_dispensacion_subtotal,
    DROP COLUMN IF EXISTS id_prescripcion_externa,
    DROP COLUMN IF EXISTS id_producto,
    DROP COLUMN IF EXISTS cantidad_prescrita,
    DROP COLUMN IF EXISTS cantidad_solicitada,
    DROP COLUMN IF EXISTS precio_unitario,
    DROP COLUMN IF EXISTS subtotal,
    DROP COLUMN IF EXISTS dosis_instrucciones;

DROP INDEX IF EXISTS uq_tf_dispensaciones_id_factura;
DROP INDEX IF EXISTS idx_tf_dispensaciones_receta_externa;
DROP INDEX IF EXISTS idx_tf_dispensaciones_numero_receta;
DROP INDEX IF EXISTS idx_tf_dispensaciones_reserva;
ALTER TABLE tf_dispensaciones
    DROP CONSTRAINT IF EXISTS ck_tf_dispensaciones_estado,
    DROP CONSTRAINT IF EXISTS ck_tf_dispensaciones_origen,
    DROP CONSTRAINT IF EXISTS ck_tf_dispensaciones_version,
    DROP CONSTRAINT IF EXISTS ck_tf_dispensaciones_total,
    DROP COLUMN IF EXISTS numero_receta_externa,
    DROP COLUMN IF EXISTS origen,
    DROP COLUMN IF EXISTS id_receta_externa,
    DROP COLUMN IF EXISTS version_receta,
    DROP COLUMN IF EXISTS id_paciente_externo,
    DROP COLUMN IF EXISTS version,
    DROP COLUMN IF EXISTS total,
    DROP COLUMN IF EXISTS reserva_hasta,
    DROP COLUMN IF EXISTS fecha_creacion,
    DROP COLUMN IF EXISTS fecha_actualizacion,
    DROP COLUMN IF EXISTS fecha_pago,
    DROP COLUMN IF EXISTS motivo_anulacion;

ALTER TABLE tf_dispensaciones
    ADD CONSTRAINT ck_tf_dispensaciones_estado
    CHECK (estado IN ('PENDIENTE', 'ENTREGADA', 'ANULADA')) NOT VALID;

-- Restaura la obligatoriedad del esquema legado solo cuando esas columnas
-- existen. El bloqueo inicial garantiza que no haya filas del flujo nuevo.
ALTER TABLE tf_dispensaciones ALTER COLUMN id_factura SET NOT NULL;
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'tf_dispensaciones'
          AND column_name = 'id_receta'
    ) THEN
        ALTER TABLE tf_dispensaciones ALTER COLUMN id_receta SET NOT NULL;
    END IF;
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'tf_detalles_dispensacion'
          AND column_name = 'id_detalle_receta'
    ) THEN
        ALTER TABLE tf_detalles_dispensacion ALTER COLUMN id_detalle_receta SET NOT NULL;
    END IF;
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'tf_detalles_dispensacion'
          AND column_name = 'id_detalle_comprobante'
    ) THEN
        ALTER TABLE tf_detalles_dispensacion ALTER COLUMN id_detalle_comprobante SET NOT NULL;
    END IF;
END $$;
ALTER TABLE tf_detalles_dispensacion
    ALTER COLUMN id_lote SET NOT NULL,
    ALTER COLUMN cantidad_entregada SET NOT NULL;

ALTER TABLE tf_productos
    DROP CONSTRAINT IF EXISTS ck_tf_productos_precio_venta,
    DROP COLUMN IF EXISTS precio_venta;

COMMIT;
