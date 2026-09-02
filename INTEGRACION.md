# Guía de integración — Farmacia

## Objetivo

Cada módulo conserva sus datos. Farmacia administra productos, lotes, reservas,
precios y movimientos; no modifica directamente recetas, pacientes, facturas,
usuarios ni solicitudes externas.

## Configuración

Copiar `.env.example` a `.env` y completar las URLs confirmadas:

```dotenv
INTEGRACION_ATENCION_URL=http://IP_ATENCION:8000
INTEGRACION_COBROS_URL=http://IP_COBROS:8000
INTEGRACION_SEGURIDAD_URL=http://IP_SEGURIDAD:8000
INTEGRACION_SOLICITUDES_URL=http://IP_INTERNACION:8000
INTEGRACION_TIMEOUT_SEGUNDOS=5
RESERVA_DISPENSACION_MINUTOS=240
```

No subir `.env`, tokens, contraseñas ni volcados. Antes de conectar cada equipo
debe confirmar URL, método, parámetros, JSON, estados, errores, autenticación e
idempotencia.

## Atención: recetas

```http
GET /clinica/prescripcion/soap/{numero_de_receta}
GET /integracion/farmacia/recetas/{id_trazabilidad}
```

Para dispensar, Atención debe devolver receta, versión, estado `FIRMADA`,
identificador de paciente y líneas con `id_prescripcion`, `id_producto`,
`cantidad_prescrita` e instrucciones. Nunca relacionar medicamentos por nombre.

Farmacia expone el proxy:

```http
GET /dispensacion/paciente/{id_trazabilidad}/recetas
POST /dispensacion/desde-receta/{numero_receta}
PUT /dispensacion/{id_dispensacion}/corregir
```

Se pueden quitar líneas o entregar cantidades parciales. Solo se añaden líneas
existentes en la receta. Corregir únicamente en `PENDIENTE_PAGO`; después del
pago se solicita anulación.

## Cobros: proforma y pago

```http
GET /api/v1/farmacia/dispensaciones/{id_dispensacion}/cobro
PUT /api/v1/farmacia/dispensaciones/{id_dispensacion}/pago
PUT /api/v1/farmacia/dispensaciones/{id_dispensacion}/anulacion-confirmada
```

La consulta devuelve `id_dispensacion`, `version`, `estado`, `reserva_hasta`,
paciente, `total` como texto decimal y `cobrable`. El pago debe enviar
`id_factura`, paciente, total, versión y estado `PAGADA`. Farmacia valida monto,
paciente, versión, reserva vigente y relación factura-dispensación 1:1.

El operador entrega con:

```http
PUT /dispensacion/{id_dispensacion}/confirmar
```

La anulación pagada requiere primero solicitud y luego confirmación de Cobros.

## Seguridad: sesión y roles

Confirmar una ruta equivalente a:

```http
GET /seguridad/sesion
Authorization: Bearer <token>
```

Debe devolver `id_usuario`, `activo` y `roles`. Roles sugeridos: `FARMACIA_OPERADOR`,
`FARMACIA_ADMIN` y `FARMACIA_CONSULTA`. Con
`INTEGRACION_SEGURIDAD_URL` configurada, Farmacia no confía en el usuario del
navegador.

## Internación: consumo interno

Confirmar las rutas:

```http
GET /solicitudes-insumo/{id_solicitud}
GET /solicitudes-insumo/{id_solicitud}/detalles
```

Cada línea debe incluir `id_detalle`, `id_producto`, cantidad autorizada,
cantidad ya atendida, área y estado. Farmacia registra `PENDIENTE`; al confirmar
valida lotes/vencimiento/stock, descuenta, registra `SALIDA` y notifica cantidades
entregadas idempotentemente. Con la integración activa no aceptar IDs manuales.

## Catálogo para Atención

```http
GET /api/v1/farmacia/productos/catalogo
GET /api/v1/farmacia/productos/catalogo/{id_producto}
```

Atención debe conservar `id_producto`; el catálogo no expone stock, lotes,
costos ni precios internos.

## Prueba de aceptación

1. Receta firmada → nota → reserva.
2. Cobros consulta total → genera comprobante → notifica `PAGADA`.
3. Farmacia confirma entrega → movimiento `SALIDA`.
4. Repetir pago y verificar que no duplica factura ni stock.
5. Probar corrección antes del pago y anulación después del pago.
6. Repetir con solicitud de consumo interno autorizada.

## Dónde adaptar

- URLs: `configuracion/parametro.py` y `.env`.
- Cliente HTTP: `configuracion/integracion.py`.
- Atención: `modelo/m_integracion_atencion.py`.
- Seguridad: `configuracion/seguridad.py`.
- Dispensación/Cobros: `routers/r_dispensacion*.py`.
- Consumo: `modelo/m_consumo_interno.py`.

