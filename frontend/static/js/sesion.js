(() => {
  "use strict";

  const STORAGE_KEY = "hospital_user";

  const obtenerUsuarioActual = () => {
    let storedUser;
    try {
      storedUser = localStorage.getItem(STORAGE_KEY);
    } catch (_) {
      return null;
    }
    if (!storedUser) return null;
    try {
      const user = JSON.parse(storedUser);
      if (!user || typeof user.username !== "string" || !user.username.trim()) {
        throw new Error("Sesión visual inválida");
      }
      return {
        id_usuario: Number.isInteger(Number(user.id_usuario)) && Number(user.id_usuario) > 0
          ? Number(user.id_usuario)
          : null,
        username: user.username.trim(),
        role: typeof user.role === "string" && user.role.trim()
          ? user.role.trim().toUpperCase()
          : null,
      };
    } catch (_) {
      try { localStorage.removeItem(STORAGE_KEY); } catch (_) {}
      return null;
    }
  };

  const guardarUsuario = user => {
    const normalized = {
      id_usuario: Number.isInteger(Number(user.id_usuario)) && Number(user.id_usuario) > 0
        ? Number(user.id_usuario)
        : null,
      username: String(user.username || "").trim(),
      role: user.role ? String(user.role).trim().toUpperCase() : null,
    };
    if (!normalized.username) throw new Error("El usuario de Seguridad es inválido");
    localStorage.setItem(STORAGE_KEY, JSON.stringify(normalized));
    return normalized;
  };

  const cerrarSesion = () => {
    try { localStorage.removeItem(STORAGE_KEY); } catch (_) {}
    window.location.replace("/login");
  };

  window.AppSession = {obtenerUsuarioActual, guardarUsuario, cerrarSesion};

  const user = obtenerUsuarioActual();
  if (document.documentElement.dataset.sesionVisual === "required" && !user) {
    window.location.replace("/login");
    return;
  }

  document.addEventListener("DOMContentLoaded", () => {
    if (!user) return;
    const name = document.getElementById("usuarioNombre");
    const role = document.getElementById("usuarioRol");
    const avatar = document.getElementById("usuarioAvatar");
    const logout = document.getElementById("btnCerrarSesion");
    if (name) name.textContent = user.username;
    if (role) role.textContent = user.role || "Rol pendiente";
    if (avatar) avatar.textContent = user.username.charAt(0).toUpperCase();
    if (logout) logout.addEventListener("click", cerrarSesion);
  });
})();
