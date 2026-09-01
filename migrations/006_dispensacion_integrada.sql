\set ON_ERROR_STOP on

BEGIN;

SELECT pg_advisory_xact_lock(hashtext('farmacia:006_dispensacion_integrada'));

DO $$
BEGIN
    IF to_regclass('public.tf_productos') IS NULL
       OR to_regclass('public.tf_lotes') IS NULL
       OR to_regclass('public.tf_dispensaciones') IS NULL
       OR to_regclass('public.tf_detalles_dispensacion') IS NULL THEN
        RAISE EXCEPTION 'Faltan tablas base de Farmacia. Ejecute primero las migraciones anteriores.';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM tf_dispensaciones
        WHERE id_factura IS NOT NULL
        GROUP BY id_factura
        HAVING count(*) > 1
    ) THEN
        RAISE EXCEPTION 'Hay facturas asociadas a más de una dispensación. Revise la auditoría previa antes de continuar.';
    END IF;
END $$;

-- Precio vigente. Los detalles guardan una copia histórica y nunca recalculan
-- una orden ya pagada a partir de este valor.
ALTER TABLE tf_productos
    ADD COLUMN IF NOT EXISTS precio_venta numeric(12,2) NOT NULL DEFAULT 0;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'tf_productos'::regclass
          AND conname = 'ck_tf_productos_precio_venta'
    ) THEN
        ALTER TABLE tf_productos
            ADD CONSTRAINT ck_tf_productos_precio_venta
            CHECK (precio_venta >= 0) NOT VALID;
    END IF;
END $$;

ALTER TABLE tf_productos VALIDATE CONSTRAINT ck_tf_productos_precio_venta;

-- La misma tabla representa la nota/proforma y, después del pago, la entrega.
ALTER TABLE tf_dispensaciones
    ADD COLUMN IF NOT EXISTS origen varchar(20) NOT NULL DEFAULT 'RECETA',
    ADD COLUMN IF NOT EXISTS numero_receta_externa varchar(80),
    ADD COLUMN IF NOT EXISTS id_receta_externa bigint,
    ADD COLUMN IF NOT EXISTS version_receta integer,
    ADD COLUMN IF NOT EXISTS id_paciente_externo varchar(80),
    ADD COLUMN IF NOT EXISTS version integer NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS total numeric(14,2) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS reserva_hasta timestamptz,
    ADD COLUMN IF NOT EXISTS fecha_creacion timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ADD COLUMN IF NOT EXISTS fecha_actualizacion timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ADD COLUMN IF NOT EXISTS fecha_pago timestamptz,
    ADD COLUMN IF NOT EXISTS motivo_anulacion varchar(255);

-- Atención confirmó que su identificador canónico es alfanumérico, por ejemplo
-- PAC-2026-00101. También convierte clones donde una versión preliminar de 006
-- hubiera creado esta columna como bigint.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'tf_dispensaciones'
          AND column_name = 'id_paciente_externo'
          AND data_type <> 'character varying'
    ) THEN
        ALTER TABLE tf_dispensaciones
            ALTER COLUMN id_paciente_externo TYPE varchar(80)
            USING id_paciente_externo::text;
    END IF;
END $$;

-- Compatibilidad con respaldos que sí conservaron receta/factura y con otros
-- que ya aplicaron la migración 004. No se elimina ninguna columna histórica.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'tf_dispensaciones'
          AND column_name = 'id_receta'
    ) THEN
        ALTER TABLE tf_dispensaciones ALTER COLUMN id_receta DROP NOT NULL;
    END IF;
    ALTER TABLE tf_dispensaciones ALTER COLUMN id_factura DROP NOT NULL;
END $$;

UPDATE tf_dispensaciones
SET fecha_creacion = COALESCE(fecha_creacion, fecha_dispensacion::timestamp),
    fecha_actualizacion = COALESCE(fecha_actualizacion, fecha_dispensacion::timestamp),
    version = GREATEST(COALESCE(version, 1), 1),
    total = COALESCE(total, 0);

ALTER TABLE tf_dispensaciones DROP CONSTRAINT IF EXISTS ck_tf_dispensaciones_estado;
ALTER TABLE tf_dispensaciones DROP CONSTRAINT IF EXISTS ck_tf_dispensaciones_origen;
ALTER TABLE tf_dispensaciones
    ADD CONSTRAINT ck_tf_dispensaciones_origen
    CHECK (origen IN ('RECETA', 'VENTA_DIRECTA')) NOT VALID;
