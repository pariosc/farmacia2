(() => {
  "use strict";
  const escapeHtml = (value = "") => String(value).replace(/[&<>'"]/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[char]));
  const api = async (url, options = {}) => {
    const response = await fetch(url, {headers:{"Content-Type":"application/json", ...(options.headers || {})}, ...options});
    if (!response.ok) {
      let message = `Error ${response.status}`;
      try { const body = await response.json(); message = body.detail || body.mensaje || message; } catch (_) {}
      throw new Error(Array.isArray(message) ? message.map(item => item.msg).join(". ") : message);
    }
    return response.status === 204 ? null : response.json();
  };
  const toast = (message, type = "success") => {
    const container = document.getElementById("toastContainer"); if (!container) return;
    const el = document.createElement("div");
    el.className = `toast align-items-center text-bg-${type === "error" ? "danger" : "success"} border-0`;
    el.setAttribute("role", "status"); el.innerHTML = `<div class="d-flex"><div class="toast-body">${escapeHtml(message)}</div><button class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Cerrar"></button></div>`;
    container.append(el); const instance = new bootstrap.Toast(el, {delay:3500}); el.addEventListener("hidden.bs.toast", () => el.remove()); instance.show();
  };
  window.App = {api, escapeHtml, toast};
})();
