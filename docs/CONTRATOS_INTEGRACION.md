# Contratos de integración de Farmacia

Este documento identifica los datos que Farmacia necesita de los demás
módulos. Las rutas marcadas como **pendientes** son contratos propuestos, no
APIs existentes. No definir una URL en `.env` hasta validar el JSON real y
agregar pruebas. Configurar Seguridad activa token y roles en rutas protegidas.

## Reglas comunes

- Cada módulo conserva la propiedad de sus entidades. Farmacia no modifica
  directamente usuarios, recetas, facturas o solicitudes externas.
- Los IDs deben ser estables. Nunca relacionar productos o pacientes por el
  nombre visible.
- Las operaciones que cambian estado deben ser idempotentes.
- Errores de red no autorizan entregas, pagos ni salidas de inventario.
- No registrar tokens, contraseñas ni datos clínicos completos en logs.
- Las URLs se configuran en `.env`; las rutas y adaptadores deben quedar
  centralizados, no repartidos entre los routers.

## 1. Seguridad y roles

Propietario: módulo de Seguridad.

### Login visual temporal confirmado

Seguridad comunicó la ruta:

```http
POST http://26.154.63.158:8000/login/
Content-Type: application/json
```

con el cuerpo `{"usuario": "nombre_usuario", "clave": "contraseña"}`. La
respuesta actual de éxito solo incluye `usuario`; un fallo de credenciales
responde HTTP 401. Farmacia puede usarla para validar el formulario y mostrar
el nombre, pero no como sesión ni autorización: no existe token, `id_usuario`,
vigencia o rol verificable. La URL temporal se configura mediante
`SEGURIDAD_LOGIN_URL` y no activa las dependencias Bearer del backend.

El navegador conserva temporalmente `{id_usuario, username, role}` en
`localStorage`; `id_usuario` queda nulo con la respuesta actual. Si Seguridad
lo incorpora, Dispensaciones y Consumo interno lo asignan visualmente como
responsable y bloquean el campo; esto sigue siendo modificable y nunca autoriza
operaciones. Falta HTTPS para evitar enviar claves por HTTP. El preflight CORS
desde Farmacia fue aceptado durante la prueba del 02/09/2026.

### Contrato requerido para autorización real

Farmacia necesita validar el token recibido y obtener como mínimo:

```json
{
  "id_usuario": 12,
  "username": "operador.farmacia",
  "activo": true,
  "roles": ["FARMACIA_OPERADOR"]
}
```

Contrato requerido (ruta definitiva pendiente):

```http
GET /seguridad/sesion
Authorization: Bearer <token>
```

Roles propuestos, sujetos a confirmación del equipo de Seguridad:

- `FARMACIA_OPERADOR`: prepara y confirma dispensaciones/consumos.
- `FARMACIA_ADMIN`: catálogos, precios y correcciones administrativas.
- `FARMACIA_CONSULTA`: inventario, kardex y reportes sin escritura.

El backend obtiene `id_usuario` de la sesión cuando la URL está configurada y
deja de confiar en el valor del navegador. Sin URL conserva el modo transitorio.

Variable: `INTEGRACION_SEGURIDAD_URL`.

## 2. Atención: recetas ambulatorias

Propietario: módulo de Atención.

Ruta informada por ese equipo:

```http
GET /clinica/prescripcion/soap/{numero_de_receta}
```

Farmacia necesita que la respuesta contenga:

```json
{
  "id_receta": 321,
  "version": 1,
  "estado": "FIRMADA",
  "fecha_emision": "2026-08-31T10:00:00-04:00",
  "paciente": {
    "id_paciente": "PAC-2026-00101",
    "ci": "1234567",
    "nombre_completo": "Paciente de prueba"
  },
  "medico": {
    "id_medico": 8,
    "nombre_completo": "Médico de prueba"
  },
  "detalles": [
    {
      "id_prescripcion": 9001,
      "id_producto": 20,
      "nombre_producto": "Amoxicilina 500 mg",
      "cantidad_prescrita": 10,
      "dosis_instrucciones": "Según indicación médica"
    }
  ]
}
```

`id_producto` debe ser el ID del catálogo de Farmacia. Atención obtiene ese
catálogo mediante:

```http
GET /api/v1/farmacia/productos/catalogo
GET /api/v1/farmacia/productos/catalogo/{id_producto}
```

Atención no debe recibir stock, lotes, costos, precios de venta ni fechas de
vencimiento. Farmacia no modifica medicamento, dosis o instrucciones de la
receta; solo decide una cantidad a dispensar menor o igual a la pendiente.

