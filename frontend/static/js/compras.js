(() => {
  "use strict";

  const $ = id => document.getElementById(id);
  const state = {compras: [], proveedores: [], productos: [], lotes: [], fila: 0};
  const usuarioConfigurado = Number($("comprasConfig").dataset.usuarioId) || null;
  const compraModal = new bootstrap.Modal($("compraModal"));
  const detalleModal = new bootstrap.Modal($("detalleCompraModal"));
  const show = (id, visible) => $(id).classList.toggle("d-none", !visible);
  const nullable = value => value.trim() || null;
  const errorText = error => error.message === "Failed to fetch" ? "No se pudo conectar con el servidor." : error.message;
  const proveedorNombre = id => state.proveedores.find(p => p.id_proveedor === id)?.razon_social || `Proveedor #${id}`;
  const productoPorId = id => state.productos.find(p => p.id_producto === id);
  const lotePorId = id => state.lotes.find(l => l.id_lote === id);
  const moneda = value => `Bs ${Number(value || 0).toLocaleString("es-BO", {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
  const fechaLegible = value => value ? new Intl.DateTimeFormat("es-BO", {timeZone: "UTC"}).format(new Date(`${value}T00:00:00Z`)) : "—";
  const hoy = () => new Date().toISOString().slice(0, 10);

  async function cargarDatos() {
    show("estadoCargaCompra", true); show("estadoErrorCompra", false); show("estadoVacioCompra", false); show("contenedorTablaCompras", false);
    $("contadorCompras").textContent = "Cargando compras…";
    try {
      [state.compras, state.proveedores, state.productos, state.lotes] = await Promise.all([
        App.api("/compra/"), App.api("/proveedor/"), App.api("/producto-farmacia/"), App.api("/lote/")
      ]);
      cargarSelects(); aplicarFiltros();
    } catch (error) {
      show("estadoCargaCompra", false); show("estadoErrorCompra", true);
      $("mensajeErrorCompra").textContent = errorText(error); $("contadorCompras").textContent = "Sin datos";
    }
  }

  function cargarSelects() {
    const opcionesFiltro = state.proveedores.map(p => `<option value="${p.id_proveedor}">${App.escapeHtml(p.razon_social)}</option>`).join("");
    const opcionesActivos = state.proveedores.filter(p => p.activo).map(p => `<option value="${p.id_proveedor}">${App.escapeHtml(p.razon_social)}</option>`).join("");
    $("filtroProveedorCompra").innerHTML = `<option value="">Todos</option>${opcionesFiltro}`;
    $("compraProveedor").innerHTML = `<option value="">Selecciona un proveedor</option>${opcionesActivos}`;
  }

  function aplicarFiltros() {
    const term = $("buscarCompra").value.trim().toLocaleLowerCase("es");
    const proveedor = $("filtroProveedorCompra").value; const estado = $("filtroEstadoCompra").value;
    const desde = $("fechaDesde").value; const hasta = $("fechaHasta").value;
    const filtradas = state.compras.filter(compra => {
      const texto = [compra.numero_documento, proveedorNombre(compra.id_proveedor)].some(v => (v || "").toLocaleLowerCase("es").includes(term));
      return (!term || texto) && (!proveedor || String(compra.id_proveedor) === proveedor) && (!estado || compra.estado === estado)
        && (!desde || compra.fecha_compra >= desde) && (!hasta || compra.fecha_compra <= hasta);
    });
    renderCompras(filtradas);
  }

  function renderCompras(compras) {
    show("estadoCargaCompra", false); show("estadoErrorCompra", false); show("estadoVacioCompra", compras.length === 0); show("contenedorTablaCompras", compras.length > 0);
    $("contadorCompras").textContent = `${compras.length} de ${state.compras.length} compra${state.compras.length === 1 ? "" : "s"}`;
    $("tablaCompras").innerHTML = compras.map(compra => `<tr><td><span class="product-name">${App.escapeHtml(compra.numero_documento || "Sin documento")}</span><span class="product-detail">Compra #${compra.id_compra}</span></td><td>${App.escapeHtml(proveedorNombre(compra.id_proveedor))}</td><td>${fechaLegible(compra.fecha_compra)}</td><td class="text-nowrap fw-semibold">${moneda(compra.total)}</td><td><span class="badge-soft ${compra.estado === "REGISTRADA" ? "success" : "muted"}">${App.escapeHtml(compra.estado)}</span></td><td><div class="action-group"><button class="btn btn-sm btn-outline-secondary" data-action="view" data-id="${compra.id_compra}">Ver</button></div></td></tr>`).join("");
  }

  function etiquetaProducto(producto) {
    const detalle = [producto.concentracion, producto.presentacion || producto.unidad_medida].filter(Boolean).join(" — ");
    return `${producto.nombre}${detalle ? ` ${detalle}` : ""}`;
  }

  function opcionesProductos() {
    return `<option value="">Selecciona</option>${state.productos.filter(p => p.activo).map(p => `<option value="${p.id_producto}">${App.escapeHtml(etiquetaProducto(p))}</option>`).join("")}`;
  }

  function agregarDetalle() {
    state.fila += 1; const id = state.fila; const row = document.createElement("tr"); row.dataset.rowId = id;
    row.innerHTML = `<td><select class="form-select detail-product" aria-label="Producto" required>${opcionesProductos()}</select></td><td><input class="form-control detail-lot" maxlength="50" aria-label="Número de lote" required><small class="detail-lot-note"></small></td><td><input class="form-control detail-expiry" type="date" aria-label="Fecha de vencimiento"></td><td><input class="form-control detail-quantity" type="number" min="0.01" step="0.01" inputmode="decimal" value="1" aria-label="Cantidad" required></td><td><input class="form-control detail-cost" type="number" min="0" step="0.01" inputmode="decimal" value="0" aria-label="Costo unitario" required></td><td class="detail-subtotal text-nowrap fw-semibold">${moneda(0)}</td><td><button class="btn btn-sm btn-outline-danger detail-remove" type="button" aria-label="Quitar producto">Quitar</button></td>`;
    $("detallesCompra").append(row); actualizarEstadoDetalle(); row.querySelector(".detail-product").focus();
  }

  function actualizarLoteExistente(row) {
    const idProducto = Number(row.querySelector(".detail-product").value); const numero = row.querySelector(".detail-lot").value.trim();
    const vencimiento = row.querySelector(".detail-expiry"); const note = row.querySelector(".detail-lot-note");
    const existente = state.lotes.find(l => l.id_producto === idProducto && l.numero_lote === numero);
    if (existente) {
      vencimiento.value = existente.fecha_vencimiento || ""; vencimiento.disabled = true; row.dataset.existingLot = String(existente.id_lote);
      note.textContent = "Lote existente; se sumará al stock."; note.className = "detail-lot-note text-success";
    } else {
      if (row.dataset.existingLot) vencimiento.value = "";
      vencimiento.disabled = false; delete row.dataset.existingLot; note.textContent = ""; note.className = "detail-lot-note";
    }
  }

  function actualizarEstadoDetalle() {
    const rows = [...$("detallesCompra").rows]; show("detalleCompraVacio", rows.length === 0);
    const total = rows.reduce((sum, row) => {
      const subtotal = Number(row.querySelector(".detail-quantity").value || 0) * Number(row.querySelector(".detail-cost").value || 0);
      row.querySelector(".detail-subtotal").textContent = moneda(subtotal); return sum + subtotal;
    }, 0);
    $("totalCompra").textContent = moneda(total);
  }

  function abrirNuevaCompra() {
    $("compraForm").reset(); $("compraForm").classList.remove("was-validated"); $("compraFormError").classList.add("d-none"); $("compraUsuario").value = usuarioConfigurado || 1;
    $("detallesCompra").innerHTML = ""; $("fechaCompra").value = hoy(); agregarDetalle(); compraModal.show();
  }

  function validarDetalles() {
    const rows = [...$("detallesCompra").rows];
    if (!rows.length) throw new Error("Agrega al menos un producto a la compra.");
    const claves = new Set();
    return rows.map((row, index) => {
      const idProducto = Number(row.querySelector(".detail-product").value); const numeroLote = row.querySelector(".detail-lot").value.trim();
      const cantidad = row.querySelector(".detail-quantity").value; const costo = row.querySelector(".detail-cost").value;
      if (!idProducto || !numeroLote || !(Number(cantidad) > 0) || Number(costo) < 0 || costo === "") throw new Error(`Revisa los datos de la fila ${index + 1}.`);
      const clave = `${idProducto}|${numeroLote.toLocaleUpperCase("es")}`;
      if (claves.has(clave)) throw new Error(`El producto y lote de la fila ${index + 1} ya están incluidos en esta compra.`);
      claves.add(clave);
      return {id_producto:idProducto, numero_lote:numeroLote, fecha_vencimiento:row.querySelector(".detail-expiry").value || null, cantidad, costo_unitario:costo};
    });
  }

  async function registrarCompra(event) {
    event.preventDefault(); if (!event.currentTarget.checkValidity()) { event.currentTarget.classList.add("was-validated"); return; }
    let detalles; try { detalles = validarDetalles(); } catch (error) { $("compraFormError").textContent=error.message; $("compraFormError").classList.remove("d-none"); return; }
    const button = $("btnRegistrarCompra"); if (button.disabled) return; button.disabled=true; button.textContent="Registrando…";
    try {
      const usuarioId = Number($("compraUsuario").value); if (!usuarioId) throw new Error("Indica un usuario responsable válido.");
      const compra = await App.api("/compra/", {method:"POST", body:JSON.stringify({id_proveedor:Number($("compraProveedor").value),id_usuario:usuarioId,numero_documento:nullable($("numeroDocumento").value),fecha_compra:$("fechaCompra").value,detalles})});
      compraModal.hide(); App.toast(`Compra #${compra.id_compra} registrada por ${moneda(compra.total)}.`); await cargarDatos();
    } catch (error) { $("compraFormError").textContent=errorText(error); $("compraFormError").classList.remove("d-none"); }
    finally { button.disabled=false; button.textContent="Registrar compra"; }
  }

  async function verCompra(id) {
    show("detalleCompraCarga", true); show("detalleCompraContenido", false); $("detalleCompraError").classList.add("d-none"); detalleModal.show();
    try {
      const compra = await App.api(`/compra/${id}`); const faltantes = compra.detalles.map(d => d.id_lote).filter(idLote => !lotePorId(idLote));
      if (faltantes.length) state.lotes.push(...await Promise.all([...new Set(faltantes)].map(idLote => App.api(`/lote/${idLote}`))));
      $("detalleCompraModalTitle").textContent = `Compra #${compra.id_compra}`;
      $("resumenCompra").innerHTML = `<div><span>Proveedor</span><strong>${App.escapeHtml(proveedorNombre(compra.id_proveedor))}</strong></div><div><span>Documento</span><strong>${App.escapeHtml(compra.numero_documento || "Sin documento")}</strong></div><div><span>Fecha</span><strong>${fechaLegible(compra.fecha_compra)}</strong></div><div><span>Estado</span><strong><span class="badge-soft ${compra.estado === "REGISTRADA" ? "success" : "muted"}">${App.escapeHtml(compra.estado)}</span></strong></div><div><span>Usuario</span><strong>#${compra.id_usuario}</strong></div><div><span>Total</span><strong>${moneda(compra.total)}</strong></div>`;
      $("tablaDetalleCompra").innerHTML = compra.detalles.map(detalle => { const lote=lotePorId(detalle.id_lote); const producto=productoPorId(lote?.id_producto); return `<tr><td><span class="product-name">${App.escapeHtml(producto ? etiquetaProducto(producto) : `Producto #${lote?.id_producto || "—"}`)}</span></td><td>${App.escapeHtml(lote?.numero_lote || `#${detalle.id_lote}`)}</td><td>${fechaLegible(lote?.fecha_vencimiento)}</td><td>${Number(detalle.cantidad).toLocaleString("es-BO")}</td><td>${moneda(detalle.costo_unitario)}</td><td class="fw-semibold">${moneda(detalle.subtotal)}</td></tr>`; }).join("");
      show("detalleCompraCarga", false); show("detalleCompraContenido", true);
    } catch (error) { show("detalleCompraCarga", false); $("detalleCompraError").textContent=errorText(error); $("detalleCompraError").classList.remove("d-none"); }
  }

  $("btnNuevaCompra").disabled = false;
  $("btnNuevaCompra").addEventListener("click", abrirNuevaCompra); $("btnReintentarCompra").addEventListener("click", cargarDatos); $("btnAgregarDetalle").addEventListener("click", agregarDetalle); $("compraForm").addEventListener("submit", registrarCompra);
  ["buscarCompra","filtroProveedorCompra","filtroEstadoCompra","fechaDesde","fechaHasta"].forEach(id => $(id).addEventListener(id === "buscarCompra" ? "input" : "change", aplicarFiltros));
  $("detallesCompra").addEventListener("input", event => { const row=event.target.closest("tr"); if (!row) return; if (event.target.matches(".detail-product,.detail-lot")) actualizarLoteExistente(row); actualizarEstadoDetalle(); });
  $("detallesCompra").addEventListener("change", event => { const row=event.target.closest("tr"); if (row && event.target.matches(".detail-product,.detail-lot")) actualizarLoteExistente(row); });
  $("detallesCompra").addEventListener("click", event => { const button=event.target.closest(".detail-remove"); if (!button) return; button.closest("tr").remove(); actualizarEstadoDetalle(); });
  $("tablaCompras").addEventListener("click", event => { const button=event.target.closest("button[data-action='view']"); if (button) verCompra(Number(button.dataset.id)); });
  cargarDatos();
})();
