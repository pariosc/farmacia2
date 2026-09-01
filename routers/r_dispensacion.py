from asyncpg import Connection
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from configuracion.conexion import get_conn
from configuracion.integracion import IntegracionError, IntegracionNoConfigurada
from configuracion.parametro import config
from configuracion.seguridad import requiere_roles
from entidades.farmacia_dispensacion import (
    AnulacionDispensacionIn,
    NotaDesdeRecetaIn,
    VentaDirectaIn,
)
from modelo import m_dispensacion as modelo
from modelo.m_integracion_atencion import (
    normalizar_prescripciones_paciente,
    normalizar_receta,
    obtener_prescripciones_por_trazabilidad,
    obtener_receta_por_soap,
)


router = APIRouter(prefix="/dispensacion", tags=["Farmacia - Dispensación"])
roles_lectura = requiere_roles("FARMACIA_CONSULTA", "FARMACIA_OPERADOR", "FARMACIA_ADMIN")
roles_operacion = requiere_roles("FARMACIA_OPERADOR", "FARMACIA_ADMIN")


def _error_integracion(error: IntegracionError) -> HTTPException:
    codigo = 503 if isinstance(error, IntegracionNoConfigurada) else 502
    return HTTPException(status_code=codigo, detail=str(error))


async def _consultar_receta(request: Request, numero_receta: int) -> dict:
    try:
        payload = await obtener_receta_por_soap(
            request.app.state.http_integraciones, numero_receta
        )
        receta = normalizar_receta(payload)
    except IntegracionError as error:
        raise _error_integracion(error) from error
    if receta is None:
        raise HTTPException(status_code=404, detail="Receta no encontrada en Atención")
    return receta


@router.get("/")
async def listar(
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    conn: Connection = Depends(get_conn),
    _identidad: dict | None = Depends(roles_lectura),
):
    return await modelo.listar(conn, limit, offset)


@router.get("/receta/{numero_receta}")
async def consultar_receta(
    numero_receta: int,
    request: Request,
    _identidad: dict | None = Depends(roles_operacion),
):
    """Proxy validado: el navegador no se comunica directamente con Atención."""
    return await _consultar_receta(request, numero_receta)


@router.get("/paciente/{id_trazabilidad}/recetas")
async def consultar_por_trazabilidad(
    id_trazabilidad: str,
    request: Request,
    _identidad: dict | None = Depends(roles_operacion),
):
    """Busca por paciente y marca las líneas que aún no son dispensables."""
    try:
        payload = await obtener_prescripciones_por_trazabilidad(
            request.app.state.http_integraciones, id_trazabilidad
        )
        resultado = normalizar_prescripciones_paciente(payload, id_trazabilidad)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except IntegracionError as error:
        raise _error_integracion(error) from error
    if resultado is None:
        raise HTTPException(
            status_code=404, detail="El paciente no tiene prescripciones en Atención"
        )
    return resultado


@router.post("/desde-receta/{numero_receta}", status_code=201)
async def registrar_desde_receta(
    numero_receta: int,
    datos: NotaDesdeRecetaIn,
    request: Request,
    conn: Connection = Depends(get_conn),
    identidad: dict | None = Depends(roles_operacion),
):
    # Seguridad sustituye id_usuario y exige rol cuando su URL está configurada;
    # el valor del body existe solo para el ambiente manual transitorio.
    receta = await _consultar_receta(request, numero_receta)
    if identidad:
        datos = datos.model_copy(update={"id_usuario": identidad["id_usuario"]})
    try:
        return await modelo.registrar_desde_receta(
            conn, numero_receta, receta, datos, config.reserva_dispensacion_minutos
        )
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/venta-directa", status_code=201)
async def registrar_venta_directa(
    datos: VentaDirectaIn,
    conn: Connection = Depends(get_conn),
    identidad: dict | None = Depends(roles_operacion),
):
    """Venta sin receta para productos OTC, con la misma garantía de cobro."""
    if identidad:
        datos = datos.model_copy(update={"id_usuario": identidad["id_usuario"]})
    try:
        return await modelo.registrar_venta_directa(
            conn, datos, config.reserva_dispensacion_minutos
        )
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.get("/{id_dispensacion}")
async def obtener(
    id_dispensacion: int,
    conn: Connection = Depends(get_conn),
    _identidad: dict | None = Depends(roles_lectura),
):
    dispensacion = await modelo.obtener(conn, id_dispensacion)
    if not dispensacion:
        raise HTTPException(status_code=404, detail="Dispensación no encontrada")
    return dispensacion


@router.put("/{id_dispensacion}/corregir")
async def corregir(
    id_dispensacion: int,
    datos: NotaDesdeRecetaIn,
    request: Request,
    conn: Connection = Depends(get_conn),
    identidad: dict | None = Depends(roles_operacion),
):
    actual = await modelo.obtener(conn, id_dispensacion)
    if not actual:
        raise HTTPException(status_code=404, detail="Dispensación no encontrada")
    try:
        numero = int(actual["numero_receta_externa"])
    except (TypeError, ValueError) as error:
        raise HTTPException(
            status_code=409,
            detail="La dispensación histórica no tiene un número de receta integrable",
        ) from error
    receta = await _consultar_receta(request, numero)
    if identidad:
        datos = datos.model_copy(update={"id_usuario": identidad["id_usuario"]})
    try:
        return await modelo.corregir_pendiente(
            conn, id_dispensacion, receta, datos,
            config.reserva_dispensacion_minutos,
        )
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.put("/{id_dispensacion}/confirmar")
async def confirmar(
    id_dispensacion: int,
    conn: Connection = Depends(get_conn),
    _identidad: dict | None = Depends(roles_operacion),
):
    # Cobros debe haber notificado el pago mediante el endpoint de integración.
    # TODO(Cobros): cuando publique consulta de comprobante, corroborar aquí su
    # estado PAGADO/no anulado antes de tocar inventario. Un fallo debe bloquear.
    try:
        dispensacion = await modelo.entregar(conn, id_dispensacion)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    if not dispensacion:
        raise HTTPException(status_code=404, detail="Dispensación no encontrada")
    # TODO(Atención): notificar cantidades entregadas por operación idempotente
    # cuando ese equipo confirme la ruta. Nunca actualizar su tabla directamente.
    return dispensacion


@router.put("/{id_dispensacion}/anular")
async def anular(
    id_dispensacion: int,
    datos: AnulacionDispensacionIn,
    conn: Connection = Depends(get_conn),
    _identidad: dict | None = Depends(roles_operacion),
):
    try:
        dispensacion = await modelo.anular_pendiente(conn, id_dispensacion, datos)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    if not dispensacion:
        raise HTTPException(status_code=404, detail="Dispensación no encontrada")
    return dispensacion


@router.put("/{id_dispensacion}/solicitar-anulacion")
async def solicitar_anulacion(
    id_dispensacion: int,
    datos: AnulacionDispensacionIn,
    conn: Connection = Depends(get_conn),
    _identidad: dict | None = Depends(roles_operacion),
):
    # TODO(Cobros): enviar la solicitud idempotente a su API cuando confirmen
    # ruta/autenticación. Por ahora queda registrada y la reserva se conserva.
    try:
        dispensacion = await modelo.solicitar_anulacion_pagada(
            conn, id_dispensacion, datos
        )
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    if not dispensacion:
        raise HTTPException(status_code=404, detail="Dispensación no encontrada")
    return dispensacion
