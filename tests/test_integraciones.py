import unittest

import httpx

from configuracion.integracion import IntegracionError, pedir_json
from configuracion.parametro import config
from modelo.m_integracion_atencion import (
    normalizar_prescripciones_paciente,
    normalizar_receta,
    obtener_prescripciones_por_trazabilidad,
    obtener_receta_por_soap,
)


class TestClienteIntegraciones(unittest.IsolatedAsyncioTestCase):
    async def test_construye_ruta_confirmada_de_receta(self):
        async def responder(request: httpx.Request):
            self.assertEqual(
                str(request.url),
                "http://atencion.test/clinica/prescripcion/soap/123",
            )
            return httpx.Response(200, json={"id_receta": 123})

        anterior = config.integracion_atencion_url
        config.integracion_atencion_url = "http://atencion.test/"
        try:
            async with httpx.AsyncClient(
                transport=httpx.MockTransport(responder)
            ) as cliente:
                receta = await obtener_receta_por_soap(cliente, 123)
        finally:
            config.integracion_atencion_url = anterior

        self.assertEqual(receta, {"id_receta": 123})

    async def test_404_se_interpreta_como_no_encontrado(self):
        async def responder(_request: httpx.Request):
            return httpx.Response(404, json={"detail": "No encontrada"})

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(responder)
        ) as cliente:
            resultado = await pedir_json(cliente, "http://externo.test", "/recurso/1")

        self.assertIsNone(resultado)

    async def test_error_externo_no_se_interpreta_como_autorizacion(self):
        async def responder(_request: httpx.Request):
            return httpx.Response(500, json={"detail": "Error"})

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(responder)
        ) as cliente:
            with self.assertRaises(IntegracionError):
                await pedir_json(cliente, "http://externo.test", "/recurso/1")

    async def test_rechaza_numero_de_receta_invalido(self):
        async with httpx.AsyncClient() as cliente:
            with self.assertRaises(ValueError):
                await obtener_receta_por_soap(cliente, 0)

    async def test_construye_ruta_por_trazabilidad(self):
        async def responder(request: httpx.Request):
            self.assertEqual(
                str(request.url),
                "http://atencion.test/integracion/farmacia/recetas/PAC-2026-00101",
            )
            return httpx.Response(200, json=[])

        anterior = config.integracion_atencion_url
        config.integracion_atencion_url = "http://atencion.test"
        try:
            async with httpx.AsyncClient(
                transport=httpx.MockTransport(responder)
            ) as cliente:
                resultado = await obtener_prescripciones_por_trazabilidad(
                    cliente, "PAC-2026-00101"
                )
        finally:
            config.integracion_atencion_url = anterior
        self.assertEqual(resultado, [])

    async def test_rechaza_trazabilidad_con_ruta_invalida(self):
        async with httpx.AsyncClient() as cliente:
            with self.assertRaises(ValueError):
                await obtener_prescripciones_por_trazabilidad(cliente, "../paciente")


class TestCatalogoOpenAPI(unittest.TestCase):
    def test_rutas_de_catalogo_estan_publicadas(self):
        import main

        rutas = main.app.openapi()["paths"]
        self.assertIn("/api/v1/farmacia/productos/catalogo", rutas)
        self.assertIn("/api/v1/farmacia/productos/catalogo/{id_producto}", rutas)
        self.assertIn("/api/v1/farmacia/dispensaciones/{id_dispensacion}/cobro", rutas)
        self.assertIn("/api/v1/farmacia/dispensaciones/{id_dispensacion}/pago", rutas)
        self.assertIn("/dispensacion/paciente/{id_trazabilidad}/recetas", rutas)


class TestContratoReceta(unittest.TestCase):
    def test_normaliza_json_acordado(self):
        receta = normalizar_receta({
            "id_receta": 10,
            "version": 2,
            "estado": "firmada",
            "paciente": {"id_paciente": 20, "ci": "123"},
            "detalles": [{
                "id_prescripcion": 30,
                "id_producto": 40,
                "cantidad_prescrita": 5,
            }],
        })
        self.assertEqual(receta["estado"], "FIRMADA")
        self.assertEqual(receta["detalles"][0]["id_producto"], 40)

    def test_respuesta_actual_es_consultable_pero_no_dispensable(self):
        resultado = normalizar_prescripciones_paciente(
            [{
                "id_prescripcion": 1,
                "medicamento": "Paracetamol",
                "dosis": "500mg",
                "cantidad": 10,
                "indicaciones": "Cada 8 horas",
            }],
            "PAC-2026-00101",
        )
        self.assertFalse(resultado["integrable"])
        self.assertIn("id_producto", resultado["faltantes"])
        self.assertNotIn("estado_receta", resultado["faltantes"])

    def test_respuesta_mejorada_queda_lista(self):
        resultado = normalizar_prescripciones_paciente(
            [{
                "id_prescripcion": 1,
                "id_receta": 100,
                "id_producto": 40,
                "medicamento": "Paracetamol",
                "cantidad": 10,
                "estado_receta": "firmada",
            }],
            "PAC-2026-00101",
        )
        self.assertTrue(resultado["integrable"])

    def test_contrato_plano_de_atencion_queda_listo_para_farmacia(self):
        resultado = normalizar_prescripciones_paciente(
            [{
                "codigo_receta": 12,
                "codigo_item": 45,
                "id_producto": 8,
                "nombre_medicamento": "Paracetamol 500mg",
                "cantidad": 10,
                "dosis_instrucciones": "Tomar 1 cada 8 horas",
                "id_trazabilidad": "ABC-12345",
                "medico_id": 3,
                "fecha_creacion": "2026-09-01T09:22:00Z",
            }],
            "ABC-12345",
        )
        self.assertTrue(resultado["integrable"])
        linea = resultado["prescripciones"][0]
        self.assertEqual(linea["id_prescripcion"], 45)
        self.assertEqual(linea["id_receta"], 12)
        self.assertEqual(linea["numero_receta"], "12")
        self.assertIsNone(linea["estado_receta"])
