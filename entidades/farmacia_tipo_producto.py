from typing import Optional

from pydantic import BaseModel, Field, field_validator


class TipoProducto(BaseModel):
    id_tipo_producto: Optional[int] = None
    codigo: str = Field(min_length=1, max_length=30)
    nombre: str = Field(min_length=1, max_length=100)
    descripcion: Optional[str] = Field(default=None, max_length=255)
    activo: bool = True

    @field_validator("codigo")
    @classmethod
    def normalizar_codigo(cls, valor: str) -> str:
        return valor.strip().upper()

    @field_validator("nombre")
    @classmethod
    def limpiar_nombre(cls, valor: str) -> str:
        return valor.strip()

    @field_validator("descripcion")
    @classmethod
    def limpiar_descripcion(cls, valor: Optional[str]) -> Optional[str]:
        if valor is None:
            return None
        texto = valor.strip()
        return texto or None
