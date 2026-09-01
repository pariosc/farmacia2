from asyncpg import Connection
from decimal import Decimal
from datetime import date

CAMPOS = "id_lote, id_producto, numero_lote, fecha_vencimiento, stock_actual, estado"


async def listar(conn: Connection):
    filas = await conn.fetch(f"SELECT {CAMPOS} FROM tf_lotes ORDER BY fecha_vencimiento")
    return [dict(f) for f in filas]


async def obtener(conn: Connection, id_lote: int):
    fila = await conn.fetchrow(f"SELECT {CAMPOS} FROM tf_lotes WHERE id_lote = $1", id_lote)
    return dict(fila) if fila else None


async def obtener_por_producto_y_numero(conn: Connection, id_producto: int, numero_lote: str):
    fila = await conn.fetchrow(
        f"SELECT {CAMPOS} FROM tf_lotes WHERE id_producto = $1 AND numero_lote = $2",
        id_producto, numero_lote,
    )
    return dict(fila) if fila else None


async def crear(conn: Connection, id_producto: int, numero_lote: str, fecha_vencimiento: date | None):
    fila = await conn.fetchrow(
        "INSERT INTO tf_lotes (id_producto, numero_lote, fecha_vencimiento, stock_actual, estado) "
        "VALUES ($1, $2, $3, 0, 'DISPONIBLE') "
        f"RETURNING {CAMPOS}",
        id_producto, numero_lote, fecha_vencimiento,
    )
    return dict(fila)


async def ajustar_stock(conn: Connection, id_lote: int, cantidad_delta: Decimal):
    """cantidad_delta positivo = entrada, negativo = salida."""
    fila = await conn.fetchrow(
        "UPDATE tf_lotes SET stock_actual = stock_actual + $2, "
        "estado = CASE WHEN stock_actual + $2 <= 0 THEN 'AGOTADO' "
        "              WHEN estado = 'AGOTADO' THEN 'DISPONIBLE' "
        "              ELSE estado END "
        f"WHERE id_lote = $1 RETURNING {CAMPOS}",
        id_lote, cantidad_delta,
    )
    return dict(fila) if fila else None


async def eliminar(conn: Connection, id_lote: int):
    resultado = await conn.execute("DELETE FROM tf_lotes WHERE id_lote = $1", id_lote)
    return resultado.endswith("1")


async def stock_bajo(conn: Connection):
    filas = await conn.fetch(
        "SELECT l.id_lote, l.id_producto, p.nombre AS nombre_producto, "
        "l.numero_lote, l.stock_actual, p.stock_minimo "
        "FROM tf_lotes l JOIN tf_productos p ON p.id_producto = l.id_producto "
        "WHERE l.stock_actual <= p.stock_minimo AND l.estado != 'VENCIDO' "
        "ORDER BY l.stock_actual ASC"
    )
    return [dict(f) for f in filas]


async def proximos_a_vencer(conn: Connection, dias: int = 30):
    filas = await conn.fetch(
        "SELECT l.id_lote, l.id_producto, p.nombre AS nombre_producto, "
        "l.numero_lote, l.fecha_vencimiento, l.stock_actual "
        "FROM tf_lotes l JOIN tf_productos p ON p.id_producto = l.id_producto "
        "WHERE l.fecha_vencimiento IS NOT NULL "
        "AND l.fecha_vencimiento <= CURRENT_DATE + make_interval(days => $1) "
        "AND l.stock_actual > 0 "
        "ORDER BY l.fecha_vencimiento ASC",
        dias,
    )
    return [dict(f) for f in filas]