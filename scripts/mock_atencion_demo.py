"""Simulador local de Atención para probar Farmacia; nunca usar en producción.

Ejecutar con:
    uvicorn scripts.mock_atencion_demo:app --host 127.0.0.1 --port 8013
"""

from fastapi import FastAPI, HTTPException


app = FastAPI(title="Mock local de Atención para Farmacia")


@app.get("/clinica/prescripcion/soap/{numero_receta}")
async def receta_por_soap(numero_receta: int):
    if numero_receta != 1001:
        raise HTTPException(status_code=404, detail="Receta de demostración no encontrada")
    return {
        "id_receta": 1001,
        "version": 1,
        "estado": "FIRMADA",
        "fecha_emision": "2026-08-31T10:00:00-04:00",
        "paciente": {
            "id_paciente": "PAC-TEST-001",
            "ci": "1234567",
            "nombre_completo": "Paciente de demostración",
        },
        "medico": {
            "id_medico": 1,
            "nombre_completo": "Médico de demostración",
        },
        "detalles": [{
            "id_prescripcion": 10001,
            "id_producto": 1,
            "nombre_producto": "Producto de demostración #1",
            "cantidad_prescrita": 5,
            "dosis_instrucciones": "Cada 8 horas según indicación médica",
        }],
    }


@app.get("/integracion/farmacia/recetas/{id_trazabilidad}")
async def recetas_por_trazabilidad(id_trazabilidad: str):
    if id_trazabilidad != "PAC-TEST-001":
        raise HTTPException(status_code=404, detail="Paciente sin recetas de demostración")
    return [{
        "id_prescripcion": 10001,
        "id_receta": 1001,
        "numero_receta": "1001",
        "version_receta": 1,
        "estado_receta": "FIRMADA",
        "id_producto": 1,
        "medicamento": "Producto de demostración #1",
        "dosis": "500 mg",
        "cantidad": 5,
        "indicaciones": "Cada 8 horas según indicación médica",
    }]
