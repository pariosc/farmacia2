from asyncpg import Connection


async def listar_productos(
    conn: Connection,
    buscar: str | None = None,
    id_categoria: int | None = None,
    id_tipo_producto: int | None = None,
):
    """Catálogo activo que otros módulos pueden usar como fuente de IDs."""
    condiciones = ["p.activo = TRUE"]
    valores = []

    if buscar and buscar.strip():
        valores.append(f"%{buscar.strip()}%")
        condiciones.append(
            "(p.nombre ILIKE $1 OR p.codigo ILIKE $1 OR p.principio_activo ILIKE $1)"
        )

    if id_categoria is not None:
        valores.append(id_categoria)
        condiciones.append(f"p.id_categoria = ${len(valores)}")

    if id_tipo_producto is not None:
        valores.append(id_tipo_producto)
        condiciones.append(f"p.id_tipo_producto = ${len(valores)}")

    query = """
        SELECT
            p.id_producto,
            p.codigo,
            p.nombre,
            p.principio_activo,
            p.concentracion,
            p.presentacion,
            p.unidad_medida,
            p.id_categoria,
            c.nombre AS nombre_categoria,
            p.id_tipo_producto,
            t.codigo AS codigo_tipo_producto,
            t.nombre AS nombre_tipo_producto,
            p.requiere_receta
        FROM tf_productos p
        JOIN tf_categorias_producto c ON c.id_categoria = p.id_categoria
        JOIN tf_tipos_producto t ON t.id_tipo_producto = p.id_tipo_producto
        WHERE {where}
        ORDER BY p.nombre, p.codigo
    """.format(where=" AND ".join(condiciones))

    filas = await conn.fetch(query, *valores)
    return [dict(fila) for fila in filas]


async def obtener_producto(conn: Connection, id_producto: int):
    # Consulta directa para no cargar todo el catálogo al pedir un solo ID.
    fila = await conn.fetchrow(
        """
        SELECT
            p.id_producto,
            p.codigo,
            p.nombre,
            p.principio_activo,
            p.concentracion,
            p.presentacion,
            p.unidad_medida,
            p.id_categoria,
            c.nombre AS nombre_categoria,
            p.id_tipo_producto,
            t.codigo AS codigo_tipo_producto,
            t.nombre AS nombre_tipo_producto,
            p.requiere_receta
        FROM tf_productos p
        JOIN tf_categorias_producto c ON c.id_categoria = p.id_categoria
        JOIN tf_tipos_producto t ON t.id_tipo_producto = p.id_tipo_producto
        WHERE p.id_producto = $1 AND p.activo = TRUE
        """,
        id_producto,
    )
    return dict(fila) if fila else None
