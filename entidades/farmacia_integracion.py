from typing import Optional

from pydantic import BaseModel


class ProductoCatalogoIntegracion(BaseModel):
    """Vista pública del producto para Atención y otros módulos.

    Deliberadamente no contiene stock, lotes, costos ni precio de venta.
    """

    id_producto: int
    codigo: str
    nombre: str
    principio_activo: Optional[str] = None
    concentracion: Optional[str] = None
    presentacion: Optional[str] = None
    unidad_medida: str
    id_categoria: int
    nombre_categoria: str
    id_tipo_producto: int
    codigo_tipo_producto: str
    nombre_tipo_producto: str
    requiere_receta: bool
