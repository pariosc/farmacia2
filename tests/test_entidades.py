"""
Pruebas de las reglas de validación en las entidades Pydantic.
No requieren base de datos — verifican solo la capa de entrada (entidades/).

Ejecutar con:
    uv run pytest
"""
import pytest
from pydantic import ValidationError

from entidades.farmacia_consumo import ConsumoInternoIn, DetalleConsumoIn
from entidades.farmacia_dispensacion import DispensacionIn, DetalleDispensacionIn


def _detalle_valido_solicitud():
    return {"id_detalle_solicitud_consumo": 1, "id_lote": 1, "cantidad_entregada": 5}


def _detalle_valido_prescripcion():
    return {"id_detalle_prescripcion": 1, "id_lote": 1, "cantidad_entregada": 5}


class TestConsumoInternoOrigen:
    def test_acepta_solo_solicitud_insumo(self):
        datos = ConsumoInternoIn(
            id_solicitud_insumo=10,
            id_usuario=1,
            fecha_consumo="2026-08-30",
            detalles=[_detalle_valido_solicitud()],
        )
        assert datos.id_solicitud_insumo == 10
        assert datos.id_prescripcion is None

    def test_acepta_solo_prescripcion(self):
        datos = ConsumoInternoIn(
            id_prescripcion=20,
            id_usuario=1,
            fecha_consumo="2026-08-30",
            detalles=[_detalle_valido_prescripcion()],
        )
        assert datos.id_prescripcion == 20
        assert datos.id_solicitud_insumo is None

    def test_rechaza_sin_ningun_origen(self):
        with pytest.raises(ValidationError):
            ConsumoInternoIn(
                id_usuario=1,
                fecha_consumo="2026-08-30",
                detalles=[_detalle_valido_solicitud()],
            )

    def test_rechaza_detalle_sin_ningun_origen(self):
        with pytest.raises(ValidationError):
            DetalleConsumoIn(id_lote=1, cantidad_entregada=5)

    def test_rechaza_cantidad_cero_o_negativa(self):
        with pytest.raises(ValidationError):
            DetalleConsumoIn(id_detalle_solicitud_consumo=1, id_lote=1, cantidad_entregada=0)


class TestDispensacionSinReceta:
    def test_no_acepta_campo_id_receta(self):
        """Confirma que id_receta ya no es un campo válido tras la corrección
        de la migración 004_eliminar_receta_dispensacion."""
        datos = DispensacionIn(
            id_factura=1,
            id_usuario=1,
            fecha_dispensacion="2026-08-30",
            detalles=[
                {"id_detalle_comprobante": 1, "id_lote": 1, "cantidad_entregada": 5}
            ],
        )
        assert not hasattr(datos, "id_receta")

    def test_rechaza_detalle_sin_comprobante(self):
        with pytest.raises(ValidationError):
            DetalleDispensacionIn(id_lote=1, cantidad_entregada=5)
