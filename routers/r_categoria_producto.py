from fastapi import APIRouter, Depends, HTTPException
from asyncpg import Connection

from configuracion.conexion import get_conn
from entidades.farmacia_catalogo import CategoriaProducto
from modelo import m_categoria_producto as modelo

router = APIRouter(prefix="/categoria-producto", tags=["Farmacia - Categorías"])


@router.get("/")
async def listar(conn: Connection = Depends(get_conn)):
    return await modelo.listar(conn)


@router.get("/{id_categoria}")
async def obtener(id_categoria: int, conn: Connection = Depends(get_conn)):
    categoria = await modelo.obtener(conn, id_categoria)
    if not categoria:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    return categoria


@router.post("/", status_code=201)
async def crear(datos: CategoriaProducto, conn: Connection = Depends(get_conn)):
    try:
        return await modelo.insertar(conn, datos.nombre, datos.descripcion, datos.activo)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.put("/{id_categoria}")
async def actualizar(id_categoria: int, datos: CategoriaProducto, conn: Connection = Depends(get_conn)):
    try:
        categoria = await modelo.actualizar(conn, id_categoria, datos.nombre, datos.descripcion, datos.activo)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    if not categoria:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    return categoria


@router.delete("/{id_categoria}")
async def eliminar(id_categoria: int, conn: Connection = Depends(get_conn)):
    if not await modelo.eliminar(conn, id_categoria):
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    return {"mensaje": "Categoría eliminada"}