# AGENTS.md — Hospital TODO SANO

## Contexto del proyecto

- Sistema: Hospital de Segundo Nivel TODO SANO.
- Módulo actual: Farmacia e Inventario.
- Backend: FastAPI con acceso asíncrono mediante `asyncpg`.
- Base de datos: PostgreSQL.
- Frontend: Jinja2, HTML5, Bootstrap 5, JavaScript vanilla, Fetch API y CSS propio.
- No usar React, Angular, Vue, TypeScript, Tailwind ni otros frameworks frontend, salvo solicitud explícita posterior.
- Mantener una solución sencilla, profesional, mantenible y sin sobreingeniería.

## Objetivo y límites del módulo

Farmacia e Inventario administra productos, categorías, proveedores, compras, lotes, inventario, dispensaciones, consumo interno y movimientos/kardex.

Usuarios, recetas, facturas y solicitudes de insumos pertenecen a otros módulos. No duplicar estas entidades ni crear tablas sustitutas dentro de Farmacia. El catálogo `tf_productos` puede ser consultado por el módulo médico, pero no debe exponerle automáticamente stock, lotes, costos ni vencimientos.

El inventario se controla con `tf_productos`, `tf_lotes` y `tf_movimientos_inventario`. No duplicar stock. Los movimientos válidos son `ENTRADA`, `SALIDA` y `AJUSTE`; compras generan entradas, y dispensaciones y consumos internos generan salidas.

## Persistencia y nomenclatura

Tablas propias principales:

- `tf_categorias_producto`
- `tf_productos`
- `tf_proveedores`
- `tf_compras`
- `tf_detalles_compra`
- `tf_lotes`
- `tf_dispensaciones`
- `tf_detalles_dispensacion`
- `tf_consumos_internos`
- `tf_detalles_consumo`
- `tf_movimientos_inventario`

Usar PostgreSQL `snake_case` y la convención `id_producto`, `id_compra`, `id_lote`, `id_usuario`, etc. Nunca introducir nombres como `producto_id`. No crear tablas o cambiar relaciones sin revisar dependencias e impacto.

## Arquitectura actual

- `main.py`: aplicación FastAPI, registro de routers y vistas Jinja.
- `configuracion/`: configuración por `.env`, pool `asyncpg` y dependencia de conexión.
- `entidades/`: schemas Pydantic de entrada/salida implícita.
- `modelo/`: consultas SQL y lógica transaccional; el proyecto no tiene una capa `servicios/` separada.
- `routers/`: endpoints REST del módulo.
- `frontend/templates/`: plantillas Jinja compartidas.
- `frontend/static/css/app.css`: sistema visual común.
- `frontend/static/js/app.js`: utilidades comunes de UI y Fetch.
- `frontend/static/js/sesion.js` y `frontend/static/js/login.js`: acceso visual temporal contra Seguridad, persistencia no autoritativa del nombre/rol y redirección de páginas; no protegen la API ni sustituyen una sesión backend.
- `frontend/static/vendor/bootstrap/`: distribución local de Bootstrap 5.3.8 (CSS, bundle JS con Popper, mapas y licencia) para que la interfaz no dependa de CDN ni de acceso a Internet.
- `frontend/static/js/productos.js`, `frontend/static/js/proveedores.js`, `frontend/static/js/compras.js`, `frontend/static/js/inventario.js`, `frontend/static/js/dispensaciones.js`, `frontend/static/js/consumos.js` y `frontend/static/js/kardex.js`: comportamiento exclusivo de cada página.
- `docs/CONTRATOS_INTEGRACION.md`: fuente de los contratos pendientes con Seguridad, Atención, Cobros e Internación/Solicitudes. Una URL configurada no habilita por sí sola una integración.
- `docs/PLAN_DISPENSACION_INTEGRADA.md`: decisiones y estado de implementación del flujo receta, precio, reserva, pago 1:1 y entrega parcial.
- `docs/INSTALACION_006_DISPENSACION.md`: orden obligatorio de auditoría, migración, verificación, despliegue y rollback conservador.
- `docs/REUNION_INTEGRACIONES_2026-09-01.md`: preguntas, JSON mínimo y pruebas preparadas para cerrar contratos con los otros módulos.
- `configuracion/integracion.py`: cliente HTTP común y normalización de errores externos; no contiene reglas de negocio.
- `modelo/m_integracion_atencion.py`: adaptador de la ruta confirmada por SOAP. El normalizador exige el contrato documentado y debe ajustarse aquí cuando llegue una muestra JSON real.