## Base de datos

Con respaldo previo, si no se conoce qué migraciones tiene la base, ejecutar el
actualizador acumulativo:

```bash
psql "$DATABASE_URL" -X -f migrations/FARMACIA_ACTUALIZACION_DESDE_ORIGINAL.sql
```

Si las migraciones 001–005 ya están confirmadas, basta ejecutar
`migrations/006_dispensacion_integrada.sql`. El actualizador no ejecuta la 004,
porque esa etapa elimina columnas históricas; la 006 es compatible con ambos
escenarios. Todos los scripts se detienen ante errores y requieren respaldo.

## Anexo: endpoints para compartir con los compañeros

### Atención → Farmacia (consumo de Farmacia)

```http
GET {ATENCION_URL}/clinica/prescripcion/soap/{numero_receta}
GET {ATENCION_URL}/integracion/farmacia/recetas/{id_trazabilidad}
```

Respuesta mínima integrable:

```json
{
  "id_receta": 321,
  "version": 1,
  "estado": "FIRMADA",
  "id_paciente": "PAC-2026-00101",
  "detalles": [
    {
      "id_prescripcion": 9001,
      "id_producto": 20,
      "cantidad_prescrita": 10,
      "dosis_instrucciones": "Cada 8 horas"
    }
  ]
}
```

`id_producto` debe ser el identificador entregado por el catálogo de Farmacia.

### Farmacia → Atención (entrega parcial, ruta pendiente)

Solicitar una ruta idempotente equivalente a:

```http
POST {ATENCION_URL}/integracion/farmacia/dispensaciones/entrega
```

```json
{
  "id_dispensacion": 100,
  "id_prescripcion": 9001,
  "cantidad_entregada": 5,
  "fecha_entrega": "2026-08-31T11:40:00-04:00"
}
```

### Farmacia → Cobros (consulta de proforma)

```http
GET {FARMACIA_URL}/api/v1/farmacia/dispensaciones/{id_dispensacion}/cobro
```

```json
{
  "id_dispensacion": 100,
  "version": 1,
  "estado": "PENDIENTE_PAGO",
  "id_paciente": "PAC-2026-00101",
  "total": "125.50",
  "reserva_hasta": "2026-08-31T11:30:00-04:00",
  "cobrable": true
}
```

### Cobros → Farmacia (pago confirmado)

```http
PUT {FARMACIA_URL}/api/v1/farmacia/dispensaciones/{id_dispensacion}/pago
```

```json
{
  "id_factura": 500,
  "id_paciente": "PAC-2026-00101",
  "total": "125.50",
  "version": 1,
  "estado": "PAGADA"
}
```

La repetición del mismo mensaje debe devolver el mismo resultado y nunca crear
otra factura ni descontar stock nuevamente.

### Cobros → Farmacia (anulación confirmada)

```http
PUT {FARMACIA_URL}/api/v1/farmacia/dispensaciones/{id_dispensacion}/anulacion-confirmada
```

```json
{
  "id_factura": 500,
  "version": 1,
  "estado": "ANULADA"
}
```

### Farmacia → Seguridad (validación de sesión)

```http
GET {SEGURIDAD_URL}/seguridad/sesion
Authorization: Bearer <token>
```

```json
{
  "id_usuario": 12,
  "activo": true,
  "roles": ["FARMACIA_OPERADOR"]
}
```

### Farmacia → Internación/Solicitudes (consumo interno)

Solicitar rutas equivalentes a:

```http
GET {SOLICITUDES_URL}/solicitudes-insumo/{id_solicitud}
GET {SOLICITUDES_URL}/solicitudes-insumo/{id_solicitud}/detalles
```

Cada detalle debe incluir `id_detalle`, `id_producto`,
`cantidad_autorizada`, `cantidad_atendida`, `area_solicitante` y `estado`.

### Farmacia → Internación/Solicitudes (entrega confirmada)

Solicitar una operación idempotente equivalente a:

```http
POST {SOLICITUDES_URL}/integracion/farmacia/entregas
```

```json
{
  "id_consumo": 700,
  "id_solicitud": 80,
  "detalles": [
    {"id_detalle": 801, "id_producto": 20, "cantidad_entregada": 5}
  ]
}
```

### Farmacia → Atención (catálogo de productos)

```http
GET {FARMACIA_URL}/api/v1/farmacia/productos/catalogo
GET {FARMACIA_URL}/api/v1/farmacia/productos/catalogo/{id_producto}
```

El catálogo devuelve identificadores y datos descriptivos, pero nunca stock,
lotes, costos ni credenciales.
