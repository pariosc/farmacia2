from asyncpg import Connection
from entidades.farmacia_consumo import ConsumoInternoIn
from modelo import m_lote

CAMPOS = ("id_consumo, id_solicitud_insumo, id_prescripcion, id_usuario, "
          "fecha_consumo, estado, observacion")
CAMPOS_DET = ("id_detalle_consumo, id_consumo, id_detalle_solicitud_consumo, "
              "id_detalle_prescripcion, id_producto, id_lote, cantidad_entregada")


async def listar(conn: Connection, limit: int = 200, offset: int = 0):
    filas = await conn.fetch(
        f"SELECT {CAMPOS} FROM tf_consumos_internos ORDER BY fecha_consumo DESC "
        "LIMIT $1 OFFSET $2",
        limit, offset,
    )
    return [dict(f) for f in filas]


async def obtener(conn: Connection, id_consumo: int):
    cabecera = await conn.fetchrow(
        f"SELECT {CAMPOS} FROM tf_consumos_internos WHERE id_consumo = $1", id_consumo
    )
    if not cabecera:
        return None
    detalles = await conn.fetch(
        f"SELECT {CAMPOS_DET} FROM tf_detalles_consumo WHERE id_consumo = $1", id_consumo
    )
    resultado = dict(cabecera)
    resultado["detalles"] = [dict(d) for d in detalles]
    return resultado


async def estado_por_solicitud(conn: Connection, id_solicitud: int):
    """Devuelve el estado que Internación necesita consultar."""
    cabecera = await conn.fetchrow(
        "SELECT id_consumo, id_solicitud_insumo, id_prescripcion, estado, "
        "fecha_consumo, observacion FROM tf_consumos_internos "
        "WHERE id_solicitud_insumo = $1 "
        "ORDER BY id_consumo DESC LIMIT 1",
        id_solicitud,
    )
    if not cabecera:
        return None
    detalles = await conn.fetch(
        "SELECT id_detalle_consumo, id_producto, id_lote, cantidad_entregada "
        "FROM tf_detalles_consumo WHERE id_consumo = $1 ORDER BY id_detalle_consumo",
        cabecera["id_consumo"],
    )
    resultado = dict(cabecera)
    resultado["entregado"] = resultado["estado"] == "REGISTRADO"
    resultado["detalles"] = [dict(detalle) for detalle in detalles]
    return resultado


async def registrar(conn: Connection, datos: ConsumoInternoIn):
    async with conn.transaction():
        cabecera = await conn.fetchrow(
            "INSERT INTO tf_consumos_internos "
            "(id_solicitud_insumo, id_prescripcion, id_usuario, fecha_consumo, estado, observacion) "
            "VALUES ($1, $2, $3, $4, 'PENDIENTE', $5) "
            f"RETURNING {CAMPOS}",
            datos.id_solicitud_insumo, datos.id_prescripcion, datos.id_usuario,
            datos.fecha_consumo, datos.observacion,
        )
        id_consumo = cabecera["id_consumo"]
        detalles_resultado = []

        for det in datos.detalles:
            id_lote = det.id_lote
            if id_lote is None:
                lote = await conn.fetchrow(
                    """SELECT l.id_lote FROM tf_lotes l
                       WHERE l.id_producto = $1 AND l.stock_actual > 0
                         AND l.estado NOT IN ('VENCIDO', 'AGOTADO')
                         AND (l.fecha_vencimiento IS NULL OR l.fecha_vencimiento >= CURRENT_DATE)
                       ORDER BY l.fecha_vencimiento NULLS LAST, l.id_lote
                       LIMIT 1""", det.id_producto,
                )
                if lote is None:
                    raise ValueError(f"No hay lote disponible para el producto #{det.id_producto}")
                id_lote = lote["id_lote"]
            detalle = await conn.fetchrow(
                "INSERT INTO tf_detalles_consumo "
                "(id_consumo, id_detalle_solicitud_consumo, id_detalle_prescripcion, id_producto, id_lote, cantidad_entregada) "
                "VALUES ($1, $2, $3, $4, $5, $6) "
                f"RETURNING {CAMPOS_DET}",
                id_consumo, det.id_detalle_solicitud_consumo, det.id_detalle_prescripcion,
                det.id_producto, id_lote, det.cantidad_entregada,
            )

            detalles_resultado.append(dict(detalle))

        resultado = dict(cabecera)
        resultado["detalles"] = detalles_resultado
        return resultado


