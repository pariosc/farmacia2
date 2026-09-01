"""Dependencias preparadas para el módulo propietario de Seguridad.

Mientras INTEGRACION_SEGURIDAD_URL esté vacía se conserva el modo transitorio
actual. Al configurarla, todas las rutas que usan ``requiere_roles`` exigen un
Bearer válido y dejan de confiar en el id_usuario del navegador.
"""

from collections.abc import Callable

from fastapi import Header, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from configuracion.integracion import IntegracionError, pedir_json
from configuracion.parametro import config


class _Sesion(BaseModel):
    model_config = ConfigDict(extra="allow")
    id_usuario: int = Field(gt=0)
    username: str
    activo: bool
    roles: list[str]


def requiere_roles(*roles_permitidos: str) -> Callable:
    async def dependencia(
        request: Request,
        authorization: str | None = Header(default=None),
    ) -> dict | None:
        if not config.integracion_seguridad_url:
            # TODO(Seguridad): retirar esta compatibilidad cuando su servicio
            # esté desplegado en todos los ambientes.
            return None
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Falta token de Seguridad")
        try:
            payload = await pedir_json(
                request.app.state.http_integraciones,
                config.integracion_seguridad_url,
                "/seguridad/sesion",
                headers={"Authorization": authorization},
            )
            sesion = _Sesion.model_validate(payload)
        except (IntegracionError, ValidationError) as error:
            raise HTTPException(
                status_code=503,
                detail="No fue posible validar la sesión con Seguridad",
            ) from error
        if not sesion.activo:
            raise HTTPException(status_code=403, detail="Usuario inactivo")
        roles_sesion = {rol.upper() for rol in sesion.roles}
        if roles_permitidos and roles_sesion.isdisjoint(roles_permitidos):
            raise HTTPException(status_code=403, detail="Rol insuficiente en Farmacia")
        return sesion.model_dump()

    return dependencia
