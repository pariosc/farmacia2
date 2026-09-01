from datetime import date

from fastapi import APIRouter, Depends, Query
from starlette.responses import Response
from asyncpg import Connection

from configuracion.conexion import get_conn
from modelo import m_reporte as modelo

router = APIRouter(prefix="/reporte", tags=["Farmacia - Reportes"])


def _respuesta_descarga(content: bytes, nombre: str, media_type: str) -> Response:
    headers = {"Content-Disposition": f'attachment; filename="{nombre}"'}
    return Response(content=content, media_type=media_type, headers=headers)


def _nombre_archivo(reporte: str, formato: str, desde: date | None,
                    hasta: date | None, dias: int) -> str:
    """Nombre del archivo con la fecha de generación y el filtro aplicado."""
    hoy = date.today().isoformat()
    parte = ""
    if reporte == "vencimientos":
        parte = f"_{dias}dias"
    elif desde or hasta:
        if desde and hasta:
            parte = f"_{desde.isoformat()}_al_{hasta.isoformat()}"
        elif desde:
            parte = f"_desde_{desde.isoformat()}"
        else:
            parte = f"_hasta_{hasta.isoformat()}"
    return f"reporte_{reporte}{parte}_{hoy}.{formato}"


async def _exportar(reporte: str, formato: str, conn: Connection,
                    desde: date | None, hasta: date | None, dias: int):
    if reporte == "compras":
        filas = await modelo.compras_por_proveedor(conn, desde, hasta)
    elif reporte == "movimientos":
        filas = await modelo.movimientos_resumen(conn, desde, hasta)
    elif reporte == "stock":
        filas = await modelo.stock_bajo_agregado(conn)
    elif reporte == "vencimientos":
        filas = await modelo.vencimientos(conn, dias)
    else:
        raise ValueError(f"Reporte desconocido: {reporte}")

    if formato == "pdf":
        return _respuesta_descarga(
            modelo.exportar_pdf(reporte, filas),
            _nombre_archivo(reporte, "pdf", desde, hasta, dias),
            "application/pdf",
        )
    return _respuesta_descarga(
        modelo.exportar_excel(reporte, filas),
        _nombre_archivo(reporte, "xlsx", desde, hasta, dias),
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@router.get("/{reporte}/exportar")
async def exportar(
    reporte: str,
    formato: str = Query(default="pdf", pattern="^(pdf|xlsx)$"),
    desde: date | None = Query(default=None),
    hasta: date | None = Query(default=None),
    dias: int = Query(default=30, ge=0, le=365),
    conn: Connection = Depends(get_conn),
):
    return await _exportar(reporte, formato, conn, desde, hasta, dias)


@router.get("/compras-por-proveedor")
async def compras_por_proveedor(
    desde: date | None = Query(default=None),
    hasta: date | None = Query(default=None),
    conn: Connection = Depends(get_conn),
):
    return await modelo.compras_por_proveedor(conn, desde, hasta)


@router.get("/movimientos-resumen")
async def movimientos_resumen(
    desde: date | None = Query(default=None),
    hasta: date | None = Query(default=None),
    conn: Connection = Depends(get_conn),
):
    return await modelo.movimientos_resumen(conn, desde, hasta)


@router.get("/stock-bajo")
async def stock_bajo(conn: Connection = Depends(get_conn)):
    return await modelo.stock_bajo_agregado(conn)


@router.get("/vencimientos")
async def vencimientos(
    dias: int = Query(default=30, ge=0, le=365),
    conn: Connection = Depends(get_conn),
):
    return await modelo.vencimientos(conn, dias)
