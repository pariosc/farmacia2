# Plan de Dispensación integrada

Estado: modelo local implementado y migración 006 probada sobre un clon. No
aplicar en la base compartida sin respaldo y aprobación del equipo. Las
integraciones pendientes continúan señaladas con contratos y comentarios TODO.

## Decisiones acordadas

- Dispensación es el proceso central. No se crea una tabla independiente de NV.
- Antes de la entrega, la dispensación funciona como orden/proforma para Cobros.
- El documento visible se denomina **Nota de dispensación** y usa el ID de la
  dispensación como referencia estable.
- El precio de venta vigente se define manualmente en Productos.
- Cada detalle conserva una copia histórica de precio unitario y subtotal.
- Se permiten entregas parciales de una receta mediante varias dispensaciones.
- Se permiten ventas directas sin receta para productos OTC
  (`requiere_receta=false`), con la misma nota, reserva, cobro y entrega.
- Atención conserva la receta original; Farmacia nunca modifica sus tablas.
- Farmacia reserva stock antes del pago y solo descuenta stock al entregar.
- Cada dispensación se relaciona 1:1 con un comprobante de Cobros.

## Flujo objetivo

1. El operador autenticado busca una receta firmada por número; la búsqueda por
   CI/nombre se habilita cuando Atención publique su ruta.
2. Farmacia carga líneas con IDs del catálogo propio y calcula la cantidad
   pendiente de cada prescripción.
3. El operador elige una cantidad menor o igual a la pendiente. No cambia el
   medicamento, dosis ni instrucciones clínicas.
4. En una transacción, Farmacia congela precios, asigna lotes por FEFO y crea
   reservas temporales sin modificar `stock_actual`.
5. La dispensación queda `PENDIENTE_PAGO` y Cobros consulta su versión, paciente,
   vigencia y total.
6. Cobros registra el pago y vincula un comprobante único. Farmacia cambia la
   orden a `PAGADA`; sus precios y cantidades quedan inmutables.
7. Farmacia corrobora el pago, confirma la entrega, consume las reservas,
   descuenta lotes y registra movimientos `SALIDA` en una transacción.
8. La dispensación queda `ENTREGADA` y se notifica idempotentemente la entrega
   parcial/completa al módulo de Atención.

Para una venta directa se omiten receta y notificación a Atención; el endpoint
`POST /dispensacion/venta-directa` valida que cada producto sea OTC y conserva
el resto del flujo.

## Cantidades parciales

Una receta puede originar varias dispensaciones. La cantidad máxima disponible
para una nueva orden es:

```text
pendiente = prescrita
          - entregada en dispensaciones ENTREGADA
          - comprometida en reservas activas PENDIENTE_PAGO/PAGADA
```

Una dispensación entrega por completo la cantidad elegida en esa orden. El
estado parcial/completo pertenece al cumplimiento de la receta, no requiere un
estado `PARCIAL` dentro de cada dispensación.

## Estados y acciones

| Estado | Editar | Anular | Inventario |
|---|---|---|---|
| `PENDIENTE_PAGO` | Sí; recalcula versión y reservas | Sí; libera reservas | Reservado |
| `PAGADA` | No | Solo coordinando con Cobros | Reservado sin vencimiento |
| `ENTREGADA` | No | No; usar futura devolución | Stock descontado |
| `VENCIDA` | No | No necesario | Reserva liberada |
| `ANULACION_SOLICITADA` | No | Espera confirmación de Cobros | Reserva conservada |
| `ANULADA` | No | Ya anulada | Reserva liberada |

La duración propuesta de una reserva sin pago es 30 minutos y debe ser
configurable. Este valor todavía necesita confirmación operativa.

## Edición/anulación desde el modal

El modal de detalle mostrará acciones según estado:

- `PENDIENTE_PAGO`: **Editar** y **Anular**.
- `PAGADA`: **Solicitar anulación a Cobros**.
- `ENTREGADA`, `VENCIDA`, `ANULADA`: solo consulta.

Editar una orden pendiente libera sus reservas anteriores y crea nuevas
reservas en la misma transacción. Si no hay stock, toda la corrección falla y
se conserva la preparación anterior.

