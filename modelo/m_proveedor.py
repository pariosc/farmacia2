from asyncpg import Connection
from entidades.farmacia_proveedor import Proveedor

CAMPOS = "id_proveedor, razon_social, nit, telefono, correo, direccion, activo"


async def listar(conn: Connection):
    filas = await conn.fetch(f"SELECT {CAMPOS} FROM tf_proveedores ORDER BY razon_social")
    return [dict(f) for f in filas]


async def obtener(conn: Connection, id_proveedor: int):
    fila = await conn.fetchrow(
        f"SELECT {CAMPOS} FROM tf_proveedores WHERE id_proveedor = $1", id_proveedor
    )
    return dict(fila) if fila else None


async def insertar(conn: Connection, p: Proveedor):
    fila = await conn.fetchrow(
        "INSERT INTO tf_proveedores (razon_social, nit, telefono, correo, direccion, activo) "
        "VALUES ($1,$2,$3,$4,$5,$6) "
        f"RETURNING {CAMPOS}",
        p.razon_social, p.nit, p.telefono, p.correo, p.direccion, p.activo,
    )
    return dict(fila)


async def actualizar(conn: Connection, id_proveedor: int, p: Proveedor):
    fila = await conn.fetchrow(
        "UPDATE tf_proveedores SET razon_social=$2, nit=$3, telefono=$4, "
        "correo=$5, direccion=$6, activo=$7 "
        "WHERE id_proveedor = $1 "
        f"RETURNING {CAMPOS}",
        id_proveedor, p.razon_social, p.nit, p.telefono, p.correo, p.direccion, p.activo,
    )
    return dict(fila) if fila else None


async def eliminar(conn: Connection, id_proveedor: int):
    resultado = await conn.execute(
        "DELETE FROM tf_proveedores WHERE id_proveedor = $1", id_proveedor
    )
    return resultado.endswith("1")