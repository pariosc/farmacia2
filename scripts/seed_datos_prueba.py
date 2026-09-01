"""
Script de datos de prueba — Módulo Farmacia (post migración 006).

Crea 5 registros de ejemplo por entidad clave usando la API real (no SQL
directo), para garantizar que respeta los triggers, reservas de stock y
constraints nuevos (precio_venta, subtotal calculado, etc.).

REQUISITO: el servidor principal debe estar corriendo en localhost:8000
    uv run uvicorn main:app --reload

Ejecutar en otra terminal:
    uv run python scripts/seed_datos_prueba.py
"""
import httpx

BASE_URL = "http://127.0.0.1:8000"


def crear_categorias(client: httpx.Client) -> list[int]:
    nombres = [
        ("Analgésicos", "Medicamentos para el manejo del dolor"),
        ("Antibióticos", "Medicamentos para infecciones bacterianas"),
        ("Antiinflamatorios", "Medicamentos para reducir inflamación"),
        ("Material de Curación", "Insumos para curaciones y procedimientos"),
        ("Antisépticos", "Productos para desinfección"),
    ]
    existentes = {c["nombre"]: c["id_categoria"] for c in client.get("/categoria-producto/").json()}
    ids = []
    for nombre, descripcion in nombres:
        if nombre in existentes:
            ids.append(existentes[nombre])
            print(f"  ✔ Categoría ya existente: {nombre} (id={ids[-1]})")
            continue
        r = client.post("/categoria-producto/", json={"nombre": nombre, "descripcion": descripcion})
        if r.status_code == 201:
            ids.append(r.json()["id_categoria"])
            print(f"  ✔ Categoría creada: {nombre} (id={ids[-1]})")
        else:
            print(f"  ⚠ Categoría '{nombre}' no se creó ({r.status_code}): {r.text[:120]}")
    return ids


def obtener_tipos_producto(client: httpx.Client) -> dict[str, int]:
    r = client.get("/tipo-producto/")
    r.raise_for_status()
    tipos = {t["codigo"]: t["id_tipo_producto"] for t in r.json()}
    print(f"  ✔ Tipos de producto disponibles: {list(tipos.keys())}")
    return tipos


def crear_proveedores(client: httpx.Client) -> list[int]:
    proveedores = [
        {"razon_social": "Distribuidora Farmacéutica La Paz S.R.L.", "nit": "1001001010",
         "telefono": "22456789", "correo": "ventas@distrifarma.bo", "direccion": "Av. Buenos Aires #1234, La Paz"},
        {"razon_social": "Corporación Boliviana de Insumos Médicos", "nit": "1002002020",
         "telefono": "22567890", "correo": "contacto@cobimed.bo", "direccion": "Av. 6 de Agosto #500, La Paz"},
        {"razon_social": "Farmacorp S.A.", "nit": "1003003030",
         "telefono": "22678901", "correo": "pedidos@farmacorp.bo", "direccion": "Calle Comercio #200, La Paz"},
        {"razon_social": "Inti Salud Distribuciones", "nit": "1004004040",
         "telefono": "22789012", "correo": "ventas@intisalud.bo", "direccion": "Av. Ballivián #1500, La Paz"},
        {"razon_social": "MedSupply Bolivia", "nit": "1005005050",
         "telefono": "22890123", "correo": "info@medsupply.bo", "direccion": "Zona Sopocachi, La Paz"},
    ]
    existentes = {p["nit"]: p["id_proveedor"] for p in client.get("/proveedor/").json()}
    ids = []
    for p in proveedores:
        if p["nit"] in existentes:
            ids.append(existentes[p["nit"]])
            print(f"  ✔ Proveedor ya existente: {p['razon_social']} (id={ids[-1]})")
            continue
        r = client.post("/proveedor/", json=p)
        if r.status_code == 201:
            ids.append(r.json()["id_proveedor"])
            print(f"  ✔ Proveedor creado: {p['razon_social']} (id={ids[-1]})")
        else:
            print(f"  ⚠ Proveedor '{p['razon_social']}' no se creó ({r.status_code}): {r.text[:120]}")
    return ids


