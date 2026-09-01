from pydantic import BaseModel, Field, model_validator
from typing import Optional
from decimal import Decimal


class CategoriaProducto(BaseModel):
    id_categoria: Optional[int] = None
    nombre: str
    descripcion: Optional[str] = None
    activo: bool = True


class Producto(BaseModel):
    id_producto: Optional[int] = None
    id_categoria: int
    codigo: str
    nombre: str
    id_tipo_producto: Optional[int] = None
    tipo_producto: Optional[str] = None  # Compatibilidad temporal
    principio_activo: Optional[str] = None
    concentracion: Optional[str] = None
    presentacion: Optional[str] = None
    unidad_medida: str
    stock_minimo: Decimal = Decimal("0")
    precio_venta: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2)
    requiere_receta: bool = False
    activo: bool = True

    @model_validator(mode="after")
    def validar_tipo(self):
        if self.id_tipo_producto is None and not self.tipo_producto:
            raise ValueError("Debe indicar id_tipo_producto o tipo_producto")
        if self.tipo_producto:
            self.tipo_producto = self.tipo_producto.strip().upper()
        return self