async def confirmar(conn: Connection, id_consumo: int):
    """Confirma un consumo pendiente y descuenta lotes en una transacción."""
    async with conn.transaction():
        cabecera = await conn.fetchrow(
            f"SELECT {CAMPOS} FROM tf_consumos_internos "
            "WHERE id_consumo = $1 AND estado = 'PENDIENTE' FOR UPDATE",
            id_consumo,
        )
        if not cabecera:
            return None
        detalles = await conn.fetch(
            f"SELECT {CAMPOS_DET} FROM tf_detalles_consumo WHERE id_consumo = $1",
            id_consumo,
        )
        for det in detalles:
            lote = await conn.fetchrow(
                "SELECT id_lote, stock_actual, estado, fecha_vencimiento "
                "FROM tf_lotes WHERE id_lote = $1 FOR UPDATE",
                det["id_lote"],
            )
            if lote is None:
                raise ValueError(f"El lote {det['id_lote']} no existe")
            if lote["estado"] == "VENCIDO" or (
                lote["fecha_vencimiento"] is not None
                and lote["fecha_vencimiento"] < cabecera["fecha_consumo"]
            ):
                raise ValueError(f"El lote {det['id_lote']} está vencido")
            if lote["stock_actual"] < det["cantidad_entregada"]:
                raise ValueError(
                    f"Stock insuficiente en el lote {det['id_lote']} "
                    f"(disponible: {lote['stock_actual']})"
                )
            await m_lote.ajustar_stock(conn, det["id_lote"], -det["cantidad_entregada"])
            await conn.execute(
                "INSERT INTO tf_movimientos_inventario "
                "(id_lote, id_usuario, id_detalle_consumo, tipo_movimiento, cantidad, fecha_movimiento, motivo) "
                "VALUES ($1, $2, $3, 'SALIDA', $4, $5, $6)",
                det["id_lote"], cabecera["id_usuario"], det["id_detalle_consumo"],
                det["cantidad_entregada"], cabecera["fecha_consumo"],
                "Salida por consumo interno",
            )
        actualizada = await conn.fetchrow(
            f"UPDATE tf_consumos_internos SET estado = 'REGISTRADO' "
            "WHERE id_consumo = $1 RETURNING " + CAMPOS,
            id_consumo,
        )
        resultado = dict(actualizada)
        resultado["detalles"] = [dict(d) for d in detalles]
        return resultado


async def anular(conn: Connection, id_consumo: int):
    """Anula un consumo interno. Si ya estaba REGISTRADO (stock descontado),
    revierte la cantidad al lote y registra el movimiento de reversión."""
    async with conn.transaction():
        cabecera = await conn.fetchrow(
            f"SELECT {CAMPOS} FROM tf_consumos_internos WHERE id_consumo = $1 FOR UPDATE",
            id_consumo,
        )
        if cabecera is None or cabecera["estado"] == "ANULADO":
            return None

        if cabecera["estado"] == "REGISTRADO":
            detalles = await conn.fetch(
                f"SELECT {CAMPOS_DET} FROM tf_detalles_consumo WHERE id_consumo = $1", id_consumo
            )
            for det in detalles:
                await m_lote.ajustar_stock(conn, det["id_lote"], det["cantidad_entregada"])
                await conn.execute(
                    "INSERT INTO tf_movimientos_inventario "
                    "(id_lote, id_usuario, id_detalle_consumo, tipo_movimiento, cantidad, fecha_movimiento, motivo) "
                    "VALUES ($1, $2, $3, 'ENTRADA', $4, CURRENT_DATE, $5)",
                    det["id_lote"], cabecera["id_usuario"], det["id_detalle_consumo"],
                    det["cantidad_entregada"], "Reversión por anulación de consumo interno",
                )

        actualizado = await conn.fetchrow(
            "UPDATE tf_consumos_internos SET estado = 'ANULADO' "
            "WHERE id_consumo = $1 "
            f"RETURNING {CAMPOS}",
            id_consumo,
        )
        return dict(actualizado)