def crear_productos(client: httpx.Client, id_categorias: list[int], tipos: dict[str, int]) -> list[int]:
    med = tipos.get("MEDICAMENTO")
    insumo = tipos.get("INSUMO_MEDICO", med)
    productos = [
        {"id_categoria": id_categorias[0], "id_tipo_producto": med, "codigo": "MED-001",
         "nombre": "Paracetamol 500mg", "principio_activo": "Paracetamol", "concentracion": "500mg",
         "presentacion": "Caja x 20 tabletas", "unidad_medida": "tableta", "stock_minimo": 50,
         "requiere_receta": False, "precio_venta": 2.50},
        {"id_categoria": id_categorias[1], "id_tipo_producto": med, "codigo": "MED-002",
         "nombre": "Amoxicilina 500mg", "principio_activo": "Amoxicilina", "concentracion": "500mg",
         "presentacion": "Caja x 12 cápsulas", "unidad_medida": "cápsula", "stock_minimo": 30,
         "requiere_receta": True, "precio_venta": 3.80},
        {"id_categoria": id_categorias[2], "id_tipo_producto": med, "codigo": "MED-003",
         "nombre": "Ibuprofeno 400mg", "principio_activo": "Ibuprofeno", "concentracion": "400mg",
         "presentacion": "Caja x 10 tabletas", "unidad_medida": "tableta", "stock_minimo": 40,
         "requiere_receta": False, "precio_venta": 1.90},
        {"id_categoria": id_categorias[3], "id_tipo_producto": insumo, "codigo": "INS-001",
         "nombre": "Gasas Estériles 10x10", "unidad_medida": "unidad", "stock_minimo": 100,
         "requiere_receta": False, "precio_venta": 0.80},
        {"id_categoria": id_categorias[4], "id_tipo_producto": insumo, "codigo": "INS-002",
         "nombre": "Alcohol en Gel 70%", "concentracion": "70%", "presentacion": "Botella 500ml",
         "unidad_medida": "ml", "stock_minimo": 20, "requiere_receta": False, "precio_venta": 15.00},
    ]
    ids = []
    existentes = {str(p["codigo"]): p["id_producto"] for p in client.get("/producto-farmacia/").json()}
    for p in productos:
        if p["codigo"] in existentes:
            id_p = existentes[p["codigo"]]
            ids.append(id_p)
            r = client.put(f"/producto-farmacia/{id_p}", json=p)
            if r.status_code == 200:
                print(f"  ✔ Producto existente actualizado: {p['nombre']} (id={id_p}, precio_venta={p['precio_venta']})")
            else:
                print(f"  ⚠ Producto '{p['nombre']}' no se pudo actualizar ({r.status_code}): {r.text[:120]}")
            continue
        r = client.post("/producto-farmacia/", json=p)
        if r.status_code == 201:
            ids.append(r.json()["id_producto"])
            print(f"  ✔ Producto creado: {p['nombre']} (id={ids[-1]}, precio_venta={p['precio_venta']})")
        else:
            print(f"  ⚠ Producto '{p['nombre']}' no se creó ({r.status_code}): {r.text[:120]}")
    return ids


def crear_compras(client: httpx.Client, id_proveedores: list[int], id_productos: list[int]) -> list[int]:
    """Crea 1 compra por producto y devuelve el id_lote generado por cada una."""
    datos = [
        {"numero_lote": "LT-2026-001", "vencimiento": "2027-06-30", "cantidad": 200, "costo": 0.50},
        {"numero_lote": "LT-2026-002", "vencimiento": "2027-03-31", "cantidad": 150, "costo": 1.20},
        {"numero_lote": "LT-2026-003", "vencimiento": "2027-09-30", "cantidad": 180, "costo": 0.80},
        {"numero_lote": "LT-2026-004", "vencimiento": "2028-01-31", "cantidad": 300, "costo": 0.15},
        {"numero_lote": "LT-2026-005", "vencimiento": "2027-12-31", "cantidad": 50, "costo": 8.00},
    ]
    lotes = []
    lotes_existentes = {l["numero_lote"]: l["id_lote"] for l in client.get("/lote/").json()}
    for i, d in enumerate(datos):
        if d["numero_lote"] in lotes_existentes:
            lotes.append(lotes_existentes[d["numero_lote"]])
            print(f"  ✔ Lote ya existente: {d['numero_lote']} (id_lote={lotes[-1]})")
            continue
        body = {
            "id_proveedor": id_proveedores[i],
            "id_usuario": 1,
            "numero_documento": f"FAC-00{100 + i}",
            "fecha_compra": "2026-08-20",
            "detalles": [{
                "id_producto": id_productos[i],
                "numero_lote": d["numero_lote"],
                "fecha_vencimiento": d["vencimiento"],
                "cantidad": d["cantidad"],
                "costo_unitario": d["costo"],
            }],
        }
        r = client.post("/compra/", json=body)
        if r.status_code == 201:
            id_lote = r.json()["detalles"][0]["id_lote"]
            lotes.append(id_lote)
            print(f"  ✔ Compra registrada: {d['numero_lote']} → stock {d['cantidad']} (id_lote={id_lote})")
        else:
            print(f"  ⚠ Compra '{d['numero_lote']}' no se creó ({r.status_code}): {r.text[:150]}")
    return lotes


