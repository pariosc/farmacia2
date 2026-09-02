from asyncpg import Connection
from fastapi import APIRouter, Depends, HTTPException

from configuracion.conexion import get_conn
from entidades.farmacia_dispensacion import (
    ConfirmacionAnulacionCobrosIn,
    PagoDispensacionIn,
)
from modelo import m_dispensacion as modelo


router = APIRouter(
    prefix="/api/v1/farmacia/dispensaciones",
    tags=["Integración - Cobros"],
)


@router.get("/cobros/pendientes")
async def listar_pendientes_cobro(conn: Connection = Depends(get_conn)):
    """Permite a Cobros obtener todas las proformas vigentes."""
    return {"proformas": await modelo.listar_para_cobro(conn)}


@router.get("/{id_dispensacion}/cobro")
async def consultar_para_cobro(
    id_dispensacion: int, conn: Connection = Depends(get_conn)
):
    """Contrato que Cobros consulta por número de nota/proforma."""
    resultado = await modelo.obtener_para_cobro(conn, id_dispensacion)
    if not resultado:
        raise HTTPException(status_code=404, detail="Nota de dispensación no encontrada")
    return resultado


@router.put("/{id_dispensacion}/pago")
async def vincular_pago(
    id_dispensacion: int,
    datos: PagoDispensacionIn,
    conn: Connection = Depends(get_conn),
):
    # TODO(Seguridad/Cobros): proteger con autenticación servicio-a-servicio.
    # La validación de paciente, versión, monto, vigencia y vínculo 1:1 permanece
    # obligatoria aunque la llamada esté autenticada.
    try:
        resultado = await modelo.registrar_pago(conn, id_dispensacion, datos)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    if not resultado:
        raise HTTPException(status_code=404, detail="Nota de dispensación no encontrada")
    return resultado


@router.put("/{id_dispensacion}/anulacion-confirmada")
async def confirmar_anulacion(
    id_dispensacion: int,
    datos: ConfirmacionAnulacionCobrosIn,
    conn: Connection = Depends(get_conn),
):
    # Callback idempotente: solo libera reservas después de que Cobros confirme.
    try:
        resultado = await modelo.confirmar_anulacion_cobros(
            conn, id_dispensacion, datos
        )
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    if not resultado:
        raise HTTPException(status_code=404, detail="Nota de dispensación no encontrada")
    return resultado
