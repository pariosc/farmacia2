# Instalación 006: dispensación integrada

Esta entrega agrega precio de venta, nota/proforma, reservas por lote, pago 1:1,
entrega y cumplimiento parcial. Los scripts son compatibles tanto con respaldos
que conservan las columnas de receta de la versión inicial como con bases que ya
aplicaron la migración 004.

`id_paciente_externo` es `varchar(80)` porque Atención usa identificadores
alfanuméricos de trazabilidad como `PAC-2026-00101`.

## Archivos para los demás equipos

- `scripts/auditoria_pre_006_dispensacion.sql`
- `migrations/006_dispensacion_integrada.sql`
- `migrations/006_dispensacion_integrada_verificar.sql`
- `migrations/006_dispensacion_integrada_rollback.sql`
- el código de esta versión

No enviar `.env`, volcados ni credenciales.

## Orden obligatorio

1. Detener temporalmente escrituras de Farmacia y crear un respaldo completo.
2. Ejecutar la auditoría previa y resolver cualquier sección que no devuelva
   cero filas donde así se indica.
3. Ejecutar la migración.
4. Ejecutar la verificación. Debe finalizar con
   `006_dispensacion_integrada verificada correctamente`.
5. Desplegar backend y frontend de la misma versión.
6. Definir precios de venta mayores a cero en Productos.
7. Configurar y probar contratos externos antes de habilitar usuarios.

```bash
psql "$DATABASE_URL" -X -f scripts/auditoria_pre_006_dispensacion.sql
psql "$DATABASE_URL" -X -f migrations/006_dispensacion_integrada.sql
psql "$DATABASE_URL" -X -f migrations/006_dispensacion_integrada_verificar.sql
```

La migración usa una transacción, `ON_ERROR_STOP` y un bloqueo asesor. Si falla,
no debe continuarse con el despliegue del código.

## Configuración

```dotenv
INTEGRACION_ATENCION_URL=http://IP_ATENCION:8000
# Alternativa equivalente aceptada: URL_MODULO_ATENCION=http://IP_ATENCION:8000
INTEGRACION_COBROS_URL=http://IP_COBROS:PUERTO
INTEGRACION_SEGURIDAD_URL=http://IP_SEGURIDAD:PUERTO
INTEGRACION_SOLICITUDES_URL=http://IP_SOLICITUDES:PUERTO
INTEGRACION_TIMEOUT_SEGUNDOS=5
RESERVA_DISPENSACION_MINUTOS=30
```

Solo la ruta de Atención por receta está confirmada. Las demás integraciones
siguen sujetas a `docs/CONTRATOS_INTEGRACION.md`.

## Rollback

El rollback solo es seguro antes de crear notas con el flujo nuevo. Se detiene
si encuentra reservas o referencias externas, para no perder información.

```bash
psql "$DATABASE_URL" -X -f migrations/006_dispensacion_integrada_rollback.sql
```

Después de que existan datos reales, corregir hacia adelante con una nueva
migración; no forzar el rollback.

## Prueba opcional sobre una base desechable

```bash
TEST_DATABASE_URL=postgresql://usuario:clave@host:5432/bd_prueba \
  pytest -q tests/test_dispensacion_integrada_db.py
```

La prueba abre una transacción y revierte precio, reservas, movimientos y stock
al finalizar.
