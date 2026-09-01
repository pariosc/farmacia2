\set ON_ERROR_STOP on
\pset pager off

SELECT
    to_regclass('public.tf_reservas_dispensacion') IS NOT NULL AS tabla_reservas,
    EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'tf_productos' AND column_name = 'precio_venta'
    ) AS producto_con_precio,
    EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'tf_dispensaciones' AND column_name = 'reserva_hasta'
    ) AS dispensacion_con_reserva,
    EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'tf_dispensaciones' AND column_name = 'origen'
    ) AS soporta_venta_directa,
    EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'tf_dispensaciones'
          AND column_name = 'id_paciente_externo'
          AND data_type = 'character varying'
          AND character_maximum_length = 80
    ) AS paciente_alfanumerico,
    EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'tf_detalles_dispensacion' AND column_name = 'precio_unitario'
    ) AS detalle_con_precio;

SELECT conrelid::regclass AS tabla, conname, convalidated
FROM pg_constraint
WHERE conname IN (
    'ck_tf_productos_precio_venta',
    'ck_tf_dispensaciones_estado',
    'ck_tf_dispensaciones_origen',
    'ck_tf_dispensaciones_version',
    'ck_tf_dispensaciones_total',
    'fk_tf_detalles_dispensacion_producto',
    'ck_tf_detalles_dispensacion_prescrita',
    'ck_tf_detalles_dispensacion_solicitada',
    'ck_tf_detalles_dispensacion_precio',
    'ck_tf_detalles_dispensacion_subtotal',
    'ck_tf_reservas_cantidad',
    'ck_tf_reservas_estado',
    'ck_tf_reservas_liberacion'
)
ORDER BY conrelid::regclass::text, conname;

SELECT indexname
FROM pg_indexes
WHERE indexname IN (
    'uq_tf_dispensaciones_id_factura',
    'uq_tf_detalles_dispensacion_prescripcion',
    'uq_tf_reservas_dispensacion_activa'
)
ORDER BY indexname;

SELECT tgname, tgrelid::regclass AS tabla
FROM pg_trigger
WHERE NOT tgisinternal
  AND tgname IN ('trg_tf_reservas_validar_producto', 'trg_tf_detalles_recalcular_total')
ORDER BY tgname;

DO $$
DECLARE
    v_errores integer;
BEGIN
    SELECT count(*) INTO v_errores
    FROM tf_dispensaciones d
    WHERE d.total <> COALESCE((
        SELECT round(sum(dd.subtotal), 2)
        FROM tf_detalles_dispensacion dd
        WHERE dd.id_dispensacion = d.id_dispensacion
    ), 0);
    IF v_errores > 0 THEN
        RAISE EXCEPTION 'Hay % dispensaciones cuyo total no coincide con sus detalles', v_errores;
    END IF;

    SELECT count(*) INTO v_errores
    FROM tf_reservas_dispensacion r
    JOIN tf_detalles_dispensacion dd USING (id_detalle_dispensacion)
    JOIN tf_lotes l ON l.id_lote = r.id_lote
    WHERE dd.id_producto <> l.id_producto;
    IF v_errores > 0 THEN
        RAISE EXCEPTION 'Hay % reservas cuyo lote pertenece a otro producto', v_errores;
    END IF;

    IF (SELECT count(*) FROM pg_trigger WHERE NOT tgisinternal AND tgname IN (
            'trg_tf_reservas_validar_producto', 'trg_tf_detalles_recalcular_total'
        )) <> 2 THEN
        RAISE EXCEPTION 'No están instalados los dos triggers de integridad de dispensación';
    END IF;
END $$;

SELECT '006_dispensacion_integrada verificada correctamente' AS resultado;
