"""Utilidades compartidas por las pruebas."""

import tempfile
from pathlib import Path

from planificador.escenario import cargar_escenario

ESCENAS = Path(__file__).resolve().parent.parent / "scenes"

ESCENARIO_MINIMO = """#tiempos por máquina
2.0\t3.0\t9.0
4.0\t1.0\t9.0
#consumo energético por máquina
1.0\t2.0\t5.0
3.0\t4.0\t5.0
#Trabajos
J1={O1,O2}
J2={O2}
"""


def escenario(numero: int):
    return cargar_escenario(ESCENAS / f"Escenario{numero}.txt")


def escenario_desde_texto(texto: str, nombre: str = "prueba.txt"):
    with tempfile.TemporaryDirectory() as carpeta:
        ruta = Path(carpeta) / nombre
        ruta.write_text(texto, encoding="utf-8")
        return cargar_escenario(ruta)
