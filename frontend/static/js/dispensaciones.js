(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  const state = {receta:null, notas:[], notaActual:null, editando:null, prescripcionesPaciente:[], productos:{}, ventaItems:[]};
  const modal = new bootstrap.Modal($("notaModal"));
  const usuarioSesion = window.AppSession?.obtenerUsuarioActual() || null;
  function configurarResponsable(inputId, ayudaId) {
    const input = $(inputId), ayuda = $(ayudaId);
    if (usuarioSesion?.id_usuario) {
      input.value = String(usuarioSesion.id_usuario);
      input.readOnly = true;
      ayuda.textContent = `Asignado por login: ${usuarioSesion.username} (#${usuarioSesion.id_usuario}).`;
      return;
    }
    ayuda.textContent = "Seguridad aún no devuelve id_usuario; usa el ID manual de transición.";
  }
  configurarResponsable("notaUsuario", "notaUsuarioAyuda");
  configurarResponsable("ventaUsuario", "ventaUsuarioAyuda");
  const usuarioInicial = Number($("notaUsuario").value) || 1;
  const usuarioVentaInicial = Number($("ventaUsuario").value) || 1;
  const show = (id, visible) => $(id).classList.toggle("d-none", !visible);
  const mensaje = error => error.message === "Failed to fetch" ? "No se pudo conectar con el servidor." : error.message;
  const dinero = value => `Bs ${Number(value || 0).toLocaleString("es-BO", {minimumFractionDigits:2, maximumFractionDigits:2})}`;
  const cantidad = value => Number(value || 0).toLocaleString("es-BO", {maximumFractionDigits:2});
  const fechaHora = value => value ? new Intl.DateTimeFormat("es-BO", {dateStyle:"short", timeStyle:"short"}).format(new Date(value)) : "—";
  const badge = estado => { const clase={PENDIENTE_PAGO:"warning",PAGADA:"info",ENTREGADA:"success",ANULADA:"muted",VENCIDA:"muted",ANULACION_SOLICITADA:"warning"}[estado]||"muted"; return `<span class="badge-soft ${clase}">${App.escapeHtml(estado||"—")}</span>`; };

  async function buscarReceta(numero = null) {
    const valor = numero || Number($("numeroReceta").value);
    if (!valor) { mostrarError("Ingresa un número de receta válido."); return; }
    const boton=$("btnBuscarReceta"); boton.disabled=true; boton.textContent="Consultando…"; mostrarError("");
    try { state.receta=await App.api(`/dispensacion/receta/${valor}`); $("numeroReceta").value=valor; renderReceta(); }
    catch(error){ state.receta=null; show("recetaContenido",false); show("recetaVacia",true); mostrarError(mensaje(error)); }
    finally { boton.disabled=false; boton.textContent="Buscar receta"; }
  }

  async function buscarPaciente() {
    const id=$("idTrazabilidad").value.trim(), boton=$("btnBuscarPaciente");
    if(!id){mostrarError("Ingresa el ID de trazabilidad del paciente.");return}
    boton.disabled=true;boton.textContent="Consultando…";mostrarError("");show("trazabilidadResultados",false);
    try{const respuesta=await App.api(`/dispensacion/paciente/${encodeURIComponent(id)}/recetas`);state.prescripcionesPaciente=respuesta.prescripciones;$("trazabilidadAviso").className=`alert ${respuesta.integrable?"alert-success":"alert-warning"} mb-3`;$("trazabilidadAviso").textContent=respuesta.integrable?"Atención ya devuelve las referencias mínimas. Selecciona la receta exacta para continuar.":`Consulta disponible, pero todavía no permite dispensar. Faltan: ${(respuesta.faltantes||[]).join(", ")}.`;$("tablaTrazabilidad").innerHTML=respuesta.prescripciones.map(p=>`<tr><td>#${p.id_prescripcion}${p.numero_receta?`<span class="product-detail">Receta ${App.escapeHtml(p.numero_receta)}</span>`:""}</td><td><span class="product-name">${App.escapeHtml(p.medicamento)}</span><span class="product-detail">${App.escapeHtml([p.dosis,p.indicaciones].filter(Boolean).join(" · "))}</span></td><td>${cantidad(p.cantidad)}</td><td>${p.integrable?'<span class="badge-soft success">Lista</span>':`<span class="badge-soft warning">Falta contrato</span><span class="product-detail">${App.escapeHtml((p.faltantes||[]).join(", "))}</span>`}</td></tr>`).join("");show("trazabilidadResultados",true)}catch(error){mostrarError(mensaje(error))}finally{boton.disabled=false;boton.textContent="Buscar paciente"}
  }

  function mostrarError(texto){ $("notaError").textContent=texto; show("notaError",Boolean(texto)); }
  function actualizarTotalReceta(){
    let total=0;
    $("tablaReceta").querySelectorAll("tr").forEach(row=>{
      const precio=Number(row.dataset.precio||0);
      const cantidadSolicitada=Number(row.querySelector(".cantidad-receta")?.value||0);
      const subtotal=precio*cantidadSolicitada;
      total+=subtotal;
      const celda=row.querySelector(".subtotal-receta");
      if(celda) celda.textContent=dinero(subtotal);
    });
    $("totalEstimado").textContent=dinero(total);
  }
  function actualizarTotalVenta(){
    const total=state.ventaItems.reduce((s,item)=>s+item.precio*item.cantidad,0);
    $("ventaLineas").textContent=state.ventaItems.length;
    $("ventaTotal").textContent=dinero(total);
  }
  function renderVenta(){
    $("tablaVenta").innerHTML=state.ventaItems.length?state.ventaItems.map((item,index)=>`<tr><td><span class="product-name">${App.escapeHtml(item.nombre)}</span><span class="product-detail">ID catálogo: ${item.id_producto}</span></td><td><input class="form-control cantidad-venta" data-index="${index}" type="number" min="0.01" step="0.01" value="${item.cantidad}"></td><td class="text-end">${dinero(item.precio)}</td><td class="text-end fw-semibold">${dinero(item.precio*item.cantidad)}</td><td class="text-end"><button class="btn btn-sm btn-outline-danger quitar-venta" data-index="${index}" type="button">Quitar</button></td></tr>`).join(""): '<tr><td colspan="5" class="text-center text-muted py-4">Agrega uno o más productos OTC</td></tr>';
    $("tablaVenta").querySelectorAll(".cantidad-venta").forEach(input=>input.addEventListener("input",()=>{const i=Number(input.dataset.index),valor=Number(input.value);if(valor>0)state.ventaItems[i].cantidad=valor;renderVenta()}));
    $("tablaVenta").querySelectorAll(".quitar-venta").forEach(btn=>btn.addEventListener("click",()=>{state.ventaItems.splice(Number(btn.dataset.index),1);renderVenta()}));
    actualizarTotalVenta();
  }
  function agregarVenta(){
    const id=Number($("ventaProducto").value), cantidadVenta=Number($("ventaCantidad").value);
    const producto=state.productos[id];
    if(!producto||!cantidadVenta||cantidadVenta<=0){$("ventaDirectaError").textContent="Selecciona un producto y una cantidad válida.";show("ventaDirectaError",true);return}
    if(Number(producto.precio_venta||0)<=0){$("ventaDirectaError").textContent="El producto seleccionado no tiene un precio de venta válido.";show("ventaDirectaError",true);return}
    const existente=state.ventaItems.find(item=>item.id_producto===id);
    if(existente) existente.cantidad+=cantidadVenta;
    else state.ventaItems.push({id_producto:id,nombre:producto.nombre,precio:Number(producto.precio_venta||0),cantidad:cantidadVenta});
    show("ventaDirectaError",false);$("ventaCantidad").value=1;renderVenta();
  }
  function renderReceta(){ const r=state.receta; show("recetaVacia",false); show("recetaContenido",true); show("recetaResumen",true); $("recetaResumen").innerHTML=`<div><span>Receta</span><strong>#${r.id_receta}</strong></div><div><span>Estado</span><strong>${badge(r.estado)}</strong></div><div><span>Paciente</span><strong>${App.escapeHtml(r.paciente.nombre_completo||`#${r.paciente.id_paciente}`)}</strong></div><div><span>CI</span><strong>${App.escapeHtml(r.paciente.ci||"—")}</strong></div>`; $("tablaReceta").innerHTML=r.detalles.map(linea=>{const previa=state.editando?.detalles?.find(d=>Number(d.id_prescripcion_externa)===Number(linea.id_prescripcion));const valor=previa?.cantidad_solicitada??linea.cantidad_prescrita;const producto=state.productos[Number(linea.id_producto)]||{};const precio=Number(producto.precio_venta||0);return `<tr data-id="${linea.id_prescripcion}" data-precio="${precio}"><td><span class="product-name">${App.escapeHtml(linea.nombre_producto||producto.nombre||`Producto #${linea.id_producto}`)}</span><span class="product-detail">ID catálogo: ${linea.id_producto}</span></td><td>${App.escapeHtml(linea.dosis_instrucciones||"Según receta")}</td><td>${cantidad(linea.cantidad_prescrita)}</td><td><input class="form-control cantidad-receta" type="number" min="0.01" max="${linea.cantidad_prescrita}" step="0.01" value="${valor}" required></td><td>${precio>0?dinero(precio):"Precio no definido"}</td><td class="subtotal-receta fw-semibold">${dinero(precio*Number(valor))}</td></tr>`}).join(""); $("notaObservacion").value=state.editando?.observacion||""; $("btnCrearNota").textContent=state.editando?"Guardar corrección y renovar reserva":"Crear nota y reservar"; $("tablaReceta").querySelectorAll(".cantidad-receta").forEach(input=>input.addEventListener("input",actualizarTotalReceta)); actualizarTotalReceta(); }

  function payloadNota(){ return {id_usuario:Number($("notaUsuario").value),observacion:$("notaObservacion").value.trim()||null,detalles:[...$("tablaReceta").querySelectorAll("tr")].map(row=>({id_prescripcion:Number(row.dataset.id),cantidad_solicitada:row.querySelector("input").value}))}; }
  async function guardarNota(event){event.preventDefault();if(!event.currentTarget.checkValidity()){event.currentTarget.classList.add("was-validated");return}const boton=$("btnCrearNota");boton.disabled=true;mostrarError("");try{const url=state.editando?`/dispensacion/${state.editando.id_dispensacion}/corregir`:`/dispensacion/desde-receta/${$("numeroReceta").value}`;const nota=await App.api(url,{method:state.editando?"PUT":"POST",body:JSON.stringify(payloadNota())});App.toast(state.editando?"Nota corregida; versión y reserva renovadas.":`Nota #${nota.id_dispensacion} creada para Cobros.`);state.editando=null;state.receta=null;event.currentTarget.reset();$("notaUsuario").value=usuarioInicial;show("recetaContenido",false);show("recetaResumen",false);show("recetaVacia",true);await cargarNotas()}catch(error){mostrarError(mensaje(error))}finally{boton.disabled=false;boton.textContent="Crear nota y reservar"}}

  async function cargarProductosVenta(){try{const respuesta=await App.api("/producto-farmacia/");const productos=Array.isArray(respuesta)?respuesta:(respuesta.productos||respuesta.items||[]);state.productos=Object.fromEntries(productos.map(p=>[Number(p.id_producto),p]));const otc=productos.filter(p=>p.activo&&!p.requiere_receta);$("ventaProducto").innerHTML=`<option value="">Selecciona un producto OTC</option>${otc.map(p=>`<option value="${p.id_producto}">${App.escapeHtml(p.nombre)} — Bs ${Number(p.precio_venta||0).toFixed(2)}</option>`).join("")}`;if(!otc.length)$("ventaProducto").innerHTML='<option value="">No hay productos OTC activos</option>';actualizarTotalVenta();if(state.receta)renderReceta()}catch(error){$("ventaDirectaError").textContent=`No se pudieron cargar los productos: ${mensaje(error)}`;show("ventaDirectaError",true)}}
  async function guardarVentaDirecta(event){event.preventDefault();if(!state.ventaItems.length){$("ventaDirectaError").textContent="Agrega al menos un producto.";show("ventaDirectaError",true);return}if(!event.currentTarget.checkValidity()){event.currentTarget.classList.add("was-validated");return}const boton=$("btnCrearVenta");boton.disabled=true;show("ventaDirectaError",false);try{const venta=await App.api("/dispensacion/venta-directa",{method:"POST",body:JSON.stringify({id_usuario:Number($("ventaUsuario").value),id_paciente:$("ventaPaciente").value.trim()||null,observacion:$("ventaObservacion").value.trim()||null,detalles:state.ventaItems.map(item=>({id_producto:item.id_producto,cantidad_solicitada:item.cantidad}))})});App.toast(`Nota OTC #${venta.id_dispensacion} creada para Cobros.`);event.currentTarget.reset();$("ventaUsuario").value=usuarioVentaInicial;state.ventaItems=[];renderVenta();await cargarNotas()}catch(error){$("ventaDirectaError").textContent=mensaje(error);show("ventaDirectaError",true)}finally{boton.disabled=false}}

  async function cargarNotas(){show("notasCarga",true);show("notasError",false);show("notasContenido",false);try{state.notas=await App.api("/dispensacion/");show("notasCarga",false);show("notasContenido",true);filtrarNotas()}catch(error){show("notasCarga",false);show("notasError",true);$("notasErrorTexto").textContent=mensaje(error)}}
  function filtrarNotas(){const termino=$("buscarNota").value.trim().toLowerCase(),estado=$("filtroEstadoNota").value;const items=state.notas.filter(n=>(!estado||n.estado===estado)&&(!termino||[n.id_dispensacion,n.numero_receta_externa,n.id_factura,n.id_paciente_externo].some(v=>String(v??"").toLowerCase().includes(termino))));$("contadorNotas").textContent=`${items.length} de ${state.notas.length} notas`;show("notasVacias",!items.length);show("notasTablaWrap",Boolean(items.length));$("tablaNotas").innerHTML=items.map(n=>`<tr><td><span class="product-name">Nota #${n.id_dispensacion}</span><span class="product-detail">Versión ${n.version}</span></td><td>Receta ${App.escapeHtml(n.numero_receta_externa||"—")}<span class="product-detail">Paciente #${n.id_paciente_externo||"—"}</span></td><td class="fw-semibold">${dinero(n.total)}</td><td>${n.id_factura?`Factura #${n.id_factura}`:fechaHora(n.reserva_hasta)}</td><td>${badge(n.estado)}</td><td class="text-end"><button class="btn btn-sm btn-outline-secondary" data-ver="${n.id_dispensacion}">Ver</button></td></tr>`).join("")}

  async function verNota(id){modal.show();show("modalNotaCarga",true);show("modalNotaContenido",false);show("modalNotaError",false);try{const n=await App.api(`/dispensacion/${id}`);state.notaActual=n;$("notaModalTitulo").textContent=`Nota #${n.id_dispensacion}`;$("modalNotaResumen").innerHTML=`<div><span>Estado</span><strong>${badge(n.estado)}</strong></div><div><span>Receta</span><strong>${App.escapeHtml(n.numero_receta_externa||"—")}</strong></div><div><span>Paciente</span><strong>#${n.id_paciente_externo||"—"}</strong></div><div><span>Versión</span><strong>${n.version}</strong></div><div><span>Total</span><strong>${dinero(n.total)}</strong></div><div><span>Factura</span><strong>${n.id_factura?`#${n.id_factura}`:"Pendiente"}</strong></div>`;$("modalNotaDetalles").innerHTML=n.detalles.map(d=>`<tr><td><span class="product-name">${App.escapeHtml(d.nombre_producto)}</span><span class="product-detail">${App.escapeHtml(d.dosis_instrucciones||"")}</span></td><td>${cantidad(d.cantidad_solicitada)} ${App.escapeHtml(d.unidad_medida)}</td><td>${dinero(d.precio_unitario)}</td><td>${dinero(d.subtotal)}</td><td>${d.reservas.map(r=>`${App.escapeHtml(r.numero_lote)}: ${cantidad(r.cantidad)} (${r.estado})`).join("<br>")||"—"}</td></tr>`).join("");show("btnEditarNota",n.estado==="PENDIENTE_PAGO");show("btnAnularNota",["PENDIENTE_PAGO","PAGADA"].includes(n.estado));show("btnEntregarNota",n.estado==="PAGADA");show("modalNotaCarga",false);show("modalNotaContenido",true)}catch(error){show("modalNotaCarga",false);$("modalNotaError").textContent=mensaje(error);show("modalNotaError",true)}}
  async function editarNota(){const n=state.notaActual;if(!n)return;modal.hide();state.editando=n;await buscarReceta(Number(n.numero_receta_externa));document.querySelector('[data-bs-target="#nuevaNotaPane"]').click()}
  async function anularNota(){const n=state.notaActual;if(!n)return;const motivo=window.prompt(n.estado==="PAGADA"?"Motivo para solicitar anulación a Cobros:":"Motivo de anulación:");if(!motivo)return;const ruta=n.estado==="PAGADA"?"solicitar-anulacion":"anular";try{await App.api(`/dispensacion/${n.id_dispensacion}/${ruta}`,{method:"PUT",body:JSON.stringify({motivo})});modal.hide();App.toast(n.estado==="PAGADA"?"Solicitud registrada; espera confirmación de Cobros.":"Nota anulada y reserva liberada.");await cargarNotas()}catch(error){App.toast(mensaje(error),"error")}}
  async function entregarNota(){const n=state.notaActual;if(!n||!window.confirm("¿Confirmar la entrega? Esta operación descontará stock."))return;try{await App.api(`/dispensacion/${n.id_dispensacion}/confirmar`,{method:"PUT"});modal.hide();App.toast("Entrega confirmada y stock descontado.");await cargarNotas()}catch(error){App.toast(mensaje(error),"error")}}

  $("btnBuscarPaciente").addEventListener("click",buscarPaciente);$("btnBuscarReceta").addEventListener("click",()=>buscarReceta());$("notaForm").addEventListener("submit",guardarNota);$("ventaDirectaForm").addEventListener("submit",guardarVentaDirecta);$("btnAgregarVenta").addEventListener("click",agregarVenta);$("btnActualizarNotas").addEventListener("click",cargarNotas);$("buscarNota").addEventListener("input",filtrarNotas);$("filtroEstadoNota").addEventListener("change",filtrarNotas);$("tablaNotas").addEventListener("click",e=>{const b=e.target.closest("button[data-ver]");if(b)verNota(Number(b.dataset.ver))});$("btnEditarNota").addEventListener("click",editarNota);$("btnAnularNota").addEventListener("click",anularNota);$("btnEntregarNota").addEventListener("click",entregarNota);cargarProductosVenta();renderVenta();cargarNotas();
})();