No mover la lógica del backend ni crear una capa adicional sin una necesidad concreta. Reutilizar los endpoints actuales; no inventar endpoints. Toda nueva incompatibilidad entre UI y API debe documentarse antes de un cambio importante.

## Páginas previstas

El frontend tiene siete áreas principales: Productos, Proveedores, Compras, Inventario, Dispensaciones, Consumo interno y Kardex, además de Login y de Reportes (área de solo consulta descrita más abajo). No crear una pantalla por tabla: usar modales, pestañas y componentes reutilizables. Todas están enlazadas desde el sidebar; las operaciones de Dispensaciones y Consumo interno permanecen bloqueadas por sus dependencias externas, pero sus historiales son consultables.

## Sistema visual

- Paleta: principal `#2563EB`, principal oscuro `#1E40AF`, sanitario `#0F766E`, fondo `#F8FAFC`, superficie `#FFFFFF`, texto `#0F172A`, secundario `#64748B`, borde `#E2E8F0`, éxito `#16A34A`, advertencia `#D97706`, peligro `#DC2626`.
- Verde, amarillo y rojo representan estados, no decoración.
- Interfaz hospitalaria, limpia, sobria, responsive y orientada a escritorio.
- Cards con borde tenue y radio cercano a 12 px; controles de 40–44 px y radio cercano a 8 px; sombras mínimas.
- Evitar gradientes, animaciones llamativas, componentes gigantes, filas completas con colores fuertes y estilos divergentes entre páginas.
- `base.html` es la fuente del layout: sidebar blanco, navbar, usuario, cierre de sesión y contenido principal.

## Reglas de desarrollo frontend

- Centralizar estilos generales en `app.css` y separar JavaScript por página cuando aporte claridad.
- Servir Bootstrap y cualquier otro recurso visual desde `frontend/static/`; no introducir dependencias de CDN que impidan operar la interfaz sin Internet.
- Evitar JavaScript inline y reutilizar las utilidades de `app.js`.
- Usar Fetch API contra las rutas REST existentes y mostrar carga, error, éxito y estado vacío.
- No incluir datos ficticios en el flujo final. Si se requiere un mock temporal, aislarlo y marcarlo claramente.
- Mantener accesibilidad básica: labels, foco visible, nombres accesibles, mensajes con `aria-live` y controles operables por teclado.
- Conservar `base.html` y Productos como patrón visual para las páginas futuras.

## Autenticación: estado y decisión actual

Seguridad expone temporalmente `POST /login/`, que recibe `usuario` y `clave`, pero su respuesta solo contiene el nombre de usuario: todavía no incluye token, `id_usuario`, vigencia ni rol. `login.html` consulta esa ruta desde JavaScript vanilla y conserva en `localStorage` `{id_usuario, username, role}` para presentación y redirección visual; `id_usuario` permanece nulo mientras Seguridad no lo entregue y nunca se almacena la contraseña. Dispensaciones y Consumo interno rellenan y bloquean visualmente el responsable cuando existe ese ID; de lo contrario conservan el campo manual de transición y lo informan al operador. `SEGURIDAD_LOGIN_URL` configura exclusivamente este acceso temporal y no debe confundirse con `INTEGRACION_SEGURIDAD_URL`, que activa la validación Bearer del backend.

