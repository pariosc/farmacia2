(() => {
  "use strict";

  const $ = id => document.getElementById(id);
  const state = {consumos: [], productos: [], lotes: []};
  const modal = new bootstrap.Modal($("consumoModal"));
  const show = (id, visible) => $(id).classList.toggle("d-none", !visible);
  const errorText = error => error.message === "Failed to fetch" ? "No se pudo conectar con el servidor." : error.message;
  const fecha = value => value ? new Intl.DateTimeFormat("es-BO", {timeZone:"UTC"}).format(new Date(`${value}T00:00:00Z`)) : "—";
  const hoy = () => new Date().toISOString().slice(0,10);
  const cantidad = value => Number(value || 0).toLocaleString("es-BO", {minimumFractionDigits:0,maximumFractionDigits:2});
  function agregarPrescripcion(p){$("consumoPrescripcion").value=p.id_prescripcion;$("consumoSolicitud").value="";const row=document.createElement("tr");row.innerHTML=`<td><input type="hidden" class="cons-producto-id" value="${p.id_producto}"><span class="product-name">${App.escapeHtml(p.nombre_producto)}</span><span class="product-detail">Producto #${p.id_producto}</span></td><td><input class="form-control cons-ref-detalle" type="number" min="1" required value="${p.id_detalle||p.id_prescripcion}"></td><td><input class="form-control cons-cantidad" type="number" min="0.01" max="${p.cantidad}" step="0.01" required value="${p.cantidad}"></td><td class="text-end"><button class="btn btn-sm btn-outline-danger cons-quitar" type="button">Quitar</button></td>`;$(`detallesConsumo`).append(row)}
  function renderPrescripcionesInternacion(items){const grupos=items.reduce((acc,p)=>{if(!acc[p.id_prescripcion])acc[p.id_prescripcion]=[];acc[p.id_prescripcion].push(p);return acc},{});$("tablaPrescripcionesInternacion").innerHTML=Object.entries(grupos).map(([id,lineas])=>{const paciente=lineas[0].id_paciente??"—";return `<tr><td colspan="6"><details><summary><strong>Prescripción #${id}</strong> · Paciente ${App.escapeHtml(paciente)} · ${lineas.length} producto${lineas.length===1?"":"s"}</summary><div class="table-responsive mt-3"><table class="table table-sm"><thead><tr><th>Producto</th><th>Cantidad</th><th>Indicaciones</th><th>Acción</th></tr></thead><tbody>${lineas.map(p=>`<tr><td><span class="product-name">${App.escapeHtml(p.nombre_producto)}</span><span class="product-detail">ID: ${p.id_producto}</span></td><td>${cantidad(p.cantidad)}</td><td>${App.escapeHtml([p.dosis,p.frecuencia,p.via_administracion,p.duracion].filter(Boolean).join(" · ")||"—")}</td><td><button class="btn btn-sm btn-outline-primary usar-prescripcion" type="button" data-id="${p.id_detalle||p.id_prescripcion}">Agregar</button></td></tr>`).join("")}</tbody></table></div></details></td></tr>`}).join("")}
  async function cargarPrescripcionesInternacion(){const boton=$("btnCargarPrescripcionesInternacion");show("prescripcionesInternacionCarga",true);show("prescripcionesInternacionResultado",false);show("prescripcionesInternacionError",false);boton.disabled=true;try{const respuesta=await App.api("/api/v1/farmacia/consumos-internos/prescripciones");const items=respuesta.prescripciones||[];renderPrescripcionesInternacion(items);show("prescripcionesInternacionCarga",false);show("prescripcionesInternacionResultado",true);window._prescripcionesInternacion=items}catch(error){show("prescripcionesInternacionCarga",false);$("prescripcionesInternacionError").textContent=errorText(error);show("prescripcionesInternacionError",true)}finally{boton.disabled=false}}
  const producto = id => state.productos.find(item => item.id_producto === id);
  const lote = id => state.lotes.find(item => item.id_lote === id);
  const badgeEstado = estado => `<span class="badge-soft ${estado === "REGISTRADO" ? "success" : estado === "PENDIENTE" ? "warning" : "muted"}">${App.escapeHtml(estado)}</span>`;
  function opcionesLote(){ const hoy=new Date().toISOString().slice(0,10); return state.lotes.filter(l=>Number(l.stock_actual)>0&&l.estado!=="VENCIDO"&&(!l.fecha_vencimiento||l.fecha_vencimiento>=hoy)).sort((a,b)=>(a.fecha_vencimiento||"9999").localeCompare(b.fecha_vencimiento||"9999")).map(l=>{const p=producto(l.id_producto);return `<option value="${l.id_lote}">${App.escapeHtml(p?.nombre||`Producto #${l.id_producto}`)} — ${App.escapeHtml(l.numero_lote)} (disp. ${cantidad(l.stock_actual)})</option>`}).join(""); }
  function agregarDetalle(){const row=document.createElement("tr");row.innerHTML=`<td><select class="form-select cons-lote" required><option value="">Selecciona producto y lote</option>${opcionesLote()}</select></td><td><input class="form-control cons-ref-detalle" type="number" min="1" required placeholder="Referencia"></td><td><input class="form-control cons-cantidad" type="number" min="0.01" step="0.01" required value="1"></td><td class="text-end"><button class="btn btn-sm btn-outline-danger cons-quitar" type="button">Quitar</button></td>`;$("detallesConsumo").append(row);}
  function limpiarFormulario(){$("detallesConsumo").innerHTML="";agregarDetalle();$("consumoFormError").classList.add("d-none");}
  async function guardarConsumo(event){event.preventDefault();const form=event.currentTarget;if(!form.checkValidity()){form.classList.add("was-validated");return}const idSolicitud=$("consumoSolicitud").value?Number($("consumoSolicitud").value):null;const idPrescripcion=$("consumoPrescripcion").value?Number($("consumoPrescripcion").value):null;if(!idSolicitud&&!idPrescripcion){$("consumoFormError").textContent="Indica una referencia de solicitud o de prescripción.";$("consumoFormError").classList.remove("d-none");return}const detalles=[...document.querySelectorAll("#detallesConsumo tr")].map(row=>{const refDetalle=Number(row.querySelector(".cons-ref-detalle").value);const producto=row.querySelector(".cons-producto-id");if(idPrescripcion&&producto)return{id_detalle_prescripcion:refDetalle,id_producto:Number(producto.value),cantidad_entregada:row.querySelector(".cons-cantidad").value};return idPrescripcion?{id_detalle_prescripcion:refDetalle,id_lote:Number(row.querySelector(".cons-lote").value),cantidad_entregada:row.querySelector(".cons-cantidad").value}:{id_detalle_solicitud_consumo:refDetalle,id_lote:Number(row.querySelector(".cons-lote").value),cantidad_entregada:row.querySelector(".cons-cantidad").value}});const button=$("btnGuardarConsumo");button.disabled=true;button.textContent="Registrando…";try{await App.api("/consumo-interno/",{method:"POST",body:JSON.stringify({id_solicitud_insumo:idSolicitud,id_prescripcion:idPrescripcion,id_usuario:Number($("consumoUsuario").value),fecha_consumo:$("consumoFecha").value,observacion:$("consumoObservacion").value.trim()||null,detalles})});App.toast("Consumo pendiente registrado.");form.reset();$("consumoUsuario").value=1;limpiarFormulario();await cargarHistorial()}catch(error){$("consumoFormError").textContent=errorText(error);$("consumoFormError").classList.remove("d-none")}finally{button.disabled=false;button.textContent="Registrar pendiente"}}

  async function cargarHistorial() {
    show("consumoCarga", true); show("consumoError", false); show("consumoResultados", false);
    try {
      const [cabeceras, productos, lotes] = await Promise.all([
        App.api("/consumo-interno/"), App.api("/producto-farmacia/"), App.api("/lote/")
      ]);
      state.productos = productos;
      state.lotes = lotes;
      state.consumos = await Promise.all(cabeceras.map(async item => {
        try { return await App.api(`/consumo-interno/${item.id_consumo}`); }
        catch (_) { return {...item, detalles:null}; }
      }));
      show("consumoCarga", false); show("consumoResultados", true); aplicarFiltros();
    } catch (error) {
      show("consumoCarga", false); show("consumoError", true); $("consumoErrorMensaje").textContent = errorText(error);
    }
  }

  function aplicarFiltros() {
    const term = $("buscarConsumo").value.trim().toLocaleLowerCase("es");
    const estado = $("filtroEstadoConsumo").value;
    const desde = $("consumoDesde").value;
    const hasta = $("consumoHasta").value;
    const items = state.consumos.filter(item =>
      (!term || String(item.id_solicitud_insumo).includes(term) || String(item.id_consumo).includes(term)) &&
      (!estado || item.estado === estado) &&
      (!desde || item.fecha_consumo >= desde) && (!hasta || item.fecha_consumo <= hasta)
    );
    $("contadorConsumos").textContent = `${items.length} de ${state.consumos.length} consumo${state.consumos.length === 1 ? "" : "s"} interno${state.consumos.length === 1 ? "" : "s"}`;
    show("vacioConsumos", items.length === 0); show("tablaConsumosContenedor", items.length > 0);
    $("tablaConsumos").innerHTML = items.map(item => `<tr><td>${fecha(item.fecha_consumo)}</td><td><span class="product-name">${item.id_prescripcion ? `Prescripción #${item.id_prescripcion}` : `Solicitud #${item.id_solicitud_insumo}`}</span></td><td>${badgeEstado(item.estado)}</td><td>${Array.isArray(item.detalles) ? `${item.detalles.length} producto${item.detalles.length === 1 ? "" : "s"}` : "No disponible"}</td><td><div class="action-group"><button class="btn btn-sm btn-outline-secondary" data-action="view" data-id="${item.id_consumo}">Ver</button>${item.estado === "PENDIENTE" ? `<button class="btn btn-sm btn-sanitary" data-action="confirm" data-id="${item.id_consumo}">Confirmar</button>` : ""}</div></td></tr>`).join("");
  }

  async function confirmar(id, button) {
    if (!window.confirm("¿Confirmar esta entrega? El stock se descontará y se registrará la salida.")) return;
    button.disabled = true;
    try { await App.api(`/consumo-interno/${id}/confirmar`, {method:"PUT"}); App.toast("Entrega confirmada correctamente."); await cargarHistorial(); }
    catch (error) { App.toast(errorText(error), "error"); button.disabled = false; }
  }

  async function verConsumo(id) {
    show("consumoModalCarga", true); show("consumoModalContenido", false); $("consumoModalError").classList.add("d-none"); modal.show();
    try {
      let item = state.consumos.find(consumo => consumo.id_consumo === id);
      if (!item || !Array.isArray(item.detalles)) item = await App.api(`/consumo-interno/${id}`);
      const faltantes = item.detalles.map(detalle => detalle.id_lote).filter(idLote => !lote(idLote));
      if (faltantes.length) state.lotes.push(...await Promise.all([...new Set(faltantes)].map(idLote => App.api(`/lote/${idLote}`))));
      $("consumoModalTitle").textContent = `Consumo interno #${item.id_consumo}`;
      $("resumenConsumo").innerHTML = `<div><span>${item.id_prescripcion ? "Prescripción" : "Solicitud"}</span><strong>#${item.id_prescripcion || item.id_solicitud_insumo}</strong></div><div><span>Fecha</span><strong>${fecha(item.fecha_consumo)}</strong></div><div><span>Estado</span><strong>${badgeEstado(item.estado)}</strong></div><div><span>Usuario</span><strong>#${item.id_usuario}</strong></div><div><span>Observación</span><strong>${App.escapeHtml(item.observacion || "Sin observación")}</strong></div>`;
      show("detalleConsumoVacio", item.detalles.length === 0); show("detalleConsumoTabla", item.detalles.length > 0);
      $("tablaDetalleConsumo").innerHTML = item.detalles.map(detalle => {
        const lot = lote(detalle.id_lote), prod = producto(lot?.id_producto);
        return `<tr><td><span class="product-name">${App.escapeHtml(prod?.nombre || `Producto #${lot?.id_producto || "—"}`)}</span><span class="product-detail">${App.escapeHtml([prod?.concentracion, prod?.presentacion || prod?.unidad_medida].filter(Boolean).join(" — "))}</span></td><td class="font-monospace">${App.escapeHtml(lot?.numero_lote || `#${detalle.id_lote}`)}</td><td>${fecha(lot?.fecha_vencimiento)}</td><td class="fw-semibold">${cantidad(detalle.cantidad_entregada)} ${App.escapeHtml(prod?.unidad_medida || "")}</td><td>#${detalle.id_detalle_solicitud_consumo}</td></tr>`;
      }).join("");
      show("consumoModalCarga", false); show("consumoModalContenido", true);
    } catch (error) {
      show("consumoModalCarga", false); $("consumoModalError").textContent = errorText(error); $("consumoModalError").classList.remove("d-none");
    }
  }

  $("btnReintentarConsumo").addEventListener("click", cargarHistorial);
  const etiquetaSolicitud=document.querySelector('label[for="consumoSolicitud"]');if(etiquetaSolicitud)etiquetaSolicitud.textContent="Referencia de solicitud (legado)";
  const etiquetaPrescripcion=document.querySelector('label[for="consumoPrescripcion"]');if(etiquetaPrescripcion)etiquetaPrescripcion.textContent="Prescripción de Internación";
  $("btnCargarPrescripcionesInternacion").addEventListener("click", cargarPrescripcionesInternacion);
  $("tablaPrescripcionesInternacion").addEventListener("click", event => {const boton=event.target.closest(".usar-prescripcion");if(!boton)return;const item=(window._prescripcionesInternacion||[]).find(p=>Number(p.id_detalle||p.id_prescripcion)===Number(boton.dataset.id));if(item){$("consumoPacienteTexto").textContent=item.id_paciente??"No informado";show("consumoPacienteResumen",true);if($("consumoPrescripcion").value!==String(item.id_prescripcion))$("detallesConsumo").innerHTML="";agregarPrescripcion(item);document.querySelector('[data-bs-target="#solicitudes-pane"]').click();}});
  $("btnAgregarDetalleConsumo").addEventListener("click", agregarDetalle);
  $("detallesConsumo").addEventListener("click", event => {if(event.target.closest(".cons-quitar")){event.target.closest("tr").remove();if(!$("detallesConsumo").children.length)agregarDetalle();}});
  $("consumoForm").addEventListener("submit", () => {document.querySelectorAll("#detallesConsumo tr").forEach(row => {if(!row.querySelector(".cons-producto-id") && !row.querySelector(".cons-lote")?.value) row.remove();});});
  $("consumoForm").addEventListener("submit", guardarConsumo);
  ["buscarConsumo", "filtroEstadoConsumo", "consumoDesde", "consumoHasta"].forEach(id => $(id).addEventListener(id === "buscarConsumo" ? "input" : "change", aplicarFiltros));
  $("tablaConsumos").addEventListener("click", event => { const button = event.target.closest("button[data-action]"); if (!button) return; const id = Number(button.dataset.id); if (button.dataset.action === "view") verConsumo(id); if (button.dataset.action === "confirm") confirmar(id, button); });
  cargarHistorial().then(() => { limpiarFormulario(); $("consumoFecha").value = hoy(); });
})();
