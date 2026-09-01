# Guía para reunión de integraciones — 2026-09-01

Objetivo: salir de la reunión con contratos verificables, no solo URLs. Probar
cada ruta desde la computadora del módulo consumidor y guardar un ejemplo JSON
real sin datos sensibles.

## 1. Atención

### Rutas que llevamos preparadas

```http
GET /clinica/prescripcion/soap/{numero_receta}
GET /integracion/farmacia/recetas/{id_trazabilidad}
```

Farmacia publica su catálogo para que Atención guarde la referencia correcta:

```http
GET /api/v1/farmacia/productos/catalogo
GET /api/v1/farmacia/productos/catalogo/{id_producto}
```

### Preguntas que deben quedar respondidas

1. ¿La búsqueda por trazabilidad devuelve líneas de una o varias recetas?
2. ¿`id_prescripcion` es global, permanente y nunca se reutiliza?
3. ¿Cuál es el identificador estable de receta: `id_receta` o `numero_receta`?
4. ¿Qué estados existen y cuál equivale exactamente a `FIRMADA`?
5. ¿Cómo se informa que una receta fue anulada, reemplazada o corregida?
6. ¿La versión cambia cuando el médico corrige la receta?
7. ¿`id_producto` se guardará desde el catálogo de Farmacia?
8. ¿Cuál será la ruta idempotente para informar una entrega parcial/completa?
9. ¿Qué autenticación llevará la llamada?
10. ¿Un 404 significa paciente inexistente o paciente sin recetas? Un 500 nunca
    debe interpretarse como lista vacía.

### Campos mínimos por línea

```json
{
  "id_trazabilidad": "PAC-2026-00101",
  "id_receta": 100,
  "numero_receta": "REC-2026-00100",
  "version_receta": 1,
  "estado_receta": "FIRMADA",
  "id_prescripcion": 1,
  "id_producto": 25,
  "medicamento": "Paracetamol 500 mg",
  "cantidad": 10,
  "dosis": "500 mg",
  "indicaciones": "Cada 8 horas por 5 días"
}
```

El nombre es descriptivo. La relación técnica obligatoria es `id_producto`.

### Pruebas durante la reunión

```bash
curl -i http://IP_ATENCION:8000/integracion/farmacia/recetas/PAC-2026-00101
curl -i http://IP_FARMACIA:PUERTO/api/v1/farmacia/productos/catalogo
```

Después de configurar `INTEGRACION_ATENCION_URL` o `URL_MODULO_ATENCION`:

```bash
curl -i http://IP_FARMACIA:PUERTO/dispensacion/paciente/PAC-2026-00101/recetas
```

La última respuesta muestra `integrable: false` y los campos faltantes mientras
el contrato siga incompleto. Eso es esperado y evita relacionar por nombre.

## 2. Cobros

Confirmar autenticación servicio-a-servicio y probar:

```http
GET /api/v1/farmacia/dispensaciones/{id}/cobro
PUT /api/v1/farmacia/dispensaciones/{id}/pago
PUT /api/v1/farmacia/dispensaciones/{id}/anulacion-confirmada
```

Cobros debe conservar y devolver: nota, versión, `id_trazabilidad`, total exacto,
ID único de comprobante y estado `PAGADA`/`ANULADA`. Acordar también una consulta
para que Farmacia corrobore el pago inmediatamente antes de entregar.

## 3. Seguridad

Confirmar ruta, encabezado Bearer y nombres definitivos de roles:

- `FARMACIA_OPERADOR`
- `FARMACIA_ADMIN`
- `FARMACIA_CONSULTA`

Al configurar `INTEGRACION_SEGURIDAD_URL`, Farmacia comienza a exigir token en
las rutas protegidas y toma `id_usuario` de la sesión.

## 4. Consumo interno

Pedir una muestra real de solicitud autorizada con área, solicitante,
`id_producto`, cantidad solicitada, cantidad ya atendida y estado. Acordar ruta
de consulta y notificación idempotente de la entrega.

## Resultado que debemos traer

- IP, puerto y prefijo de cada módulo.
- Autenticación acordada.
- JSON real de éxito, vacío, 404 y error.
- IDs y estados definitivos.
- Persona responsable de cada contrato.
- Fecha para prueba conjunta.
