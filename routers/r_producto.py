from fastapi import APIRouter, Depends, HTTPException
from asyncpg import Connection

from configuracion.conexion import get_conn
from configuracion.seguridad import requiere_roles
from entidades.farmacia_catalogo import Producto
from modelo import m_producto as modelo

router = APIRouter(prefix="/producto-farmacia", tags=["Farmacia - Productos"])
roles_admin = requiere_roles("FARMACIA_ADMIN")


@router.get("/")
async def listar(conn: Connection = Depends(get_conn)):
    return await modelo.listar(conn)


@router.get("/{id_producto}")
async def obtener(id_producto: int, conn: Connection = Depends(get_conn)):
    producto = await modelo.obtener(conn, id_producto)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return producto


@router.post("/", status_code=201)
async def crear(
    datos: Producto,
    conn: Connection = Depends(get_conn),
    _identidad: dict | None = Depends(roles_admin),
):
    try:
        return await modelo.insertar(conn, datos)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.put("/{id_producto}")
async def actualizar(
    id_producto: int,
    datos: Producto,
    conn: Connection = Depends(get_conn),
    _identidad: dict | None = Depends(roles_admin),
):
    try:
        producto = await modelo.actualizar(conn, id_producto, datos)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return producto


@router.delete("/{id_producto}")
async def eliminar(
    id_producto: int,
    conn: Connection = Depends(get_conn),
    _identidad: dict | None = Depends(roles_admin),
):
    if not await modelo.eliminar(conn, id_producto):
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return {"mensaje": "Producto eliminado"}
