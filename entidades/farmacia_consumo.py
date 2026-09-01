from pydantic import BaseModel, Field, model_validator
from typing import Optional, List
from decimal import Decimal
from datetime import date


class DetalleConsumoIn(BaseModel):
    id_detalle_solicitud_consumo: Optional[int] = None
    id_detalle_prescripcion: Optional[int] = None
    id_producto: Optional[int] = Field(default=None, gt=0)
    id_lote: Optional[int] = Field(default=None, gt=0)
    cantidad_entregada: Decimal = Field(gt=0)

    @model_validator(mode="after")
    def validar_origen(self):
        if self.id_detalle_solicitud_consumo is None and self.id_detalle_prescripcion is None:
            raise ValueError(
                "Cada detalle debe indicar id_detalle_solicitud_consumo o "
                "id_detalle_prescripcion (al menos uno)."
            )
        if self.id_producto is None and self.id_lote is None:
            raise ValueError("Cada detalle debe indicar id_producto o id_lote")
        return self


class ConsumoInternoIn(BaseModel):
    id_solicitud_insumo: Optional[int] = None
    id_prescripcion: Optional[int] = None
    id_usuario: int
    fecha_consumo: date
    observacion: Optional[str] = None
    detalles: List[DetalleConsumoIn] = Field(min_length=1)

    @model_validator(mode="after")
    def validar_origen(self):
        if self.id_solicitud_insumo is None and self.id_prescripcion is None:
            raise ValueError(
                "El consumo debe indicar id_solicitud_insumo (flujo antiguo) o "
                "id_prescripcion (flujo conectado a Internación) — al menos uno."
            )
        return self
