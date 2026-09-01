from asyncpg import Connection
from fastapi import APIRouter, Depends, HTTPException, Query

from configuracion.conexion import get_conn
from entidades.farmacia_tipo_producto import TipoProducto
from modelo import m_tipo_producto as modelo

router = APIRouter(prefix="/tipo-producto", tags=["Farmacia - Tipos de producto"])


@router.get("/")
async def listar(
    solo_activos: bool = Query(default=False),
    conn: Connection = Depends(get_conn),
):
    return await modelo.listar(conn, solo_activos)


@router.get("/{id_tipo_producto}")
async def obtener(id_tipo_producto: int, conn: Connection = Depends(get_conn)):
    tipo = await modelo.obtener(conn, id_tipo_producto)
    if not tipo:
        raise HTTPException(status_code=404, detail="Tipo de producto no encontrado")
    return tipo


@router.post("/", status_code=201)
async def crear(datos: TipoProducto, conn: Connection = Depends(get_conn)):
    try:
        return await modelo.insertar(conn, datos)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.put("/{id_tipo_producto}")
async def actualizar(
    id_tipo_producto: int,
    datos: TipoProducto,
    conn: Connection = Depends(get_conn),
):
    try:
        tipo = await modelo.actualizar(conn, id_tipo_producto, datos)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    if not tipo:
        raise HTTPException(status_code=404, detail="Tipo de producto no encontrado")
    return tipo
