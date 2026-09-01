from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from asyncpg import Connection

from entidades.farmacia_dispensacion import (
    AnulacionDispensacionIn,
    ConfirmacionAnulacionCobrosIn,
    NotaDesdeRecetaIn,
    PagoDispensacionIn,
)
from modelo import m_lote


CAMPOS = (
    "id_dispensacion, numero_receta_externa, id_receta_externa, version_receta, "
    "origen, id_paciente_externo, id_factura, id_usuario, fecha_dispensacion, estado, "
    "observacion, version, total, reserva_hasta, fecha_creacion, "
    "fecha_actualizacion, fecha_pago, motivo_anulacion"
)


async def expirar_reservas(conn: Connection) -> int:
    """Libera notas sin pago vencidas. PAGADA nunca vence automáticamente."""
    fila = await conn.fetchrow(
        """
        WITH vencidas AS (
            UPDATE tf_dispensaciones
            SET estado = 'VENCIDA', fecha_actualizacion = CURRENT_TIMESTAMP
            WHERE estado = 'PENDIENTE_PAGO' AND reserva_hasta <= CURRENT_TIMESTAMP
            RETURNING id_dispensacion
        ), liberadas AS (
            UPDATE tf_reservas_dispensacion r
            SET estado = 'LIBERADA', fecha_liberacion = CURRENT_TIMESTAMP
            FROM tf_detalles_dispensacion dd, vencidas v
            WHERE r.id_detalle_dispensacion = dd.id_detalle_dispensacion
              AND dd.id_dispensacion = v.id_dispensacion AND r.estado = 'ACTIVA'
            RETURNING r.id_reserva
        )
        SELECT (SELECT count(*) FROM vencidas)::integer AS cantidad
        """
    )
    return fila["cantidad"] if fila else 0


async def listar(conn: Connection, limit: int = 200, offset: int = 0):
    await expirar_reservas(conn)
    filas = await conn.fetch(
        f"SELECT {CAMPOS} FROM tf_dispensaciones "
        "ORDER BY fecha_creacion DESC, id_dispensacion DESC LIMIT $1 OFFSET $2",
        limit, offset,
    )
    return [dict(f) for f in filas]


async def obtener(conn: Connection, id_dispensacion: int):
    cabecera = await conn.fetchrow(
        f"SELECT {CAMPOS} FROM tf_dispensaciones WHERE id_dispensacion = $1",
        id_dispensacion,
    )
    if not cabecera:
        return None
    detalles = await conn.fetch(
        """
        SELECT dd.id_detalle_dispensacion, dd.id_dispensacion,
               dd.id_prescripcion_externa, dd.id_producto, p.codigo AS codigo_producto,
               p.nombre AS nombre_producto, p.unidad_medida,
               dd.cantidad_prescrita, dd.cantidad_solicitada,
               dd.cantidad_entregada, dd.precio_unitario, dd.subtotal,
               dd.dosis_instrucciones, dd.id_lote
        FROM tf_detalles_dispensacion dd
        JOIN tf_productos p ON p.id_producto = dd.id_producto
        WHERE dd.id_dispensacion = $1
        ORDER BY dd.id_detalle_dispensacion
        """, id_dispensacion,
    )
    reservas = await conn.fetch(
        """
        SELECT r.id_reserva, r.id_detalle_dispensacion, r.id_lote,
               l.numero_lote, l.fecha_vencimiento, r.cantidad, r.estado,
               r.fecha_reserva, r.fecha_liberacion
        FROM tf_reservas_dispensacion r
        JOIN tf_detalles_dispensacion dd USING (id_detalle_dispensacion)
        JOIN tf_lotes l ON l.id_lote = r.id_lote
        WHERE dd.id_dispensacion = $1
        ORDER BY dd.id_detalle_dispensacion, l.fecha_vencimiento NULLS LAST, r.id_reserva
        """, id_dispensacion,
    )
    por_detalle: dict[int, list[dict]] = {}
    for reserva in reservas:
        por_detalle.setdefault(reserva["id_detalle_dispensacion"], []).append(dict(reserva))
    resultado = dict(cabecera)
    resultado["detalles"] = [
        {**dict(detalle), "reservas": por_detalle.get(detalle["id_detalle_dispensacion"], [])}
        for detalle in detalles
    ]
    return resultado


def _lineas_receta(receta: dict) -> dict[int, dict]:
    return {int(linea["id_prescripcion"]): linea for linea in receta["detalles"]}


