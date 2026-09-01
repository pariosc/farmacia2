from asyncpg import Connection
from decimal import Decimal
from datetime import date
from modelo import m_lote

CAMPOS = ("id_movimiento, id_lote, id_usuario, id_detalle_compra, "
          "id_detalle_dispensacion, id_detalle_consumo, tipo_movimiento, "
          "cantidad, fecha_movimiento, motivo")


async def listar(conn: Connection, id_lote: int | None = None, limit: int = 300, offset: int = 0):
    if id_lote:
        filas = await conn.fetch(
            f"SELECT {CAMPOS} FROM tf_movimientos_inventario "
            "WHERE id_lote = $1 ORDER BY fecha_movimiento DESC, id_movimiento DESC "
            "LIMIT $2 OFFSET $3",
            id_lote, limit, offset,
        )
    else:
        filas = await conn.fetch(
            f"SELECT {CAMPOS} FROM tf_movimientos_inventario "
            "ORDER BY fecha_movimiento DESC, id_movimiento DESC "
            "LIMIT $1 OFFSET $2",
            limit, offset,
        )
    return [dict(f) for f in filas]


async def obtener(conn: Connection, id_movimiento: int):
    fila = await conn.fetchrow(
        f"SELECT {CAMPOS} FROM tf_movimientos_inventario WHERE id_movimiento = $1",
        id_movimiento,
    )
    return dict(fila) if fila else None


async def ajuste_manual(conn: Connection, id_lote: int, id_usuario: int,
                         cantidad: Decimal, motivo: str, fecha_movimiento: date):
    """cantidad positivo = ajuste a favor, negativo = ajuste en contra (merma, daño, etc.)."""
    async with conn.transaction():
        await m_lote.ajustar_stock(conn, id_lote, cantidad)
        fila = await conn.fetchrow(
            "INSERT INTO tf_movimientos_inventario "
            "(id_lote, id_usuario, tipo_movimiento, cantidad, fecha_movimiento, motivo) "
            "VALUES ($1, $2, 'AJUSTE', $3, $4, $5) "
            f"RETURNING {CAMPOS}",
            id_lote, id_usuario, cantidad, fecha_movimiento, motivo,
        )
        return dict(fila)