"""Operadores de selección, cruza y mutación, registrados por nombre.

Todos preservan la validez del cromosoma por construcción:

- OS sigue siendo una permutación con repetición (cada trabajo aparece tantas
  veces como operaciones tiene).
- MA solo contiene máquinas existentes.
"""

from __future__ import annotations

from itertools import accumulate
from random import Random
from typing import Callable

from .escenario import Escenario


class Individuo:
    __slots__ = ("os", "ma", "aptitud")

    def __init__(self, os: list[int], ma: list[int], aptitud: float | None = None):
        self.os = os
        self.ma = ma
        self.aptitud = aptitud  # makespan; menor es mejor


# --------------------------------------------------------------------------
# Selección: cada técnica recibe la población ya evaluada y devuelve una
# función que entrega un padre por llamada.
# --------------------------------------------------------------------------

Selector = Callable[[], Individuo]


def seleccion_torneo(poblacion: list[Individuo], rng: Random, k: int = 3) -> Selector:
    def elegir() -> Individuo:
        return min(rng.sample(poblacion, k), key=lambda ind: ind.aptitud)

    return elegir


def seleccion_ruleta(poblacion: list[Individuo], rng: Random, k: int = 3) -> Selector:
    # Se minimiza: el peso es la distancia al peor individuo, más un épsilon
    # para que el peor conserve una probabilidad pequeña y no nula.
    aptitudes = [ind.aptitud for ind in poblacion]
    peor, mejor = max(aptitudes), min(aptitudes)
    epsilon = 0.01 * (peor - mejor) + 1e-9
    acumulados = list(accumulate(peor - a + epsilon for a in aptitudes))

    def elegir() -> Individuo:
        return rng.choices(poblacion, cum_weights=acumulados)[0]

    return elegir


def seleccion_ranking(poblacion: list[Individuo], rng: Random, k: int = 3) -> Selector:
    # Ranking lineal: el mejor recibe peso n y el peor peso 1.
    ordenada = sorted(poblacion, key=lambda ind: ind.aptitud)
    n = len(ordenada)
    acumulados = list(accumulate(range(n, 0, -1)))

    def elegir() -> Individuo:
        return rng.choices(ordenada, cum_weights=acumulados)[0]

    return elegir


# --------------------------------------------------------------------------
# Cruza de la secuencia de operaciones (OS)
# --------------------------------------------------------------------------


def _subconjunto_trabajos(escenario: Escenario, rng: Random) -> set[int]:
    n = escenario.num_trabajos
    return set(rng.sample(range(n), rng.randint(1, n - 1)))


def _heredar(conserva: list[int], aporta: list[int], trabajos: set[int]) -> list[int]:
    """Conserva en su lugar los genes de ``trabajos`` y rellena con el otro padre."""
    resto = (g for g in aporta if g not in trabajos)
    return [g if g in trabajos else next(resto) for g in conserva]


def cruza_pox(p1: list[int], p2: list[int], escenario: Escenario, rng: Random):
    """Precedence preserving order-based crossover."""
    if escenario.num_trabajos < 2:
        return p1[:], p2[:]
    trabajos = _subconjunto_trabajos(escenario, rng)
    return _heredar(p1, p2, trabajos), _heredar(p2, p1, trabajos)


def cruza_jbx(p1: list[int], p2: list[int], escenario: Escenario, rng: Random):
    """Job-based crossover: el segundo hijo conserva el subconjunto complementario."""
    if escenario.num_trabajos < 2:
        return p1[:], p2[:]
    trabajos = _subconjunto_trabajos(escenario, rng)
    complemento = set(range(escenario.num_trabajos)) - trabajos
    return _heredar(p1, p2, trabajos), _heredar(p2, p1, complemento)


# --------------------------------------------------------------------------
# Cruza de la asignación de máquinas (MA)
# --------------------------------------------------------------------------


def cruza_uniforme(p1: list[int], p2: list[int], escenario: Escenario, rng: Random):
    h1, h2 = p1[:], p2[:]
    for i in range(len(h1)):
        if rng.random() < 0.5:
            h1[i], h2[i] = h2[i], h1[i]
    return h1, h2


def cruza_dos_puntos(p1: list[int], p2: list[int], escenario: Escenario, rng: Random):
    n = len(p1)
    if n < 2:
        return p1[:], p2[:]
    a, b = sorted(rng.sample(range(n + 1), 2))
    return p1[:a] + p2[a:b] + p1[b:], p2[:a] + p1[a:b] + p2[b:]


# --------------------------------------------------------------------------
# Mutación de OS (modifican la lista en su lugar)
# --------------------------------------------------------------------------


def mutacion_intercambio(os: list[int], escenario: Escenario, rng: Random) -> None:
    if escenario.num_trabajos < 2:
        return
    i = rng.randrange(len(os))
    candidatos = [k for k, g in enumerate(os) if g != os[i]]
    j = rng.choice(candidatos)
    os[i], os[j] = os[j], os[i]


def mutacion_insercion(os: list[int], escenario: Escenario, rng: Random) -> None:
    if len(os) < 2:
        return
    gen = os.pop(rng.randrange(len(os)))
    os.insert(rng.randrange(len(os) + 1), gen)


# --------------------------------------------------------------------------
# Mutación de MA (modifican la lista en su lugar)
# --------------------------------------------------------------------------


def mutacion_aleatoria(ma: list[int], escenario: Escenario, rng: Random) -> None:
    p = escenario.num_maquinas
    if p < 2:
        return
    i = rng.randrange(len(ma))
    ma[i] = (ma[i] + rng.randrange(1, p)) % p  # siempre una máquina distinta


def mutacion_balance(ma: list[int], escenario: Escenario, rng: Random) -> None:
    """Mueve una operación de la máquina más cargada a la que menos crecería."""
    p = escenario.num_maquinas
    if p < 2:
        return
    tiempos = escenario.tiempos_gen
    cargas = [0.0] * p
    for gen, m in enumerate(ma):
        cargas[m] += tiempos[gen][m]
    origen = max(range(p), key=cargas.__getitem__)
    gen = rng.choice([g for g, m in enumerate(ma) if m == origen])
    ma[gen] = min(
        (m for m in range(p) if m != origen),
        key=lambda m: cargas[m] + tiempos[gen][m],
    )


SELECCIONES = {
    "torneo": seleccion_torneo,
    "ruleta": seleccion_ruleta,
    "ranking": seleccion_ranking,
}
CRUZAS_OS = {"pox": cruza_pox, "jbx": cruza_jbx}
CRUZAS_MA = {"uniforme": cruza_uniforme, "dos_puntos": cruza_dos_puntos}
MUTACIONES_OS = {"intercambio": mutacion_intercambio, "insercion": mutacion_insercion}
MUTACIONES_MA = {"aleatoria": mutacion_aleatoria, "balance": mutacion_balance}