El control visual no constituye autorización: `localStorage` es modificable, las vistas FastAPI pueden solicitarse directamente y los endpoints REST continúan públicos. Si Seguridad comienza a devolver `rol`, la UI admite visualmente `FARMACEUTICO` y `ADMINISTRADOR`; mientras no lo devuelva muestra `Rol pendiente`. No usar ese valor para decisiones de inventario. La integración definitiva requiere token o cookie segura, `id_usuario`, vigencia, cierre de sesión y un contrato para validar la sesión en backend; entonces debe retirarse este modo temporal y proteger tanto vistas como API sin crear autenticación paralela.

## Endpoints existentes relevantes para Productos

- `GET /producto-farmacia/`
- `GET /producto-farmacia/{id_producto}`
- `POST /producto-farmacia/`
- `PUT /producto-farmacia/{id_producto}`
- `DELETE /producto-farmacia/{id_producto}`
- `GET /categoria-producto/`
- `GET /categoria-producto/{id_categoria}`
- `POST /categoria-producto/`
- `PUT /categoria-producto/{id_categoria}`
- `DELETE /categoria-producto/{id_categoria}`
- `GET /api/v1/farmacia/productos/catalogo`
- `GET /api/v1/farmacia/productos/catalogo/{id_producto}`

La interfaz usa `PUT` para activar/desactivar productos y categorías conservando todos sus campos. El borrado físico existe en la API, pero la interfaz de Productos prefiere desactivar para preservar integridad e historial.

El catálogo de integración expone únicamente productos activos y metadatos clínicos/administrativos necesarios para que Atención guarde el verdadero `id_producto` al prescribir. No expone stock, lotes, costos, precios ni vencimientos. Cambiar este contrato requiere coordinación con el equipo consumidor.

## Migración aplicada: tipos de producto

- El 27/08/2026 se aplicó en `bd_hospital` la migración `migrations/001_catalogo_tipos_producto.sql` después de validarla sobre una copia temporal y generar un respaldo interno.
- Existe `tf_tipos_producto` con los códigos iniciales `MEDICAMENTO`, `INSUMO_MEDICO`, `DISPOSITIVO_MEDICO`, `REACTIVO` y `OTRO`.
- `tf_productos.id_tipo_producto` es obligatorio y referencia el catálogo. El producto existente fue relacionado correctamente y la verificación no encontró registros sin tipo o inconsistentes.
- `tf_productos.tipo_producto` se conserva temporalmente para compatibilidad y trazabilidad. Un trigger sincroniza ambas columnas para que el backend anterior pueda seguir creando y editando productos mientras se realiza la transición.
- No eliminar la columna legada ni el trigger hasta que los siete backends consuman y escriban `id_tipo_producto` y todos los grupos confirmen la migración.
- El backend expone `GET/POST/PUT /tipo-producto`, permite listar solo activos mediante `solo_activos=true` y no ofrece borrado físico: los tipos se desactivan para conservar referencias históricas.
- Productos acepta durante la transición tanto `id_tipo_producto` como el campo legado `tipo_producto`; si llegan ambos deben corresponder. Sus respuestas incluyen ID, código y nombre legible del tipo.
- El frontend de Productos carga `GET /tipo-producto/`, usa los tipos activos en el formulario y filtro, y permite administrarlos (crear, editar nombre/descripción y activar/desactivar) desde un modal. El código de un tipo utilizado no se edita desde la interfaz, de acuerdo con la regla del backend.

## Endpoints existentes relevantes para Proveedores

- `GET /proveedor/`
- `GET /proveedor/{id_proveedor}`
- `POST /proveedor/`
- `PUT /proveedor/{id_proveedor}`
- `DELETE /proveedor/{id_proveedor}`

No existe búsqueda o filtro del lado servidor. La interfaz filtra el listado localmente y usa `PUT` para activar/desactivar, preservando todos los campos. Aunque existe borrado físico, no se expone en la interfaz para evitar afectar compras relacionadas y conservar el historial.

## Flujo real de Compras

