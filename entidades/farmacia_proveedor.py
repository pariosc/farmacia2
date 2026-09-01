from pydantic import BaseModel
from typing import Optional


class Proveedor(BaseModel):
    id_proveedor: Optional[int] = None
    razon_social: str
    nit: Optional[str] = None
    telefono: Optional[str] = None
    correo: Optional[str] = None
    direccion: Optional[str] = None
    activo: bool = True