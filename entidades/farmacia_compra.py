from pydantic import BaseModel, Field
from typing import Optional, List
from decimal import Decimal
from datetime import date


class DetalleCompraIn(BaseModel):
    id_producto: int
    numero_lote: str
    fecha_vencimiento: Optional[date] = None
    cantidad: Decimal
    costo_unitario: Decimal


class CompraIn(BaseModel):
    id_proveedor: int
    id_usuario: int
    numero_documento: Optional[str] = None
    fecha_compra: date = Field(default_factory=date.today)
    detalles: List[DetalleCompraIn]
