from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from configuracion.conexion import lifespan
from configuracion.parametro import config
from routers import (
    r_categoria_producto,
    r_tipo_producto,
    r_producto,
    r_proveedor,
    r_lote,
    r_compra,
    r_dispensacion,
    r_consumo_interno,
    r_movimiento,
    r_reporte,
    r_catalogo_integracion,
    r_dispensacion_integracion,
)

app = FastAPI(title="API Módulo Farmacia - Hospital TODO SANO", lifespan=lifespan)

# --- Seguridad (paquete del equipo de Seguridad) ---
# Instrucción recibida: agregar esto justo después de crear `app`.
# Con try/except para que la app siga arrancando aunque el paquete todavía no
# esté instalado (útil para probar hoy sin bloquear nada). En cuanto instales
# el paquete real, esto se activa solo sin tocar más código.
#
# Instalar cuando Seguridad confirme el nombre/URL real del paquete:
#   uv add seguridad_hospital   (o el nombre/URL git que te den)
try:
    from seguridad_hospital import proteger_modulo
    proteger_modulo(app, roles_permitidos=["FARMACEUTICO", "ADMINISTRADOR"])
except ImportError:
    print(
        "[Seguridad] Paquete 'seguridad_hospital' no instalado todavía. "
        "La app sigue sin protección global — instalar antes de producción."
    )

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"
templates = Jinja2Templates(directory=FRONTEND_DIR / "templates")
app.mount("/static", StaticFiles(directory=FRONTEND_DIR / "static"), name="static")

app.include_router(r_categoria_producto.router)
app.include_router(r_tipo_producto.router)
app.include_router(r_producto.router)
app.include_router(r_proveedor.router)
app.include_router(r_lote.router)
app.include_router(r_compra.router)
app.include_router(r_dispensacion.router)
app.include_router(r_consumo_interno.router)
app.include_router(r_consumo_interno.router_integracion)
app.include_router(r_movimiento.router)
app.include_router(r_reporte.router)
app.include_router(r_catalogo_integracion.router)
app.include_router(r_dispensacion_integracion.router)


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return RedirectResponse(url="/static/img/favicon.svg")


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def raiz(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"seguridad_login_url": config.seguridad_login_url},
    )


@app.get("/login", response_class=HTMLResponse, include_in_schema=False)
async def login(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"seguridad_login_url": config.seguridad_login_url},
    )


@app.get("/productos", response_class=HTMLResponse, include_in_schema=False)
async def productos(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="productos.html",
        context={"pagina_activa": "productos", "usuario_nombre": "Usuario"},
    )


@app.get("/proveedores", response_class=HTMLResponse, include_in_schema=False)
async def proveedores(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="proveedores.html",
        context={"pagina_activa": "proveedores", "usuario_nombre": "Usuario"},
    )


@app.get("/compras", response_class=HTMLResponse, include_in_schema=False)
async def compras(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="compras.html",
        context={
            "pagina_activa": "compras",
            "usuario_nombre": "Usuario",
            "farmacia_usuario_id": config.farmacia_usuario_id,
        },
    )


@app.get("/inventario", response_class=HTMLResponse, include_in_schema=False)
async def inventario(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="inventario.html",
        context={"pagina_activa": "inventario", "usuario_nombre": "Usuario"},
    )


@app.get("/dispensaciones", response_class=HTMLResponse, include_in_schema=False)
async def dispensaciones(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="dispensaciones.html",
        context={
            "pagina_activa": "dispensaciones",
            "usuario_nombre": "Usuario",
            "farmacia_usuario_id": config.farmacia_usuario_id,
        },
    )


@app.get("/consumos", response_class=HTMLResponse, include_in_schema=False)
async def consumos(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="consumos.html",
        context={"pagina_activa": "consumos", "usuario_nombre": "Usuario"},
    )


@app.get("/kardex", response_class=HTMLResponse, include_in_schema=False)
async def kardex(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="kardex.html",
        context={"pagina_activa": "kardex", "usuario_nombre": "Usuario"},
    )


@app.get("/reportes", response_class=HTMLResponse, include_in_schema=False)
async def reportes(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="reportes.html",
        context={"pagina_activa": "reportes", "usuario_nombre": "Usuario"},
    )

# Prueba para github actions
