from asyncpg import Connection, UniqueViolationError

from entidades.farmacia_tipo_producto import TipoProducto

CAMPOS = "id_tipo_producto, codigo, nombre, descripcion, activo"


async def listar(conn: Connection, solo_activos: bool = False):
    condicion = "WHERE activo = true" if solo_activos else ""
    filas = await conn.fetch(
        f"SELECT {CAMPOS} FROM tf_tipos_producto {condicion} ORDER BY nombre"
    )
    return [dict(fila) for fila in filas]


async def obtener(conn: Connection, id_tipo_producto: int):
    fila = await conn.fetchrow(
        f"SELECT {CAMPOS} FROM tf_tipos_producto WHERE id_tipo_producto = $1",
        id_tipo_producto,
    )
    return dict(fila) if fila else None


async def insertar(conn: Connection, tipo: TipoProducto):
    try:
        fila = await conn.fetchrow(
            "INSERT INTO tf_tipos_producto (codigo, nombre, descripcion, activo) "
            "VALUES ($1,$2,$3,$4) "
            f"RETURNING {CAMPOS}",
            tipo.codigo, tipo.nombre, tipo.descripcion, tipo.activo,
        )
    except UniqueViolationError as error:
        raise ValueError("Ya existe un tipo con el mismo código o nombre") from error
    return dict(fila)


async def actualizar(conn: Connection, id_tipo_producto: int, tipo: TipoProducto):
    actual = await obtener(conn, id_tipo_producto)
    if not actual:
        return None

    if actual["codigo"] != tipo.codigo:
        en_uso = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM tf_productos WHERE id_tipo_producto = $1)",
            id_tipo_producto,
        )
        if en_uso:
            raise ValueError("No se puede cambiar el código de un tipo utilizado por productos")

    try:
        fila = await conn.fetchrow(
            "UPDATE tf_tipos_producto SET codigo=$2, nombre=$3, descripcion=$4, activo=$5 "
            "WHERE id_tipo_producto=$1 "
            f"RETURNING {CAMPOS}",
            id_tipo_producto, tipo.codigo, tipo.nombre, tipo.descripcion, tipo.activo,
        )
    except UniqueViolationError as error:
        raise ValueError("Ya existe un tipo con el mismo código o nombre") from error
    return dict(fila) if fila else None
