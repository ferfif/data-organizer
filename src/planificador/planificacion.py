"""Decodificación de una solución en una planificación y cálculo de sus métricas.

Una solución son dos listas de longitud N (operaciones a planificar):

- ``os``: secuencia de índices de trabajo; la k-ésima aparición del trabajo j
  representa su k-ésima operación.
- ``ma``: máquina (base 0) de cada operación, en el orden fijo de genes del escenario.
"""

from __future__ import annotations

from dataclasses import dataclass

from .escenario import Escenario

TOLERANCIA = 1e-9


@dataclass(frozen=True)
class OperacionPlanificada:
    gen: int
    trabajo: int
    maquina: int
    inicio: float
    fin: float


@dataclass
class Planificacion:
    escenario: Escenario
    operaciones: list[OperacionPlanificada]  # en orden de encolado
    makespan: float
    cargas: list[float]  # suma de tiempos de proceso por máquina
    fin_trabajos: list[float]
    energia: float | None

    @property
    def carga_maxima(self) -> float:
        return max(self.cargas)

    def por_maquina(self) -> list[list[OperacionPlanificada]]:
        colas: list[list[OperacionPlanificada]] = [
            [] for _ in range(self.escenario.num_maquinas)
        ]
        for op in self.operaciones:
            colas[op.maquina].append(op)
        return colas


def calcular_makespan(escenario: Escenario, os: list[int], ma: list[int]) -> float:
    """Versión rápida de ``decodificar`` que solo devuelve el makespan (aptitud)."""
    siguiente = escenario.inicio_trabajo[:]
    libre_trabajo = escenario.llegadas[:]
    libre_maquina = [0.0] * escenario.num_maquinas
    tiempos = escenario.tiempos_gen
    for j in os:
        gen = siguiente[j]
        siguiente[j] = gen + 1
        m = ma[gen]
        a = libre_trabajo[j]
        b = libre_maquina[m]
        fin = (a if a > b else b) + tiempos[gen][m]
        libre_trabajo[j] = fin
        libre_maquina[m] = fin
    return max(libre_maquina)


def decodificar(escenario: Escenario, os: list[int], ma: list[int]) -> Planificacion:
    """Decodificador semiactivo: cada operación se encola al final de su máquina.

    inicio = max(fin de la operación previa del trabajo, máquina libre, llegada)
    """
    siguiente = escenario.inicio_trabajo[:]
    libre_trabajo = escenario.llegadas[:]
    libre_maquina = [0.0] * escenario.num_maquinas
    cargas = [0.0] * escenario.num_maquinas
    energia = 0.0 if escenario.consumo is not None else None
    operaciones = []
    for j in os:
        gen = siguiente[j]
        siguiente[j] = gen + 1
        m = ma[gen]
        duracion = escenario.tiempos_gen[gen][m]
        inicio = max(libre_trabajo[j], libre_maquina[m])
        fin = inicio + duracion
        libre_trabajo[j] = fin
        libre_maquina[m] = fin
        cargas[m] += duracion
        if energia is not None:
            energia += escenario.consumo[escenario.tipo_gen[gen]][m]
        operaciones.append(OperacionPlanificada(gen, j, m, inicio, fin))
    return Planificacion(
        escenario, operaciones, max(libre_maquina), cargas, libre_trabajo, energia
    )


def verificar_factibilidad(plan: Planificacion) -> list[str]:
    """Devuelve la lista de violaciones encontradas (vacía si es factible)."""
    esc = plan.escenario
    problemas = []

    genes = sorted(op.gen for op in plan.operaciones)
    if genes != list(range(esc.total_operaciones)):
        problemas.append("no todas las operaciones están planificadas exactamente una vez")

    por_gen = {op.gen: op for op in plan.operaciones}
    for op in plan.operaciones:
        etiqueta = esc.etiqueta(op.gen)
        if not 0 <= op.maquina < esc.num_maquinas:
            problemas.append(f"{etiqueta}: máquina inexistente")
            continue
        duracion = esc.tiempos_gen[op.gen][op.maquina]
        if abs((op.fin - op.inicio) - duracion) > TOLERANCIA:
            problemas.append(f"{etiqueta}: la duración no coincide con la tabla")
        if op.inicio < esc.llegadas[op.trabajo] - TOLERANCIA:
            problemas.append(f"{etiqueta}: inicia antes de la llegada de su trabajo")
        if op.gen > esc.inicio_trabajo[op.trabajo]:
            previa = por_gen.get(op.gen - 1)
            if previa is not None and op.inicio < previa.fin - TOLERANCIA:
                problemas.append(f"{etiqueta}: inicia antes de terminar la operación previa")

    for m, cola in enumerate(plan.por_maquina(), start=1):
        ordenada = sorted(cola, key=lambda o: o.inicio)
        for anterior, actual in zip(ordenada, ordenada[1:]):
            if actual.inicio < anterior.fin - TOLERANCIA:
                problemas.append(
                    f"M{m}: {esc.etiqueta(anterior.gen)} y {esc.etiqueta(actual.gen)} se traslapan"
                )

    fin_real = max((op.fin for op in plan.operaciones), default=0.0)
    if abs(fin_real - plan.makespan) > TOLERANCIA:
        problemas.append("el makespan no coincide con el mayor tiempo de finalización")
    return problemas
