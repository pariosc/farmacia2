from fastapi import APIRouter, Depends, HTTPException
from asyncpg import Connection

from configuracion.conexion import get_conn
from entidades.farmacia_lote import AjusteManual
from modelo import m_lote as modelo, m_movimiento

router = APIRouter(prefix="/lote", tags=["Farmacia - Lotes"])


@router.get("/")
async def listar(conn: Connection = Depends(get_conn)):
    return await modelo.listar(conn)


@router.get("/alertas/stock-bajo")
async def alertas_stock_bajo(conn: Connection = Depends(get_conn)):
    return await modelo.stock_bajo(conn)


@router.get("/alertas/por-vencer")
async def alertas_por_vencer(dias: int = 30, conn: Connection = Depends(get_conn)):
    return await modelo.proximos_a_vencer(conn, dias)


@router.get("/{id_lote}")
async def obtener(id_lote: int, conn: Connection = Depends(get_conn)):
    lote = await modelo.obtener(conn, id_lote)
    if not lote:
        raise HTTPException(status_code=404, detail="Lote no encontrado")
    return lote


@router.get("/{id_lote}/kardex")
async def kardex(id_lote: int, conn: Connection = Depends(get_conn)):
    return await m_movimiento.listar(conn, id_lote)


@router.post("/ajuste-manual", status_code=201)
async def ajuste_manual(datos: AjusteManual, conn: Connection = Depends(get_conn)):
    try:
        return await m_movimiento.ajuste_manual(
            conn, datos.id_lote, datos.id_usuario, datos.cantidad,
            datos.motivo, datos.fecha_movimiento,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{id_lote}")
async def eliminar(id_lote: int, conn: Connection = Depends(get_conn)):
    if not await modelo.eliminar(conn, id_lote):
        raise HTTPException(status_code=404, detail="Lote no encontrado")
    return {"mensaje": "Lote eliminado"}