ALTER TABLE tf_dispensaciones
    ADD CONSTRAINT ck_tf_dispensaciones_estado
    CHECK (estado IN (
        'PENDIENTE',              -- legado; no crear nuevas filas con este estado
        'PENDIENTE_PAGO',
        'PAGADA',
        'PARCIAL',                 -- legado de la BD original
        'ENTREGADA',
        'VENCIDA',
        'ANULACION_SOLICITADA',
        'ANULADA'
    )) NOT VALID;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'tf_dispensaciones'::regclass
          AND conname = 'ck_tf_dispensaciones_version'
    ) THEN
        ALTER TABLE tf_dispensaciones
            ADD CONSTRAINT ck_tf_dispensaciones_version CHECK (version > 0) NOT VALID;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'tf_dispensaciones'::regclass
          AND conname = 'ck_tf_dispensaciones_total'
    ) THEN
        ALTER TABLE tf_dispensaciones
            ADD CONSTRAINT ck_tf_dispensaciones_total CHECK (total >= 0) NOT VALID;
    END IF;
END $$;

ALTER TABLE tf_dispensaciones VALIDATE CONSTRAINT ck_tf_dispensaciones_estado;
ALTER TABLE tf_dispensaciones VALIDATE CONSTRAINT ck_tf_dispensaciones_origen;
ALTER TABLE tf_dispensaciones VALIDATE CONSTRAINT ck_tf_dispensaciones_version;
ALTER TABLE tf_dispensaciones VALIDATE CONSTRAINT ck_tf_dispensaciones_total;

CREATE UNIQUE INDEX IF NOT EXISTS uq_tf_dispensaciones_id_factura
    ON tf_dispensaciones (id_factura)
    WHERE id_factura IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_tf_dispensaciones_receta_externa
    ON tf_dispensaciones (id_receta_externa, estado);
CREATE INDEX IF NOT EXISTS idx_tf_dispensaciones_numero_receta
    ON tf_dispensaciones (numero_receta_externa, estado);
CREATE INDEX IF NOT EXISTS idx_tf_dispensaciones_reserva
    ON tf_dispensaciones (estado, reserva_hasta);

ALTER TABLE tf_detalles_dispensacion
    ADD COLUMN IF NOT EXISTS id_prescripcion_externa bigint,
    ADD COLUMN IF NOT EXISTS id_producto integer,
    ADD COLUMN IF NOT EXISTS cantidad_prescrita numeric(14,2),
    ADD COLUMN IF NOT EXISTS cantidad_solicitada numeric(14,2),
    ADD COLUMN IF NOT EXISTS precio_unitario numeric(12,2) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS subtotal numeric(14,2),
    ADD COLUMN IF NOT EXISTS dosis_instrucciones text;

-- Convierte filas históricas sin inventar referencias externas. El producto
-- se obtiene del lote ya validado por la FK existente.
UPDATE tf_detalles_dispensacion d
SET id_producto = COALESCE(d.id_producto, l.id_producto),
    cantidad_solicitada = COALESCE(d.cantidad_solicitada, d.cantidad_entregada),
    cantidad_prescrita = COALESCE(d.cantidad_prescrita, d.cantidad_entregada),
    precio_unitario = COALESCE(d.precio_unitario, 0),
    subtotal = COALESCE(
        d.subtotal,
        round(COALESCE(d.cantidad_solicitada, d.cantidad_entregada, 0)
              * COALESCE(d.precio_unitario, 0), 2)
    )
FROM tf_lotes l
WHERE d.id_lote = l.id_lote;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM tf_detalles_dispensacion
        WHERE id_producto IS NULL OR cantidad_solicitada IS NULL OR cantidad_prescrita IS NULL
    ) THEN
        RAISE EXCEPTION 'No fue posible completar producto/cantidades de detalles históricos. Revise lotes huérfanos.';
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'tf_detalles_dispensacion'
          AND column_name = 'id_detalle_receta'
    ) THEN
        ALTER TABLE tf_detalles_dispensacion ALTER COLUMN id_detalle_receta DROP NOT NULL;
    END IF;
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'tf_detalles_dispensacion'
          AND column_name = 'id_detalle_comprobante'
    ) THEN
        ALTER TABLE tf_detalles_dispensacion ALTER COLUMN id_detalle_comprobante DROP NOT NULL;
    END IF;
END $$;

