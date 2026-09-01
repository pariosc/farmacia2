(() => {
  "use strict";

  const $ = id => document.getElementById(id);
  const errorText = error => error.message === "Failed to fetch" ? "No se pudo conectar con el servidor." : error.message;
  const numero = value => Number(value || 0).toLocaleString("es-BO", {maximumFractionDigits: 2});
  const moneda = value => `Bs ${Number(value || 0).toLocaleString("es-BO", {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
  const fechaLegible = value => value ? new Intl.DateTimeFormat("es-BO", {timeZone: "UTC"}).format(new Date(`${value}T00:00:00Z`)) : "—";
  const badge = (clase, texto) => `<span class="badge-soft ${clase}">${texto}</span>`;
  const pct = (valor, maximo) => `${maximo > 0 ? Math.max(2, Math.round((valor / maximo) * 100)) : 0}%`;
  const barra = (ancho, clase = "") => `<div class="rep-track"><div class="rep-fill ${clase}" style="width:${ancho}"></div></div>`;

  function rango() {
    const params = new URLSearchParams();
    if ($("reporteDesde").value) params.set("desde", $("reporteDesde").value);
    if ($("reporteHasta").value) params.set("hasta", $("reporteHasta").value);
    const query = params.toString();
    return query ? `?${query}` : "";
  }

  function descargar(clave, formato, todo) {
    const params = new URLSearchParams();
    if (clave === "vencimientos") {
      params.set("dias", Math.max(0, Number($("reporteDias").value) || 0));
    } else if (clave !== "stock" && !todo) {
      if ($("reporteDesde").value) params.set("desde", $("reporteDesde").value);
      if ($("reporteHasta").value) params.set("hasta", $("reporteHasta").value);
    }
    params.set("formato", formato);
    const query = params.toString();
    window.location.assign(`/reporte/${clave}/exportar${query ? `?${query}` : ""}`);
  }

  const REPORTES = {
    compras: {
      url: () => `/reporte/compras-por-proveedor${rango()}`,
      contador: filas => `${filas.length} proveedor${filas.length === 1 ? "" : "es"} con compras`,
      cuerpo(filas) {
        const max = Math.max(...filas.map(r => Number(r.total_comprado)));
        return filas.map(r => `<tr><td class="product-name">${App.escapeHtml(r.razon_social)}</td>`
          + `<td class="text-end">${numero(r.numero_compras)}</td>`
          + `<td class="text-end"><span class="fw-semibold">${moneda(r.total_comprado)}</span>${barra(pct(Number(r.total_comprado), max))}</td></tr>`).join("");
      },
    },
    movimientos: {
      url: () => `/reporte/movimientos-resumen${rango()}`,
      contador: filas => `${filas.length} producto${filas.length === 1 ? "" : "s"} con movimientos`,
      cuerpo(filas) {
        const max = Math.max(...filas.flatMap(r => [Number(r.total_entradas), Number(r.total_salidas)]));
        return filas.map(r => `<tr><td><span class="product-name">${App.escapeHtml(r.nombre_producto)}</span><span class="product-detail">${App.escapeHtml(r.codigo)}</span></td>`
          + `<td class="text-end">${numero(r.total_entradas)}</td>`
          + `<td class="text-end">${numero(r.total_salidas)}</td>`
          + `<td class="text-end">${numero(r.total_ajustes)}</td>`
          + `<td class="text-end">${numero(r.numero_movimientos)}</td>`
          + `<td class="report-col-bar"><div class="rep-dual">${barra(pct(Number(r.total_entradas), max), "is-in")}${barra(pct(Number(r.total_salidas), max), "is-out")}</div></td></tr>`).join("");
      },
    },
    stock: {
      url: () => "/reporte/stock-bajo",
      contador: filas => `${filas.length} producto${filas.length === 1 ? "" : "s"} en o por debajo del mínimo`,
      cuerpo(filas) {
        return filas.map(r => {
          const minimo = Number(r.stock_minimo);
          const cobertura = minimo > 0 ? Math.min(100, Math.round((Number(r.stock_total) / minimo) * 100)) : 0;
          const clase = r.estado === "AGOTADO" ? "is-danger" : "is-warn";
          return `<tr><td><span class="product-name">${App.escapeHtml(r.nombre_producto)}</span><span class="product-detail">${App.escapeHtml(r.codigo)}</span></td>`
            + `<td class="text-end fw-semibold">${numero(r.stock_total)} ${App.escapeHtml(r.unidad_medida)}</td>`
            + `<td class="text-end">${numero(r.stock_minimo)}</td>`
            + `<td class="report-col-bar">${barra(`${cobertura}%`, clase)}<span class="rep-caption">${cobertura}%</span></td>`
            + `<td>${r.estado === "AGOTADO" ? badge("danger", "Agotado") : badge("warning", "Stock bajo")}</td></tr>`;
        }).join("");
      },
    },
    vencimientos: {
      url: () => `/reporte/vencimientos?dias=${encodeURIComponent(Math.max(0, Number($("reporteDias").value) || 0))}`,
      contador: filas => `${filas.length} lote${filas.length === 1 ? "" : "s"} con stock afectado`,
      cuerpo(filas) {
        return filas.map(r => {
          const dias = Number(r.dias_para_vencer);
          return `<tr><td><span class="product-name">${App.escapeHtml(r.nombre_producto)}</span><span class="product-detail">${App.escapeHtml(r.codigo)}</span></td>`
            + `<td>${App.escapeHtml(r.numero_lote)}</td>`
            + `<td>${fechaLegible(r.fecha_vencimiento)}</td>`
            + `<td class="text-end">${numero(r.stock_actual)}</td>`
            + `<td class="text-end ${dias < 0 ? "rep-neg" : ""}">${numero(dias)}</td>`
            + `<td>${r.estado === "VENCIDO" ? badge("danger", "Vencido") : badge("warning", "Por vencer")}</td></tr>`;
        }).join("");
      },
    },
  };

  function mostrar(item, rol) {
    ["carga", "error", "vacio", "tabla"].forEach(r => item.querySelector(`[data-role="${r}"]`).classList.toggle("d-none", r !== rol));
  }

  async function generar(clave) {
    const config = REPORTES[clave];
    const item = document.querySelector(`.accordion-item[data-reporte="${clave}"]`);
    const contador = item.querySelector('[data-role="contador"]');
    mostrar(item, "carga"); contador.textContent = "Generando…";
    try {
      const filas = await App.api(config.url());
      contador.textContent = config.contador(filas);
      if (!filas.length) { mostrar(item, "vacio"); return; }
      item.querySelector('[data-role="cuerpo"]').innerHTML = config.cuerpo(filas);
      mostrar(item, "tabla");
    } catch (error) {
      contador.textContent = "Sin datos";
      item.querySelector('[data-role="error-msg"]').textContent = errorText(error);
      mostrar(item, "error");
    }
  }

  function generarTodo() {
    Object.keys(REPORTES).forEach(generar);
  }

  document.querySelectorAll('[data-dl]').forEach(btn => {
    btn.addEventListener("click", () => descargar(btn.dataset.dl, btn.dataset.formato, btn.dataset.todo === "1"));
  });

  $("btnActualizarReportes").addEventListener("click", generarTodo);
  generarTodo();
})();
