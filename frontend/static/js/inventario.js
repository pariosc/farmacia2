(() => {
  "use strict";

  const $ = id => document.getElementById(id);
  const PROXIMOS_DIAS = 30;
  const state = {productos: [], categorias: [], lotes: [], existencias: []};
  const loteModal = new bootstrap.Modal($("loteModal"));
  const show = (id, visible) => $(id).classList.toggle("d-none", !visible);
  const errorText = error => error.message === "Failed to fetch" ? "No se pudo conectar con el servidor." : error.message;
  const producto = id => state.productos.find(item => item.id_producto === id);
  const categoria = id => state.categorias.find(item => item.id_categoria === id)?.nombre || "Sin categoría";
  const cantidad = value => Number(value || 0).toLocaleString("es-BO", {minimumFractionDigits: 0, maximumFractionDigits: 2});
  const fecha = value => value ? new Intl.DateTimeFormat("es-BO", {timeZone:"UTC"}).format(new Date(`${value}T00:00:00Z`)) : "Sin fecha";
  const fechaHoy = () => new Date().toISOString().slice(0, 10);
  const diasHasta = value => value ? Math.round((Date.parse(`${value}T00:00:00Z`) - Date.parse(`${fechaHoy()}T00:00:00Z`)) / 86400000) : null;
  const estaVencido = lote => lote.fecha_vencimiento && diasHasta(lote.fecha_vencimiento) < 0;
  const estaProximo = lote => { const dias=diasHasta(lote.fecha_vencimiento); return dias !== null && dias >= 0 && dias <= PROXIMOS_DIAS; };
  const estadoLote = lote => estaVencido(lote) || lote.estado === "VENCIDO" ? "VENCIDO" : Number(lote.stock_actual) <= 0 || lote.estado === "AGOTADO" ? "AGOTADO" : "DISPONIBLE";
  const badgeEstado = estado => `<span class="badge-soft ${estado === "DISPONIBLE" ? "success" : estado === "BAJO" ? "warning" : estado === "VENCIDO" ? "danger" : "muted"}">${estado === "BAJO" ? "Stock bajo" : estado.charAt(0) + estado.slice(1).toLowerCase()}</span>`;

  async function cargarInventario() {
    show("inventarioCarga", true); show("inventarioError", false); show("inventoryTabContent", false);
    try {
      [state.productos, state.categorias, state.lotes] = await Promise.all([App.api("/producto-farmacia/"), App.api("/categoria-producto/"), App.api("/lote/")]);
      calcularExistencias(); cargarSelects(); renderResumen(); aplicarFiltrosExistencias(); aplicarFiltrosLotes(); aplicarFiltrosVencimientos();
      show("inventarioCarga", false); show("inventoryTabContent", true);
    } catch (error) { show("inventarioCarga", false); show("inventarioError", true); $("inventarioErrorMensaje").textContent=errorText(error); }
  }

  function calcularExistencias() {
    state.existencias = state.productos.map(item => {
      const lotesValidos = state.lotes.filter(lote => lote.id_producto === item.id_producto && estadoLote(lote) !== "VENCIDO");
      const stock = lotesValidos.reduce((total, lote) => total + Math.max(0, Number(lote.stock_actual || 0)), 0);
      const minimo = Number(item.stock_minimo || 0); const estado = stock <= 0 ? "AGOTADO" : stock <= minimo ? "BAJO" : "DISPONIBLE";
      return {...item, stock_disponible:stock, estado_inventario:estado};
    }).sort((a,b) => a.nombre.localeCompare(b.nombre,"es"));
  }

  function cargarSelects() {
    $("filtroCategoriaExistencia").innerHTML = `<option value="">Todas</option>${state.categorias.map(item => `<option value="${item.id_categoria}">${App.escapeHtml(item.nombre)}</option>`).join("")}`;
    $("filtroProductoLote").innerHTML = `<option value="">Todos los productos</option>${state.productos.map(item => `<option value="${item.id_producto}">${App.escapeHtml(item.nombre)}</option>`).join("")}`;
  }

  function renderResumen() {
    $("resumenProductos").textContent = state.productos.filter(item => item.activo).length;
    $("resumenStockBajo").textContent = state.existencias.filter(item => item.activo && item.estado_inventario === "BAJO").length;
    $("resumenPorVencer").textContent = state.lotes.filter(lote => Number(lote.stock_actual) > 0 && estaProximo(lote)).length;
    $("resumenVencidos").textContent = state.lotes.filter(lote => Number(lote.stock_actual) > 0 && estadoLote(lote) === "VENCIDO").length;
  }

  function aplicarFiltrosExistencias() {
    const term=$("buscarExistencia").value.trim().toLocaleLowerCase("es"), cat=$("filtroCategoriaExistencia").value, tipo=$("filtroTipoExistencia").value, estado=$("filtroEstadoExistencia").value;
    const items=state.existencias.filter(item => (!term || [item.codigo,item.nombre].some(v=>(v||"").toLocaleLowerCase("es").includes(term))) && (!cat || String(item.id_categoria)===cat) && (!tipo || item.tipo_producto===tipo) && (!estado || item.estado_inventario===estado));
    $("contadorExistencias").textContent=`${items.length} de ${state.existencias.length} productos`; show("vacioExistencias",items.length===0); show("tablaExistenciasContenedor",items.length>0);
    $("tablaExistencias").innerHTML=items.map(item=>`<tr><td class="font-monospace">${App.escapeHtml(item.codigo)}</td><td><span class="product-name">${App.escapeHtml(item.nombre)}</span><span class="product-detail">${App.escapeHtml(item.tipo_producto)}</span></td><td>${App.escapeHtml(item.presentacion || item.unidad_medida)}</td><td>${App.escapeHtml(categoria(item.id_categoria))}</td><td class="fw-semibold">${cantidad(item.stock_disponible)} ${App.escapeHtml(item.unidad_medida)}</td><td>${cantidad(item.stock_minimo)}</td><td>${badgeEstado(item.estado_inventario)}</td><td><div class="action-group"><button class="btn btn-sm btn-outline-secondary" data-action="product-lots" data-id="${item.id_producto}">Ver lotes</button></div></td></tr>`).join("");
  }

  function aplicarFiltrosLotes() {
    const idProducto=$("filtroProductoLote").value, estado=$("filtroEstadoLote").value, vencimiento=$("filtroVencimientoLote").value;
    const items=[...state.lotes].sort((a,b)=>{const nombres=(producto(a.id_producto)?.nombre||"").localeCompare(producto(b.id_producto)?.nombre||"","es");return nombres || (a.fecha_vencimiento||"9999").localeCompare(b.fecha_vencimiento||"9999")}).filter(lote => (!idProducto || String(lote.id_producto)===idProducto) && (!estado || estadoLote(lote)===estado) && (!vencimiento || (vencimiento==="SIN_FECHA"&&!lote.fecha_vencimiento) || (vencimiento==="PROXIMO"&&estaProximo(lote)) || (vencimiento==="VENCIDO"&&estadoLote(lote)==="VENCIDO")));
    $("contadorLotes").textContent=`${items.length} de ${state.lotes.length} lotes`; show("vacioLotes",items.length===0); show("tablaLotesContenedor",items.length>0);
    $("tablaLotes").innerHTML=items.map(lote=>`<tr><td><span class="product-name">${App.escapeHtml(producto(lote.id_producto)?.nombre || `Producto #${lote.id_producto}`)}</span></td><td class="font-monospace">${App.escapeHtml(lote.numero_lote)}</td><td>${fecha(lote.fecha_vencimiento)}</td><td class="fw-semibold">${cantidad(lote.stock_actual)}</td><td>${badgeEstado(estadoLote(lote))}</td><td><div class="action-group"><button class="btn btn-sm btn-outline-secondary" data-action="view-lot" data-id="${lote.id_lote}">Ver</button></div></td></tr>`).join("");
  }

  function textoDias(lote) { const dias=diasHasta(lote.fecha_vencimiento); return dias < 0 ? `Vencido hace ${Math.abs(dias)} día${Math.abs(dias)===1?"":"s"}` : dias===0 ? "Vence hoy" : `Vence en ${dias} días`; }

  function aplicarFiltrosVencimientos() {
    const term=$("buscarVencimiento").value.trim().toLocaleLowerCase("es"), tipo=$("filtroTipoVencimiento").value;
    const items=state.lotes.filter(lote=>Number(lote.stock_actual)>0 && (estaProximo(lote)||estadoLote(lote)==="VENCIDO")).filter(lote=>(!term || [producto(lote.id_producto)?.nombre,lote.numero_lote].some(v=>(v||"").toLocaleLowerCase("es").includes(term))) && (!tipo || (tipo==="PROXIMO"&&estaProximo(lote)) || (tipo==="VENCIDO"&&estadoLote(lote)==="VENCIDO"))).sort((a,b)=>a.fecha_vencimiento.localeCompare(b.fecha_vencimiento));
    $("contadorVencimientos").textContent=`${items.length} lote${items.length===1?"":"s"} con seguimiento`; show("vacioVencimientos",items.length===0); show("tablaVencimientosContenedor",items.length>0);
    $("tablaVencimientos").innerHTML=items.map(lote=>`<tr><td><span class="product-name">${App.escapeHtml(producto(lote.id_producto)?.nombre || `Producto #${lote.id_producto}`)}</span></td><td class="font-monospace">${App.escapeHtml(lote.numero_lote)}</td><td>${fecha(lote.fecha_vencimiento)}</td><td class="fw-semibold ${estadoLote(lote)==="VENCIDO"?"text-danger":"text-warning"}">${textoDias(lote)}</td><td>${cantidad(lote.stock_actual)}</td><td>${estadoLote(lote)==="VENCIDO"?badgeEstado("VENCIDO"):'<span class="badge-soft warning">Por vencer</span>'}</td></tr>`).join("");
  }

  function verLotesProducto(idProducto) {
    $("filtroProductoLote").value=String(idProducto); aplicarFiltrosLotes(); bootstrap.Tab.getOrCreateInstance($("lotes-tab")).show();
  }

  async function verLote(idLote) {
    show("loteModalCarga",true); show("loteModalContenido",false); $("loteModalError").classList.add("d-none"); loteModal.show();
    try {
      const [lote,movimientos]=await Promise.all([App.api(`/lote/${idLote}`),App.api(`/lote/${idLote}/kardex`)]); const prod=producto(lote.id_producto); const estado=estadoLote(lote);
      $("loteModalTitle").textContent=`Lote ${lote.numero_lote}`; $("resumenLote").innerHTML=`<div><span>Producto</span><strong>${App.escapeHtml(prod?.nombre||`Producto #${lote.id_producto}`)}</strong></div><div><span>Número de lote</span><strong>${App.escapeHtml(lote.numero_lote)}</strong></div><div><span>Vencimiento</span><strong>${fecha(lote.fecha_vencimiento)}</strong></div><div><span>Stock actual</span><strong>${cantidad(lote.stock_actual)} ${App.escapeHtml(prod?.unidad_medida||"")}</strong></div><div><span>Estado</span><strong>${badgeEstado(estado)}</strong></div>`;
      const recientes=movimientos.slice(0,10); show("kardexLoteVacio",recientes.length===0); show("kardexLoteTabla",recientes.length>0);
      $("tablaKardexLote").innerHTML=recientes.map(mov=>`<tr><td>${fecha(mov.fecha_movimiento)}</td><td><span class="badge-soft ${mov.tipo_movimiento==="ENTRADA"?"success":mov.tipo_movimiento==="SALIDA"?"danger":"warning"}">${App.escapeHtml(mov.tipo_movimiento)}</span></td><td class="fw-semibold">${mov.tipo_movimiento==="SALIDA"?"−":"+"}${cantidad(Math.abs(Number(mov.cantidad)))}</td><td>${App.escapeHtml(mov.motivo||"Sin motivo")}</td></tr>`).join("");
      show("loteModalCarga",false); show("loteModalContenido",true);
    } catch(error) { show("loteModalCarga",false); $("loteModalError").textContent=errorText(error); $("loteModalError").classList.remove("d-none"); }
  }

  $("btnReintentarInventario").addEventListener("click",cargarInventario);
  ["buscarExistencia","filtroCategoriaExistencia","filtroTipoExistencia","filtroEstadoExistencia"].forEach(id=>$(id).addEventListener(id==="buscarExistencia"?"input":"change",aplicarFiltrosExistencias));
  ["filtroProductoLote","filtroEstadoLote","filtroVencimientoLote"].forEach(id=>$(id).addEventListener("change",aplicarFiltrosLotes));
  ["buscarVencimiento","filtroTipoVencimiento"].forEach(id=>$(id).addEventListener(id==="buscarVencimiento"?"input":"change",aplicarFiltrosVencimientos));
  $("tablaExistencias").addEventListener("click",event=>{const button=event.target.closest("button[data-action='product-lots']");if(button)verLotesProducto(Number(button.dataset.id));});
  $("tablaLotes").addEventListener("click",event=>{const button=event.target.closest("button[data-action='view-lot']");if(button)verLote(Number(button.dataset.id));});
  cargarInventario();
})();
