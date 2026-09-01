from fastapi import APIRouter, Depends, HTTPException, Query
from asyncpg import Connection

from configuracion.conexion import get_conn
from entidades.farmacia_compra import CompraIn
from modelo import m_compra as modelo

router = APIRouter(prefix="/compra", tags=["Farmacia - Compras"])


@router.get("/")
async def listar(
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    conn: Connection = Depends(get_conn),
):
    return await modelo.listar(conn, limit, offset)


@router.get("/{id_compra}")
async def obtener(id_compra: int, conn: Connection = Depends(get_conn)):
    compra = await modelo.obtener(conn, id_compra)
    if not compra:
        raise HTTPException(status_code=404, detail="Compra no encontrada")
    return compra


@router.post("/", status_code=201)
async def registrar(datos: CompraIn, conn: Connection = Depends(get_conn)):
    try:
        return await modelo.registrar(conn, datos)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{id_compra}/anular")
async def anular(id_compra: int, conn: Connection = Depends(get_conn)):
    compra = await modelo.anular(conn, id_compra)
    if not compra:
        raise HTTPException(status_code=404, detail="Compra no encontrada o ya anulada")
    return compra