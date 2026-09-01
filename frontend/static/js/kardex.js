(() => {
  "use strict";

  const $ = id => document.getElementById(id);
  const state = {movimientos: [], productos: new Map(), lotes: new Map()};
  const modal = new bootstrap.Modal($("movimientoModal"));
  const show = (id, visible) => $(id).classList.toggle("d-none", !visible);
  const errorText = error => error.message === "Failed to fetch" ? "No se pudo conectar con el servidor." : error.message;
  const fecha = value => value ? new Intl.DateTimeFormat("es-BO", {timeZone:"UTC"}).format(new Date(`${value}T00:00:00Z`)) : "—";
  const numero = value => Number(value || 0).toLocaleString("es-BO", {minimumFractionDigits:0, maximumFractionDigits:2});
  const lote = id => state.lotes.get(Number(id));
  const producto = idLote => state.productos.get(lote(idLote)?.id_producto);

  function origen(movimiento) {
    if (movimiento.id_detalle_compra != null) return {clave:"COMPRA", nombre:"Compra", referencia:`Detalle #${movimiento.id_detalle_compra}`};
    if (movimiento.id_detalle_dispensacion != null) return {clave:"DISPENSACION", nombre:"Dispensación", referencia:`Detalle #${movimiento.id_detalle_dispensacion}`};
    if (movimiento.id_detalle_consumo != null) return {clave:"CONSUMO", nombre:"Consumo interno", referencia:`Detalle #${movimiento.id_detalle_consumo}`};
    if (movimiento.tipo_movimiento === "AJUSTE") return {clave:"AJUSTE", nombre:"Ajuste manual", referencia:"Sin proceso asociado"};
    return {clave:"OTRO", nombre:"Sin referencia", referencia:"Origen no identificado"};
  }

  function badgeTipo(tipo) {
    const clase = tipo === "ENTRADA" ? "success" : tipo === "SALIDA" ? "danger" : "info";
    return `<span class="badge-soft ${clase}">${App.escapeHtml(tipo)}</span>`;
  }

  function cantidadVisual(movimiento) {
    const valor = Number(movimiento.cantidad || 0);
    if (movimiento.tipo_movimiento === "ENTRADA") return {texto:`+${numero(Math.abs(valor))}`, clase:"entry"};
    if (movimiento.tipo_movimiento === "SALIDA") return {texto:`−${numero(Math.abs(valor))}`, clase:"exit"};
    return {texto:`${valor > 0 ? "+" : valor < 0 ? "−" : ""}${numero(Math.abs(valor))}`, clase:"adjustment"};
  }

  function actualizarResumen() {
    $("totalMovimientos").textContent = state.movimientos.length;
    $("totalEntradas").textContent = state.movimientos.filter(item => item.tipo_movimiento === "ENTRADA").length;
    $("totalSalidas").textContent = state.movimientos.filter(item => item.tipo_movimiento === "SALIDA").length;
    $("totalAjustes").textContent = state.movimientos.filter(item => item.tipo_movimiento === "AJUSTE").length;
  }

  function cargarLotesFiltro() {
    const items = [...new Set(state.movimientos.map(item => item.id_lote))].map(id => lote(id)).filter(Boolean);
    items.sort((a, b) => String(a.numero_lote).localeCompare(String(b.numero_lote), "es", {numeric:true}));
    $("filtroLoteMovimiento").innerHTML = `<option value="">Todos los lotes</option>${items.map(item => `<option value="${item.id_lote}">${App.escapeHtml(item.numero_lote)} — ${App.escapeHtml(state.productos.get(item.id_producto)?.nombre || `Producto #${item.id_producto}`)}</option>`).join("")}`;
  }

  async function cargarKardex() {
    show("kardexCarga", true); show("kardexError", false); show("kardexResultados", false);
    try {
      const [movimientos, lotes, productos] = await Promise.all([App.api("/movimiento-inventario/"), App.api("/lote/"), App.api("/producto-farmacia/")]);
      state.movimientos = movimientos;
      state.lotes = new Map(lotes.map(item => [item.id_lote, item]));
      state.productos = new Map(productos.map(item => [item.id_producto, item]));
      actualizarResumen(); cargarLotesFiltro();
      show("kardexCarga", false); show("kardexResultados", true); aplicarFiltros();
    } catch (error) {
      show("kardexCarga", false); show("kardexError", true); $("kardexErrorMensaje").textContent = errorText(error);
    }
  }

  function aplicarFiltros() {
    const termino = $("buscarMovimiento").value.trim().toLocaleLowerCase("es");
    const tipo = $("filtroTipoMovimiento").value, idLote = $("filtroLoteMovimiento").value;
    const filtroOrigen = $("filtroOrigenMovimiento").value, desde = $("movimientoDesde").value, hasta = $("movimientoHasta").value;
    const items = state.movimientos.filter(item => {
      const prod = producto(item.id_lote), lot = lote(item.id_lote), fuente = origen(item);
      const coincideProducto = !termino || [prod?.codigo, prod?.nombre, prod?.concentracion, prod?.presentacion, lot?.numero_lote].filter(Boolean).some(value => String(value).toLocaleLowerCase("es").includes(termino));
      return coincideProducto && (!tipo || item.tipo_movimiento === tipo) && (!idLote || String(item.id_lote) === idLote) && (!filtroOrigen || fuente.clave === filtroOrigen) && (!desde || item.fecha_movimiento >= desde) && (!hasta || item.fecha_movimiento <= hasta);
    });
    $("contadorMovimientos").textContent = `${items.length} de ${state.movimientos.length} movimiento${state.movimientos.length === 1 ? "" : "s"}`;
    const filtrando = [termino, tipo, idLote, filtroOrigen, desde, hasta].some(Boolean);
    $("vacioKardexTitulo").textContent = filtrando ? "No hay movimientos que coincidan con los filtros seleccionados" : "No se encontraron movimientos de inventario";
    $("vacioKardexTexto").textContent = filtrando ? "Modifica o limpia los filtros para ampliar la búsqueda." : "Todavía no existen movimientos registrados.";
    show("vacioKardex", items.length === 0); show("tablaKardexContenedor", items.length > 0);
    $("tablaKardex").innerHTML = items.map(item => {
      const prod = producto(item.id_lote), lot = lote(item.id_lote), fuente = origen(item), cant = cantidadVisual(item);
      return `<tr><td>${fecha(item.fecha_movimiento)}</td><td><span class="product-name">${App.escapeHtml(prod?.nombre || `Producto #${lot?.id_producto || "—"}`)}</span><span class="product-detail">${App.escapeHtml([prod?.codigo, prod?.concentracion, prod?.presentacion || prod?.unidad_medida].filter(Boolean).join(" · "))}</span></td><td><span class="font-monospace">${App.escapeHtml(lot?.numero_lote || `#${item.id_lote}`)}</span></td><td>${badgeTipo(item.tipo_movimiento)}</td><td><span class="movement-quantity ${cant.clase}">${cant.texto}</span><span class="product-detail">${App.escapeHtml(prod?.unidad_medida || "")}</span></td><td class="kardex-secondary"><span class="product-name">${fuente.nombre}</span><span class="product-detail">${fuente.referencia}</span></td><td class="kardex-secondary">Usuario #${item.id_usuario}</td><td><div class="action-group"><button class="btn btn-sm btn-outline-secondary" data-action="view" data-id="${item.id_movimiento}">Ver</button></div></td></tr>`;
    }).join("");
  }

  async function verMovimiento(id) {
    show("movimientoModalCarga", true); show("movimientoModalContenido", false); $("movimientoModalError").classList.add("d-none"); modal.show();
    try {
      const movimiento = await App.api(`/movimiento-inventario/${id}`);
      const historial = await App.api(`/lote/${movimiento.id_lote}/kardex`);
      const lot = lote(movimiento.id_lote), prod = producto(movimiento.id_lote), fuente = origen(movimiento), cant = cantidadVisual(movimiento);
      $("movimientoModalTitle").textContent = `Movimiento #${movimiento.id_movimiento}`;
      $("resumenMovimiento").innerHTML = `<div><span>Tipo</span><strong>${badgeTipo(movimiento.tipo_movimiento)}</strong></div><div><span>Fecha</span><strong>${fecha(movimiento.fecha_movimiento)}</strong></div><div><span>Cantidad</span><strong class="movement-quantity ${cant.clase}">${cant.texto} ${App.escapeHtml(prod?.unidad_medida || "")}</strong></div><div><span>Producto</span><strong>${App.escapeHtml(prod?.nombre || "No disponible")}</strong></div><div><span>Presentación</span><strong>${App.escapeHtml(prod?.presentacion || prod?.unidad_medida || "—")}</strong></div><div><span>Lote</span><strong>${App.escapeHtml(lot?.numero_lote || `#${movimiento.id_lote}`)}</strong></div><div><span>Vencimiento</span><strong>${fecha(lot?.fecha_vencimiento)}</strong></div><div><span>Estado actual del lote</span><strong>${App.escapeHtml(lot?.estado || "—")}</strong></div><div><span>Origen</span><strong>${fuente.nombre} · ${fuente.referencia}</strong></div><div><span>Usuario</span><strong>Usuario #${movimiento.id_usuario}</strong></div><div><span>Motivo</span><strong>${App.escapeHtml(movimiento.motivo || "Sin motivo")}</strong></div>`;
      $("descripcionHistorialLote").textContent = `${historial.length} movimiento${historial.length === 1 ? "" : "s"} registrado${historial.length === 1 ? "" : "s"} para el lote ${lot?.numero_lote || `#${movimiento.id_lote}`}.`;
      show("historialLoteVacio", historial.length === 0); show("historialLoteTabla", historial.length > 0);
      $("tablaHistorialLote").innerHTML = historial.map(item => { const cantidad = cantidadVisual(item), fuenteLote = origen(item); return `<tr class="${item.id_movimiento === movimiento.id_movimiento ? "table-active" : ""}"><td>${fecha(item.fecha_movimiento)}</td><td>${badgeTipo(item.tipo_movimiento)}</td><td><span class="movement-quantity ${cantidad.clase}">${cantidad.texto}</span></td><td>${fuenteLote.nombre}</td></tr>`; }).join("");
      show("movimientoModalCarga", false); show("movimientoModalContenido", true);
    } catch (error) {
      show("movimientoModalCarga", false); $("movimientoModalError").textContent = errorText(error); $("movimientoModalError").classList.remove("d-none");
    }
  }

  function limpiarFiltros() {
    ["buscarMovimiento", "filtroTipoMovimiento", "filtroLoteMovimiento", "filtroOrigenMovimiento", "movimientoDesde", "movimientoHasta"].forEach(id => { $(id).value = ""; });
    aplicarFiltros(); $("buscarMovimiento").focus();
  }

  $("btnReintentarKardex").addEventListener("click", cargarKardex);
  $("btnLimpiarKardex").addEventListener("click", limpiarFiltros);
  ["buscarMovimiento", "filtroTipoMovimiento", "filtroLoteMovimiento", "filtroOrigenMovimiento", "movimientoDesde", "movimientoHasta"].forEach(id => $(id).addEventListener(id === "buscarMovimiento" ? "input" : "change", aplicarFiltros));
  $("tablaKardex").addEventListener("click", event => { const button = event.target.closest("button[data-action='view']"); if (button) verMovimiento(Number(button.dataset.id)); });
  cargarKardex();
})();
