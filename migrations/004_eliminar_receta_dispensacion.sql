\set ON_ERROR_STOP on

BEGIN;

-- Evita que dos personas apliquen simultáneamente esta migración.
SELECT pg_advisory_xact_lock(hashtext('farmacia:004_eliminar_receta_dispensacion'));

-- Contexto: la receta médica es física/manual (no queda registrada en un
-- sistema digital compartido), por lo que tf_dispensaciones e
-- tf_detalles_dispensacion ya no referencian una tabla de recetas.
-- La autorización de entrega pasa a validarse únicamente contra el
-- comprobante de pago (id_factura / id_detalle_comprobante), que ya
-- existía en ambas tablas.

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'tf_dispensaciones' AND column_name = 'id_receta'
    ) THEN
        ALTER TABLE tf_dispensaciones DROP COLUMN id_receta;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'tf_detalles_dispensacion' AND column_name = 'id_detalle_receta'
    ) THEN
        ALTER TABLE tf_detalles_dispensacion DROP COLUMN id_detalle_receta;
    END IF;
END $$;

COMMENT ON TABLE tf_dispensaciones IS
    'Registra la dispensación de medicamentos autorizados por comprobante de pago. '
    'No referencia receta: la prescripción médica es manual/física.';

COMMENT ON TABLE tf_detalles_dispensacion IS
    'Producto, lote y cantidad entregados en una dispensación, validados contra '
    'el detalle del comprobante de pago (no contra receta).';

COMMIT;