- Consulta: `GET /compra/` y `GET /compra/{id_compra}`.
- Registro transaccional: `POST /compra/` recibe `id_proveedor`, `id_usuario`, `numero_documento`, `fecha_compra` y una lista `detalles` con `id_producto`, `numero_lote`, `fecha_vencimiento`, `cantidad` y `costo_unitario`.
- Por cada detalle, el backend busca el lote por `(id_producto, numero_lote)`. Si no existe, lo crea con stock cero; si existe, lo reutiliza y conserva su fecha de vencimiento actual.
- El backend calcula subtotales y total, incrementa `tf_lotes.stock_actual` y crea un movimiento `ENTRADA` enlazado a `id_detalle_compra`, todo dentro de una transacción. El frontend nunca escribe stock ni kardex directamente.
- El detalle de `GET /compra/{id_compra}` solo contiene `id_lote`; la interfaz lo enriquece usando los endpoints existentes de lotes y productos.
- `PUT /compra/{id_compra}/anular` solo cambia `estado` a `ANULADA`: no revierte stock ni crea movimiento contrario. No exponer la anulación hasta que sea transaccionalmente segura.
- Como todavía no hay autenticación, `id_usuario` no puede obtenerse de una sesión. La vista prellena opcionalmente `FARMACIA_USUARIO_ID`, pero permite indicar manualmente el usuario responsable para pruebas. Retirar este campo auxiliar cuando Seguridad proporcione una identidad autenticada.

## Consulta y cálculo de Inventario

- No existe endpoint de stock agregado por producto. Inventario relaciona `GET /producto-farmacia/` con `GET /lote/` y suma `stock_actual` por `id_producto` únicamente en memoria; también carga categorías mediante `GET /categoria-producto/`.
- El stock disponible excluye lotes cuya fecha de vencimiento sea anterior a la fecha actual o cuyo estado persistido sea `VENCIDO`. No se persiste ni modifica el estado por este cálculo visual. Los productos sin lotes se muestran con stock cero.
- Estado agregado: stock cero es `AGOTADO`; stock mayor que cero y menor o igual a `stock_minimo` es `Stock bajo`; stock mayor al mínimo es `Disponible`.
- La ventana de próximos vencimientos es 30 días, coherente con el valor predeterminado de `GET /lote/alertas/por-vencer`. La vista considera próximos los lotes con stock positivo cuya fecha esté entre hoy y los siguientes 30 días, y vencidos los de fecha anterior a hoy.
- El backend no actualiza automáticamente lotes a `VENCIDO` cuando pasa la fecha y los flujos de salida actuales no validan vencimiento. Inventario compensa esto solo para consulta; esta limitación debe resolverse en backend antes de considerar segura la dispensación.
- El detalle de lote utiliza `GET /lote/{id_lote}` y muestra como contexto hasta diez movimientos de `GET /lote/{id_lote}/kardex`. No sustituye la futura página Kardex general.
- `GET /lote/alertas/stock-bajo` evalúa cada lote contra el mínimo del producto, no el total agregado; por ello no se usa para el indicador de productos con stock bajo.
- `GET /lote/alertas/por-vencer?dias=30` falla actualmente con HTTP 500 porque su SQL trata `$1` como texto mientras el router entrega un entero. Inventario no depende de esa ruta y calcula la ventana desde `GET /lote/`; corregir el tipado del endpoint en una etapa de backend.

## Flujo integrado de Dispensaciones (migración 006)

