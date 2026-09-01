SELECT
    (SELECT is_nullable FROM information_schema.columns
     WHERE table_name = 'tf_consumos_internos' AND column_name = 'id_solicitud_insumo') = 'YES'
        AS id_solicitud_insumo_nullable,
    (SELECT is_nullable FROM information_schema.columns
     WHERE table_name = 'tf_detalles_consumo' AND column_name = 'id_detalle_solicitud_consumo') = 'YES'
        AS id_detalle_solicitud_consumo_nullable,
    EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'tf_consumos_internos'::regclass
          AND conname = 'ck_tf_consumos_internos_origen'
    ) AS check_cabecera_presente,
    EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'tf_detalles_consumo'::regclass
          AND conname = 'ck_tf_detalles_consumo_origen'
    ) AS check_detalle_presente;
