"""Cliente para las prescripciones de Internación que consume Farmacia."""

from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict, AliasChoices

from configuracion.integracion import pedir_json
from configuracion.parametro import config


class PrescripcionInternacion(BaseModel):
    model_config = ConfigDict(extra="allow")

    id_prescripcion: int = Field(gt=0)
    id_producto: int = Field(gt=0)
    cantidad: Decimal = Field(gt=0)
    id_paciente: int | str | None = None
    nombre_producto: str = Field(
        min_length=1,
        validation_alias=AliasChoices("nombre_producto", "nombre_medicamento"),
    )
    dosis: str | None = None
    frecuencia: str | None = None
    via_administracion: str | None = None
    duracion: str | None = None


async def obtener_prescripciones(cliente, id_prescripcion: int | None = None):
    """Consulta las prescripciones pendientes publicadas por Internación."""
    payload = await pedir_json(
        cliente,
        config.integracion_consumo_url or config.integracion_solicitudes_url,
        "/prescripcion/farmacia/",
    )
    if payload is None:
        return []
    items = payload.get("prescripciones", []) if isinstance(payload, dict) else payload
    if not isinstance(items, list):
        raise ValueError("Internación devolvió un formato inválido")
    resultado = [PrescripcionInternacion.model_validate(item).model_dump() for item in items]
    if id_prescripcion is not None:
        resultado = [item for item in resultado if item["id_prescripcion"] == id_prescripcion]
    return resultado
