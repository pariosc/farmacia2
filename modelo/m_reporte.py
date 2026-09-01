from io import BytesIO
from datetime import date

from asyncpg import Connection
from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)


async def compras_por_proveedor(conn: Connection, desde: date | None = None,
                                hasta: date | None = None):
    """Total comprado y número de compras por proveedor. Solo compras REGISTRADA."""
    filas = await conn.fetch(
        "SELECT c.id_proveedor, pr.razon_social, "
        "COUNT(*) AS numero_compras, "
        "COALESCE(SUM(c.total), 0) AS total_comprado "
        "FROM tf_compras c "
        "JOIN tf_proveedores pr ON pr.id_proveedor = c.id_proveedor "
        "WHERE c.estado = 'REGISTRADA' "
        "AND ($1::date IS NULL OR c.fecha_compra >= $1) "
        "AND ($2::date IS NULL OR c.fecha_compra <= $2) "
        "GROUP BY c.id_proveedor, pr.razon_social "
        "ORDER BY total_comprado DESC",
        desde, hasta,
    )
    return [dict(f) for f in filas]


async def movimientos_resumen(conn: Connection, desde: date | None = None,
                              hasta: date | None = None):
    """Entradas, salidas y ajustes agregados por producto en el rango indicado.
    AJUSTE conserva el signo almacenado, según la lógica actual de kardex."""
    filas = await conn.fetch(
        "SELECT pr.id_producto, pr.codigo, pr.nombre AS nombre_producto, "
        "COALESCE(SUM(m.cantidad) FILTER (WHERE m.tipo_movimiento = 'ENTRADA'), 0) AS total_entradas, "
        "COALESCE(SUM(m.cantidad) FILTER (WHERE m.tipo_movimiento = 'SALIDA'), 0) AS total_salidas, "
        "COALESCE(SUM(m.cantidad) FILTER (WHERE m.tipo_movimiento = 'AJUSTE'), 0) AS total_ajustes, "
        "COUNT(*) AS numero_movimientos "
        "FROM tf_movimientos_inventario m "
        "JOIN tf_lotes l ON l.id_lote = m.id_lote "
        "JOIN tf_productos pr ON pr.id_producto = l.id_producto "
        "WHERE ($1::date IS NULL OR m.fecha_movimiento >= $1) "
        "AND ($2::date IS NULL OR m.fecha_movimiento <= $2) "
        "GROUP BY pr.id_producto, pr.codigo, pr.nombre "
        "ORDER BY pr.nombre",
        desde, hasta,
    )
    return [dict(f) for f in filas]


async def stock_bajo_agregado(conn: Connection):
    """Stock total por producto activo (excluye lotes vencidos) frente a stock_minimo.
    A diferencia de /lote/alertas/stock-bajo, compara la existencia agregada, no lote a lote."""
    filas = await conn.fetch(
        "SELECT pr.id_producto, pr.codigo, pr.nombre AS nombre_producto, "
        "pr.unidad_medida, pr.stock_minimo, "
        "COALESCE(SUM(l.stock_actual) FILTER ("
        "  WHERE l.estado <> 'VENCIDO' "
        "  AND (l.fecha_vencimiento IS NULL OR l.fecha_vencimiento >= CURRENT_DATE)"
        "), 0) AS stock_total "
        "FROM tf_productos pr "
        "LEFT JOIN tf_lotes l ON l.id_producto = pr.id_producto "
        "WHERE pr.activo = true "
        "GROUP BY pr.id_producto, pr.codigo, pr.nombre, pr.unidad_medida, pr.stock_minimo "
        "HAVING COALESCE(SUM(l.stock_actual) FILTER ("
        "  WHERE l.estado <> 'VENCIDO' "
        "  AND (l.fecha_vencimiento IS NULL OR l.fecha_vencimiento >= CURRENT_DATE)"
        "), 0) <= pr.stock_minimo "
        "ORDER BY stock_total ASC, pr.nombre"
    )
    reporte = []
    for f in filas:
        fila = dict(f)
        fila["estado"] = "AGOTADO" if fila["stock_total"] <= 0 else "STOCK_BAJO"
        reporte.append(fila)
    return reporte


