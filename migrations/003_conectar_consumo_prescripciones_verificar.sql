-- Verificación de solo lectura tras aplicar 003_conectar_consumo_prescripciones.sql

SELECT
    to_regclass('ti_prescripciones') IS NOT NULL AS tabla_prescripciones_presente,
    to_regclass('ti_detalle_prescripciones') IS NOT NULL AS tabla_detalle_prescripciones_presente,
    EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'tf_consumos_internos' AND column_name = 'id_prescripcion'
    ) AS id_prescripcion_presente,
    EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'tf_detalles_consumo' AND column_name = 'id_detalle_prescripcion'
    ) AS id_detalle_prescripcion_presente,
    EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'tf_consumos_internos'::regclass
          AND conname = 'fk_tf_consumos_prescripcion'
    ) AS fk_consumos_prescripcion_presente,
    EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'tf_detalles_consumo'::regclass
          AND conname = 'fk_tf_detalles_consumo_detalle_prescripcion'
    ) AS fk_detalle_consumo_prescripcion_presente;