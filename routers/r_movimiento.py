from fastapi import APIRouter, Depends, HTTPException, Query
from asyncpg import Connection

from configuracion.conexion import get_conn
from modelo import m_movimiento as modelo

router = APIRouter(prefix="/movimiento-inventario", tags=["Farmacia - Kardex"])


@router.get("/")
async def listar(
    id_lote: int | None = Query(default=None),
    limit: int = Query(default=300, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    conn: Connection = Depends(get_conn),
):
    return await modelo.listar(conn, id_lote, limit, offset)


@router.get("/{id_movimiento}")
async def obtener(id_movimiento: int, conn: Connection = Depends(get_conn)):
    movimiento = await modelo.obtener(conn, id_movimiento)
    if not movimiento:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")
    return movimiento