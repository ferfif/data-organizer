import unittest

from comun import ESCENARIO_MINIMO, ESCENAS, escenario, escenario_desde_texto

from planificador.escenario import ErrorEscenario, cargar_escenario


class CargaDeEscenarios(unittest.TestCase):
    def test_dimensiones_de_los_tres_escenarios(self):
        esperado = {1: (5, 4, 6, 19), 2: (8, 10, 10, 40), 3: (15, 5, 12, 59)}
        for numero, dimensiones in esperado.items():
            with self.subTest(escenario=numero):
                esc = escenario(numero)
                self.assertEqual(
                    (esc.num_operaciones, esc.num_maquinas, esc.num_trabajos, esc.total_operaciones),
                    dimensiones,
                )

    def test_valores_del_escenario_1(self):
        esc = escenario(1)
        self.assertEqual(esc.tiempos[0][2], 2.5)  # O1 en M3
        self.assertEqual(esc.tiempos[1][3], 9.0)
        self.assertEqual(esc.consumo[0][0], 1.2)

    def test_secuencia_de_operaciones_conservada(self):
        esc = escenario(1)
        self.assertEqual(esc.trabajos[2].nombre, "J3")
        self.assertEqual(esc.trabajos[2].operaciones, (0, 1, 2, 3, 4))
        self.assertEqual(esc.trabajos[0].operaciones, (1, 3, 4))
        self.assertEqual([t.nombre for t in esc.trabajos], ["J1", "J2", "J3", "J4", "J5", "J6"])

    def test_sin_llegadas_todos_llegan_en_cero(self):
        for numero in (1, 2, 3):
            self.assertTrue(all(t.llegada == 0 for t in escenario(numero).trabajos))

    def test_seccion_de_llegadas(self):
        texto = ESCENARIO_MINIMO + "#Llegadas\nJ2=6.5\n"
        esc = escenario_desde_texto(texto)
        self.assertEqual([t.llegada for t in esc.trabajos], [0.0, 6.5])

    def test_consumo_es_opcional(self):
        texto = "#tiempos\n1 2\n#trabajos\nJ1={O1}\n"
        self.assertIsNone(escenario_desde_texto(texto).consumo)

    def test_etiquetas(self):
        esc = escenario(1)
        self.assertEqual(esc.etiqueta(0), "J1-O2")
        self.assertEqual(esc.etiqueta(6), "J3-O1")
        repetido = escenario_desde_texto("#tiempos\n1 2\n#trabajos\nJ1={O1,O1}\n")
        self.assertEqual([repetido.etiqueta(g) for g in (0, 1)], ["J1-O1#1", "J1-O1#2"])


class ValidacionDeEscenarios(unittest.TestCase):
    def _falla(self, texto: str, *fragmentos: str):
        with self.assertRaises(ErrorEscenario) as contexto:
            escenario_desde_texto(texto, "malo.txt")
        mensaje = str(contexto.exception)
        self.assertIn("malo.txt", mensaje)
        for fragmento in fragmentos:
            self.assertIn(fragmento, mensaje)

    def test_archivo_inexistente(self):
        with self.assertRaises(ErrorEscenario) as contexto:
            cargar_escenario(ESCENAS / "no_existe.txt")
        self.assertIn("no_existe.txt", str(contexto.exception))

    def test_falta_seccion_de_tiempos(self):
        self._falla("#trabajos\nJ1={O1}\n", "tiempos")

    def test_falta_seccion_de_trabajos(self):
        self._falla("#tiempos\n1 2\n", "trabajos")

    def test_matriz_irregular(self):
        self._falla("#tiempos\n1 2 3\n4 5\n#trabajos\nJ1={O1}\n", "fila 2", "tiempos")

    def test_dimensiones_distintas(self):
        self._falla("#tiempos\n1 2\n#consumo\n1 2\n3 4\n#trabajos\nJ1={O1}\n", "consumo")

    def test_valor_no_numerico(self):
        self._falla("#tiempos\n1 abc\n#trabajos\nJ1={O1}\n", "abc")

    def test_tiempo_no_positivo(self):
        self._falla("#tiempos\n1 0\n#trabajos\nJ1={O1}\n", "no positivo")

    def test_operacion_inexistente(self):
        self._falla("#tiempos\n1 2\n#trabajos\nJ1={O1,O9}\n", "J1", "O9")

    def test_trabajo_vacio(self):
        self._falla("#tiempos\n1 2\n#trabajos\nJ1={}\n", "J1", "no tiene operaciones")

    def test_llegada_negativa(self):
        self._falla("#tiempos\n1 2\n#trabajos\nJ1={O1}\n#llegadas\nJ1=-1\n", "negativo")

    def test_encabezado_desconocido(self):
        self._falla("#tiempos\n1 2\n#otra cosa\n1\n#trabajos\nJ1={O1}\n", "no reconocido")


if __name__ == "__main__":
    unittest.main()
