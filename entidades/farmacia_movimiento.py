from pydantic import BaseModel
from typing import Optional
from decimal import Decimal
from datetime import date


class MovimientoInventario(BaseModel):
    id_movimiento: Optional[int] = None
    id_lote: int
    id_usuario: int
    id_detalle_compra: Optional[int] = None
    id_detalle_dispensacion: Optional[int] = None
    id_detalle_consumo: Optional[int] = None
    tipo_movimiento: str        # ENTRADA, SALIDA o AJUSTE
    cantidad: Decimal
    fecha_movimiento: date
    motivo: Optional[str] = None