async def _cantidades_previas(
    conn: Connection, id_receta: int, ids_prescripcion: list[int],
    excluir_dispensacion: int | None = None,
) -> dict[int, tuple[Decimal, Decimal]]:
    filas = await conn.fetch(
        """
        SELECT dd.id_prescripcion_externa,
               COALESCE(sum(CASE WHEN d.estado = 'ENTREGADA'
                    THEN COALESCE(dd.cantidad_entregada, dd.cantidad_solicitada)
                    ELSE 0 END), 0) AS entregada,
               COALESCE(sum(CASE
                    WHEN d.estado IN ('PAGADA', 'ANULACION_SOLICITADA') THEN dd.cantidad_solicitada
                    WHEN d.estado = 'PENDIENTE_PAGO' AND d.reserva_hasta > CURRENT_TIMESTAMP
                        THEN dd.cantidad_solicitada ELSE 0 END), 0) AS comprometida
        FROM tf_detalles_dispensacion dd
        JOIN tf_dispensaciones d USING (id_dispensacion)
        WHERE d.id_receta_externa = $1
          AND dd.id_prescripcion_externa = ANY($2::bigint[])
          AND ($3::integer IS NULL OR d.id_dispensacion <> $3)
        GROUP BY dd.id_prescripcion_externa
        """, id_receta, ids_prescripcion, excluir_dispensacion,
    )
    return {
        fila["id_prescripcion_externa"]: (fila["entregada"], fila["comprometida"])
        for fila in filas
    }


async def _lotes_disponibles(conn: Connection, id_producto: int):
    return await conn.fetch(
        """
        SELECT l.id_lote, l.numero_lote, l.fecha_vencimiento, l.stock_actual,
               l.stock_actual - COALESCE((
                   SELECT sum(r.cantidad)
                   FROM tf_reservas_dispensacion r
                   JOIN tf_detalles_dispensacion dd USING (id_detalle_dispensacion)
                   JOIN tf_dispensaciones d USING (id_dispensacion)
                   WHERE r.id_lote = l.id_lote AND r.estado = 'ACTIVA'
                     AND (d.estado IN ('PAGADA', 'ANULACION_SOLICITADA')
                          OR (d.estado = 'PENDIENTE_PAGO'
                              AND d.reserva_hasta > CURRENT_TIMESTAMP))
               ), 0) AS disponible
        FROM tf_lotes l
        WHERE l.id_producto = $1 AND l.stock_actual > 0
          AND l.estado NOT IN ('VENCIDO', 'AGOTADO')
          AND (l.fecha_vencimiento IS NULL OR l.fecha_vencimiento >= CURRENT_DATE)
        ORDER BY l.fecha_vencimiento NULLS LAST, l.id_lote
        FOR UPDATE OF l
        """, id_producto,
    )


async def _crear_detalles_y_reservas(
    conn: Connection, id_dispensacion: int, receta: dict,
    datos: NotaDesdeRecetaIn, excluir_dispensacion: int | None = None,
):
    lineas = _lineas_receta(receta)
    ids = [item.id_prescripcion for item in datos.detalles]
    if len(ids) != len(set(ids)):
        raise ValueError("No repita una línea de prescripción en la misma nota")
    if any(item_id not in lineas for item_id in ids):
        raise ValueError("La receta no contiene una de las prescripciones seleccionadas")

    ids_productos = list({int(lineas[item_id]["id_producto"]) for item_id in ids})
    productos = await conn.fetch(
        "SELECT id_producto, nombre, precio_venta, activo FROM tf_productos "
        "WHERE id_producto = ANY($1::integer[]) FOR UPDATE", ids_productos,
    )
    por_producto = {fila["id_producto"]: fila for fila in productos}
    previas = await _cantidades_previas(
        conn, int(receta["id_receta"]), ids, excluir_dispensacion
    )

    for seleccion in datos.detalles:
        linea = lineas[seleccion.id_prescripcion]
        id_producto = int(linea["id_producto"])
        producto = por_producto.get(id_producto)
        if not producto or not producto["activo"]:
            raise ValueError(f"El producto #{id_producto} no existe o está inactivo")
        if producto["precio_venta"] <= 0:
            raise ValueError(f"Defina un precio de venta mayor a cero para {producto['nombre']}")

        prescrita = Decimal(str(linea["cantidad_prescrita"]))
        entregada, comprometida = previas.get(
            seleccion.id_prescripcion, (Decimal("0"), Decimal("0"))
        )
        pendiente = prescrita - entregada - comprometida
        if pendiente <= 0:
            raise ValueError(f"La prescripción #{seleccion.id_prescripcion} ya fue atendida")
        if seleccion.cantidad_solicitada > pendiente:
            raise ValueError(
                f"La cantidad de la prescripción #{seleccion.id_prescripcion} "
                f"supera el pendiente ({pendiente})"
            )

        precio = producto["precio_venta"]
        subtotal = (seleccion.cantidad_solicitada * precio).quantize(Decimal("0.01"))
        detalle = await conn.fetchrow(
            """
            INSERT INTO tf_detalles_dispensacion
                (id_dispensacion, id_prescripcion_externa, id_producto,
                 cantidad_prescrita, cantidad_solicitada, precio_unitario,
                 subtotal, dosis_instrucciones)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING id_detalle_dispensacion
            """,
            id_dispensacion, seleccion.id_prescripcion, id_producto, prescrita,
            seleccion.cantidad_solicitada, precio, subtotal,
            linea.get("dosis_instrucciones"),
        )

        restante = seleccion.cantidad_solicitada
        for lote in await _lotes_disponibles(conn, id_producto):
            disponible = max(Decimal("0"), lote["disponible"])
            asignada = min(restante, disponible)
            if asignada <= 0:
                continue
            await conn.execute(
                "INSERT INTO tf_reservas_dispensacion "
                "(id_detalle_dispensacion, id_lote, cantidad) VALUES ($1, $2, $3)",
                detalle["id_detalle_dispensacion"], lote["id_lote"], asignada,
            )
            restante -= asignada
            if restante == 0:
                break
        if restante > 0:
            raise ValueError(
                f"Stock disponible insuficiente para {producto['nombre']} (faltan {restante})"
            )


