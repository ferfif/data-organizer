"""Ciclo del algoritmo genético: generacional con elitismo."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import factorial
from random import Random

from . import operadores as ops
from .escenario import Escenario
from .operadores import Individuo
from .planificacion import Planificacion, calcular_makespan, decodificar

PROPORCION_SEMBRADA = 0.2


class ErrorConfiguracion(ValueError):
    """Parámetro o técnica inválida en la configuración del algoritmo."""


@dataclass(frozen=True)
class Configuracion:
    nombre: str = "A"
    seleccion: str = "torneo"
    cruza_os: str = "pox"
    cruza_ma: str = "uniforme"
    mutacion_os: str = "intercambio"
    mutacion_ma: str = "aleatoria"
    poblacion: int = 200
    generaciones: int = 500
    pc: float = 0.9
    pm: float = 0.4
    elites: int = 2
    torneo_k: int = 3

    def como_dict(self) -> dict:
        return asdict(self)

    def validar(self) -> None:
        tecnicas = (
            ("seleccion", self.seleccion, ops.SELECCIONES),
            ("cruza_os", self.cruza_os, ops.CRUZAS_OS),
            ("cruza_ma", self.cruza_ma, ops.CRUZAS_MA),
            ("mutacion_os", self.mutacion_os, ops.MUTACIONES_OS),
            ("mutacion_ma", self.mutacion_ma, ops.MUTACIONES_MA),
        )
        for campo, valor, registro in tecnicas:
            if valor not in registro:
                raise ErrorConfiguracion(
                    f"técnica desconocida para {campo}: '{valor}'. "
                    f"Disponibles: {', '.join(sorted(registro))}"
                )
        if self.poblacion < 2:
            raise ErrorConfiguracion(f"poblacion debe ser al menos 2 (se indicó {self.poblacion})")
        if self.generaciones < 0:
            raise ErrorConfiguracion(
                f"generaciones no puede ser negativo (se indicó {self.generaciones})"
            )
        for campo, valor in (("pc", self.pc), ("pm", self.pm)):
            if not 0.0 <= valor <= 1.0:
                raise ErrorConfiguracion(f"{campo} debe estar entre 0 y 1 (se indicó {valor})")
        if not 0 <= self.elites < self.poblacion:
            raise ErrorConfiguracion(
                f"elites debe estar entre 0 y poblacion - 1 (se indicó {self.elites})"
            )
        if not 1 <= self.torneo_k <= self.poblacion:
            raise ErrorConfiguracion(
                f"torneo_k debe estar entre 1 y poblacion (se indicó {self.torneo_k})"
            )


@dataclass
class Resultado:
    semilla: int
    configuracion: Configuracion
    mejor: Individuo
    historial: list[float]  # mejor makespan hasta cada generación (incluye la inicial)
    planificacion: Planificacion

    @property
    def makespan(self) -> float:
        return self.mejor.aptitud


def tamano_espacio(escenario: Escenario) -> tuple[int, int, int]:
    """(asignaciones p^N, secuencias N!/prod(n_j!), total) de la codificación."""
    n = escenario.total_operaciones
    asignaciones = escenario.num_maquinas**n
    secuencias = factorial(n)
    for trabajo in escenario.trabajos:
        secuencias //= factorial(len(trabajo.operaciones))
    return asignaciones, secuencias, asignaciones * secuencias


def es_valido(escenario: Escenario, individuo: Individuo) -> bool:
    n = escenario.total_operaciones
    if len(individuo.os) != n or len(individuo.ma) != n:
        return False
    if any(not 0 <= m < escenario.num_maquinas for m in individuo.ma):
        return False
    return all(
        individuo.os.count(j) == len(trabajo.operaciones)
        for j, trabajo in enumerate(escenario.trabajos)
    )


def _os_por_llegada(escenario: Escenario) -> list[int]:
    orden = sorted(range(escenario.num_trabajos), key=lambda j: (escenario.llegadas[j], j))
    return [j for j in orden for _ in escenario.trabajos[j].operaciones]


def _ma_minimo_tiempo(escenario: Escenario) -> list[int]:
    return [fila.index(min(fila)) for fila in escenario.tiempos_gen]


def poblacion_inicial(escenario: Escenario, tamano: int, rng: Random) -> list[Individuo]:
    """80 % aleatoria y 20 % sembrada con la máquina de menor tiempo por operación.

    El primer sembrado encola por orden de llegada; los demás usan un orden
    aleatorio para no llenar la población de clones.
    """
    base_os = escenario.trabajo_gen[:]
    p = escenario.num_maquinas
    sembrados = int(tamano * PROPORCION_SEMBRADA)
    poblacion = []
    for i in range(tamano):
        if i == 0 and sembrados:
            os = _os_por_llegada(escenario)
        else:
            os = base_os[:]
            rng.shuffle(os)
        if i < sembrados:
            ma = _ma_minimo_tiempo(escenario)
        else:
            ma = [rng.randrange(p) for _ in base_os]
        poblacion.append(Individuo(os, ma))
    return poblacion


def ejecutar(escenario: Escenario, configuracion: Configuracion, semilla: int) -> Resultado:
    """Una corrida completa, determinada por (escenario, configuración, semilla)."""
    configuracion.validar()
    cfg = configuracion
    rng = Random(semilla)
    seleccionar = ops.SELECCIONES[cfg.seleccion]
    cruzar_os = ops.CRUZAS_OS[cfg.cruza_os]
    cruzar_ma = ops.CRUZAS_MA[cfg.cruza_ma]
    mutar_os = ops.MUTACIONES_OS[cfg.mutacion_os]
    mutar_ma = ops.MUTACIONES_MA[cfg.mutacion_ma]

    poblacion = poblacion_inicial(escenario, cfg.poblacion, rng)
    for ind in poblacion:
        ind.aptitud = calcular_makespan(escenario, ind.os, ind.ma)
    poblacion.sort(key=lambda ind: ind.aptitud)
    mejor = poblacion[0]
    historial = [mejor.aptitud]

    for _ in range(cfg.generaciones):
        elegir = seleccionar(poblacion, rng, cfg.torneo_k)
        nueva = [Individuo(e.os[:], e.ma[:], e.aptitud) for e in poblacion[: cfg.elites]]
        while len(nueva) < cfg.poblacion:
            padre, madre = elegir(), elegir()
            if rng.random() < cfg.pc:
                os1, os2 = cruzar_os(padre.os, madre.os, escenario, rng)
                ma1, ma2 = cruzar_ma(padre.ma, madre.ma, escenario, rng)
            else:
                os1, os2 = padre.os[:], madre.os[:]
                ma1, ma2 = padre.ma[:], madre.ma[:]
            for os, ma in ((os1, ma1), (os2, ma2)):
                if len(nueva) == cfg.poblacion:
                    break
                if rng.random() < cfg.pm:
                    mutar_os(os, escenario, rng)
                if rng.random() < cfg.pm:
                    mutar_ma(ma, escenario, rng)
                nueva.append(Individuo(os, ma, calcular_makespan(escenario, os, ma)))
        nueva.sort(key=lambda ind: ind.aptitud)
        poblacion = nueva
        if poblacion[0].aptitud < mejor.aptitud:
            mejor = poblacion[0]
        historial.append(mejor.aptitud)

    return Resultado(
        semilla, cfg, mejor, historial, decodificar(escenario, mejor.os, mejor.ma)
    )
