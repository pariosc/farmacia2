# Auditoría de base de datos — Farmacia e Inventario

Fecha: 27/08/2026  
Base auditada: `bd_hospital` (PostgreSQL 17)  
Alcance: solo lectura; no se modificaron esquema ni datos.

> Actualización posterior: se aplicó exclusivamente la migración de catálogo de tipos documentada en `migrations/001_catalogo_tipos_producto.sql`. Los demás hallazgos continúan pendientes y no fueron corregidos durante esa migración.

## Resumen ejecutivo

La estructura propia de Farmacia existe y el stock actual coincide aritméticamente con los nueve movimientos registrados. Sin embargo, todavía no es seguro habilitar completamente Dispensaciones y Consumo interno: faltan contratos y datos externos, las anulaciones no revierten inventario y no hay restricciones de dominio o cantidades en PostgreSQL.

Hallazgos prioritarios:

1. Una compra `ANULADA` conserva una `ENTRADA` de 500 unidades.
2. Una dispensación `ANULADA` conserva una `SALIDA` de 20 unidades.
3. El mismo `id_detalle_solicitud_consumo = 1` fue entregado cuatro veces, totalizando 60 unidades.
4. No existe una tabla real de solicitudes de insumos ni detalles de solicitud.
5. `ts_usuarios`, `td_factura`, `ta_prescripciones` y las demás fuentes externas relevantes están vacías; todos los IDs usados por Farmacia son referencias no verificables.
6. Facturación no posee estado de pago/autorización y su detalle referencia servicios, no productos o prescripciones.
7. Ninguna tabla `tf_` tiene restricciones `CHECK` ni triggers.
8. `tipo_producto` es texto libre y solo contiene un registro `MEDICAMENTO` de prueba.

## Inventario real

| Entidad | Registros |
|---|---:|
| Categorías | 3 |
| Productos | 1 |
| Proveedores | 1 |
| Compras | 2 |
| Detalles de compra | 3 |
| Lotes | 3 |
| Dispensaciones | 1 |
| Detalles de dispensación | 1 |
| Consumos internos | 4 |
| Detalles de consumo | 4 |
| Movimientos | 9 |

Estados encontrados:

- Compras: una `REGISTRADA`, una `ANULADA`.
- Dispensaciones: una `ANULADA`.
- Consumos: cuatro `REGISTRADO`.
- Lotes: tres `DISPONIBLE`.

Tipos encontrados:

- Productos: un `MEDICAMENTO`.

## Integridad que sí se cumple

- No existen cantidades no positivas en detalles actuales.
- No existen costos, stock o mínimos negativos en los datos actuales.
- Los movimientos usan únicamente `ENTRADA`, `SALIDA` y `AJUSTE`.
- Cada movimiento operativo tiene exactamente un origen.
- Los totales de compras coinciden con sus detalles.
- El stock de cada lote coincide con la suma histórica: entradas menos salidas más ajustes.
- No se detectaron lotes con estado incompatible con stock o vencimiento a la fecha de la auditoría.
- Códigos, nombres y números de lote actuales no tienen espacios laterales.

Esto describe los datos actuales, pero no está garantizado por restricciones de base de datos.

## Integraciones externas

### Usuarios

`ts_usuarios` existe, pero está vacía. Por ello son inexistentes:

- 2 referencias desde compras;
- 1 desde dispensaciones;
- 4 desde consumos;
- 9 desde movimientos.

No hay claves foráneas activas hacia usuarios.

### Prescripciones

No existe una cabecera denominada receta. `ta_prescripciones` representa líneas individuales y contiene:

- `id`;
- `medicamento_id`;
- `nombre_medicamento`;
- `cantidad`;
- `historia_soap_id`.

Está vacía y usa `medicamento_id`, no la convención `id_producto`. `tf_dispensaciones.id_receta` no tiene actualmente una relación inequívoca con esta estructura.

### Facturación

`td_factura` y `td_detalle_factura` existen, pero están vacías. No contienen estado pagado, autorizado o anulado. El detalle usa `id_servicio`, por lo que no puede demostrar qué medicamento fue pagado.

La dispensación de prueba referencia una factura inexistente.

### Solicitudes internas

No existen `solicitudes_insumo` ni `detalles_solicitud_consumo`. `ta_procedimiento_insumos` registra insumos ya utilizados en procedimientos y no sustituye una solicitud de Internación.

## Modelo objetivo recomendado

### Tipos de producto

Crear `tf_tipos_producto` porque el catálogo dejó de ser binario y será compartido entre grupos:

```text
id_tipo_producto
codigo
nombre
descripcion
activo
```

No usar el tipo para inferir automáticamente todas las reglas. Propiedades como control de vencimiento, receta o fraccionamiento deben ser explícitas cuando correspondan.

Migración compatible:

