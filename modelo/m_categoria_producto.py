from asyncpg import Connection


async def listar(conn: Connection):
    filas = await conn.fetch(
        "SELECT id_categoria, nombre, descripcion, activo "
        "FROM tf_categorias_producto ORDER BY nombre"
    )
    return [dict(f) for f in filas]


async def obtener(conn: Connection, id_categoria: int):
    fila = await conn.fetchrow(
        "SELECT id_categoria, nombre, descripcion, activo "
        "FROM tf_categorias_producto WHERE id_categoria = $1",
        id_categoria,
    )
    return dict(fila) if fila else None


async def insertar(conn: Connection, nombre: str, descripcion: str | None, activo: bool):
    fila = await conn.fetchrow(
        "INSERT INTO tf_categorias_producto (nombre, descripcion, activo) "
        "VALUES ($1, $2, $3) "
        "RETURNING id_categoria, nombre, descripcion, activo",
        nombre, descripcion, activo,
    )
    return dict(fila)


async def actualizar(conn: Connection, id_categoria: int, nombre: str, descripcion: str | None, activo: bool):
    fila = await conn.fetchrow(
        "UPDATE tf_categorias_producto SET nombre = $2, descripcion = $3, activo = $4 "
        "WHERE id_categoria = $1 "
        "RETURNING id_categoria, nombre, descripcion, activo",
        id_categoria, nombre, descripcion, activo,
    )
    return dict(fila) if fila else None


async def eliminar(conn: Connection, id_categoria: int):
    resultado = await conn.execute(
        "DELETE FROM tf_categorias_producto WHERE id_categoria = $1", id_categoria
    )
    return resultado.endswith("1")