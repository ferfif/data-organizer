import unittest
from collections import Counter
from random import Random

from comun import escenario

from planificador import operadores as ops
from planificador.genetico import (
    Configuracion,
    ErrorConfiguracion,
    ejecutar,
    es_valido,
    poblacion_inicial,
    tamano_espacio,
)
from planificador.operadores import Individuo
from planificador.planificacion import verificar_factibilidad

RAPIDA = Configuracion(poblacion=30, generaciones=25)


class PoblacionYEspacio(unittest.TestCase):
    def test_poblacion_inicial_valida(self):
        for numero in (1, 2, 3):
            esc = escenario(numero)
            poblacion = poblacion_inicial(esc, 100, Random(0))
            self.assertEqual(len(poblacion), 100)
            self.assertTrue(all(es_valido(esc, ind) for ind in poblacion))

    def test_validador_rechaza_individuos_invalidos(self):
        esc = escenario(1)
        ind = poblacion_inicial(esc, 2, Random(0))[1]
        self.assertFalse(es_valido(esc, Individuo(ind.os[:-1], ind.ma)))
        self.assertFalse(es_valido(esc, Individuo(ind.os, [esc.num_maquinas] * len(ind.ma))))
        self.assertFalse(es_valido(esc, Individuo([0] * len(ind.os), ind.ma)))

    def test_tamano_del_espacio_de_busqueda(self):
        ordenes = {1: (11, 11, 22), 2: (40, 33, 73), 3: (41, 54, 95)}
        for numero, esperado in ordenes.items():
            partes = tamano_espacio(escenario(numero))
            self.assertEqual(tuple(len(str(x)) - 1 for x in partes), esperado)
            self.assertEqual(partes[0] * partes[1], partes[2])
        self.assertEqual(tamano_espacio(escenario(1))[0], 4**19)


class Operadores(unittest.TestCase):
    def setUp(self):
        self.esc = escenario(3)
        self.rng = Random(42)
        self.poblacion = poblacion_inicial(self.esc, 60, self.rng)

    def _pareja(self):
        return self.rng.sample(self.poblacion, 2)

    def test_seleccion_prefiere_al_mejor(self):
        poblacion = [Individuo([], [], float(a)) for a in range(10, 30)]
        for nombre, tecnica in ops.SELECCIONES.items():
            with self.subTest(seleccion=nombre):
                elegir = tecnica(poblacion, Random(1), 3)
                conteo = Counter(elegir().aptitud for _ in range(5000))
                self.assertGreater(conteo[10.0], conteo[29.0])
                self.assertGreater(conteo[10.0], 5000 / len(poblacion))

    def test_cruzas_de_os_dan_hijos_validos(self):
        for nombre, cruza in ops.CRUZAS_OS.items():
            with self.subTest(cruza=nombre):
                for _ in range(1000):
                    a, b = self._pareja()
                    for hijo in cruza(a.os, b.os, self.esc, self.rng):
                        self.assertTrue(es_valido(self.esc, Individuo(hijo, a.ma)))

    def test_pox_conserva_las_posiciones_del_subconjunto(self):
        a, b = self._pareja()
        hijo, _ = ops.cruza_pox(a.os, b.os, self.esc, Random(5))
        trabajos = ops._subconjunto_trabajos(self.esc, Random(5))
        for gen_padre, gen_hijo in zip(a.os, hijo):
            self.assertEqual(gen_padre in trabajos, gen_hijo in trabajos)
            if gen_padre in trabajos:
                self.assertEqual(gen_padre, gen_hijo)
        self.assertEqual(
            [g for g in hijo if g not in trabajos], [g for g in b.os if g not in trabajos]
        )

    def test_cruzas_de_ma_dan_hijos_validos(self):
        for nombre, cruza in ops.CRUZAS_MA.items():
            with self.subTest(cruza=nombre):
                for _ in range(1000):
                    a, b = self._pareja()
                    for hijo in cruza(a.ma, b.ma, self.esc, self.rng):
                        self.assertTrue(es_valido(self.esc, Individuo(a.os, hijo)))
                        self.assertTrue(all(g in (x, y) for g, x, y in zip(hijo, a.ma, b.ma)))

    def test_mutaciones_dan_individuos_validos(self):
        for nombre, mutar in ops.MUTACIONES_OS.items():
            with self.subTest(mutacion=nombre):
                for _ in range(1000):
                    ind = self.rng.choice(self.poblacion)
                    os = ind.os[:]
                    mutar(os, self.esc, self.rng)
                    self.assertTrue(es_valido(self.esc, Individuo(os, ind.ma)))
        for nombre, mutar in ops.MUTACIONES_MA.items():
            with self.subTest(mutacion=nombre):
                for _ in range(1000):
                    ind = self.rng.choice(self.poblacion)
                    ma = ind.ma[:]
                    mutar(ma, self.esc, self.rng)
                    self.assertTrue(es_valido(self.esc, Individuo(ind.os, ma)))
                    self.assertEqual(sum(x != y for x, y in zip(ma, ind.ma)), 1)

    def test_mutacion_de_balance_descarga_la_maquina_mas_cargada(self):
        n = self.esc.total_operaciones
        ma = [0] * n  # todo en M1: es, con claridad, la más cargada
        ops.mutacion_balance(ma, self.esc, self.rng)
        self.assertEqual(ma.count(0), n - 1)
        movida = next(g for g, m in enumerate(ma) if m != 0)
        fila = self.esc.tiempos_gen[movida]
        self.assertEqual(fila[ma[movida]], min(fila[1:]))


