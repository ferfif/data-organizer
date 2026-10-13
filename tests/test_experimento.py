import contextlib
import csv
import io
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from statistics import fmean

from comun import ESCENAS, escenario

from planificador.__main__ import main
from planificador.experimento import (
    CONFIGURACIONES,
    SEMILLAS,
    curvas_convergencia,
    ejecutar_campana,
    guardar_campana,
    seleccionar_configuracion,
    tres_mejores,
)

REDUCIDAS = [replace(cfg, poblacion=20, generaciones=10) for cfg in CONFIGURACIONES.values()]


def ejecutar_cli(*argumentos: str) -> tuple[int, str, str]:
    salida, errores = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(salida), contextlib.redirect_stderr(errores):
        codigo = main(list(argumentos))
    return codigo, salida.getvalue(), errores.getvalue()


class Campana(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.esc = escenario(1)
        cls.campana = ejecutar_campana(cls.esc, REDUCIDAS)
        cls.temporal = tempfile.TemporaryDirectory()
        cls.carpeta = Path(cls.temporal.name) / "Escenario1"
        cls.seleccionada = guardar_campana(cls.esc, cls.campana, cls.carpeta)

    @classmethod
    def tearDownClass(cls):
        cls.temporal.cleanup()

    def test_veinte_corridas_con_semillas_distintas(self):
        self.assertEqual(SEMILLAS, tuple(range(1, 21)))
        self.assertEqual(len(self.campana), 4)
        for rc in self.campana:
            self.assertEqual(sorted(r.semilla for r in rc.resultados), list(range(1, 21)))

    def test_configuraciones_difieren_en_los_tres_operadores(self):
        cfgs = CONFIGURACIONES.values()
        self.assertGreaterEqual(len(CONFIGURACIONES), 3)
        self.assertGreaterEqual(len({c.seleccion for c in cfgs}), 3)
        self.assertGreaterEqual(len({(c.cruza_os, c.cruza_ma) for c in cfgs}), 3)
        self.assertGreaterEqual(len({(c.mutacion_os, c.mutacion_ma) for c in cfgs}), 3)

    def test_estadisticas(self):
        for rc in self.campana:
            valores = [r.makespan for r in rc.resultados]
            est = rc.estadisticas
            self.assertEqual(est.mejor, min(valores))
            self.assertEqual(est.peor, max(valores))
            self.assertAlmostEqual(est.promedio, fmean(valores))
            self.assertGreaterEqual(est.desviacion, 0)

    def test_seleccion_de_configuracion(self):
        menor = min(rc.estadisticas.promedio for rc in self.campana)
        self.assertEqual(seleccionar_configuracion(self.campana).estadisticas.promedio, menor)
        self.assertIs(self.seleccionada, seleccionar_configuracion(self.campana))

    def test_tres_mejores(self):
        resultados = self.seleccionada.resultados
        mejores = tres_mejores(resultados)
        claves = [(r.makespan, r.semilla) for r in mejores]
        self.assertEqual(claves, sorted((r.makespan, r.semilla) for r in resultados)[:3])

    def test_curvas_de_convergencia(self):
        resultados = self.seleccionada.resultados
        mejor, peor, promedio = curvas_convergencia(resultados)
        self.assertEqual(len(promedio), 11)
        self.assertEqual(mejor[-1], self.seleccionada.estadisticas.mejor)
        self.assertEqual(peor[-1], self.seleccionada.estadisticas.peor)
        self.assertAlmostEqual(promedio[-1], self.seleccionada.estadisticas.promedio)
        self.assertAlmostEqual(promedio[0], fmean(r.historial[0] for r in resultados))

    def test_estructura_de_salida(self):
        for nombre in ("comparacion.csv", "comparacion.md", "convergencia.png",
                       "gantt_top1.png", "gantt_top2.png", "gantt_top3.png"):  # fmt: skip
            self.assertGreater((self.carpeta / nombre).stat().st_size, 0, nombre)
        for cfg in CONFIGURACIONES:
            carpeta = self.carpeta / cfg
            self.assertEqual(len(list(carpeta.glob("corrida_*.txt"))), 20)
            for nombre in ("resumen.csv", "estadisticas.txt", "convergencia.csv"):
                self.assertTrue((carpeta / nombre).is_file(), nombre)
            parametros = json.loads((carpeta / "parametros.json").read_text(encoding="utf-8"))
            self.assertEqual(parametros["semillas"], list(range(1, 21)))
            self.assertEqual(parametros["configuracion"]["poblacion"], 20)
            with open(carpeta / "resumen.csv", newline="", encoding="utf-8") as archivo:
                filas = list(csv.DictReader(archivo))
            self.assertEqual(len(filas), 20)
            with open(carpeta / "convergencia.csv", newline="", encoding="utf-8") as archivo:
                self.assertEqual(len(list(csv.reader(archivo))), 12)  # encabezado + 11

    def test_tabla_comparativa(self):
        with open(self.carpeta / "comparacion.csv", newline="", encoding="utf-8") as archivo:
            filas = list(csv.DictReader(archivo))
        self.assertEqual([f["configuracion"] for f in filas], list(CONFIGURACIONES))
        marcadas = [f["configuracion"] for f in filas if f["seleccionada"] == "si"]
        self.assertEqual(marcadas, [self.seleccionada.configuracion.nombre])


class LineaDeComandos(unittest.TestCase):
    ESCENARIO1 = str(ESCENAS / "Escenario1.txt")

    def test_corrida_unica(self):
        codigo, salida, _ = ejecutar_cli(
            self.ESCENARIO1, "--unica", "--semilla", "5", "--generaciones", "10"
        )
        self.assertEqual(codigo, 0)
        self.assertIn("Semilla: 5", salida)
        self.assertIn("Makespan (C_max):", salida)
        self.assertIn("Máquina M4", salida)
        self.assertIn("Espacio de búsqueda", salida)

    def test_archivo_inexistente(self):
        codigo, _, errores = ejecutar_cli("no_existe.txt", "--unica")
        self.assertEqual(codigo, 1)
        self.assertIn("no se encontró", errores)

    def test_parametro_invalido(self):
        codigo, _, errores = ejecutar_cli(self.ESCENARIO1, "--unica", "--pc", "1.5")
        self.assertEqual(codigo, 2)
        self.assertIn("pc", errores)

    def test_tecnica_desconocida(self):
        codigo, _, errores = ejecutar_cli(self.ESCENARIO1, "--unica", "--cruza-os", "pmx")
        self.assertEqual(codigo, 2)
        self.assertIn("jbx, pox", errores)

    def test_campana_sobre_carpeta_y_aviso_de_resultados_previos(self):
        with tempfile.TemporaryDirectory() as salida:
            argumentos = [str(ESCENAS), "--corridas", "3", "--generaciones", "5",
                          "--poblacion", "10", "--salida", salida]  # fmt: skip
            codigo, texto, _ = ejecutar_cli(*argumentos)
            self.assertEqual(codigo, 0)
            carpetas = sorted(p.name for p in Path(salida).iterdir())
            self.assertEqual(carpetas, ["Escenario1", "Escenario2", "Escenario3"])
            self.assertIn("promedio", texto)

            codigo, _, errores = ejecutar_cli(*argumentos)
            self.assertEqual(codigo, 2)
            self.assertIn("--sobrescribir", errores)

            codigo, texto, _ = ejecutar_cli(*argumentos, "--sobrescribir")
            self.assertEqual(codigo, 0)
            self.assertIn("Aviso", texto)


if __name__ == "__main__":
    unittest.main()
