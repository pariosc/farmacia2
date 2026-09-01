"""Infraestructura HTTP común para integraciones salientes.

Este módulo solo administra el cliente y normaliza errores. Los contratos de
Seguridad, Atención, Cobros y Solicitudes deben vivir en adaptadores separados;
no colocar rutas externas directamente dentro de los routers de Farmacia.
"""

import httpx

from configuracion.parametro import config


class IntegracionError(RuntimeError):
    """La API externa falló, respondió inválido o no está disponible."""


class IntegracionNoConfigurada(IntegracionError):
    """La URL base requerida todavía no fue configurada."""


async def abrir_cliente(app):
    """Crea un único cliente reutilizable durante la vida de la aplicación."""
    app.state.http_integraciones = httpx.AsyncClient(
        timeout=config.integracion_timeout_segundos
    )


async def cerrar_cliente(app):
    cliente = getattr(app.state, "http_integraciones", None)
    if cliente is not None:
        await cliente.aclose()


async def pedir_json(
    cliente: httpx.AsyncClient,
    base_url: str | None,
    path: str,
    *,
    method: str = "GET",
    params: dict | None = None,
    json: dict | None = None,
    headers: dict | None = None,
):
    """Ejecuta una llamada JSON sin convertir fallos externos en autorizaciones.

    El adaptador propietario decide cómo interpretar el JSON. Un 404 devuelve
    ``None``; errores de red, JSON inválido u otros HTTP se propagan como
    ``IntegracionError`` para que el router responda 502/503 y detenga el flujo.
    """
    if not base_url:
        raise IntegracionNoConfigurada(f"No existe URL configurada para {path}")

    url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
    try:
        respuesta = await cliente.request(
            method,
            url,
            params=params,
            json=json,
            headers=headers,
        )
    except httpx.HTTPError as error:
        raise IntegracionError(f"No se pudo conectar con {url}") from error

    if respuesta.status_code == 404:
        return None
    if respuesta.status_code >= 400:
        raise IntegracionError(
            f"La integración {url} respondió HTTP {respuesta.status_code}"
        )
    try:
        return respuesta.json()
    except ValueError as error:
        raise IntegracionError(f"La integración {url} no devolvió JSON válido") from error
