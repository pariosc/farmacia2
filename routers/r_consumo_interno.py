from fastapi import APIRouter, Depends, HTTPException, Query
from asyncpg import Connection

from configuracion.conexion import get_conn
from entidades.farmacia_consumo import ConsumoInternoIn
from modelo import m_consumo_interno as modelo

router = APIRouter(prefix="/consumo-interno", tags=["Farmacia - Consumo Interno"])


@router.get("/")
async def listar(
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    conn: Connection = Depends(get_conn),
):
    return await modelo.listar(conn, limit, offset)


@router.get("/{id_consumo}")
async def obtener(id_consumo: int, conn: Connection = Depends(get_conn)):
    consumo = await modelo.obtener(conn, id_consumo)
    if not consumo:
        raise HTTPException(status_code=404, detail="Consumo interno no encontrado")
    return consumo


@router.post("/", status_code=201)
async def registrar(datos: ConsumoInternoIn, conn: Connection = Depends(get_conn)):
    # INTEGRACIONES PENDIENTES:
    # - Seguridad debe obtener id_usuario/roles desde la sesión.
    # - Internación/Solicitudes debe corroborar por API que la solicitud o
    #   prescripción existe, está autorizada y contiene cada id_producto.
    # Los IDs manuales actuales son únicamente un modo transitorio de prueba.
    # Ver docs/CONTRATOS_INTEGRACION.md.
    try:
        return await modelo.registrar(conn, datos)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{id_consumo}/confirmar")
async def confirmar(id_consumo: int, conn: Connection = Depends(get_conn)):
    # Tras la salida transaccional de inventario, la integración definitiva
    # notificará al módulo propietario mediante una operación idempotente.
    # Nunca descontar stock en el módulo externo ni confirmar ante error de red.
    try:
        consumo = await modelo.confirmar(conn, id_consumo)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    if not consumo:
        raise HTTPException(status_code=404, detail="Consumo interno no encontrado o ya confirmado")
    return consumo


@router.put("/{id_consumo}/anular")
async def anular(id_consumo: int, conn: Connection = Depends(get_conn)):
    consumo = await modelo.anular(conn, id_consumo)
    if not consumo:
        raise HTTPException(status_code=404, detail="Consumo interno no encontrado o ya anulado")
    return consumo
