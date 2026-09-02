# Farmacia e inventario

Módulo de farmacia hospitalaria con dispensación por receta o venta directa sin receta, reserva temporal de stock y flujo de cobro antes de la entrega.

## Instalación rápida

1. Copiar `.env.example` a `.env` y completar únicamente los valores del entorno.
2. Respaldar la base de datos.
3. Para una BD original sin nuestras modificaciones, ejecutar el SQL único `migrations/FARMACIA_ACTUALIZACION_DESDE_ORIGINAL.sql`.
4. Preparar el entorno virtual:

```bash
uv sync --frozen
```

5. Iniciar la API con `uv`:

```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8010
```

La aplicación queda disponible en `http://localhost:8010` y la documentación en `http://localhost:8010/docs`. Para activar recarga automática durante desarrollo:

```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8010 --reload
```

Las integraciones con Atención, Consumo, Cobros y Seguridad se configuran mediante variables `INTEGRACION_*`/`URL_MODULO_ATENCION`; sus contratos están documentados en `docs/CONTRATOS_INTEGRACION.md`.

## Verificación y pruebas

Los scripts `migrations/006_dispensacion_integrada_verificar.sql` y `scripts/auditoria_pre_006_dispensacion.sql` son auxiliares para soporte; no sustituyen la migración principal. Para ejecutar las pruebas:

```bash
uv run pytest -q
```

`scripts/mock_atencion_demo.py` es exclusivamente un simulador local para probar la integración; no debe desplegarse como Atención en producción.
