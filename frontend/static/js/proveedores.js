(() => {
  "use strict";

  const $ = id => document.getElementById(id);
  const state = {proveedores: []};
  const proveedorModal = new bootstrap.Modal($("proveedorModal"));
  const campos = ["razonSocial", "nit", "telefono", "correo", "direccion"];
  const show = (id, visible) => $(id).classList.toggle("d-none", !visible);
  const nullable = value => value.trim() || null;
  const errorText = error => error.message.includes("duplicate key")
    ? "Ya existe un proveedor con esos datos."
    : error.message;

  async function cargarProveedores() {
    show("estadoCargaProveedor", true);
    show("estadoErrorProveedor", false);
    show("estadoVacioProveedor", false);
    show("contenedorTablaProveedores", false);
    $("contadorProveedores").textContent = "Cargando proveedores…";
    try {
      state.proveedores = await App.api("/proveedor/");
      aplicarFiltros();
    } catch (error) {
      show("estadoCargaProveedor", false);
      show("estadoErrorProveedor", true);
      $("mensajeErrorProveedor").textContent = errorText(error);
      $("contadorProveedores").textContent = "Sin datos";
    }
  }

  function aplicarFiltros() {
    const term = $("buscarProveedor").value.trim().toLocaleLowerCase("es");
    const estado = $("filtroEstado").value;
    const filtrados = state.proveedores.filter(proveedor => {
      const coincideTexto = !term || [proveedor.razon_social, proveedor.nit]
        .some(value => (value || "").toLocaleLowerCase("es").includes(term));
      const coincideEstado = !estado
        || (estado === "activo" && proveedor.activo)
        || (estado === "inactivo" && !proveedor.activo);
      return coincideTexto && coincideEstado;
    });
    renderProveedores(filtrados);
  }

  function renderProveedores(proveedores) {
    show("estadoCargaProveedor", false);
    show("estadoErrorProveedor", false);
    show("estadoVacioProveedor", proveedores.length === 0);
    show("contenedorTablaProveedores", proveedores.length > 0);
    $("contadorProveedores").textContent = `${proveedores.length} de ${state.proveedores.length} proveedor${state.proveedores.length === 1 ? "" : "es"}`;
    $("tablaProveedores").innerHTML = proveedores.map(proveedor => `
      <tr>
        <td><span class="product-name">${App.escapeHtml(proveedor.razon_social)}</span><span class="product-detail">${App.escapeHtml(proveedor.direccion || "Sin dirección registrada")}</span></td>
        <td class="d-none d-sm-table-cell">${App.escapeHtml(proveedor.nit || "—")}</td>
        <td class="d-none d-lg-table-cell">${App.escapeHtml(proveedor.telefono || "—")}</td>
        <td class="d-none d-md-table-cell">${proveedor.correo ? `<a href="mailto:${App.escapeHtml(proveedor.correo)}">${App.escapeHtml(proveedor.correo)}</a>` : "—"}</td>
        <td><span class="badge-soft ${proveedor.activo ? "success" : "muted"}">${proveedor.activo ? "Activo" : "Inactivo"}</span></td>
        <td><div class="action-group">
          <button class="btn btn-sm btn-outline-secondary" data-action="view" data-id="${proveedor.id_proveedor}" aria-label="Ver ${App.escapeHtml(proveedor.razon_social)}">Ver</button>
          <button class="btn btn-sm btn-outline-secondary" data-action="edit" data-id="${proveedor.id_proveedor}" aria-label="Editar ${App.escapeHtml(proveedor.razon_social)}">Editar</button>
          <button class="btn btn-sm ${proveedor.activo ? "btn-outline-danger" : "btn-outline-success"}" data-action="toggle" data-id="${proveedor.id_proveedor}">${proveedor.activo ? "Desactivar" : "Activar"}</button>
        </div></td>
      </tr>`).join("");
  }

  function completarFormulario(proveedor) {
    $("idProveedor").value = proveedor?.id_proveedor || "";
    $("razonSocial").value = proveedor?.razon_social || "";
    $("nit").value = proveedor?.nit || "";
    $("telefono").value = proveedor?.telefono || "";
    $("correo").value = proveedor?.correo || "";
    $("direccion").value = proveedor?.direccion || "";
  }

  function abrirFormulario(proveedor = null) {
    $("proveedorForm").reset();
    $("proveedorForm").classList.remove("was-validated");
    $("proveedorFormError").classList.add("d-none");
    campos.forEach(id => $(id).disabled = false);
    completarFormulario(proveedor);
    $("proveedorModalTitle").textContent = proveedor ? "Editar proveedor" : "Nuevo proveedor";
    $("btnGuardarProveedor").classList.remove("d-none");
    proveedorModal.show();
  }

  async function verProveedor(id) {
    try {
      const proveedor = await App.api(`/proveedor/${id}`);
      $("proveedorForm").reset();
      $("proveedorFormError").classList.add("d-none");
      completarFormulario(proveedor);
      campos.forEach(campo => $(campo).disabled = true);
      $("proveedorModalTitle").textContent = "Información del proveedor";
      $("btnGuardarProveedor").classList.add("d-none");
      proveedorModal.show();
    } catch (error) {
      App.toast(errorText(error), "error");
    }
  }

  function proveedorPayload(activo = true) {
    return {
      razon_social: $("razonSocial").value.trim(),
      nit: nullable($("nit").value),
      telefono: nullable($("telefono").value),
      correo: nullable($("correo").value),
      direccion: nullable($("direccion").value),
      activo
    };
  }

  async function guardarProveedor(event) {
    event.preventDefault();
    if (!event.currentTarget.checkValidity()) {
      event.currentTarget.classList.add("was-validated");
      return;
    }
    const id = $("idProveedor").value;
    const existente = state.proveedores.find(proveedor => String(proveedor.id_proveedor) === id);
    const button = $("btnGuardarProveedor");
    button.disabled = true;
    button.textContent = "Guardando…";
    try {
      await App.api(id ? `/proveedor/${id}` : "/proveedor/", {
        method: id ? "PUT" : "POST",
        body: JSON.stringify(proveedorPayload(existente?.activo ?? true))
      });
      proveedorModal.hide();
      App.toast(id ? "Proveedor actualizado correctamente." : "Proveedor creado correctamente.");
      await cargarProveedores();
    } catch (error) {
      $("proveedorFormError").textContent = errorText(error);
      $("proveedorFormError").classList.remove("d-none");
    } finally {
      button.disabled = false;
      button.textContent = "Guardar proveedor";
    }
  }

  async function alternarProveedor(id) {
    const proveedor = state.proveedores.find(item => item.id_proveedor === id);
    if (!proveedor) return;
    const accion = proveedor.activo ? "desactivar" : "activar";
    if (!confirm(`¿Deseas ${accion} ${proveedor.razon_social}?`)) return;
    try {
      await App.api(`/proveedor/${id}`, {
        method: "PUT",
        body: JSON.stringify({...proveedor, activo: !proveedor.activo})
      });
      App.toast(`Proveedor ${proveedor.activo ? "desactivado" : "activado"}.`);
      await cargarProveedores();
    } catch (error) {
      App.toast(errorText(error), "error");
    }
  }

  $("btnNuevoProveedor").addEventListener("click", () => abrirFormulario());
  $("btnReintentarProveedor").addEventListener("click", cargarProveedores);
  $("proveedorForm").addEventListener("submit", guardarProveedor);
  $("buscarProveedor").addEventListener("input", aplicarFiltros);
  $("filtroEstado").addEventListener("change", aplicarFiltros);
  $("tablaProveedores").addEventListener("click", event => {
    const button = event.target.closest("button[data-action]");
    if (!button) return;
    const id = Number(button.dataset.id);
    if (button.dataset.action === "view") return verProveedor(id);
    if (button.dataset.action === "edit") return abrirFormulario(state.proveedores.find(proveedor => proveedor.id_proveedor === id));
    alternarProveedor(id);
  });

  cargarProveedores();
})();