1. Crear y sembrar la tabla.
2. Agregar `tf_productos.id_tipo_producto` nullable.
3. Mapear los textos existentes.
4. Agregar y validar la clave foránea.
5. Actualizar backend y frontend para lectura dual durante la transición.
6. Convertir a `NOT NULL` cuando las siete bases estén migradas.
7. Retirar `tipo_producto` en una versión posterior, nunca en el primer despliegue.

El catálogo inicial debe aprobarse con Farmacia/Laboratorio antes de escribir la migración definitiva.

### Dispensaciones

Estados objetivo iniciales:

```text
PENDIENTE
ENTREGADA
PARCIAL
ANULADA
```

Reglas:

- Crear `PENDIENTE` no descuenta stock ni crea detalles entregados o movimientos.
- Confirmar una entrega bloquea los lotes, valida stock/vencimiento y crea detalles, `SALIDA` y estado final en una transacción.
- `PARCIAL` requiere calcular cantidades prescritas, autorizadas y previamente entregadas.
- Anular una operación con salida debe reponer stock y crear movimientos inversos; no basta con cambiar el estado.

No se recomienda guardar `cantidad_entregada = 0` como preparación pendiente.

### Consumo interno

`PENDIENTE` debe pertenecer a la solicitud externa, no a `tf_consumos_internos`. Propuesta para el equipo propietario:

```text
Solicitud: PENDIENTE, APROBADA, PARCIAL, ATENDIDA, RECHAZADA, ANULADA
Detalle: cantidad_solicitada, cantidad_aprobada
```

La cantidad entregada debe obtenerse de los consumos efectivos o actualizarse dentro de la misma transacción coordinada. `tf_consumos_internos` debe crearse cuando existe salida física.

### Reversiones

Para conservar trazabilidad se recomienda agregar a movimientos una referencia opcional al movimiento revertido, por ejemplo `id_movimiento_origen`, con una restricción que impida revertir dos veces el mismo movimiento. La reversión mantiene los tipos actuales:

- anular compra: `SALIDA` compensatoria;
- anular dispensación/consumo: `ENTRADA` compensatoria.

No borrar movimientos históricos.

## Restricciones necesarias

Después de limpiar y verificar cada base:

- estados válidos por entidad;
- `stock_minimo >= 0`;
- `stock_actual >= 0`;
- cantidades de compra, dispensación y consumo `> 0`;
- costo unitario `>= 0`;
- subtotal y total `>= 0`;
- tipos de movimiento válidos;
- coherencia entre tipo de movimiento y columna de origen;
- unicidad controlada por operación, detalle externo y lote;
- claves foráneas externas solo cuando los equipos propietarios unifiquen nombres y datos.

## Plan de migraciones para siete grupos

### Fase 0 — Contratos

- Aprobar catálogo de tipos.
- Definir quién es propietario de receta, autorización de pago y solicitud interna.
- Definir estados y transiciones.
- Acordar IDs y endpoints entre módulos.

### Fase 1 — Diagnóstico idéntico

Cada grupo ejecuta `scripts/auditoria_pre_migracion_farmacia.sql` y entrega el resultado. No se migra una base con valores desconocidos.

### Fase 2 — Cambios aditivos

- Crear catálogo de tipos.
- Agregar nuevas columnas nullable.
- Agregar índices necesarios.
- Agregar constraints como `NOT VALID` cuando corresponda.
- No borrar ni renombrar columnas existentes.

### Fase 3 — Backend compatible

- Lectura dual del tipo viejo/nuevo.
- Validadores Pydantic.
- Operaciones pendientes y confirmación transaccional.
- Reversiones seguras.
- Errores HTTP de integridad controlados.

### Fase 4 — Migración de datos

- Mapear tipos conocidos.
- Detenerse ante valores desconocidos.
- Validar constraints.
- Conciliar stock y movimientos.

### Fase 5 — Cierre

- Convertir columnas requeridas a `NOT NULL`.
- Retirar compatibilidad antigua solo cuando los siete grupos confirmen versión.
- Eliminar columnas obsoletas en una migración separada y con rollback probado.

## Reglas operativas para los scripts

- Un archivo versionado por migración.
- `BEGIN`/`COMMIT` y `ON_ERROR_STOP`.
- Precondiciones que aborten ante datos incompatibles.
- Idempotencia mediante consultas a catálogos del sistema.
- Script de verificación posterior.
- Rollback cuando sea técnicamente seguro.
- Copia de seguridad y ensayo sobre clon antes de producción.
- Registro por grupo: versión, fecha, responsable, checksum y resultado.
- Nunca editar manualmente las siete bases.

## Decisiones pendientes antes de escribir migraciones DDL

1. Catálogo definitivo de tipos de producto.
2. Identificador real de la receta o agrupación de prescripciones.
3. Forma de vincular factura/autorización con medicamentos.
4. Tabla y propietario de solicitudes internas.
5. Si una dispensación pendiente necesita persistir una preparación o solo cabecera.
6. Política exacta para anular entregas parciales.
7. Estrategia de usuario mientras Seguridad integra autenticación.