async def vencimientos(conn: Connection, dias: int = 30):
    """Lotes con stock positivo cuyo vencimiento ya pasó o cae dentro de la ventana de días.
    Calcula la ventana en el servidor y evita el error de tipado de /lote/alertas/por-vencer."""
    filas = await conn.fetch(
        "SELECT l.id_lote, l.numero_lote, l.id_producto, pr.codigo, "
        "pr.nombre AS nombre_producto, l.fecha_vencimiento, l.stock_actual, "
        "(l.fecha_vencimiento - CURRENT_DATE) AS dias_para_vencer "
        "FROM tf_lotes l "
        "JOIN tf_productos pr ON pr.id_producto = l.id_producto "
        "WHERE l.stock_actual > 0 "
        "AND l.fecha_vencimiento IS NOT NULL "
        "AND l.fecha_vencimiento <= CURRENT_DATE + $1::int "
        "ORDER BY l.fecha_vencimiento ASC",
        dias,
    )
    reporte = []
    for f in filas:
        fila = dict(f)
        fila["estado"] = "VENCIDO" if fila["dias_para_vencer"] < 0 else "POR_VENCER"
        reporte.append(fila)
    return reporte


# ---------------------------------------------------------------------------
# Exportación a PDF / Excel
# ---------------------------------------------------------------------------

def _generar_pdf(titulo, subtitulo, cabeceras, filas, alineaciones=None):
    """Devuelve los bytes de un PDF con la tabla del reporte.
    `filas` es una lista de filas (listas/tuplas) listas para imprimir."""
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=landscape(A4), leftMargin=14 * mm, rightMargin=14 * mm,
        topMargin=14 * mm, bottomMargin=16 * mm,
        title=titulo,
    )
    estilos = getSampleStyleSheet()
    titulo_estilo = ParagraphStyle(
        "RepTitulo", parent=estilos["Title"], fontSize=15, leading=18,
        spaceAfter=2)
    sub_estilo = ParagraphStyle(
        "RepSub", parent=estilos["Normal"], fontSize=8.5, textColor=colors.HexColor("#64748B"),
        spaceAfter=10)
    cabecera_estilo = ParagraphStyle(
        "RepCab", parent=estilos["Normal"], fontSize=8.3, fontName="Helvetica-Bold",
        textColor=colors.white)

    encabezado = [Paragraph(titulo, titulo_estilo)]
    if subtitulo:
        encabezado.append(Paragraph(subtitulo, sub_estilo))

    tabla = [cabeceras]
    for fila in filas:
        tabla.append([str(celda) if celda is not None else "" for celda in fila])

    ancho = doc.width
    n = len(cabeceras)
    col_w = [ancho / n] * n
    cuerpo = []
    for i, fila in enumerate(tabla):
        if i == 0:
            cuerpo.append([Paragraph(c, cabecera_estilo) for c in fila])
        else:
            par = [Paragraph(c, estilos["Normal"]) for c in fila]
            cuerpo.append(par)

    t = Table(cuerpo, colWidths=col_w, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563EB")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F1F5F9")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    if alineaciones:
        for col, al in enumerate(alineaciones):
            if al == "right":
                t.setStyle(TableStyle([("ALIGN", (col, 0), (col, -1), "RIGHT")]))

    doc.build(encabezado + [Spacer(1, 4), t])
    return buf.getvalue()


