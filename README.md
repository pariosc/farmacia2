# Farmacia e inventario

Módulo de farmacia hospitalaria con dispensación por receta o venta directa sin receta, reserva temporal de stock y flujo de cobro antes de la entrega.

## Instalación rápida

1. Copiar `.env.example` a `.env` y completar únicamente los valores del entorno.
2. Respaldar la base de datos.
3. Para una BD original sin nuestras modificaciones, ejecutar el SQL único `migrations/FARMACIA_ACTUALIZACION_DESDE_ORIGINAL.sql`.
4. Iniciar la API:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

La documentación queda disponible en `/docs`. Las integraciones con Atención, Cobros y Seguridad se configuran mediante variables `INTEGRACION_*`/`URL_MODULO_ATENCION`; sus contratos están documentados en `docs/CONTRATOS_INTEGRACION.md`.

## Verificación y pruebas

Los scripts `migrations/006_dispensacion_integrada_verificar.sql` y `scripts/auditoria_pre_006_dispensacion.sql` son auxiliares para soporte; no sustituyen la migración principal. Para ejecutar las pruebas:

```bash
python -m pytest -q
```

`scripts/mock_atencion_demo.py` es exclusivamente un simulador local para probar la integración; no debe desplegarse como Atención en producción.