async def registrar_desde_receta(
    conn: Connection, numero_receta: int, receta: dict,
    datos: NotaDesdeRecetaIn, minutos_reserva: int,
):
    if receta["estado"] != "FIRMADA":
        raise ValueError("Solo se pueden dispensar recetas en estado FIRMADA")
    async with conn.transaction():
        await expirar_reservas(conn)
        cabecera = await conn.fetchrow(
            """
            INSERT INTO tf_dispensaciones
                (numero_receta_externa, id_receta_externa, version_receta,
                 id_paciente_externo, id_usuario, fecha_dispensacion, estado,
                 observacion, version, total, reserva_hasta)
            VALUES ($1, $2, $3, $4, $5, CURRENT_DATE, 'PENDIENTE_PAGO',
                    $6, 1, 0, CURRENT_TIMESTAMP + make_interval(mins => $7))
            RETURNING id_dispensacion
            """,
            str(numero_receta), receta["id_receta"], receta.get("version"),
            receta["paciente"]["id_paciente"], datos.id_usuario,
            datos.observacion, minutos_reserva,
        )
        await _crear_detalles_y_reservas(conn, cabecera["id_dispensacion"], receta, datos)
    return await obtener(conn, cabecera["id_dispensacion"])


async def registrar_venta_directa(
    conn: Connection, datos, minutos_reserva: int,
):
    """Crea una nota OTC; nunca acepta productos que requieren receta."""
    async with conn.transaction():
        await expirar_reservas(conn)
        cabecera = await conn.fetchrow(
            """
            INSERT INTO tf_dispensaciones
                (origen, id_paciente_externo, id_usuario, fecha_dispensacion,
                 estado, observacion, version, total, reserva_hasta)
            VALUES ('VENTA_DIRECTA', $1, $2, CURRENT_DATE, 'PENDIENTE_PAGO',
                    $3, 1, 0, CURRENT_TIMESTAMP + make_interval(mins => $4))
            RETURNING id_dispensacion
            """,
            datos.id_paciente, datos.id_usuario, datos.observacion, minutos_reserva,
        )
        ids = list({item.id_producto for item in datos.detalles})
        productos = await conn.fetch(
            "SELECT id_producto, nombre, precio_venta, activo, requiere_receta "
            "FROM tf_productos WHERE id_producto = ANY($1::integer[]) FOR UPDATE", ids
        )
        por_id = {row["id_producto"]: row for row in productos}
        for item in datos.detalles:
            producto = por_id.get(item.id_producto)
            if not producto or not producto["activo"]:
                raise ValueError(f"El producto #{item.id_producto} no existe o está inactivo")
            if producto["requiere_receta"]:
                raise ValueError(f"{producto['nombre']} requiere receta médica")
            if producto["precio_venta"] <= 0:
                raise ValueError(f"Defina un precio de venta mayor a cero para {producto['nombre']}")
            subtotal = (item.cantidad_solicitada * producto["precio_venta"]).quantize(Decimal("0.01"))
            detalle = await conn.fetchrow(
                """
                INSERT INTO tf_detalles_dispensacion
                    (id_dispensacion, id_producto, cantidad_prescrita,
                     cantidad_solicitada, precio_unitario, subtotal)
                VALUES ($1, $2, $3, $3, $4, $5)
                RETURNING id_detalle_dispensacion
                """, cabecera["id_dispensacion"], item.id_producto,
                item.cantidad_solicitada, producto["precio_venta"], subtotal,
            )
            restante = item.cantidad_solicitada
            for lote in await _lotes_disponibles(conn, item.id_producto):
                asignada = min(restante, max(Decimal("0"), lote["disponible"]))
                if asignada <= 0:
                    continue
                await conn.execute(
                    "INSERT INTO tf_reservas_dispensacion "
                    "(id_detalle_dispensacion, id_lote, cantidad) VALUES ($1, $2, $3)",
                    detalle["id_detalle_dispensacion"], lote["id_lote"], asignada,
                )
                restante -= asignada
                if restante == 0:
                    break
            if restante > 0:
                raise ValueError(f"Stock insuficiente para {producto['nombre']} (faltan {restante})")
    return await obtener(conn, cabecera["id_dispensacion"])


