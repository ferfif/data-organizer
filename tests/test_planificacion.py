import unittest
from random import Random

from comun import ESCENARIO_MINIMO, escenario, escenario_desde_texto

from planificador.genetico import poblacion_inicial
from planificador.planificacion import (
    OperacionPlanificada,
    calcular_makespan,
    decodificar,
    verificar_factibilidad,
)
from planificador.reportes import reporte_maquinas

# Caso calculado a mano sobre el Escenario 1: los trabajos se encolan en orden
# J1..J6 y cada tipo de operación va siempre a la misma máquina:
#   O1->M3 (2.5)  O2->M2 (4.2)  O3->M3 (5.5)  O4->M1 (4.8)  O5->M4 (3.6)
MAQUINA_POR_TIPO = {0: 2, 1: 1, 2: 2, 3: 0, 4: 3}
ESPERADO = {  # etiqueta: (máquina, inicio, fin)
    "J1-O2": (1, 0.0, 4.2), "J1-O4": (0, 4.2, 9.0), "J1-O5": (3, 9.0, 12.6),
    "J2-O1": (2, 0.0, 2.5), "J2-O3": (2, 2.5, 8.0), "J2-O5": (3, 12.6, 16.2),
    "J3-O1": (2, 8.0, 10.5), "J3-O2": (1, 10.5, 14.7), "J3-O3": (2, 14.7, 20.2),
    "J3-O4": (0, 20.2, 25.0), "J3-O5": (3, 25.0, 28.6),
    "J4-O4": (0, 25.0, 29.8), "J4-O5": (3, 29.8, 33.4),
    "J5-O2": (1, 14.7, 18.9), "J5-O4": (0, 29.8, 34.6),
    "J6-O1": (2, 20.2, 22.7), "J6-O2": (1, 22.7, 26.9), "J6-O4": (0, 34.6, 39.4),
    "J6-O5": (3, 39.4, 43.0),
}  # fmt: skip


def caso_manual():
    esc = escenario(1)
    os = esc.trabajo_gen[:]
    ma = [MAQUINA_POR_TIPO[tipo] for tipo in esc.tipo_gen]
    return esc, os, ma


class CasoManual(unittest.TestCase):
    def setUp(self):
        self.esc, self.os, self.ma = caso_manual()
        self.plan = decodificar(self.esc, self.os, self.ma)

    def test_inicio_y_fin_de_cada_operacion(self):
        self.assertEqual(len(self.plan.operaciones), 19)
        for op in self.plan.operaciones:
            maquina, inicio, fin = ESPERADO[self.esc.etiqueta(op.gen)]
            self.assertEqual(op.maquina, maquina)
            self.assertAlmostEqual(op.inicio, inicio)
            self.assertAlmostEqual(op.fin, fin)

    def test_metricas(self):
        self.assertAlmostEqual(self.plan.makespan, 43.0)
        for carga, esperada in zip(self.plan.cargas, (24.0, 16.8, 18.5, 18.0)):
            self.assertAlmostEqual(carga, esperada)
        self.assertAlmostEqual(self.plan.carga_maxima, 24.0)
        for fin, esperado in zip(self.plan.fin_trabajos, (12.6, 16.2, 28.6, 33.4, 34.6, 43.0)):
            self.assertAlmostEqual(fin, esperado)
        self.assertAlmostEqual(self.plan.energia, 90.5)

    def test_makespan_rapido_coincide(self):
        self.assertAlmostEqual(calcular_makespan(self.esc, self.os, self.ma), 43.0)

    def test_es_factible(self):
        self.assertEqual(verificar_factibilidad(self.plan), [])

    def test_evaluacion_determinista(self):
        self.assertEqual(self.plan.operaciones, decodificar(self.esc, self.os, self.ma).operaciones)

    def test_reporte_por_maquina(self):
        texto = reporte_maquinas(self.plan, {"Semilla": 7})
        self.assertIn("Semilla: 7", texto)
        self.assertIn("Makespan (C_max): 43.00", texto)
        self.assertIn("Carga máxima por máquina (f1): 24.00", texto)
        self.assertIn("Consumo energético total: 90.50", texto)
        for m in (1, 2, 3, 4):
            self.assertIn(f"Máquina M{m}", texto)
        lineas = [l.split() for l in texto.splitlines()]
        self.assertIn(["J3-O2", "10.50", "14.70", "4.20"], lineas)
        self.assertIn("Tiempo total de proceso: 24.00 | Fin de la última operación: 39.40", texto)
        self.assertIn("J4: 33.40", texto)


class Propiedades(unittest.TestCase):
    def test_individuos_aleatorios_son_factibles(self):
        for numero in (1, 2, 3):
            esc = escenario(numero)
            for ind in poblacion_inicial(esc, 1000, Random(numero)):
                plan = decodificar(esc, ind.os, ind.ma)
                self.assertEqual(verificar_factibilidad(plan), [])
                self.assertGreaterEqual(plan.makespan, plan.carga_maxima - 1e-9)
                self.assertAlmostEqual(plan.makespan, calcular_makespan(esc, ind.os, ind.ma))

    def test_el_verificador_detecta_traslapes_y_precedencia(self):
        esc, os, ma = caso_manual()
        plan = decodificar(esc, os, ma)
        op = plan.operaciones[1]  # J1-O4: se adelanta antes de que termine J1-O2
        plan.operaciones[1] = OperacionPlanificada(op.gen, op.trabajo, op.maquina, 0.0, 4.8)
        problemas = " ".join(verificar_factibilidad(plan))
        self.assertIn("operación previa", problemas)
        plan = decodificar(esc, os, ma)
        op = plan.operaciones[3]  # J2-O1 pasa a M2 en t=0, donde ya está J1-O2
        plan.operaciones[3] = OperacionPlanificada(op.gen, op.trabajo, 1, 0.0, 6.7)
        self.assertIn("se traslapan", " ".join(verificar_factibilidad(plan)))


class LlegadasYCasosEspeciales(unittest.TestCase):
    def test_espera_por_llegada(self):
        esc = escenario_desde_texto(ESCENARIO_MINIMO + "#llegadas\nJ2=6.5\n")
        plan = decodificar(esc, [1, 0, 0], [0, 1, 1])  # J2-O2 primero, en M2
        primera = plan.operaciones[0]
        self.assertEqual(esc.etiqueta(primera.gen), "J2-O2")
        self.assertAlmostEqual(primera.inicio, 6.5)
        self.assertAlmostEqual(primera.fin, 7.5)
        self.assertEqual(verificar_factibilidad(plan), [])

    def test_maquina_sin_operaciones_en_el_reporte(self):
        esc = escenario_desde_texto(ESCENARIO_MINIMO)
        plan = decodificar(esc, [0, 0, 1], [0, 1, 1])
        texto = reporte_maquinas(plan)
        self.assertIn("Máquina M3\n  (sin operaciones)\n  Tiempo total de proceso: 0.00", texto)

    def test_energia_no_disponible(self):
        esc = escenario_desde_texto("#tiempos\n1 2\n#trabajos\nJ1={O1}\n")
        plan = decodificar(esc, [0], [0])
        self.assertIsNone(plan.energia)
        self.assertIn("Consumo energético total: no disponible", reporte_maquinas(plan))


if __name__ == "__main__":
    unittest.main()
