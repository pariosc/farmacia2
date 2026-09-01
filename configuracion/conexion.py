import asyncpg
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from configuracion.integracion import abrir_cliente, cerrar_cliente
from configuracion.parametro import config

DB_CONFIG = f"postgresql://{config.db_user}:{config.db_pass}@{config.db_host}:{config.db_port}/{config.db_name}"

# 1. Gestionamos el ciclo de vida del Pool
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Se ejecuta al arrancar el servidor
    app.state.pool = await asyncpg.create_pool(dsn=DB_CONFIG, min_size=5, max_size=20)
    # El cliente HTTP no llama por sí solo. Seguridad lo usa por solicitud si
    # su URL está configurada; Atención lo usa al buscar/corregir una receta.
    try:
        await abrir_cliente(app)
        yield  # <-- aquí la app queda "viva" atendiendo requests
    finally:
        await cerrar_cliente(app)
        # Se ejecuta al apagar el servidor
        await app.state.pool.close()

# 2. Dependencia para inyectar la conexión en las rutas
async def get_conn(request: Request):
    async with request.app.state.pool.acquire() as conn:
        yield conn          # al salir del bloque vuelve sola al pool
