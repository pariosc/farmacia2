from asyncpg import Connection
from entidades.farmacia_compra import CompraIn
from modelo import m_lote

CAMPOS = "id_compra, id_proveedor, id_usuario, numero_documento, fecha_compra, total, estado"
CAMPOS_DET = "id_detalle_compra, id_compra, id_lote, cantidad, costo_unitario, subtotal"


async def listar(conn: Connection, limit: int = 200, offset: int = 0):
    filas = await conn.fetch(
        f"SELECT {CAMPOS} FROM tf_compras ORDER BY fecha_compra DESC LIMIT $1 OFFSET $2",
        limit, offset,
    )
    return [dict(f) for f in filas]


async def obtener(conn: Connection, id_compra: int):
    cabecera = await conn.fetchrow(f"SELECT {CAMPOS} FROM tf_compras WHERE id_compra = $1", id_compra)
    if not cabecera:
        return None
    detalles = await conn.fetch(
        f"SELECT {CAMPOS_DET} FROM tf_detalles_compra WHERE id_compra = $1", id_compra
    )
    resultado = dict(cabecera)
    resultado["detalles"] = [dict(d) for d in detalles]
    return resultado


async def registrar(conn: Connection, datos: CompraIn):
    """Registra la compra, crea/actualiza lotes, descuenta... (suma stock)
    y genera el movimiento de inventario tipo ENTRADA. Todo en una transacción."""
    async with conn.transaction():
        total = sum(d.cantidad * d.costo_unitario for d in datos.detalles)

        cabecera = await conn.fetchrow(
            "INSERT INTO tf_compras "
            "(id_proveedor, id_usuario, numero_documento, fecha_compra, total, estado) "
            "VALUES ($1, $2, $3, $4, $5, 'REGISTRADA') "
            f"RETURNING {CAMPOS}",
            datos.id_proveedor, datos.id_usuario, datos.numero_documento,
            datos.fecha_compra, total,
        )
        id_compra = cabecera["id_compra"]
        detalles_resultado = []

        for det in datos.detalles:
            lote = await m_lote.obtener_por_producto_y_numero(conn, det.id_producto, det.numero_lote)
            if lote is None:
                lote = await m_lote.crear(conn, det.id_producto, det.numero_lote, det.fecha_vencimiento)

            subtotal = det.cantidad * det.costo_unitario

            detalle = await conn.fetchrow(
                "INSERT INTO tf_detalles_compra (id_compra, id_lote, cantidad, costo_unitario, subtotal) "
                "VALUES ($1, $2, $3, $4, $5) "
                f"RETURNING {CAMPOS_DET}",
                id_compra, lote["id_lote"], det.cantidad, det.costo_unitario, subtotal,
            )

            await m_lote.ajustar_stock(conn, lote["id_lote"], det.cantidad)

            await conn.execute(
                "INSERT INTO tf_movimientos_inventario "
                "(id_lote, id_usuario, id_detalle_compra, tipo_movimiento, cantidad, fecha_movimiento, motivo) "
                "VALUES ($1, $2, $3, 'ENTRADA', $4, $5, $6)",
                lote["id_lote"], datos.id_usuario, detalle["id_detalle_compra"],
                det.cantidad, datos.fecha_compra, "Ingreso por compra",
            )
            detalles_resultado.append(dict(detalle))

        resultado = dict(cabecera)
        resultado["detalles"] = detalles_resultado
        return resultado


async def anular(conn: Connection, id_compra: int):
    fila = await conn.fetchrow(
        "UPDATE tf_compras SET estado = 'ANULADA' "
        "WHERE id_compra = $1 AND estado = 'REGISTRADA' "
        f"RETURNING {CAMPOS}",
        id_compra,
    )
    return dict(fila) if fila else None