async def corregir_pendiente(
    conn: Connection, id_dispensacion: int, receta: dict,
    datos: NotaDesdeRecetaIn, minutos_reserva: int,
):
    async with conn.transaction():
        await expirar_reservas(conn)
        cabecera = await conn.fetchrow(
            "SELECT id_dispensacion, id_receta_externa, estado FROM tf_dispensaciones "
            "WHERE id_dispensacion = $1 FOR UPDATE", id_dispensacion,
        )
        if not cabecera:
            return None
        if cabecera["estado"] != "PENDIENTE_PAGO":
            raise ValueError("Solo se puede corregir una nota pendiente de pago vigente")
        if cabecera["id_receta_externa"] != receta["id_receta"]:
            raise ValueError("La receta consultada no corresponde a esta dispensación")

        await conn.execute(
            "DELETE FROM tf_reservas_dispensacion WHERE id_detalle_dispensacion IN "
            "(SELECT id_detalle_dispensacion FROM tf_detalles_dispensacion "
            " WHERE id_dispensacion = $1)", id_dispensacion,
        )
        await conn.execute(
            "DELETE FROM tf_detalles_dispensacion WHERE id_dispensacion = $1",
            id_dispensacion,
        )
        await conn.execute(
            """
            UPDATE tf_dispensaciones
            SET id_usuario = $2, observacion = $3, version = version + 1,
                version_receta = $4, total = 0,
                reserva_hasta = CURRENT_TIMESTAMP + make_interval(mins => $5),
                fecha_actualizacion = CURRENT_TIMESTAMP
            WHERE id_dispensacion = $1
            """,
            id_dispensacion, datos.id_usuario, datos.observacion,
            receta.get("version"), minutos_reserva,
        )
        await _crear_detalles_y_reservas(
            conn, id_dispensacion, receta, datos, excluir_dispensacion=id_dispensacion
        )
    return await obtener(conn, id_dispensacion)


async def obtener_para_cobro(conn: Connection, id_dispensacion: int):
    await expirar_reservas(conn)
    fila = await conn.fetchrow(
        """
        SELECT id_dispensacion, version, estado, reserva_hasta,
               id_paciente_externo AS id_paciente, total,
               (estado = 'PENDIENTE_PAGO' AND reserva_hasta > CURRENT_TIMESTAMP
                AND id_factura IS NULL) AS cobrable
        FROM tf_dispensaciones WHERE id_dispensacion = $1
        """, id_dispensacion,
    )
    if not fila:
        return None
    resultado = dict(fila)
    # Contrato monetario para Cobros: texto con dos decimales, no float.
    resultado["total"] = f"{resultado['total']:.2f}"
    return resultado


