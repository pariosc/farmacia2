(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  const state = {productos:[], categorias:[], tipos:[]};
  const productoModal = new bootstrap.Modal($("productoModal"));
  const categoriasModal = new bootstrap.Modal($("categoriasModal"));
  const tiposModal = new bootstrap.Modal($("tiposModal"));

  const nullable = value => value.trim() || null;
  const categoriaNombre = id => state.categorias.find(c => c.id_categoria === id)?.nombre || "Sin categoría";
  const tipoCodigo = id => state.tipos.find(t => t.id_tipo_producto === id)?.codigo || "";
  const show = (id, visible) => $(id).classList.toggle("d-none", !visible);
  const errorText = error => error.message.includes("duplicate key") ? "Ya existe un registro con ese código o nombre." : error.message;

  async function cargarDatos() {
    show("estadoCarga", true); show("estadoError", false); show("estadoVacio", false); show("contenedorTabla", false);
    try {
      [state.productos, state.categorias, state.tipos] = await Promise.all([App.api("/producto-farmacia/"), App.api("/categoria-producto/"), App.api("/tipo-producto/")]);
      cargarSelects(); renderCategorias(); renderTipos(); aplicarFiltros();
    } catch (error) { show("estadoCarga", false); show("estadoError", true); $("mensajeError").textContent = errorText(error); $("contadorProductos").textContent = "Sin datos"; }
  }

  function cargarSelects() {
    const activas = state.categorias.filter(c => c.activo);
    $("filtroCategoria").innerHTML = `<option value="">Todas</option>${state.categorias.map(c => `<option value="${c.id_categoria}">${App.escapeHtml(c.nombre)}${c.activo ? "" : " (inactiva)"}</option>`).join("")}`;
    $("idCategoria").innerHTML = `<option value="">Selecciona</option>${activas.map(c => `<option value="${c.id_categoria}">${App.escapeHtml(c.nombre)}</option>`).join("")}`;
    const tiposActivos = state.tipos.filter(t => t.activo);
    $("filtroTipo").innerHTML = `<option value="">Todos</option>${state.tipos.map(t => `<option value="${t.id_tipo_producto}">${App.escapeHtml(t.nombre)}${t.activo ? "" : " (inactivo)"}</option>`).join("")}`;
    $("tipoProducto").innerHTML = `<option value="">Selecciona</option>${tiposActivos.map(t => `<option value="${t.id_tipo_producto}" data-codigo="${App.escapeHtml(t.codigo)}">${App.escapeHtml(t.nombre)}</option>`).join("")}`;
  }

  function aplicarFiltros() {
    const term = $("buscarProducto").value.trim().toLocaleLowerCase("es"); const categoria = $("filtroCategoria").value; const tipo = $("filtroTipo").value;
    const filtrados = state.productos.filter(p => (!term || [p.codigo,p.nombre,p.principio_activo].some(v => (v || "").toLocaleLowerCase("es").includes(term))) && (!categoria || String(p.id_categoria) === categoria) && (!tipo || String(p.id_tipo_producto) === tipo));
    renderProductos(filtrados);
  }

  function renderProductos(productos) {
    show("estadoCarga", false); show("estadoError", false); show("estadoVacio", productos.length === 0); show("contenedorTabla", productos.length > 0);
    $("contadorProductos").textContent = `${productos.length} de ${state.productos.length} producto${state.productos.length === 1 ? "" : "s"}`;
    $("tablaProductos").innerHTML = productos.map(p => `<tr><td><span class="font-monospace">${App.escapeHtml(p.codigo)}</span></td><td><span class="product-name">${App.escapeHtml(p.nombre)}</span><span class="product-detail">${App.escapeHtml([p.principio_activo,p.concentracion,p.presentacion].filter(Boolean).join(" · ") || "Sin detalle adicional")}</span></td><td>${App.escapeHtml(categoriaNombre(p.id_categoria))}</td><td><span class="badge-soft info">${App.escapeHtml(p.tipo_producto)}</span></td><td>${App.escapeHtml(p.unidad_medida)}</td><td class="fw-semibold">Bs ${Number(p.precio_venta || 0).toFixed(2)}</td><td><span class="badge-soft ${p.activo ? "success" : "muted"}">${p.activo ? "Activo" : "Inactivo"}</span></td><td><div class="action-group"><button class="btn btn-sm btn-outline-secondary" data-action="edit" data-id="${p.id_producto}">Editar</button><button class="btn btn-sm ${p.activo ? "btn-outline-danger" : "btn-outline-success"}" data-action="toggle" data-id="${p.id_producto}">${p.activo ? "Desactivar" : "Activar"}</button></div></td></tr>`).join("");
  }

  function abrirProducto(producto = null) {
    $("productoForm").reset(); $("productoFormError").classList.add("d-none"); $("idProducto").value = producto?.id_producto || ""; $("productoModalTitle").textContent = producto ? "Editar producto" : "Nuevo producto";
    if (producto) { $("codigo").value=producto.codigo; $("nombre").value=producto.nombre; $("idCategoria").value=producto.id_categoria; $("tipoProducto").value=producto.id_tipo_producto || state.tipos.find(t => t.codigo === producto.tipo_producto)?.id_tipo_producto || ""; $("principioActivo").value=producto.principio_activo || ""; $("concentracion").value=producto.concentracion || ""; $("presentacion").value=producto.presentacion || ""; $("unidadMedida").value=producto.unidad_medida; $("stockMinimo").value=producto.stock_minimo; $("precioVenta").value=producto.precio_venta || 0; }
    productoModal.show();
  }

  const productoPayload = (activo = true) => { const tipo = state.tipos.find(t => String(t.id_tipo_producto) === $("tipoProducto").value); return {id_categoria:Number($("idCategoria").value),codigo:$("codigo").value.trim(),nombre:$("nombre").value.trim(),id_tipo_producto:Number($("tipoProducto").value),tipo_producto:tipo?.codigo,principio_activo:nullable($("principioActivo").value),concentracion:nullable($("concentracion").value),presentacion:nullable($("presentacion").value),unidad_medida:$("unidadMedida").value.trim(),stock_minimo:$("stockMinimo").value,precio_venta:$("precioVenta").value,activo}; };

  async function guardarProducto(event) {
    event.preventDefault(); if (!event.currentTarget.checkValidity()) { event.currentTarget.classList.add("was-validated"); return; }
    const id = $("idProducto").value; const existente = state.productos.find(p => String(p.id_producto) === id); const button = $("btnGuardarProducto"); button.disabled=true; button.textContent="Guardando…";
    try { await App.api(id ? `/producto-farmacia/${id}` : "/producto-farmacia/", {method:id ? "PUT" : "POST", body:JSON.stringify(productoPayload(existente?.activo ?? true))}); productoModal.hide(); App.toast(id ? "Producto actualizado correctamente." : "Producto creado correctamente."); await cargarDatos(); }
    catch(error){ $("productoFormError").textContent=errorText(error); $("productoFormError").classList.remove("d-none"); }
    finally { button.disabled=false; button.textContent="Guardar producto"; }
  }

  async function alternarProducto(id) {
    const p=state.productos.find(item => item.id_producto===id); if(!p) return; const accion=p.activo?"desactivar":"activar"; if(!confirm(`¿Deseas ${accion} ${p.nombre}?`)) return;
    try { await App.api(`/producto-farmacia/${id}`,{method:"PUT",body:JSON.stringify({...p,activo:!p.activo})}); App.toast(`Producto ${p.activo ? "desactivado" : "activado"}.`); await cargarDatos(); } catch(error){ App.toast(errorText(error),"error"); }
  }

  function renderCategorias() {
    $("listaCategorias").innerHTML = state.categorias.length ? state.categorias.map(c => `<div class="category-item"><div><strong>${App.escapeHtml(c.nombre)}</strong> <span class="badge-soft ${c.activo?"success":"muted"}">${c.activo?"Activa":"Inactiva"}</span><p>${App.escapeHtml(c.descripcion || "Sin descripción")}</p></div><div class="category-actions"><button class="btn btn-sm btn-outline-secondary" data-category-action="edit" data-id="${c.id_categoria}">Editar</button><button class="btn btn-sm ${c.activo?"btn-outline-danger":"btn-outline-success"}" data-category-action="toggle" data-id="${c.id_categoria}">${c.activo?"Desactivar":"Activar"}</button></div></div>`).join("") : `<div class="state-panel"><p>No hay categorías registradas.</p></div>`;
  }
  function cancelarEdicionCategoria(){ $("categoriaForm").reset(); $("idCategoriaEditar").value=""; $("btnGuardarCategoria").textContent="Agregar"; $("btnCancelarCategoria").classList.add("d-none"); }
  async function guardarCategoria(event){ event.preventDefault(); if(!event.currentTarget.checkValidity()){event.currentTarget.classList.add("was-validated");return} const id=$("idCategoriaEditar").value; const previa=state.categorias.find(c=>String(c.id_categoria)===id); try{await App.api(id?`/categoria-producto/${id}`:"/categoria-producto/",{method:id?"PUT":"POST",body:JSON.stringify({nombre:$("categoriaNombre").value.trim(),descripcion:nullable($("categoriaDescripcion").value),activo:previa?.activo??true})});App.toast(id?"Categoría actualizada.":"Categoría creada.");cancelarEdicionCategoria();await cargarDatos()}catch(error){$("categoriaError").textContent=errorText(error);$("categoriaError").classList.remove("d-none")}}
  async function alternarCategoria(id){const c=state.categorias.find(item=>item.id_categoria===id);if(!c)return;try{await App.api(`/categoria-producto/${id}`,{method:"PUT",body:JSON.stringify({...c,activo:!c.activo})});App.toast(`Categoría ${c.activo?"desactivada":"activada"}.`);await cargarDatos()}catch(error){App.toast(errorText(error),"error")}}

  function renderTipos(){ $("listaTipos").innerHTML=state.tipos.length?state.tipos.map(t=>`<div class="category-item"><div><strong>${App.escapeHtml(t.nombre)}</strong> <span class="badge-soft ${t.activo?"success":"muted"}">${t.activo?"Activo":"Inactivo"}</span><p><span class="font-monospace">${App.escapeHtml(t.codigo)}</span>${t.descripcion?` · ${App.escapeHtml(t.descripcion)}`:""}</p></div><div class="category-actions"><button class="btn btn-sm btn-outline-secondary" data-type-action="edit" data-id="${t.id_tipo_producto}">Editar</button><button class="btn btn-sm ${t.activo?"btn-outline-danger":"btn-outline-success"}" data-type-action="toggle" data-id="${t.id_tipo_producto}">${t.activo?"Desactivar":"Activar"}</button></div></div>`).join(""):"<div class=\"state-panel\"><p>No hay tipos registrados.</p></div>"; }
  function cancelarEdicionTipo(){ $("tipoForm").reset(); $("idTipoEditar").value=""; $("tipoCodigo").disabled=false; $("btnGuardarTipo").textContent="Agregar"; $("btnCancelarTipo").classList.add("d-none"); $("tipoError").classList.add("d-none"); }
  async function guardarTipo(event){ event.preventDefault(); if(!event.currentTarget.checkValidity()){event.currentTarget.classList.add("was-validated");return} const id=$("idTipoEditar").value, previo=state.tipos.find(t=>String(t.id_tipo_producto)===id), button=$("btnGuardarTipo"); button.disabled=true; try{await App.api(id?`/tipo-producto/${id}`:"/tipo-producto/",{method:id?"PUT":"POST",body:JSON.stringify({codigo:$("tipoCodigo").value.trim().toUpperCase(),nombre:$("tipoNombre").value.trim(),descripcion:nullable($("tipoDescripcion").value),activo:previo?.activo??true})});App.toast(id?"Tipo actualizado correctamente.":"Tipo creado correctamente.");cancelarEdicionTipo();await cargarDatos()}catch(error){$("tipoError").textContent=errorText(error);$("tipoError").classList.remove("d-none")}finally{button.disabled=false}}
  async function alternarTipo(id){const tipo=state.tipos.find(item=>item.id_tipo_producto===id);if(!tipo)return;if(!confirm(`¿Deseas ${tipo.activo?"desactivar":"activar"} ${tipo.nombre}?`))return;try{await App.api(`/tipo-producto/${id}`,{method:"PUT",body:JSON.stringify({...tipo,activo:!tipo.activo})});App.toast(`Tipo ${tipo.activo?"desactivado":"activado"}.`);await cargarDatos()}catch(error){App.toast(errorText(error),"error")}}

  $("btnNuevo").addEventListener("click",()=>abrirProducto()); $("btnCategorias").addEventListener("click",()=>categoriasModal.show()); $("btnTipos").addEventListener("click",()=>{cancelarEdicionTipo();tiposModal.show()}); $("btnReintentar").addEventListener("click",cargarDatos); $("productoForm").addEventListener("submit",guardarProducto); $("categoriaForm").addEventListener("submit",guardarCategoria); $("btnCancelarCategoria").addEventListener("click",cancelarEdicionCategoria); $("tipoForm").addEventListener("submit",guardarTipo); $("btnCancelarTipo").addEventListener("click",cancelarEdicionTipo);
  ["buscarProducto","filtroCategoria","filtroTipo"].forEach(id=>$(id).addEventListener(id==="buscarProducto"?"input":"change",aplicarFiltros));
  $("tablaProductos").addEventListener("click",e=>{const b=e.target.closest("button[data-action]");if(!b)return;const id=Number(b.dataset.id);b.dataset.action==="edit"?abrirProducto(state.productos.find(p=>p.id_producto===id)):alternarProducto(id)});
  $("listaCategorias").addEventListener("click",e=>{const b=e.target.closest("button[data-category-action]");if(!b)return;const c=state.categorias.find(item=>item.id_categoria===Number(b.dataset.id));if(b.dataset.categoryAction==="toggle")return alternarCategoria(c.id_categoria);$("idCategoriaEditar").value=c.id_categoria;$("categoriaNombre").value=c.nombre;$("categoriaDescripcion").value=c.descripcion||"";$("btnGuardarCategoria").textContent="Guardar";$("btnCancelarCategoria").classList.remove("d-none")});
  $("listaTipos").addEventListener("click",e=>{const b=e.target.closest("button[data-type-action]");if(!b)return;const tipo=state.tipos.find(item=>item.id_tipo_producto===Number(b.dataset.id));if(b.dataset.typeAction==="toggle")return alternarTipo(tipo.id_tipo_producto);$("idTipoEditar").value=tipo.id_tipo_producto;$("tipoCodigo").value=tipo.codigo;$("tipoCodigo").disabled=true;$("tipoNombre").value=tipo.nombre;$("tipoDescripcion").value=tipo.descripcion||"";$("btnGuardarTipo").textContent="Guardar";$("btnCancelarTipo").classList.remove("d-none")});
  cargarDatos();
})();