def crear_ventas_directas(client: httpx.Client, id_productos: list[int]):
    """Crea 5 dispensaciones tipo VENTA_DIRECTA en PENDIENTE_PAGO, cada una
    reservando stock del producto correspondiente (sin necesidad de receta ni
    de que el mock de Atención esté corriendo)."""
    productos = {p["id_producto"]: p for p in client.get("/producto-farmacia/").json()}
    otc = [p["id_producto"] for p in client.get("/producto-farmacia/").json()
           if p["id_producto"] in id_productos and not p["requiere_receta"]]
    elegidos = []
    for i in range(5):
        elegidos.append(otc[i % len(otc)] if otc else id_productos[i])
    pacientes = [f"PAC-DEMO-{i:03d}" for i in range(1, 6)]
    existentes = {
        d["id_paciente_externo"]: d["id_dispensacion"]
        for d in client.get("/dispensacion/").json()
        if d.get("origen") == "VENTA_DIRECTA" and d.get("id_paciente_externo") in pacientes
    }
    for i, (id_producto, id_paciente) in enumerate(zip(elegidos, pacientes), start=1):
        nombre = productos[id_producto]["nombre"]
        if id_paciente in existentes:
            print(f"  ✔ Venta directa #{i} ya existente: id_dispensacion={existentes[id_paciente]}")
            continue
        body = {
            "id_usuario": 1,
            "id_paciente": id_paciente,
            "observacion": f"Venta directa de prueba #{i} ({nombre})",
            "detalles": [{"id_producto": id_producto, "cantidad_solicitada": 5}],
        }
        r = client.post("/dispensacion/venta-directa", json=body)
        if r.status_code == 201:
            data = r.json()
            print(f"  ✔ Venta directa #{i} ({nombre}): id_dispensacion={data['id_dispensacion']}, "
                  f"estado={data['estado']}, total={data['total']}")
        else:
            print(f"  ⚠ Venta directa #{i} ({nombre}) no se creó ({r.status_code}): {r.text[:200]}")


def main():
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        print("1) Categorías")
        id_categorias = crear_categorias(client)

        print("\n2) Tipos de producto (ya sembrados por la migración 001)")
        tipos = obtener_tipos_producto(client)

        print("\n3) Proveedores")
        id_proveedores = crear_proveedores(client)

        print("\n4) Productos (con precio_venta)")
        id_productos = crear_productos(client, id_categorias, tipos)

        print("\n5) Compras (crean lote + stock + movimiento ENTRADA)")
        crear_compras(client, id_proveedores, id_productos)

        print("\n6) Ventas directas PENDIENTE_PAGO (reservan stock, sin tocar Atención)")
        crear_ventas_directas(client, id_productos)

    print("\nListo. Revisa /dispensacion/ en Swagger para ver las 5 notas en PENDIENTE_PAGO.")
    print("Para simular el pago de la primera, usa su id_dispensacion en:")
    print("  GET  /api/v1/farmacia/dispensaciones/{id}/cobro")
    print("  PUT  /api/v1/farmacia/dispensaciones/{id}/pago")
    print("  PUT  /dispensacion/{id}/confirmar   (o el endpoint de entrega equivalente)")


if __name__ == "__main__":
    main()
