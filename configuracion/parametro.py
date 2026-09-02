# archivo parametros.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AliasChoices, Field

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # ajusta según dónde quede el .env

class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env",
                                    env_file_encoding="utf-8")
    
    db_name:str
    db_user:str
    db_pass:str
    db_host:str
    db_port:int = 5432
    farmacia_usuario_id: int | None = None

    # URLs base de módulos externos. Permanecen opcionales mientras no exista
    # un contrato confirmado. Ver docs/CONTRATOS_INTEGRACION.md antes de usar.
    seguridad_login_url: str | None = None
    integracion_seguridad_url: str | None = None
    integracion_atencion_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "INTEGRACION_ATENCION_URL", "URL_MODULO_ATENCION"
        ),
    )
    integracion_cobros_url: str | None = None
    integracion_solicitudes_url: str | None = None
    integracion_consumo_url: str | None = None
    integracion_consumo_usuario: str | None = None
    integracion_consumo_clave: str | None = None
    integracion_timeout_segundos: float = 5.0
    # La reserva debe dar tiempo suficiente para que Cobros genere el comprobante.
    # Puede reducirse por entorno, pero por defecto dura cuatro horas.
    reserva_dispensacion_minutos: int = Field(default=240, ge=5, le=240)


config = Config()
