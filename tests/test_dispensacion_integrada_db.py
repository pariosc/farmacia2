"""Prueba transaccional del flujo 006.

Se omite por defecto. Para ejecutarla contra una base desechable ya migrada:
TEST_DATABASE_URL=postgresql://.../bd_prueba pytest -q tests/test_dispensacion_integrada_db.py
"""

import os
import unittest
from decimal import Decimal

import asyncpg

from entidades.farmacia_dispensacion import NotaDesdeRecetaIn, PagoDispensacionIn
from entidades.farmacia_catalogo import Producto
from modelo import m_dispensacion, m_producto


@unittest.skipUnless(os.getenv("TEST_DATABASE_URL"), "requiere base temporal")
class TestFlujoDispensacionIntegrada(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.conn = await asyncpg.connect(os.environ["TEST_DATABASE_URL"])
        self.transaccion = self.conn.transaction()
        await self.transaccion.start()

    async def asyncTearDown(self):
        await self.transaccion.rollback()
        await self.conn.close()

    async def test_reserva_pago_entrega_idempotente_y_parcial(self):
        fila = await self.conn.fetchrow(
            """
            SELECT p.id_producto, p.nombre, l.id_lote, l.stock_actual
            FROM tf_productos p
            JOIN tf_lotes l USING (id_producto)
            WHERE p.activo = TRUE
            ORDER BY p.id_producto, l.fecha_vencimiento NULLS LAST
            LIMIT 1
            """
        )
        usuario = await self.conn.fetchval(
            "SELECT id_usuario FROM ts_usuarios ORDER BY id_usuario LIMIT 1"
        ) or 1
        if not fila:
            self.skipTest("la copia necesita al menos un producto activo con lote")

        await self.conn.execute(
            "UPDATE tf_productos SET precio_venta = 12.50 WHERE id_producto = $1",
            fila["id_producto"],
        )
        producto_actual = await m_producto.obtener(self.conn, fila["id_producto"])
        actualizado = await m_producto.actualizar(
            self.conn,
            fila["id_producto"],
            Producto(**{**producto_actual, "precio_venta": "12.50"}),
        )
        self.assertEqual(actualizado["precio_venta"], Decimal("12.50"))
        await self.conn.execute(
            "UPDATE tf_lotes SET stock_actual = GREATEST(stock_actual, 10), "
            "estado = 'DISPONIBLE', fecha_vencimiento = CURRENT_DATE + 365 "
            "WHERE id_lote = $1",
            fila["id_lote"],
        )
        stock_inicial = await self.conn.fetchval(
            "SELECT sum(stock_actual) FROM tf_lotes WHERE id_producto = $1", fila["id_producto"]
        )
        receta = {
            "id_receta": 9_900_001,
            "version": 1,
            "estado": "FIRMADA",
            "paciente": {"id_paciente": "PAC-TEST-9900002"},
            "detalles": [{
                "id_prescripcion": 9_900_003,
                "id_producto": fila["id_producto"],
                "nombre_producto": fila["nombre"],
                "cantidad_prescrita": Decimal("3"),
                "dosis_instrucciones": "Prueba transaccional",
            }],
        }
        entrada = NotaDesdeRecetaIn(
            id_usuario=usuario,
            detalles=[{"id_prescripcion": 9_900_003, "cantidad_solicitada": "1"}],
        )
        nota = await m_dispensacion.registrar_desde_receta(
            self.conn, 9_900_001, receta, entrada, 30
        )
        self.assertEqual(nota["estado"], "PENDIENTE_PAGO")
        self.assertEqual(nota["total"], Decimal("12.50"))
        self.assertEqual(nota["detalles"][0]["reservas"][0]["estado"], "ACTIVA")
        self.assertEqual(
            await self.conn.fetchval(
                "SELECT sum(stock_actual) FROM tf_lotes WHERE id_producto = $1", fila["id_producto"]
            ),
            stock_inicial,
        )

        cobrable = await m_dispensacion.obtener_para_cobro(
            self.conn, nota["id_dispensacion"]
        )
        self.assertTrue(cobrable["cobrable"])
        pago = PagoDispensacionIn(
            id_factura=9_900_004,
            id_paciente="PAC-TEST-9900002",
            total="12.50",
            version=1,
        )
        pagada = await m_dispensacion.registrar_pago(
            self.conn, nota["id_dispensacion"], pago
        )
        self.assertEqual(pagada["estado"], "PAGADA")

        entregada = await m_dispensacion.entregar(self.conn, nota["id_dispensacion"])
        self.assertEqual(entregada["estado"], "ENTREGADA")
        stock_final = await self.conn.fetchval(
            "SELECT sum(stock_actual) FROM tf_lotes WHERE id_producto = $1", fila["id_producto"]
        )
        self.assertEqual(stock_final, stock_inicial - Decimal("1"))

        await m_dispensacion.entregar(self.conn, nota["id_dispensacion"])
        self.assertEqual(
            await self.conn.fetchval(
                "SELECT sum(stock_actual) FROM tf_lotes WHERE id_producto = $1", fila["id_producto"]
            ),
            stock_final,
        )

        segunda = await m_dispensacion.registrar_desde_receta(
            self.conn,
            9_900_001,
            receta,
            NotaDesdeRecetaIn(
                id_usuario=usuario,
                detalles=[{"id_prescripcion": 9_900_003, "cantidad_solicitada": "2"}],
            ),
            30,
        )
        self.assertEqual(segunda["estado"], "PENDIENTE_PAGO")
        self.assertEqual(segunda["detalles"][0]["cantidad_solicitada"], Decimal("2"))
