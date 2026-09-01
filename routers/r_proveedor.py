from fastapi import APIRouter, Depends, HTTPException
from asyncpg import Connection

from configuracion.conexion import get_conn
from entidades.farmacia_proveedor import Proveedor
from modelo import m_proveedor as modelo

router = APIRouter(prefix="/proveedor", tags=["Farmacia - Proveedores"])


@router.get("/")
async def listar(conn: Connection = Depends(get_conn)):
    return await modelo.listar(conn)


@router.get("/{id_proveedor}")
async def obtener(id_proveedor: int, conn: Connection = Depends(get_conn)):
    proveedor = await modelo.obtener(conn, id_proveedor)
    if not proveedor:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    return proveedor


@router.post("/", status_code=201)
async def crear(datos: Proveedor, conn: Connection = Depends(get_conn)):
    return await modelo.insertar(conn, datos)


@router.put("/{id_proveedor}")
async def actualizar(id_proveedor: int, datos: Proveedor, conn: Connection = Depends(get_conn)):
    proveedor = await modelo.actualizar(conn, id_proveedor, datos)
    if not proveedor:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    return proveedor


@router.delete("/{id_proveedor}")
async def eliminar(id_proveedor: int, conn: Connection = Depends(get_conn)):
    if not await modelo.eliminar(conn, id_proveedor):
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    return {"mensaje": "Proveedor eliminado"}