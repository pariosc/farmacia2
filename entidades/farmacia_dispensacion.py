from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Literal, Optional, List
from decimal import Decimal
from datetime import date


class DetalleDispensacionIn(BaseModel):
    id_detalle_comprobante: int
    id_lote: int
    cantidad_entregada: Decimal = Field(gt=0)


class DispensacionIn(BaseModel):
    """Entrada legada; se conserva para clientes antiguos durante la transición."""

    model_config = ConfigDict(extra="forbid")
    id_factura: int
    id_usuario: int
    fecha_dispensacion: date
    observacion: Optional[str] = None
    detalles: List[DetalleDispensacionIn] = Field(min_length=1)


class SeleccionPrescripcion(BaseModel):
    id_prescripcion: int = Field(gt=0)
    cantidad_solicitada: Decimal = Field(gt=0, max_digits=14, decimal_places=2)


class NotaDesdeRecetaIn(BaseModel):
    """Selección del operador; medicamento, precio y paciente se verifican en backend."""

    id_usuario: int = Field(gt=0)
    observacion: Optional[str] = Field(default=None, max_length=255)
    detalles: List[SeleccionPrescripcion] = Field(min_length=1)


class DetalleVentaDirecta(BaseModel):
    id_producto: int = Field(gt=0)
    cantidad_solicitada: Decimal = Field(gt=0, max_digits=14, decimal_places=2)


class VentaDirectaIn(BaseModel):
    """Venta sin receta; el catálogo decide si el producto es OTC."""

    id_usuario: int = Field(gt=0)
    id_paciente: str | None = Field(default=None, min_length=1, max_length=80)
    observacion: Optional[str] = Field(default=None, max_length=255)
    detalles: List[DetalleVentaDirecta] = Field(min_length=1)


class AnulacionDispensacionIn(BaseModel):
    motivo: str = Field(min_length=3, max_length=255)


class PagoDispensacionIn(BaseModel):
    """Notificación idempotente de Cobros; proteger la ruta con servicio-a-servicio."""

    id_factura: int = Field(gt=0)
    id_paciente: str | None = Field(default=None, min_length=1, max_length=80)
    total: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    version: int = Field(gt=0)
    estado: Literal["PAGADA"] = "PAGADA"

    @field_validator("id_paciente", mode="before")
    @classmethod
    def normalizar_paciente(cls, valor):
        return str(valor).strip()


class ConfirmacionAnulacionCobrosIn(BaseModel):
    id_factura: int = Field(gt=0)
    version: int = Field(gt=0)
    estado: Literal["ANULADA"] = "ANULADA"