async def registrar_pago(conn: Connection, id_dispensacion: int, pago: PagoDispensacionIn):
    resultado_idempotente = False
    async with conn.transaction():
        await expirar_reservas(conn)
        cabecera = await conn.fetchrow(
            f"SELECT {CAMPOS} FROM tf_dispensaciones "
            "WHERE id_dispensacion = $1 FOR UPDATE", id_dispensacion,
        )
        if not cabecera:
            return None
        if cabecera["estado"] in ("PAGADA", "ENTREGADA"):
            if cabecera["id_factura"] != pago.id_factura:
                raise ValueError("La dispensación ya está vinculada a otro comprobante")
            resultado_idempotente = True
        elif cabecera["estado"] != "PENDIENTE_PAGO":
            raise ValueError("La nota ya no está disponible para cobro")

        if not resultado_idempotente:
            if cabecera["reserva_hasta"] <= datetime.now(timezone.utc):
                raise ValueError("La reserva venció antes de registrar el pago")
            if cabecera["version"] != pago.version:
                raise ValueError("La nota fue corregida; Cobros debe consultar la versión actual")
            if cabecera["id_paciente_externo"] != pago.id_paciente:
                raise ValueError("El paciente del comprobante no coincide con la nota")
            if cabecera["total"] != pago.total:
                raise ValueError("El total pagado no coincide con la nota")
            await conn.execute(
                """
                UPDATE tf_dispensaciones
                SET id_factura = $2, estado = 'PAGADA', fecha_pago = CURRENT_TIMESTAMP,
                    reserva_hasta = NULL, fecha_actualizacion = CURRENT_TIMESTAMP
                WHERE id_dispensacion = $1
                """, id_dispensacion, pago.id_factura,
            )
    return await obtener(conn, id_dispensacion)


async def entregar(conn: Connection, id_dispensacion: int):
    async with conn.transaction():
        cabecera = await conn.fetchrow(
            f"SELECT {CAMPOS} FROM tf_dispensaciones "
            "WHERE id_dispensacion = $1 FOR UPDATE", id_dispensacion,
        )
        if not cabecera:
            return None
        if cabecera["estado"] == "ENTREGADA":
            pass
        elif cabecera["estado"] != "PAGADA":
            raise ValueError("La dispensación debe estar PAGADA antes de la entrega")
        else:
            reservas = await conn.fetch(
                """
                SELECT r.id_reserva, r.id_lote, r.cantidad, dd.id_detalle_dispensacion
                FROM tf_reservas_dispensacion r
                JOIN tf_detalles_dispensacion dd USING (id_detalle_dispensacion)
                JOIN tf_lotes l ON l.id_lote = r.id_lote
                WHERE dd.id_dispensacion = $1 AND r.estado = 'ACTIVA'
                ORDER BY r.id_lote FOR UPDATE OF l, r
                """, id_dispensacion,
            )
            totales = await conn.fetch(
                """
                SELECT dd.id_detalle_dispensacion, dd.cantidad_solicitada,
                       COALESCE(sum(r.cantidad) FILTER (WHERE r.estado = 'ACTIVA'), 0) AS reservada
                FROM tf_detalles_dispensacion dd
                LEFT JOIN tf_reservas_dispensacion r USING (id_detalle_dispensacion)
                WHERE dd.id_dispensacion = $1
                GROUP BY dd.id_detalle_dispensacion, dd.cantidad_solicitada
                """, id_dispensacion,
            )
            if not totales or any(f["reservada"] != f["cantidad_solicitada"] for f in totales):
                raise ValueError("Las reservas activas no cubren todos los detalles")

            for reserva in reservas:
                lote = await m_lote.ajustar_stock(conn, reserva["id_lote"], -reserva["cantidad"])
                if lote is None or lote["stock_actual"] < 0:
                    raise ValueError(f"Stock inconsistente en lote {reserva['id_lote']}")
                await conn.execute(
                    """
                    INSERT INTO tf_movimientos_inventario
                        (id_lote, id_usuario, id_detalle_dispensacion,
                         tipo_movimiento, cantidad, fecha_movimiento, motivo)
                    VALUES ($1, $2, $3, 'SALIDA', $4, CURRENT_DATE, $5)
                    """,
                    reserva["id_lote"], cabecera["id_usuario"],
                    reserva["id_detalle_dispensacion"], reserva["cantidad"],
                    f"Entrega de nota de dispensación #{id_dispensacion}",
                )
            await conn.execute(
                """
                UPDATE tf_reservas_dispensacion r
                SET estado = 'CONSUMIDA', fecha_liberacion = CURRENT_TIMESTAMP
                FROM tf_detalles_dispensacion dd
                WHERE r.id_detalle_dispensacion = dd.id_detalle_dispensacion
                  AND dd.id_dispensacion = $1 AND r.estado = 'ACTIVA'
                """, id_dispensacion,
            )
            await conn.execute(
                """
                UPDATE tf_detalles_dispensacion dd
                SET cantidad_entregada = cantidad_solicitada,
                    id_lote = (SELECT min(r.id_lote) FROM tf_reservas_dispensacion r
                               WHERE r.id_detalle_dispensacion = dd.id_detalle_dispensacion
                               HAVING count(*) = 1)
                WHERE dd.id_dispensacion = $1
                """, id_dispensacion,
            )
            await conn.execute(
                "UPDATE tf_dispensaciones SET estado = 'ENTREGADA', "
                "fecha_dispensacion = CURRENT_DATE, fecha_actualizacion = CURRENT_TIMESTAMP "
                "WHERE id_dispensacion = $1", id_dispensacion,
            )
    return await obtener(conn, id_dispensacion)


