from asyncpg import Connection
from entidades.farmacia_catalogo import Producto

CAMPOS = (
    "p.id_producto, p.id_categoria, p.codigo, p.nombre, "
    "p.id_tipo_producto, p.tipo_producto, t.codigo AS codigo_tipo_producto, "
    "t.nombre AS nombre_tipo_producto, p.principio_activo, p.concentracion, "
    "p.presentacion, p.unidad_medida, p.stock_minimo, p.precio_venta, "
    "p.requiere_receta, p.activo"
)


def _normalizar_codigo_tipo(valor: str) -> str:
    codigo = valor.strip().upper()
    return {"INSUMO": "INSUMO_MEDICO", "DISPOSITIVO": "DISPOSITIVO_MEDICO"}.get(
        codigo, codigo
    )


async def _resolver_tipo(conn: Connection, producto: Producto):
    if producto.id_tipo_producto is not None:
        tipo = await conn.fetchrow(
            "SELECT id_tipo_producto, codigo FROM tf_tipos_producto "
            "WHERE id_tipo_producto = $1",
            producto.id_tipo_producto,
        )
        if not tipo:
            raise ValueError("El tipo de producto seleccionado no existe")
        if producto.tipo_producto:
            if _normalizar_codigo_tipo(producto.tipo_producto) != tipo["codigo"]:
                raise ValueError("id_tipo_producto no coincide con tipo_producto")
        producto.tipo_producto = tipo["codigo"]
        return

    codigo = _normalizar_codigo_tipo(producto.tipo_producto or "")
    tipo = await conn.fetchrow(
        "SELECT id_tipo_producto, codigo FROM tf_tipos_producto WHERE codigo = $1",
        codigo,
    )
    if not tipo:
        raise ValueError("El tipo de producto indicado no existe")
    producto.id_tipo_producto = tipo["id_tipo_producto"]
    producto.tipo_producto = tipo["codigo"]


async def listar(conn: Connection):
    filas = await conn.fetch(
        f"SELECT {CAMPOS} FROM tf_productos p "
        "JOIN tf_tipos_producto t ON t.id_tipo_producto = p.id_tipo_producto "
        "ORDER BY p.nombre"
    )
    return [dict(f) for f in filas]


async def obtener(conn: Connection, id_producto: int):
    fila = await conn.fetchrow(
        f"SELECT {CAMPOS} FROM tf_productos p "
        "JOIN tf_tipos_producto t ON t.id_tipo_producto = p.id_tipo_producto "
        "WHERE p.id_producto = $1",
        id_producto,
    )
    return dict(fila) if fila else None


async def insertar(conn: Connection, p: Producto):
    await _resolver_tipo(conn, p)
    fila = await conn.fetchrow(
        "INSERT INTO tf_productos "
        "(id_categoria, codigo, nombre, id_tipo_producto, tipo_producto, principio_activo, "
        " concentracion, presentacion, unidad_medida, stock_minimo, precio_venta, "
        " requiere_receta, activo) "
        "VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13) "
        "RETURNING id_producto",
        p.id_categoria, p.codigo, p.nombre, p.id_tipo_producto, p.tipo_producto, p.principio_activo,
        p.concentracion, p.presentacion, p.unidad_medida, p.stock_minimo,
        p.precio_venta, p.requiere_receta, p.activo,
    )
    return await obtener(conn, fila["id_producto"])


async def actualizar(conn: Connection, id_producto: int, p: Producto):
    await _resolver_tipo(conn, p)
    fila = await conn.fetchrow(
        "UPDATE tf_productos SET id_categoria=$2, codigo=$3, nombre=$4, "
        "id_tipo_producto=COALESCE($5,id_tipo_producto), tipo_producto=$6, principio_activo=$7, concentracion=$8, "
        "presentacion=$9, unidad_medida=$10, stock_minimo=$11, precio_venta=$12, "
        "requiere_receta=$13, activo=$14 "
        "WHERE id_producto = $1 "
        "RETURNING id_producto",
        id_producto, p.id_categoria, p.codigo, p.nombre, p.id_tipo_producto, p.tipo_producto,
        p.principio_activo, p.concentracion, p.presentacion, p.unidad_medida,
        p.stock_minimo, p.precio_venta, p.requiere_receta, p.activo,
    )
    return await obtener(conn, fila["id_producto"]) if fila else None


async def eliminar(conn: Connection, id_producto: int):
    resultado = await conn.execute(
        "DELETE FROM tf_productos WHERE id_producto = $1", id_producto
    )
    return resultado.endswith("1")