- Dispensación es la nota/proforma central; no existe una tabla NV separada.
- `GET /dispensacion/receta/{numero}` consulta Atención y valida el JSON. El navegador no envía medicamento, precio o paciente como fuente confiable.
- `GET /dispensacion/paciente/{id_trazabilidad}/recetas` consume la nueva lista plana de Atención y señala qué campos impiden integrarla; nunca resuelve productos por nombre.
- `POST /dispensacion/desde-receta/{numero}` permite cantidades parciales, congela precio/subtotal, asigna lotes FEFO y crea reservas sin modificar `stock_actual`.
- `POST /dispensacion/venta-directa` permite ventas sin receta únicamente para productos OTC (`requiere_receta=false`), con el mismo circuito de Cobros y entrega.
- Estados: `PENDIENTE_PAGO`, `PAGADA`, `ENTREGADA`, `VENCIDA`, `ANULACION_SOLICITADA` y `ANULADA`; `PENDIENTE` se conserva solo para historia legada.
- Cobros consulta `GET /api/v1/farmacia/dispensaciones/{id}/cobro` y notifica por `PUT .../{id}/pago`. El backend valida paciente, total, versión, vigencia y comprobante 1:1.
- `PUT /dispensacion/{id}/confirmar` solo entrega una nota `PAGADA`, consume reservas, descuenta lotes y crea movimientos `SALIDA` en una transacción. Repetir la entrega es idempotente.
- Una pendiente puede corregirse o anularse liberando reservas. Una pagada requiere confirmación de Cobros; una entregada deberá usar una futura devolución.
- `FARMACIA_USUARIO_ID` continúa siendo transición hasta integrar Seguridad.
- La migración 006 no se aplicó a `bd_hospital` durante el desarrollo: solo se probó en el clon `bd_hospital_disp006_test_20260831`.

### Migraciones 003 y 004 (renumeradas el 30/08/2026)

- La carpeta `migrations/` conserva una migración por etapa, cada una con su rollback y su verificación cuando corresponde. El archivo `farmacia_correcciones_1.sql` fue retirado de la raíz porque su contenido quedó repartido como `001_...`, `002_...` y `003_conectar_consumo_prescripciones...`.
- `migrations/003_conectar_consumo_prescripciones.sql`: conexión aditiva de Consumo interno con las prescripciones del módulo de Internación. Crea (solo si no existe) `ti_detalle_prescripciones` como tabla mínima de pruebas, agrega `tf_consumos_internos.id_prescripcion` y `tf_detalles_consumo.id_detalle_prescripcion` con sus FKs e índices, y no elimina las referencias a solicitudes. Aplicada en `bd_hospital`; es idempotente y su verificación confirma las columnas, la tabla y las FKs.
- `migrations/004_eliminar_receta_dispensacion.sql` existe históricamente, pero el respaldo restaurado conserva esas columnas. No asumir que fue aplicada. La migración 006 es compatible con ambos casos y no elimina datos legados.

## Flujo real y bloqueo de Consumo interno

- Farmacia expone `GET /consumo-interno/`, `GET /consumo-interno/{id_consumo}`, `POST /consumo-interno/` y `PUT /consumo-interno/{id_consumo}/anular`. No existen en este proyecto endpoints para solicitudes de insumos, detalles de solicitud, áreas, solicitantes ni estados de atención.
- El `POST` espera `id_solicitud_insumo`, `id_usuario`, `fecha_consumo`, `observacion` y detalles con `id_detalle_solicitud_consumo`, `id_lote` y `cantidad_entregada`. Acepta varios detalles en una transacción, bloquea cada lote con `FOR UPDATE`, valida su existencia y stock numérico, descuenta `stock_actual` y crea un movimiento `SALIDA` enlazado a `id_detalle_consumo`, con motivo `Salida por consumo interno`.
- El backend no valida existencia o estado de la solicitud, relación entre detalle solicitado, producto y lote, cantidad solicitada o pendiente, duplicidad, cantidad positiva, estado o vencimiento del lote. Una cantidad negativa incrementaría stock. La cabecera siempre queda `REGISTRADO`; no existe un estado ni cálculo de entrega parcial.
- Repetir `id_detalle_solicitud_consumo` con varios lotes es técnicamente aceptado porque no hay restricción, pero no constituye soporte seguro de múltiples lotes sin validar la cantidad solicitada y ya entregada. FEFO tampoco se aplica en backend.
- `PUT /consumo-interno/{id_consumo}/anular` solo cambia el estado: no repone stock ni crea movimiento contrario. No exponerlo.
- La integración automática con solicitudes externas permanece bloqueada. Para pruebas internas, Consumo interno ofrece un formulario manual temporal con referencia de solicitud y lotes reales; no sustituye la futura validación del módulo solicitante.
- Cuando el registro sea seguro, reutilizar `FARMACIA_USUARIO_ID` solo como transición, presentar lotes válidos con stock positivo ordenados visualmente por FEFO y conservar la validación transaccional de stock con `FOR UPDATE`.
- El frontend también ofrece un modo manual temporal para registrar referencias de solicitud y detalles de lote, manteniendo el flujo `PENDIENTE` y confirmación transaccional del backend.