ALTER TABLE tf_detalles_dispensacion
    ALTER COLUMN id_lote DROP NOT NULL,
    ALTER COLUMN cantidad_entregada DROP NOT NULL,
    ALTER COLUMN id_producto SET NOT NULL,
    ALTER COLUMN cantidad_prescrita SET NOT NULL,
    ALTER COLUMN cantidad_solicitada SET NOT NULL,
    ALTER COLUMN subtotal SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'tf_detalles_dispensacion'::regclass
          AND conname = 'fk_tf_detalles_dispensacion_producto'
    ) THEN
        ALTER TABLE tf_detalles_dispensacion
            ADD CONSTRAINT fk_tf_detalles_dispensacion_producto
            FOREIGN KEY (id_producto) REFERENCES tf_productos(id_producto)
            DEFERRABLE INITIALLY IMMEDIATE NOT VALID;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'tf_detalles_dispensacion'::regclass
          AND conname = 'ck_tf_detalles_dispensacion_prescrita'
    ) THEN
        ALTER TABLE tf_detalles_dispensacion
            ADD CONSTRAINT ck_tf_detalles_dispensacion_prescrita
            CHECK (cantidad_prescrita > 0) NOT VALID;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'tf_detalles_dispensacion'::regclass
          AND conname = 'ck_tf_detalles_dispensacion_solicitada'
    ) THEN
        ALTER TABLE tf_detalles_dispensacion
            ADD CONSTRAINT ck_tf_detalles_dispensacion_solicitada
            CHECK (cantidad_solicitada > 0 AND cantidad_solicitada <= cantidad_prescrita) NOT VALID;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'tf_detalles_dispensacion'::regclass
          AND conname = 'ck_tf_detalles_dispensacion_precio'
    ) THEN
        ALTER TABLE tf_detalles_dispensacion
            ADD CONSTRAINT ck_tf_detalles_dispensacion_precio
            CHECK (precio_unitario >= 0) NOT VALID;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'tf_detalles_dispensacion'::regclass
          AND conname = 'ck_tf_detalles_dispensacion_subtotal'
    ) THEN
        ALTER TABLE tf_detalles_dispensacion
            ADD CONSTRAINT ck_tf_detalles_dispensacion_subtotal
            CHECK (subtotal = round(cantidad_solicitada * precio_unitario, 2)) NOT VALID;
    END IF;
END $$;

ALTER TABLE tf_detalles_dispensacion VALIDATE CONSTRAINT fk_tf_detalles_dispensacion_producto;
ALTER TABLE tf_detalles_dispensacion VALIDATE CONSTRAINT ck_tf_detalles_dispensacion_prescrita;
ALTER TABLE tf_detalles_dispensacion VALIDATE CONSTRAINT ck_tf_detalles_dispensacion_solicitada;
ALTER TABLE tf_detalles_dispensacion VALIDATE CONSTRAINT ck_tf_detalles_dispensacion_precio;
ALTER TABLE tf_detalles_dispensacion VALIDATE CONSTRAINT ck_tf_detalles_dispensacion_subtotal;

CREATE UNIQUE INDEX IF NOT EXISTS uq_tf_detalles_dispensacion_prescripcion
    ON tf_detalles_dispensacion (id_dispensacion, id_prescripcion_externa)
    WHERE id_prescripcion_externa IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_tf_detalles_dispensacion_producto
    ON tf_detalles_dispensacion (id_producto);
CREATE INDEX IF NOT EXISTS idx_tf_detalles_dispensacion_prescripcion
    ON tf_detalles_dispensacion (id_prescripcion_externa);

CREATE TABLE IF NOT EXISTS tf_reservas_dispensacion (
    id_reserva integer GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    id_detalle_dispensacion integer NOT NULL,
    id_lote integer NOT NULL,
    cantidad numeric(14,2) NOT NULL,
    estado varchar(20) NOT NULL DEFAULT 'ACTIVA',
    fecha_reserva timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_liberacion timestamptz,
    CONSTRAINT fk_tf_reservas_detalle
        FOREIGN KEY (id_detalle_dispensacion)
        REFERENCES tf_detalles_dispensacion(id_detalle_dispensacion)
        ON DELETE RESTRICT DEFERRABLE INITIALLY IMMEDIATE,
    CONSTRAINT fk_tf_reservas_lote
        FOREIGN KEY (id_lote) REFERENCES tf_lotes(id_lote)
        ON DELETE RESTRICT DEFERRABLE INITIALLY IMMEDIATE,
    CONSTRAINT ck_tf_reservas_cantidad CHECK (cantidad > 0),
    CONSTRAINT ck_tf_reservas_estado CHECK (estado IN ('ACTIVA', 'CONSUMIDA', 'LIBERADA')),
    CONSTRAINT ck_tf_reservas_liberacion CHECK (
        (estado = 'ACTIVA' AND fecha_liberacion IS NULL)
        OR (estado IN ('CONSUMIDA', 'LIBERADA') AND fecha_liberacion IS NOT NULL)
    )
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_tf_reservas_dispensacion_activa
    ON tf_reservas_dispensacion (id_detalle_dispensacion, id_lote)
    WHERE estado = 'ACTIVA';
CREATE INDEX IF NOT EXISTS idx_tf_reservas_lote_estado
    ON tf_reservas_dispensacion (id_lote, estado);
CREATE INDEX IF NOT EXISTS idx_tf_reservas_detalle
    ON tf_reservas_dispensacion (id_detalle_dispensacion);

CREATE OR REPLACE FUNCTION farmacia_validar_reserva_producto()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM tf_detalles_dispensacion dd
        JOIN tf_lotes l ON l.id_lote = NEW.id_lote
        WHERE dd.id_detalle_dispensacion = NEW.id_detalle_dispensacion
          AND dd.id_producto = l.id_producto
    ) THEN
        RAISE EXCEPTION 'El lote % no pertenece al producto del detalle %',
            NEW.id_lote, NEW.id_detalle_dispensacion;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_tf_reservas_validar_producto ON tf_reservas_dispensacion;
