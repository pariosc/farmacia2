\set ON_ERROR_STOP on

-- Actualización acumulativa y conservadora para una base existente.
-- Ejecutar con psql desde la raíz del proyecto:
--   psql "$DATABASE_URL" -X -f migrations/ACTUALIZAR_FARMACIA_COMPLETO.sql
--
-- Cada migración incluida es idempotente y se ejecuta en su propia transacción.
-- La migración 004 NO se incluye porque elimina columnas históricas; 006 es
-- compatible tanto con bases que las conservan como con bases que no las tienen.

DO $$
BEGIN
    IF to_regclass('public.tf_productos') IS NULL
       OR to_regclass('public.tf_lotes') IS NULL
       OR to_regclass('public.tf_dispensaciones') IS NULL
       OR to_regclass('public.tf_detalles_dispensacion') IS NULL
       OR to_regclass('public.tf_consumos_internos') IS NULL
       OR to_regclass('public.tf_detalles_consumo') IS NULL
       OR to_regclass('public.tf_movimientos_inventario') IS NULL THEN
        RAISE EXCEPTION
            'La base no corresponde al esquema base de Farmacia. No se modificó nada.';
    END IF;
END $$;

-- Cambios aditivos y validaciones históricas de Farmacia.
\ir 001_catalogo_tipos_producto.sql
\ir 002_operaciones_pendientes_y_validaciones.sql
\ir 003_conectar_consumo_prescripciones.sql
\ir 005_permitir_origen_alternativo_consumo.sql
\ir 006_dispensacion_integrada.sql

DO $$
BEGIN
    IF to_regclass('public.tf_reservas_dispensacion') IS NULL THEN
        RAISE EXCEPTION 'La actualización no creó tf_reservas_dispensacion';
    END IF;
    RAISE NOTICE 'Actualización completa de Farmacia finalizada correctamente';
END $$;
