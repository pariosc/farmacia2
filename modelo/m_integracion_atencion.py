"""Adaptadores salientes hacia las recetas del módulo de Atención.

Se mantienen las dos rutas comunicadas por ese equipo: consulta exacta por
SOAP y búsqueda por trazabilidad. Toda adaptación de su JSON debe quedar aquí.
"""

import httpx
import re
from urllib.parse import quote

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
)
from decimal import Decimal

from configuracion.integracion import IntegracionError, pedir_json
from configuracion.parametro import config


async def obtener_receta_por_soap(
    cliente: httpx.AsyncClient,
    numero_receta: int,
) -> dict | None:
    """Obtiene la receta original; no la modifica ni descuenta inventario.

    La respuesta se valida con ``normalizar_receta`` antes de usarla. Falta
    contrastar ese schema con una muestra real del equipo de Atención.
    """
    if numero_receta <= 0:
        raise ValueError("El número de receta debe ser positivo")
    return await pedir_json(
        cliente,
        config.integracion_atencion_url,
        f"/clinica/prescripcion/soap/{numero_receta}",
    )


async def obtener_prescripciones_por_trazabilidad(
    cliente: httpx.AsyncClient,
    id_trazabilidad: str,
) -> list[dict] | dict | None:
    """Consulta el endpoint anunciado el 31/08/2026 para Farmacia."""
    identificador = id_trazabilidad.strip()
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,80}", identificador):
        raise ValueError("El ID de trazabilidad tiene un formato inválido")
    return await pedir_json(
        cliente,
        config.integracion_atencion_url,
        f"/integracion/farmacia/recetas/{quote(identificador, safe='')}",
    )


class _Paciente(BaseModel):
    model_config = ConfigDict(extra="allow")
    id_paciente: str = Field(min_length=1, max_length=80)
    ci: str | None = None
    nombre_completo: str | None = None

    @field_validator("id_paciente", mode="before")
    @classmethod
    def normalizar_id(cls, valor):
        return str(valor).strip()


class _Linea(BaseModel):
    model_config = ConfigDict(extra="allow")
    id_prescripcion: int = Field(gt=0)
    id_producto: int = Field(gt=0)
    nombre_producto: str | None = None
    cantidad_prescrita: Decimal = Field(gt=0)
    dosis_instrucciones: str | None = None


class _Receta(BaseModel):
    model_config = ConfigDict(extra="allow")
    id_receta: int = Field(gt=0)
    version: int = Field(default=1, gt=0)
    estado: str
    paciente: _Paciente
    detalles: list[_Linea] = Field(min_length=1)


class _PrescripcionPaciente(BaseModel):
    """Respuesta actual; los campos opcionales son los pedidos para mañana."""

    model_config = ConfigDict(extra="allow")
    id_prescripcion: int = Field(gt=0)
    medicamento: str = Field(
        min_length=1,
        validation_alias=AliasChoices("medicamento", "nombre_producto"),
    )
    dosis: str | None = None
    cantidad: Decimal = Field(
        gt=0,
        validation_alias=AliasChoices("cantidad", "cantidad_prescrita"),
    )
    indicaciones: str | None = Field(
        default=None,
        validation_alias=AliasChoices("indicaciones", "dosis_instrucciones"),
    )
    id_producto: int | None = Field(default=None, gt=0)
    id_receta: int | None = Field(default=None, gt=0)
    numero_receta: str | None = None
    estado_receta: str | None = None
    version_receta: int | None = Field(default=None, gt=0)


def normalizar_receta(payload: dict | None) -> dict | None:
    """Valida el JSON acordado sin convertir un payload ambiguo en receta."""
    if payload is None:
        return None
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        payload = payload["data"]
    try:
        receta = _Receta.model_validate(payload)
    except ValidationError as error:
        # TODO(Atención): si el JSON real difiere, adaptar únicamente aquí y
        # actualizar la prueba de contrato; no aceptar campos enviados por UI.
        raise IntegracionError(
            "Atención devolvió una receta con formato distinto al contrato acordado"
        ) from error
    normalizada = receta.model_dump()
    normalizada["estado"] = normalizada["estado"].strip().upper()
    return normalizada


def normalizar_prescripciones_paciente(
    payload: list | dict | None,
    id_trazabilidad: str,
) -> dict | None:
    """Acepta la respuesta improvisada, pero informa si aún no es dispensable.

    Esta función nunca intenta resolver productos por nombre. Hasta recibir
    ``id_producto``, receta y estado firmado, la línea es solo informativa.
    """
    if payload is None:
        return None
    if isinstance(payload, dict):
        if isinstance(payload.get("data"), list):
            payload = payload["data"]
        elif isinstance(payload.get("prescripciones"), list):
            payload = payload["prescripciones"]
    if not isinstance(payload, list):
        raise IntegracionError(
            "Atención devolvió un formato inválido para la búsqueda por paciente"
        )

    resultado = []
    faltantes_globales: set[str] = set()
    try:
        lineas = [_PrescripcionPaciente.model_validate(item) for item in payload]
    except ValidationError as error:
        raise IntegracionError(
            "Atención devolvió prescripciones con formato distinto al documentado"
        ) from error

    for linea in lineas:
        faltantes = []
        if linea.id_producto is None:
            faltantes.append("id_producto")
        if linea.id_receta is None and not linea.numero_receta:
            faltantes.append("id_receta_o_numero_receta")
        estado = (linea.estado_receta or "").strip().upper()
        if not estado:
            faltantes.append("estado_receta")
        elif estado != "FIRMADA":
            faltantes.append(f"estado_no_dispensable:{estado}")
        faltantes_globales.update(faltantes)
        item = linea.model_dump()
        item["estado_receta"] = estado or None
        item["integrable"] = not faltantes
        item["faltantes"] = faltantes
        resultado.append(item)

    return {
        "id_trazabilidad": id_trazabilidad.strip(),
        "prescripciones": resultado,
        "integrable": bool(resultado) and not faltantes_globales,
        "faltantes": sorted(faltantes_globales),
    }
