# Entrega al grupo — Catálogo de tipos de producto

## Alcance de esta entrega

Esta entrega modifica únicamente el catálogo de tipos de producto del módulo Farmacia e Inventario.

No modifica:

- estados de compras, dispensaciones, consumos o lotes;
- recetas o prescripciones;
- facturación;
- usuarios o autenticación;
- solicitudes de Internación;
- stock ni movimientos existentes.

La estructura del frontend está contenida en `frontend/templates/` y `frontend/static/`. FastAPI conserva las URLs públicas `/static/...` y las rutas de las páginas; solo cambió la ubicación física de los recursos.

## Resumen del cambio

Se agregó la tabla:

```text
tf_tipos_producto
------------------------
id_tipo_producto
codigo
nombre
descripcion
activo
```

Catálogo inicial:

```text
MEDICAMENTO
INSUMO_MEDICO
DISPOSITIVO_MEDICO
REACTIVO
OTRO
```

Se agregó a `tf_productos`:

```text
id_tipo_producto
```

La columna anterior `tipo_producto` no se elimina. Se conserva temporalmente para que las versiones anteriores del backend continúen funcionando mientras todos los grupos migran.

## Estado en la base de referencia

La migración ya fue aplicada y verificada en la base de referencia `bd_hospital` el 27/08/2026. El verificador reportó:

```text
tipos iniciales = 5
productos_sin_tipo = 0
productos_con_tipo_inconsistente = 0
```

Cada grupo debe ejecutar igualmente la auditoría, respaldo, migración y verificación sobre su propia base. No se debe asumir que las siete copias contienen exactamente los mismos valores históricos.

## Archivos de base de datos

- `migrations/001_catalogo_tipos_producto.sql`: migración principal.
- `migrations/001_catalogo_tipos_producto_verificar.sql`: verificación de solo lectura.
- `migrations/001_catalogo_tipos_producto_rollback.sql`: reversión controlada.
- `scripts/auditoria_pre_migracion_farmacia.sql`: auditoría previa de solo lectura.

## Orden obligatorio de despliegue

```text
1. Respaldar la base
2. Ejecutar auditoría previa
3. Revisar tipos desconocidos
4. Aplicar migración 001
5. Ejecutar verificación
6. Desplegar backend actualizado
7. Probar Productos y tipos
```

No desplegar primero el backend actualizado sobre una base que todavía no tenga `tf_tipos_producto`.

## 1. Respaldo

Ejemplo si PostgreSQL está en el contenedor del proyecto:

```bash
docker exec tecnologia_web_db \
  pg_dump -U postgres -d bd_hospital -Fc \
  -f /tmp/bd_hospital_pre_tipo_producto.dump
```

Verificar el respaldo:

```bash
docker exec tecnologia_web_db \
  sh -lc 'ls -lh /tmp/bd_hospital_pre_tipo_producto.dump && sha256sum /tmp/bd_hospital_pre_tipo_producto.dump'
```

Cada grupo debe reemplazar contenedor, usuario y base por sus propios valores.

## 2. Auditoría previa

```bash
docker exec -i tecnologia_web_db \
  psql -U postgres -d bd_hospital -P pager=off -f - \
  < scripts/auditoria_pre_migracion_farmacia.sql
```

Antes de migrar, revisar especialmente:

```sql
SELECT tipo_producto, count(*)
FROM tf_productos
GROUP BY tipo_producto;
```

La migración reconoce:

```text
MEDICAMENTO
INSUMO
INSUMO_MEDICO
DISPOSITIVO
DISPOSITIVO_MEDICO
REACTIVO
OTRO
```

Si aparece otro valor, la migración se detendrá. No cambiarlo automáticamente a `OTRO`; primero se debe acordar su equivalencia.

## 3. Aplicar migración

```bash
docker exec -i tecnologia_web_db \
  psql -U postgres -d bd_hospital -P pager=off -f - \
  < migrations/001_catalogo_tipos_producto.sql
```

El script:

- usa una transacción;
- se detiene ante cualquier error;
- evita ejecuciones simultáneas;
- puede ejecutarse nuevamente sin duplicar la estructura;
- crea cinco tipos iniciales;
- relaciona productos existentes;
- agrega clave foránea e índice;
- conserva el texto anterior;
- agrega sincronización temporal entre ambas columnas.

Resultado esperado:

```text
COMMIT
```

## 4. Verificar migración

```bash
docker exec -i tecnologia_web_db \
  psql -U postgres -d bd_hospital -P pager=off -f - \
  < migrations/001_catalogo_tipos_producto_verificar.sql
```

Los resultados obligatorios son:

```text
productos_sin_tipo = 0
productos_con_tipo_inconsistente = 0
```

También deben aparecer:

- cinco tipos iniciales;
- clave foránea `fk_tf_productos_tipo_producto`;
- trigger `trg_tf_productos_sincronizar_tipo` para INSERT y UPDATE.

## 5. Cambios del backend

Archivos nuevos:

```text
entidades/farmacia_tipo_producto.py
modelo/m_tipo_producto.py
routers/r_tipo_producto.py
```

Archivos modificados:

```text
entidades/farmacia_catalogo.py
modelo/m_producto.py
routers/r_producto.py
main.py
```

### Endpoints agregados

```text
GET  /tipo-producto/
GET  /tipo-producto/?solo_activos=true
GET  /tipo-producto/{id_tipo_producto}
POST /tipo-producto/
PUT  /tipo-producto/{id_tipo_producto}
```

No se agregó `DELETE`. Los tipos se desactivan con `activo=false` para conservar productos e historial.

### Crear tipo

