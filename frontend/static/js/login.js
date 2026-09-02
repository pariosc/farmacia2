(() => {
  "use strict";

  const form = document.getElementById("loginForm");
  const usernameInput = document.getElementById("usuario");
  const passwordInput = document.getElementById("password");
  const submitButton = document.getElementById("loginSubmit");
  const errorBox = document.getElementById("loginError");
  const allowedRoles = new Set(["FARMACEUTICO", "ADMINISTRADOR"]);

  if (!form || !window.AppSession) return;

  const showError = message => {
    errorBox.textContent = message;
    errorBox.classList.remove("d-none");
  };

  const clearError = () => {
    errorBox.textContent = "";
    errorBox.classList.add("d-none");
  };

  const setLoading = loading => {
    submitButton.disabled = loading;
    submitButton.textContent = loading ? "Ingresando..." : "Iniciar sesión";
    usernameInput.readOnly = loading;
    passwordInput.readOnly = loading;
  };

  form.addEventListener("submit", async event => {
    event.preventDefault();
    clearError();

    const username = usernameInput.value.trim();
    const password = passwordInput.value;
    const baseUrl = form.dataset.seguridadUrl.trim().replace(/\/+$/, "");
    if (!username || !password) {
      showError("Ingresa tu usuario y contraseña");
      return;
    }
    if (!baseUrl) {
      showError("La URL de login de Seguridad no está configurada");
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`${baseUrl}/login/`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({usuario: username, clave: password}),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.detail || "Usuario o contraseña incorrectos");
      }
      if (!data.usuario || typeof data.usuario !== "string") {
        throw new Error("Seguridad no devolvió el nombre del usuario");
      }

      const rawRole = data.role ?? data.rol ?? null;
      const role = typeof rawRole === "string" && rawRole.trim()
        ? rawRole.trim().toUpperCase()
        : null;
      if (role && !allowedRoles.has(role)) {
        throw new Error("No tienes permiso para ingresar al módulo de Farmacia");
      }

      window.AppSession.guardarUsuario({username: data.usuario, role});
      window.location.replace("/productos");
    } catch (error) {
      passwordInput.value = "";
      showError(error instanceof TypeError
        ? "No se pudo conectar con el módulo de Seguridad"
        : error.message);
      passwordInput.focus();
    } finally {
      setLoading(false);
    }
  });
})();