Para búsqueda por CI/nombre falta que Atención confirme una ruta equivalente
a `GET /clinica/prescripciones?ci=&nombre=&estado=FIRMADA`.

El 31/08/2026 Atención comunicó además esta búsqueda por paciente:

```http
GET /integracion/farmacia/recetas/{id_trazabilidad}
```

Su respuesta actual es una lista plana con `id_prescripcion`, nombre, dosis,
cantidad e indicaciones. Farmacia ya puede consultarla mediante
`GET /dispensacion/paciente/{id_trazabilidad}/recetas`, pero la marca como no
integrable mientras falten `id_producto`, receta y estado firmado. Nunca se
relaciona un producto por el nombre recibido.

Para informar entregas parciales falta confirmar una operación idempotente
que reciba `id_dispensacion`, `id_prescripcion` y `cantidad_entregada`.

Variable: `INTEGRACION_ATENCION_URL`.

## 3. Cobros

Propietario: módulo de Cobros/Facturación.

Farmacia expone una consulta de la orden cobrable:

```http
GET /api/v1/farmacia/dispensaciones/{id_dispensacion}/cobro
```

Respuesta mínima propuesta:

```json
{
  "id_dispensacion": 100,
  "version": 2,
  "estado": "PENDIENTE_PAGO",
  "reserva_hasta": "2026-08-31T11:30:00-04:00",
  "id_paciente": "PAC-2026-00101",
  "total": "125.50",
  "cobrable": true
}
```

Después de cobrar, Farmacia tiene preparado este callback idempotente (falta
acordar autenticación servicio-a-servicio con Cobros):

```http
PUT /api/v1/farmacia/dispensaciones/{id_dispensacion}/pago
```

```json
{
  "id_factura": 500,
  "id_paciente": "PAC-2026-00101",
  "total": "125.50",
  "version": 2,
  "estado": "PAGADA"
}
```

Farmacia corrobora:

- mismo paciente, total y versión;
- reserva vigente;
- comprobante pagado y no anulado;
- relación 1:1 entre comprobante y dispensación.

Farmacia registra la solicitud de anulación de una nota pagada y conserva la
reserva. Cobros puede confirmarla mediante:

```http
PUT /api/v1/farmacia/dispensaciones/{id_dispensacion}/anulacion-confirmada
```

Una dispensación `PAGADA` nunca libera su reserva ni se anula localmente sin
esa confirmación. Falta la ruta saliente para enviar la solicitud a Cobros.

La tabla actual `td_factura` no tiene estado de pago/anulación; por ello no es
un contrato suficiente todavía.

Variable: `INTEGRACION_COBROS_URL`.

## 4. Consumo interno

Propietario del origen: Internación o el módulo que emite la solicitud.

Farmacia necesita consultar la cabecera y los detalles autorizados de una
solicitud/prescripción interna. Rutas definitivas pendientes:

```http
GET /solicitudes-insumo/{id_solicitud}
GET /solicitudes-insumo/{id_solicitud}/detalles
```

La respuesta debe identificar área, solicitante, estado autorizado y líneas
con `id_detalle`, `id_producto`, cantidad solicitada/aprobada y cantidad ya
atendida. Farmacia no debe aceptar IDs manuales sin corroborar este origen.

Después de confirmar la salida, se necesita una notificación idempotente con
las cantidades realmente entregadas. Stock, lotes y movimientos continúan
siendo propiedad exclusiva de Farmacia.

Variable: `INTEGRACION_SOLICITUDES_URL`.

## Dónde adaptar cuando lleguen las APIs

- Configuración: `configuracion/parametro.py` y `.env`.
- Cliente HTTP y manejo común de errores: `configuracion/integracion.py`.
- Receta por SOAP confirmada: `modelo/m_integracion_atencion.py`. Este
  adaptador todavía no es invocado por Dispensación.
- Seguridad: dependencia común de autenticación; no repetirla en cada router.
- Recetas y Cobros: adaptadores dedicados dentro de `modelo/`, llamados desde
  la futura lógica transaccional de Dispensación.
- Solicitudes: adaptador dentro de `modelo/`, llamado antes de crear/confirmar
  Consumo interno.
- Catálogo saliente: `routers/r_catalogo_integracion.py` y
  `modelo/m_catalogo_integracion.py`.

No pegar lógica HTTP directamente en SQL ni dentro de bucles de detalles.