```json
{
  "codigo": "MATERIAL_CURACION",
  "nombre": "Material de curación",
  "descripcion": "Material utilizado en curaciones",
  "activo": true
}
```

Los códigos se normalizan a mayúsculas. Código o nombre duplicado devuelve HTTP 409.

No se permite cambiar el código de un tipo que ya esté siendo utilizado por productos. Sí pueden modificarse nombre, descripción y estado activo.

### Productos

Durante la transición se aceptan los tres formatos siguientes.

Formato anterior:

```json
{
  "tipo_producto": "MEDICAMENTO"
}
```

Formato nuevo:

```json
{
  "id_tipo_producto": 1
}
```

Formato explícito:

```json
{
  "id_tipo_producto": 1,
  "tipo_producto": "MEDICAMENTO"
}
```

Si se envían ambos deben corresponder al mismo tipo.

Las respuestas de Productos ahora incluyen:

```json
{
  "id_tipo_producto": 1,
  "tipo_producto": "MEDICAMENTO",
  "codigo_tipo_producto": "MEDICAMENTO",
  "nombre_tipo_producto": "Medicamento"
}
```

## 6. Pruebas mínimas

Con el backend iniciado:

```bash
curl -sS http://127.0.0.1:8010/tipo-producto/
curl -sS 'http://127.0.0.1:8010/tipo-producto/?solo_activos=true'
curl -sS http://127.0.0.1:8010/producto-farmacia/
```

Verificar además:

- crear un tipo temporal en una base de ensayo;
- editar nombre y descripción;
- desactivar el tipo;
- crear producto con el formato anterior;
- crear producto con `id_tipo_producto`;
- rechazar un ID inexistente;
- rechazar tipo textual e ID incompatibles;
- Productos, Compras e Inventario siguen cargando.

No crear datos temporales en la base compartida si después no pueden eliminarse con seguridad.

## Estados pendientes y confirmación

La migración adicional `migrations/002_operaciones_pendientes_y_validaciones.sql` ya fue probada en una copia y aplicada en `bd_hospital`.

Su reversión controlada está en `migrations/002_operaciones_pendientes_y_validaciones_rollback.sql`. El rollback solo retira las restricciones; no revierte operaciones ya confirmadas ni repone stock.

- Dispensaciones nuevas quedan `PENDIENTE` y no descuentan stock.
- Se confirman con `PUT /dispensacion/{id_dispensacion}/confirmar`; esa operación valida lote/vencimiento/stock, descuenta y crea `SALIDA`.
- Consumos internos nuevos quedan `PENDIENTE` y se confirman con `PUT /consumo-interno/{id_consumo}/confirmar`.
- Las cantidades nuevas deben ser mayores que cero.
- Las restricciones se instalaron `NOT VALID` para no alterar ni bloquear registros históricos. No ejecutar `VALIDATE CONSTRAINT` hasta auditar esos históricos.
- No se habilitó anulación de operaciones confirmadas porque aún no repone stock ni registra movimiento inverso.

### Arranque del backend

Después de migrar la base e instalar las dependencias habituales del proyecto:

```bash
FARMACIA_USUARIO_ID=1 .venv/bin/uvicorn main:app --host 127.0.0.1 --port 8010
```

La documentación interactiva queda disponible en:

```text
http://127.0.0.1:8010/docs
```

Si el equipo utiliza otro usuario operativo, debe cambiar `FARMACIA_USUARIO_ID`. Esta variable sigue siendo una solución temporal y no reemplaza autenticación.

## 7. Rollback

Solo usar si el despliegue debe revertirse antes de que otros módulos empiecen a depender de `tf_tipos_producto`:

```bash
docker exec -i tecnologia_web_db \
  psql -U postgres -d bd_hospital -P pager=off -f - \
  < migrations/001_catalogo_tipos_producto_rollback.sql
```

El rollback conserva `tf_productos.tipo_producto`, por lo que no pierde la clasificación anterior.

No ejecutar el rollback si otra tabla o backend ya depende formalmente del catálogo nuevo sin revisar primero su impacto.

## 8. Elementos deliberadamente pendientes (actualizado)

Resueltos en entregas posteriores a esta migración:

- ✅ estados pendientes de dispensación y consumo interno (migración 002/004);
- ✅ confirmación transaccional de entregas (`confirmar()` en `m_dispensacion.py` / `m_consumo_interno.py`);
- ✅ anulación con devolución de stock cuando el estado ya era ENTREGADA/REGISTRADO;
- ✅ validación de lotes vencidos al confirmar;
- ✅ recetas eliminadas de dispensación (migración 004 — la prescripción es manual/física);
- ✅ consumo interno conectado a `ti_prescripciones` (Internación) como origen alternativo a `id_solicitud_insumo` (migración 003 + 005, columnas nullable con CHECK de "al menos una").

Siguen pendientes:

- cantidades negativas o duplicadas en el mismo detalle (falta un `UNIQUE`/validación por `id_lote` repetido dentro de una misma dispensación/consumo);
- autenticación real (sigue usando `FARMACIA_USUARIO_ID` como solución temporal);
- pagos o solicitudes externas con FK real (siguen siendo enteros sin validar contra Facturación/Atención hasta que esos módulos expongan su API);
- retirar `tf_productos.tipo_producto` (columna legada) una vez que **los 7 grupos** confirmen su migración a `id_tipo_producto` — sin fecha límite fijada todavía, coordinar en la próxima reunión de equipo;
- pruebas automatizadas: existe un punto de partida en `tests/test_entidades.py` (validación de entrada), falta cobertura de integración contra base de datos real.

Estos elementos deben implementarse en migraciones y entregas posteriores, no mezclarse con la migración del catálogo.
