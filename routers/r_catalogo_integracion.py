from typing import Optional

from asyncpg import Connection
from fastapi import APIRouter, Depends, HTTPException, Query

from configuracion.conexion import get_conn
from entidades.farmacia_integracion import ProductoCatalogoIntegracion
from modelo import m_catalogo_integracion as modelo


# CONTRATO SALIENTE PARA ATENCIÓN:
# El médico debe guardar id_producto como identificador del medicamento en la
# receta. Si el otro equipo cambia su cliente, no cambiar estas respuestas sin
# coordinar primero docs/CONTRATOS_INTEGRACION.md y sus pruebas de contrato.
router = APIRouter(
    prefix="/api/v1/farmacia/productos",
    tags=["Integración - Catálogo de Farmacia"],
)


@router.get(
    "/catalogo",
    response_model=list[ProductoCatalogoIntegracion],
    summary="Catálogo activo de productos para otros módulos",
)
async def listar_catalogo(
    buscar: Optional[str] = Query(default=None, max_length=100),
    id_categoria: Optional[int] = Query(default=None, ge=1),
    id_tipo_producto: Optional[int] = Query(default=None, ge=1),
    conn: Connection = Depends(get_conn),
):
    return await modelo.listar_productos(
        conn,
        buscar=buscar,
        id_categoria=id_categoria,
        id_tipo_producto=id_tipo_producto,
    )


@router.get(
    "/catalogo/{id_producto}",
    response_model=ProductoCatalogoIntegracion,
    summary="Producto activo del catálogo para otros módulos",
)
async def obtener_catalogo(id_producto: int, conn: Connection = Depends(get_conn)):
    producto = await modelo.obtener_producto(conn, id_producto)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto activo no encontrado")
    return producto