async def anular_pendiente(
    conn: Connection, id_dispensacion: int, datos: AnulacionDispensacionIn,
):
    async with conn.transaction():
        await expirar_reservas(conn)
        cabecera = await conn.fetchrow(
            "SELECT estado FROM tf_dispensaciones WHERE id_dispensacion = $1 FOR UPDATE",
            id_dispensacion,
        )
        if not cabecera:
            return None
        if cabecera["estado"] == "ANULADA":
            pass
        elif cabecera["estado"] != "PENDIENTE_PAGO":
            raise ValueError("Solo una nota pendiente de pago puede anularse localmente")
        else:
            await _liberar_reservas(conn, id_dispensacion)
            await conn.execute(
                "UPDATE tf_dispensaciones SET estado = 'ANULADA', motivo_anulacion = $2, "
                "reserva_hasta = NULL, fecha_actualizacion = CURRENT_TIMESTAMP "
                "WHERE id_dispensacion = $1", id_dispensacion, datos.motivo,
            )
    return await obtener(conn, id_dispensacion)


async def _liberar_reservas(conn: Connection, id_dispensacion: int):
    await conn.execute(
        """
        UPDATE tf_reservas_dispensacion r
        SET estado = 'LIBERADA', fecha_liberacion = CURRENT_TIMESTAMP
        FROM tf_detalles_dispensacion dd
        WHERE r.id_detalle_dispensacion = dd.id_detalle_dispensacion
          AND dd.id_dispensacion = $1 AND r.estado = 'ACTIVA'
        """, id_dispensacion,
    )


async def solicitar_anulacion_pagada(
    conn: Connection, id_dispensacion: int, datos: AnulacionDispensacionIn,
):
    async with conn.transaction():
        cabecera = await conn.fetchrow(
            "SELECT estado FROM tf_dispensaciones WHERE id_dispensacion = $1 FOR UPDATE",
            id_dispensacion,
        )
        if not cabecera:
            return None
        if cabecera["estado"] == "ANULACION_SOLICITADA":
            pass
        elif cabecera["estado"] != "PAGADA":
            raise ValueError("Solo una nota PAGADA puede solicitar anulación a Cobros")
        else:
            await conn.execute(
                "UPDATE tf_dispensaciones SET estado = 'ANULACION_SOLICITADA', "
                "motivo_anulacion = $2, fecha_actualizacion = CURRENT_TIMESTAMP "
                "WHERE id_dispensacion = $1", id_dispensacion, datos.motivo,
            )
    return await obtener(conn, id_dispensacion)


async def confirmar_anulacion_cobros(
    conn: Connection, id_dispensacion: int, datos: ConfirmacionAnulacionCobrosIn,
):
    async with conn.transaction():
        cabecera = await conn.fetchrow(
            "SELECT estado, id_factura, version FROM tf_dispensaciones "
            "WHERE id_dispensacion = $1 FOR UPDATE", id_dispensacion,
        )
        if not cabecera:
            return None
        if cabecera["estado"] == "ANULADA":
            pass
        elif cabecera["estado"] != "ANULACION_SOLICITADA":
            raise ValueError("La dispensación no espera confirmación de anulación")
        else:
            if cabecera["id_factura"] != datos.id_factura or cabecera["version"] != datos.version:
                raise ValueError("El comprobante o versión no coincide con la dispensación")
            await _liberar_reservas(conn, id_dispensacion)
            await conn.execute(
                "UPDATE tf_dispensaciones SET estado = 'ANULADA', "
                "fecha_actualizacion = CURRENT_TIMESTAMP WHERE id_dispensacion = $1",
                id_dispensacion,
            )
    return await obtener(conn, id_dispensacion)
