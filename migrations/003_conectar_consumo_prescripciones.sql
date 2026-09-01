\set ON_ERROR_STOP on

-- Tabla mínima para pruebas de integración con Internación.
-- En producción debe conservarse la definición oficial del módulo clínico.
CREATE TABLE IF NOT EXISTS ti_detalle_prescripciones (
    id_detalle_prescripcion BIGSERIAL PRIMARY KEY,
    id_prescripcion BIGINT NOT NULL,
    id_producto INTEGER NOT NULL,
    cantidad_prescrita NUMERIC(12,2) NOT NULL,
    observacion TEXT,
    CONSTRAINT ck_ti_detalle_prescripciones_cantidad
        CHECK (cantidad_prescrita > 0),
    CONSTRAINT fk_ti_detalle_prescripcion_prescripcion
        FOREIGN KEY (id_prescripcion)
        REFERENCES ti_prescripciones(id_prescripcion),
    CONSTRAINT fk_ti_detalle_prescripcion_producto
        FOREIGN KEY (id_producto)
        REFERENCES tf_productos(id_producto)
);

CREATE INDEX IF NOT EXISTS idx_ti_detalle_prescripciones_prescripcion
    ON ti_detalle_prescripciones(id_prescripcion);

CREATE INDEX IF NOT EXISTS idx_ti_detalle_prescripciones_producto
    ON ti_detalle_prescripciones(id_producto);

BEGIN;

-- Conecta Consumo interno con las prescripciones del módulo de Internación.
-- Esta migración es aditiva: conserva las referencias antiguas a solicitudes
-- para no perder trazabilidad de datos ya registrados.
SELECT pg_advisory_xact_lock(hashtext('farmacia:003_consumo_prescripciones'));

-- La tabla de detalle pertenece al módulo clínico. No se crea aquí ni se
-- inventa su estructura; la base debe traerla desde la versión clínica
-- correspondiente.
DO $$
BEGIN
    IF to_regclass('ti_prescripciones') IS NULL THEN
        RAISE EXCEPTION
            'Falta la tabla ti_prescripciones. Instale primero la versión clínica requerida.';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'ti_prescripciones'
          AND column_name = 'id_prescripcion'
    ) THEN
        RAISE EXCEPTION
            'ti_prescripciones no contiene la columna id_prescripcion.';
    END IF;

    IF to_regclass('ti_detalle_prescripciones') IS NULL THEN
        RAISE EXCEPTION
            'Falta la tabla ti_detalle_prescripciones. Instale primero la versión clínica requerida.';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'ti_detalle_prescripciones'
          AND column_name = 'id_detalle_prescripcion'
    ) THEN
        RAISE EXCEPTION
            'ti_detalle_prescripciones no contiene la columna id_detalle_prescripcion.';
    END IF;
END $$;

ALTER TABLE tf_consumos_internos
    ADD COLUMN IF NOT EXISTS id_prescripcion bigint;

ALTER TABLE tf_detalles_consumo
    ADD COLUMN IF NOT EXISTS id_detalle_prescripcion bigint;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'tf_consumos_internos'::regclass
          AND conname = 'fk_tf_consumos_prescripcion'
    ) THEN
        ALTER TABLE tf_consumos_internos
            ADD CONSTRAINT fk_tf_consumos_prescripcion
            FOREIGN KEY (id_prescripcion)
            REFERENCES ti_prescripciones(id_prescripcion)
            DEFERRABLE INITIALLY IMMEDIATE;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'tf_detalles_consumo'::regclass
          AND conname = 'fk_tf_detalles_consumo_detalle_prescripcion'
    ) THEN
        ALTER TABLE tf_detalles_consumo
            ADD CONSTRAINT fk_tf_detalles_consumo_detalle_prescripcion
            FOREIGN KEY (id_detalle_prescripcion)
            REFERENCES ti_detalle_prescripciones(id_detalle_prescripcion)
            DEFERRABLE INITIALLY IMMEDIATE;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_tf_consumos_internos_id_prescripcion
    ON tf_consumos_internos(id_prescripcion);

CREATE INDEX IF NOT EXISTS idx_tf_detalles_consumo_id_detalle_prescripcion
    ON tf_detalles_consumo(id_detalle_prescripcion);

COMMENT ON COLUMN tf_consumos_internos.id_prescripcion IS
    'Prescripción clínica relacionada; nullable para conservar consumos históricos.';

COMMENT ON COLUMN tf_detalles_consumo.id_detalle_prescripcion IS
    'Detalle de prescripción clínica atendido; nullable para conservar consumos históricos.';

COMMIT;