## Consulta de Kardex y trazabilidad

- El endpoint principal es `GET /movimiento-inventario/`; admite únicamente el query param opcional `id_lote`, no tiene paginación ni filtros por producto, tipo o fechas. Ordena por `fecha_movimiento DESC, id_movimiento DESC`. `GET /movimiento-inventario/{id_movimiento}` obtiene un movimiento y `GET /lote/{id_lote}/kardex` devuelve el mismo historial limitado al lote.
- La respuesta solo contiene referencias: `id_lote`, `id_usuario`, `id_detalle_compra`, `id_detalle_dispensacion` e `id_detalle_consumo`; no incluye producto, número de lote, usuario legible ni cabecera del proceso. La UI carga una vez `GET /lote/` y `GET /producto-farmacia/` y construye mapas locales para resolver lote y producto sin llamadas por fila.
- El origen se clasifica por la referencia no nula: detalle de compra, dispensación o consumo; un `AJUSTE` sin esas referencias se presenta como ajuste manual. Como no existen endpoints directos de detalle a cabecera, se muestra la referencia del detalle y no se hacen consultas N+1 para inventar un número de documento padre.
- Los filtros y estadísticas se calculan localmente. Si el volumen crece, el backend deberá incorporar paginación y filtros server-side antes de cargar el historial completo en el navegador.
- `fecha_movimiento` es `date`, no timestamp; la interfaz muestra fecha legible, pero no puede mostrar una hora inexistente. ENTRADA y SALIDA guardan cantidades positivas y su signo es visual; AJUSTE conserva el signo almacenado, según la lógica actual de ajuste manual.
- No se calcula saldo acumulado: no existe saldo inicial verificable, las anulaciones no crean movimientos inversos y el sistema admite cambios inseguros que impiden garantizar una reconstrucción histórica completa.
- Kardex es una página de consulta y trazabilidad. No debe permitir modificar movimientos históricos, registrar ajustes ni alterar stock.

## Reportes (módulo de solo consulta)

- Agregado el 27/08/2026. Es un módulo de solo lectura: no crea tablas ni escribe stock o kardex. Todo lo que muestra se resuelve con `SELECT` agregados sobre las tablas existentes. La exportación a PDF/Excel solo reúne esas mismas filas en un archivo descargable.
- Backend: `routers/r_reporte.py` (prefijo `/reporte`, tag `Farmacia - Reportes`) delega en `modelo/m_reporte.py`. Registrado en `main.py`, que además sirve la vista `GET /reportes` (`reportes.html` + `frontend/static/js/reportes.js`).
- Endpoints:
  - `GET /reporte/compras-por-proveedor?desde=&hasta=`: número de compras y total por proveedor, solo compras `REGISTRADA`. Fechas opcionales sobre `fecha_compra`.
  - `GET /reporte/movimientos-resumen?desde=&hasta=`: entradas, salidas y ajustes agregados por producto en la ventana. `AJUSTE` se suma con su signo almacenado, coherente con Kardex.
  - `GET /reporte/stock-bajo`: stock agregado por producto activo (excluye lotes `VENCIDO` o ya vencidos por fecha) frente a `stock_minimo`. Es el cálculo agregado correcto; complementa, no reemplaza, a `GET /lote/alertas/stock-bajo`, que compara lote a lote. Devuelve `estado` `AGOTADO` o `STOCK_BAJO`.
  - `GET /reporte/vencimientos?dias=30` (0–365): lotes con stock positivo cuyo vencimiento ya pasó o cae dentro de la ventana; calcula la ventana en el servidor con `CURRENT_DATE + $1::int` y evita el error de tipado de `GET /lote/alertas/por-vencer`. Devuelve `dias_para_vencer` (negativo si ya venció) y `estado` `VENCIDO` o `POR_VENCER`.