CREATE TRIGGER trg_tf_reservas_validar_producto
BEFORE INSERT OR UPDATE OF id_detalle_dispensacion, id_lote
ON tf_reservas_dispensacion
FOR EACH ROW EXECUTE FUNCTION farmacia_validar_reserva_producto();

-- La base protege el total incluso si un proceso distinto al backend actualiza
-- los detalles. La aplicación sigue calculándolo para responder inmediatamente.
CREATE OR REPLACE FUNCTION farmacia_recalcular_total_dispensacion()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    v_id integer;
BEGIN
    v_id := COALESCE(NEW.id_dispensacion, OLD.id_dispensacion);
    UPDATE tf_dispensaciones
    SET total = COALESCE((
            SELECT round(sum(subtotal), 2)
            FROM tf_detalles_dispensacion
            WHERE id_dispensacion = v_id
        ), 0),
        fecha_actualizacion = CURRENT_TIMESTAMP
    WHERE id_dispensacion = v_id;
    RETURN COALESCE(NEW, OLD);
END;
$$;

DROP TRIGGER IF EXISTS trg_tf_detalles_recalcular_total ON tf_detalles_dispensacion;
CREATE TRIGGER trg_tf_detalles_recalcular_total
AFTER INSERT OR UPDATE OF cantidad_solicitada, precio_unitario, subtotal OR DELETE
ON tf_detalles_dispensacion
FOR EACH ROW EXECUTE FUNCTION farmacia_recalcular_total_dispensacion();

UPDATE tf_dispensaciones d
SET total = COALESCE((
        SELECT round(sum(dd.subtotal), 2)
        FROM tf_detalles_dispensacion dd
        WHERE dd.id_dispensacion = d.id_dispensacion
    ), 0),
    fecha_actualizacion = CURRENT_TIMESTAMP;

COMMENT ON COLUMN tf_productos.precio_venta IS
    'Precio vigente; se copia al detalle al crear/corregir una nota pendiente.';
COMMENT ON TABLE tf_dispensaciones IS
    'Nota de dispensación central: proforma, pago y entrega. Factura/comprobante 1:1.';
COMMENT ON TABLE tf_reservas_dispensacion IS
    'Stock comprometido por lote sin modificar stock_actual hasta la entrega.';

-- Consumo interno: Internación puede enviar producto sin conocer el lote.
-- Farmacia asigna el lote disponible; se conservan lotes históricos.
ALTER TABLE tf_detalles_consumo
    ADD COLUMN IF NOT EXISTS id_producto integer;
ALTER TABLE tf_detalles_consumo
    ALTER COLUMN id_lote DROP NOT NULL;
UPDATE tf_detalles_consumo d
SET id_producto = l.id_producto
FROM tf_lotes l
WHERE d.id_lote = l.id_lote AND d.id_producto IS NULL;
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'tf_detalles_consumo'::regclass
          AND conname = 'ck_tf_detalles_consumo_producto_o_lote'
    ) THEN
        ALTER TABLE tf_detalles_consumo
            ADD CONSTRAINT ck_tf_detalles_consumo_producto_o_lote
            CHECK (id_producto IS NOT NULL OR id_lote IS NOT NULL) NOT VALID;
    END IF;
END $$;
CREATE INDEX IF NOT EXISTS idx_tf_detalles_consumo_producto
    ON tf_detalles_consumo(id_producto);

COMMIT;
