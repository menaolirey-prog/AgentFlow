import pytest

from agentflow.agent.verifier import verificar_respuesta

DATOS = [{
    "moneda": "PEN", "periodo": {"inicio": "2026-11-01", "fin": "2026-11-10"},
    "ingresos_totales": 6850.5, "unidades": 29, "variacion_ingresos_pct": -12.53,
    "productos": [{"producto": "Laptop", "ingresos": 5000.0}, {"producto": "Mouse", "ingresos": 850.0}],
}]


@pytest.mark.parametrize("texto", [
    "Vendimos S/ 6,850.50 en 29 unidades.",
    "Ingresos: S/ 6850.50.",
    "Entre el 2026-11-01 y el 2026-11-10 vendimos S/ 6,850.50.",
    "Cayó 12.5% respecto al periodo anterior.",           # redondeo al decimal escrito
    "Las ventas fueron de S/ 6,851 (aprox.).",            # redondeo a entero
    "Hay 2 productos: Laptop con S/ 5,000.00 y Mouse con S/ 850.",
    "1. Laptop: S/ 5,000\n2. Mouse: S/ 850",              # numeración de lista ignorada
    "No tengo datos para eso.",                           # sin cifras
])
def test_respuestas_respaldadas(texto):
    assert verificar_respuesta(texto, DATOS).ok


@pytest.mark.parametrize("texto,sobrante", [
    ("Vendimos S/ 6,580.50.", "6,580.50"),                # dígitos transpuestos
    ("Vendimos 30 unidades.", "30"),
    ("Cayó 15% frente al mes previo.", "15"),
    ("Total: S/ 7,000.", "7,000"),
    ("Crecimiento de 12.9%.", "12.9"),
    ("Ingresos S/ 6,850,50.", "6,850,50"),                # formato ambiguo no se acepta
    ("Vendimos 12,5 mil.", "12,5"),
])
def test_cifras_alteradas_o_inventadas(texto, sobrante):
    v = verificar_respuesta(texto, DATOS)
    assert not v.ok and sobrante in v.no_respaldadas


def test_sin_resultados_cualquier_cifra_falla():
    assert not verificar_respuesta("Vendimos S/ 100.", []).ok
    assert verificar_respuesta("Pregunta fuera de alcance.", []).ok
