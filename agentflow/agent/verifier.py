"""Verificador determinista: toda cifra de la redacción debe existir en los resultados de las herramientas.

Límite conocido: solo comprueba números escritos con dígitos; no valida la interpretación
("subió" vs "bajó") ni cifras escritas con letras.
"""
import re
from dataclasses import dataclass

_TOKEN = re.compile(r"\d[\d.,]*\d|\d")
_FORMATO_VALIDO = re.compile(r"^(\d{1,3}(,\d{3})+|\d+)(\.\d+)?$")  # 1,234.56 | 1234.56 | 12
_NUMERACION = re.compile(r"^\s*\d+[.)]\s+", re.MULTILINE)  # "1. item" de listas


@dataclass(frozen=True)
class ResultadoVerificacion:
    ok: bool
    no_respaldadas: tuple[str, ...] = ()


def _numeros_de(valor, destino: set[float]) -> None:
    if isinstance(valor, bool) or valor is None:
        return
    if isinstance(valor, (int, float)):
        destino.add(abs(float(valor)))
    elif isinstance(valor, str):  # fechas ISO y nombres con dígitos
        for t in _TOKEN.findall(valor):
            try:
                destino.add(float(t.replace(",", "")))
            except ValueError:
                pass
    elif isinstance(valor, dict):
        for v in valor.values():
            _numeros_de(v, destino)
    elif isinstance(valor, (list, tuple)):
        destino.add(float(len(valor)))  # "3 productos"
        for v in valor:
            _numeros_de(v, destino)


def verificar_respuesta(texto: str, resultados: list[dict]) -> ResultadoVerificacion:
    permitidos: set[float] = set()
    for r in resultados:
        _numeros_de(r, permitidos)
    fallidas = []
    for token in _TOKEN.findall(_NUMERACION.sub("", texto)):
        if not _FORMATO_VALIDO.match(token):
            fallidas.append(token)  # formato ambiguo (p. ej. "12,5"): no se puede respaldar
            continue
        valor = float(token.replace(",", ""))
        decimales = len(token.split(".")[1]) if "." in token else 0
        tolerancia = 0.5 * 10 ** -decimales + 1e-9  # redondeo al nivel de precisión escrito
        if not any(abs(p - valor) <= tolerancia for p in permitidos):
            fallidas.append(token)
    return ResultadoVerificacion(not fallidas, tuple(fallidas))
