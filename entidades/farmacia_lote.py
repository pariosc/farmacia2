from pydantic import BaseModel
from typing import Optional
from decimal import Decimal
from datetime import date


class Lote(BaseModel):
    id_lote: Optional[int] = None
    id_producto: int
    numero_lote: str
    fecha_vencimiento: Optional[date] = None
    stock_actual: Decimal = Decimal("0")
    estado: str = "DISPONIBLE"


class AjusteManual(BaseModel):
    id_lote: int
    id_usuario: int
    cantidad: Decimal          # positivo = entrada, negativo = salida
    motivo: str
    fecha_movimiento: date