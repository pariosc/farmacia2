-- Verificación de solo lectura tras aplicar 004_eliminar_receta_dispensacion.sql

SELECT
    NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'tf_dispensaciones' AND column_name = 'id_receta'
    ) AS id_receta_eliminado,
    NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'tf_detalles_dispensacion' AND column_name = 'id_detalle_receta'
    ) AS id_detalle_receta_eliminado,
    EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'tf_dispensaciones' AND column_name = 'id_factura'
    ) AS id_factura_presente,
    EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'tf_detalles_dispensacion' AND column_name = 'id_detalle_comprobante'
    ) AS id_detalle_comprobante_presente;