def _generar_excel(titulo, cabeceras, filas):
    """Devuelve los bytes de un archivo .xlsx con el reporte."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Reporte"
    ws.append(cabeceras)
    for fila in filas:
        ws.append(fila)
    for celda in ws[1]:
        celda.font = celda.font.copy(bold=True)
    for col in ws.columns:
        max_len = max((len(str(c.value)) if c.value is not None else 0) for c in col)
        ws.column_dimensions[col[0].column_letter].width = max(min(max_len + 2, 40), 10)
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()


def exportar_pdf(reporte: str, filas) -> bytes:
    """Genera el PDF del reporte indicado a partir de sus filas consultadas."""
    if reporte == "compras":
        return _generar_pdf(
            "Compras por proveedor", "Compras REGISTRADA",
            ["Proveedor", "N.º compras", "Total comprado (Bs)"],
            [[f["razon_social"], f["numero_compras"], round(f["total_comprado"], 2)] for f in filas],
            alineaciones=[None, "right", "right"],
        )
    if reporte == "movimientos":
        return _generar_pdf(
            "Entradas y salidas por periodo", "Movimientos de inventario",
            ["Producto", "Código", "Entradas", "Salidas", "Ajustes", "N.º mov."],
            [[f["nombre_producto"], f["codigo"], round(f["total_entradas"], 2),
              round(f["total_salidas"], 2), round(f["total_ajustes"], 2),
              f["numero_movimientos"]] for f in filas],
            alineaciones=[None, None, "right", "right", "right", "right"],
        )
    if reporte == "stock":
        return _generar_pdf(
            "Stock bajo agregado por producto", "Productos en o por debajo del stock mínimo",
            ["Producto", "Código", "Unidad", "Stock disponible", "Mínimo", "Estado"],
            [[f["nombre_producto"], f["codigo"], f["unidad_medida"],
              round(f["stock_total"], 2), round(f["stock_minimo"], 2),
              "Agotado" if f["estado"] == "AGOTADO" else "Stock bajo"] for f in filas],
            alineaciones=[None, None, None, "right", "right", None],
        )
    if reporte == "vencimientos":
        return _generar_pdf(
            "Próximos vencimientos y lotes vencidos", "Lotes por vencer",
            ["Producto", "Código", "Lote", "Vencimiento", "Stock", "Días", "Estado"],
            [[f["nombre_producto"], f["codigo"], f["numero_lote"],
              str(f["fecha_vencimiento"]), round(f["stock_actual"], 2),
              f["dias_para_vencer"],
              "Vencido" if f["estado"] == "VENCIDO" else "Por vencer"] for f in filas],
            alineaciones=[None, None, None, None, "right", "right", None],
        )
    raise ValueError(f"Reporte desconocido: {reporte}")


def exportar_excel(reporte: str, filas) -> bytes:
    """Genera el archivo .xlsx del reporte indicado a partir de sus filas consultadas."""
    if reporte == "compras":
        return _generar_excel(
            "Compras por proveedor",
            ["Proveedor", "N.º compras", "Total comprado (Bs)"],
            [[f["razon_social"], f["numero_compras"], round(f["total_comprado"], 2)] for f in filas],
        )
    if reporte == "movimientos":
        return _generar_excel(
            "Entradas y salidas por periodo",
            ["Producto", "Código", "Entradas", "Salidas", "Ajustes", "N.º mov."],
            [[f["nombre_producto"], f["codigo"], round(f["total_entradas"], 2),
              round(f["total_salidas"], 2), round(f["total_ajustes"], 2),
              f["numero_movimientos"]] for f in filas],
        )
    if reporte == "stock":
        return _generar_excel(
            "Stock bajo agregado por producto",
            ["Producto", "Código", "Unidad", "Stock disponible", "Mínimo", "Estado"],
            [[f["nombre_producto"], f["codigo"], f["unidad_medida"],
              round(f["stock_total"], 2), round(f["stock_minimo"], 2),
              "Agotado" if f["estado"] == "AGOTADO" else "Stock bajo"] for f in filas],
        )
    if reporte == "vencimientos":
        return _generar_excel(
            "Próximos vencimientos y lotes vencidos",
            ["Producto", "Código", "Lote", "Vencimiento", "Stock", "Días", "Estado"],
            [[f["nombre_producto"], f["codigo"], f["numero_lote"],
              str(f["fecha_vencimiento"]), round(f["stock_actual"], 2),
              f["dias_para_vencer"],
              "Vencido" if f["estado"] == "VENCIDO" else "Por vencer"] for f in filas],
        )
    raise ValueError(f"Reporte desconocido: {reporte}")