## Integraciones

### Seguridad

- Valida token, cuenta activa y roles.
- Proporciona `id_usuario`; el navegador deja de enviarlo manualmente.
- Roles propuestos: operador, administrador y consulta de Farmacia.

### Atención

- Consume el catálogo publicado por Farmacia.
- Ruta confirmada: `GET /clinica/prescripcion/soap/{numero_de_receta}`.
- Pendiente: JSON real, búsqueda por paciente y notificación idempotente de
  cantidades entregadas.

### Cobros

- Consulta una orden cobrable por `id_dispensacion` y `version`.
- Debe rechazar órdenes vencidas/no cobrables.
- Informa comprobante pagado y confirma anulaciones.
- Pendiente: estado real del comprobante, rutas y estrategia idempotente.

### Internación/Solicitudes

- Proporciona solicitudes/prescripciones internas autorizadas.
- Recibe cantidades confirmadas de Consumo interno.
- Pendiente: rutas, JSON, estados y definición del propietario de solicitud.

Los JSON esperados están en `docs/CONTRATOS_INTEGRACION.md`.

## Modelo de datos implementado en la migración 006

Cambios aditivos, preservando datos históricos:

### `tf_productos`

- `precio_venta numeric(12,2)` con restricción no negativa.

### `tf_dispensaciones`

- referencia estable de receta externa/historia SOAP;
- referencia canónica de paciente;
- `version` para evitar cobrar una edición antigua;
- `total`, `reserva_hasta`, fechas de creación/actualización;
- `id_factura` nullable y único;
- motivo de anulación;
- restricción de estados objetivo.

### `tf_detalles_dispensacion`

- referencia estable de la línea externa `ta_prescripciones.id`;
- `id_producto` del catálogo;
- cantidad prescrita como instantánea;
- cantidad elegida para esta dispensación;
- precio unitario y subtotal congelados.

Los campos legados se conservarán durante la transición. No reutilizar
`cantidad_entregada` para representar una reserva si todavía no hubo entrega.

### `tf_reservas_dispensacion` (nueva)

- detalle de dispensación;
- lote;
- cantidad reservada;
- estado `ACTIVA`, `CONSUMIDA` o `LIBERADA`;
- fecha de vencimiento y liberación;
- restricciones para impedir reservas no positivas o duplicadas.

Una línea puede repartirse entre varios lotes. El stock disponible será
`stock_actual - reservas_activas`.

## Artefactos de migración

No se reescribieron migraciones históricas. La migración 006 es compatible con
bases que conserven o hayan eliminado columnas de receta.

1. `scripts/auditoria_pre_006_dispensacion.sql`.
2. `migrations/006_dispensacion_integrada.sql`.
3. `migrations/006_dispensacion_integrada_verificar.sql`.
4. `migrations/006_dispensacion_integrada_rollback.sql`.
5. `docs/INSTALACION_006_DISPENSACION.md`.

## Orden de implementación

1. Catálogo y cliente HTTP común — completado.
2. Migración, verificación y rollback — completados y probados en clon.
3. Precio, reservas FEFO, parciales, pago y entrega — completados localmente.
4. Formulario por receta y modal con acciones por estado — completados.
5. Recibir y probar JSON real de Atención.
6. Recibir autenticación/rutas definitivas de Seguridad, Cobros y Solicitudes.
7. Ejecutar pruebas entre módulos y de concurrencia con sus equipos.
8. Aplicar en la base compartida solo con respaldo y aprobación.

## Bloqueos actuales

- Respuesta JSON real de la receta por SOAP. La búsqueda por trazabilidad ya fue
  comunicada, pero todavía carece de producto, receta y estado firmado.
- Identificador canónico de paciente compartido por Atención y Cobros.
- Rutas y estados reales de comprobantes de Cobros.
- Endpoint de búsqueda de recetas por CI/nombre.
- Endpoint idempotente para informar entregas a Atención.
- Contrato de solicitudes/prescripciones de Consumo interno.
- Nombres definitivos de roles y formato del token de Seguridad.