class Ejecucion(unittest.TestCase):
    def test_historial_no_creciente_y_longitud(self):
        for cfg in (RAPIDA, Configuracion("C", "ranking", "pox", "uniforme", "intercambio",
                                           "balance", 30, 25)):  # fmt: skip
            resultado = ejecutar(escenario(1), cfg, 3)
            historial = resultado.historial
            self.assertEqual(len(historial), cfg.generaciones + 1)
            self.assertTrue(all(a >= b for a, b in zip(historial, historial[1:])))
            self.assertEqual(historial[-1], resultado.makespan)

    def test_devuelve_la_mejor_solucion_y_es_factible(self):
        esc = escenario(2)
        resultado = ejecutar(esc, RAPIDA, 1)
        self.assertTrue(es_valido(esc, resultado.mejor))
        self.assertAlmostEqual(resultado.planificacion.makespan, resultado.makespan)
        self.assertEqual(verificar_factibilidad(resultado.planificacion), [])
        self.assertLess(resultado.makespan, resultado.historial[0])

    def test_misma_semilla_mismo_resultado(self):
        esc = escenario(1)
        a, b = ejecutar(esc, RAPIDA, 7), ejecutar(esc, RAPIDA, 7)
        self.assertEqual(a.makespan, b.makespan)
        self.assertEqual(a.historial, b.historial)
        self.assertEqual((a.mejor.os, a.mejor.ma), (b.mejor.os, b.mejor.ma))

    def test_semillas_distintas_historiales_distintos(self):
        esc = escenario(3)
        self.assertNotEqual(ejecutar(esc, RAPIDA, 1).historial, ejecutar(esc, RAPIDA, 2).historial)

    def test_parametros_invalidos(self):
        esc = escenario(1)
        casos = {
            "pc": Configuracion(pc=1.5),
            "pm": Configuracion(pm=-0.1),
            "poblacion": Configuracion(poblacion=1),
            "elites": Configuracion(poblacion=10, elites=10),
            "generaciones": Configuracion(generaciones=-1),
        }
        for campo, cfg in casos.items():
            with self.subTest(campo=campo):
                with self.assertRaises(ErrorConfiguracion) as contexto:
                    ejecutar(esc, cfg, 1)
                self.assertIn(campo, str(contexto.exception))

    def test_tecnica_desconocida_lista_las_disponibles(self):
        with self.assertRaises(ErrorConfiguracion) as contexto:
            ejecutar(escenario(1), Configuracion(cruza_os="pmx"), 1)
        mensaje = str(contexto.exception)
        self.assertIn("pmx", mensaje)
        self.assertIn("jbx, pox", mensaje)


if __name__ == "__main__":
    unittest.main()