- La página `/reportes` tiene un filtro común (desde, hasta, días) y un acordeón Bootstrap con un panel desplegable por reporte (el primero abierto, los demás plegados y con apertura independiente). Cada panel muestra su tabla con barras comparativas ligeras en CSS (sin librería de gráficos). Consulta los endpoints al cargar y al pulsar «Actualizar». Sin paginación; si el volumen crece habrá que mover filtros y paginación al backend.
- Cada panel tiene un menú «Descargar» (PDF / Excel) que genera el archivo en el servidor reutilizando las mismas consultas del reporte. Los paneles de Compras y Movimientos ofrecen «Descargar todo» (sin rango de fechas) y «Según filtros» (respeta desde/hasta); Stock y Vencimientos descargan siempre su consulta completa. Endpoint único de exportación: `GET /reporte/{reporte}/exportar?formato=pdf|xlsx&desde=&hasta=&dias=` donde `{reporte}` usa los nombres internos `compras`, `movimientos`, `stock` o `vencimientos` (los endpoints de consulta conservan sus rutas amigables existentes). Devuelve el archivo vía `Content-Disposition` con nombre `reporte_<reporte>[<filtro>]_<fecha>.ext` (p. ej. `reporte_compras_2026-08-01_al_2026-08-30_2026-08-30.pdf`, `reporte_vencimientos_30dias_2026-08-30.xlsx`).
- La generación de PDF usa `reportlab` y la de Excel `openpyxl` (dependencias agregadas en `pyproject.toml`, instaladas en el `.venv`). La lógica de exportación vive en `modelo/m_reporte.py` (`exportar_pdf`/`exportar_excel` reciben ya las filas consultadas; el router resuelve la consulta con la conexión inyectada y luego genera el archivo). No se exporta desde el navegador sobre la tabla HTML.

## Inconsistencias conocidas del backend/SQL

- No hay autenticación implementada aunque existen tablas de seguridad en el SQL.
- La API no aplica autorización a ningún endpoint.
- El esquema SQL comenta varias claves foráneas hacia usuarios, recetas, facturas, comprobantes y solicitudes; sus nombres no están unificados con algunas tablas reales del mismo archivo.
- Los estados operativos, las cantidades no negativas y `stock_minimo` todavía no tienen restricciones `CHECK` completas en SQL ni validadores Pydantic específicos. El catálogo nuevo sí controla el formato de su código; la columna textual legada se conserva únicamente por compatibilidad temporal.
- Las escrituras de catálogo no traducen errores de unicidad o integridad de `asyncpg` a respuestas HTTP controladas.
- El listado de productos no incluye el nombre de categoría; la UI lo resuelve cruzando los dos listados existentes.
- Los listados no ofrecen búsqueda, filtros ni paginación del lado servidor; Productos filtra localmente.
- Los endpoints `anular` de compras, dispensaciones y consumos cambian el estado, pero no revierten stock ni movimientos.
- El ajuste manual puede llevar un lote a stock negativo porque no hay validación previa.
- La alerta de stock bajo compara el stock de cada lote con el mínimo del producto, no la existencia total por producto.

## Disciplina de cambios

Priorizar simplicidad y reutilización. No añadir librerías, endpoints, tablas o abstracciones sin necesidad. No eliminar código funcional ni cambiar la arquitectura gratuitamente. Respetar nombres existentes. Realizar cambios mínimos en FastAPI para servir Jinja/static. Actualizar este archivo cuando se tomen decisiones arquitectónicas relevantes. No avanzar a otra página principal sin aprobación de la etapa actual.
