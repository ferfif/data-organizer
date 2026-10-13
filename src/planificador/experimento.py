"""Campaña experimental: 20 corridas por configuración, estadísticas y salidas."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, replace
from pathlib import Path
from statistics import fmean, stdev
from typing import Callable

from .escenario import Escenario
from .genetico import Configuracion, Resultado, ejecutar, tamano_espacio
from .reportes import notacion_cientifica, reporte_maquinas, tabla_markdown

SEMILLAS = tuple(range(1, 21))

CONFIGURACIONES = {
    "A": Configuracion("A", "torneo", "pox", "uniforme", "intercambio", "aleatoria"),
    "B": Configuracion("B", "ruleta", "jbx", "dos_puntos", "insercion", "aleatoria"),
    "C": Configuracion("C", "ranking", "pox", "uniforme", "intercambio", "balance"),
    "D": Configuracion("D", "torneo", "pox", "dos_puntos", "insercion", "balance"),
}


@dataclass(frozen=True)
class Estadisticas:
    mejor: float
    peor: float
    promedio: float
    desviacion: float


@dataclass
class ResultadoConfiguracion:
    configuracion: Configuracion
    resultados: list[Resultado]

    @property
    def estadisticas(self) -> Estadisticas:
        valores = [r.makespan for r in self.resultados]
        return Estadisticas(
            min(valores),
            max(valores),
            fmean(valores),
            stdev(valores) if len(valores) > 1 else 0.0,
        )


def ejecutar_campana(
    escenario: Escenario,
    configuraciones: list[Configuracion],
    semillas: tuple[int, ...] = SEMILLAS,
    al_terminar: Callable[[ResultadoConfiguracion], None] | None = None,
) -> list[ResultadoConfiguracion]:
    """Ejecuta cada configuración una vez por semilla (las mismas para todas)."""
    if len(set(semillas)) != len(semillas):
        raise ValueError("las semillas de una campaña deben ser distintas")
    for cfg in configuraciones:
        cfg.validar()
    campana = []
    for cfg in configuraciones:
        resultado = ResultadoConfiguracion(cfg, [ejecutar(escenario, cfg, s) for s in semillas])
        campana.append(resultado)
        if al_terminar is not None:
            al_terminar(resultado)
    return campana


def seleccionar_configuracion(campana: list[ResultadoConfiguracion]) -> ResultadoConfiguracion:
    """La de menor makespan promedio; el empate se resuelve por mejor valor."""
    return min(campana, key=lambda rc: (rc.estadisticas.promedio, rc.estadisticas.mejor))


def tres_mejores(resultados: list[Resultado]) -> list[Resultado]:
    """Las tres corridas de menor makespan final; empate -> semilla menor."""
    return sorted(resultados, key=lambda r: (r.makespan, r.semilla))[:3]


def curvas_convergencia(
    resultados: list[Resultado],
) -> tuple[list[float], list[float], list[float]]:
    """Historial de la mejor corrida, de la peor, y promedio por generación.

    Empates: la mejor es la de semilla menor y la peor la de semilla mayor, para
    que no sean la misma corrida cuando todas terminan con el mismo makespan.
    """
    mejor = min(resultados, key=lambda r: (r.makespan, r.semilla))
    peor = max(resultados, key=lambda r: (r.makespan, r.semilla))
    promedio = [fmean(valores) for valores in zip(*(r.historial for r in resultados))]
    return mejor.historial, peor.historial, promedio


def _guardar_configuracion(escenario: Escenario, rc: ResultadoConfiguracion, carpeta: Path) -> None:
    carpeta.mkdir(parents=True, exist_ok=True)
    asignaciones, secuencias, total = tamano_espacio(escenario)
    parametros = {
        "escenario": escenario.nombre,
        "configuracion": rc.configuracion.como_dict(),
        "semillas": [r.semilla for r in rc.resultados],
        "espacio_de_busqueda": {
            "formula": "p^N * N! / prod(n_j!)",
            "asignaciones": str(asignaciones),
            "secuencias": str(secuencias),
            "total": str(total),
        },
    }
    (carpeta / "parametros.json").write_text(
        json.dumps(parametros, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    with open(carpeta / "resumen.csv", "w", newline="", encoding="utf-8") as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow(["semilla", "makespan", "carga_maxima", "energia"])
        for r in rc.resultados:
            plan = r.planificacion
            energia = "" if plan.energia is None else f"{plan.energia:.2f}"
            escritor.writerow(
                [r.semilla, f"{r.makespan:.4f}", f"{plan.carga_maxima:.4f}", energia]
            )

    est = rc.estadisticas
    (carpeta / "estadisticas.txt").write_text(
        f"Escenario: {escenario.nombre}\n"
        f"Configuración: {rc.configuracion.nombre}\n"
        f"Ejecuciones: {len(rc.resultados)}\n"
        f"Mejor makespan: {est.mejor:.4f}\n"
        f"Peor makespan: {est.peor:.4f}\n"
        f"Promedio: {est.promedio:.4f}\n"
        f"Desviación estándar: {est.desviacion:.4f}\n",
        encoding="utf-8",
    )

    mejor, peor, promedio = curvas_convergencia(rc.resultados)
    with open(carpeta / "convergencia.csv", "w", newline="", encoding="utf-8") as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow(
            ["generacion"]
            + [f"semilla_{r.semilla}" for r in rc.resultados]
            + ["mejor", "peor", "promedio"]
        )
        for g in range(len(promedio)):
            fila = [f"{r.historial[g]:.4f}" for r in rc.resultados]
            fila += [f"{mejor[g]:.4f}", f"{peor[g]:.4f}", f"{promedio[g]:.4f}"]
            escritor.writerow([g] + fila)

    for r in rc.resultados:
        encabezado = {"Configuración": rc.configuracion.nombre, "Semilla": r.semilla}
        (carpeta / f"corrida_{r.semilla:02d}.txt").write_text(
            reporte_maquinas(r.planificacion, encabezado), encoding="utf-8"
        )


def guardar_campana(
    escenario: Escenario, campana: list[ResultadoConfiguracion], carpeta: str | Path
) -> ResultadoConfiguracion:
    """Escribe todos los archivos de salida del escenario y devuelve la configuración seleccionada."""
    from .graficas import diagrama_gantt, grafica_convergencia

    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    for rc in campana:
        _guardar_configuracion(escenario, rc, carpeta / rc.configuracion.nombre)

    seleccionada = seleccionar_configuracion(campana)
    encabezados = [
        "configuracion", "seleccion", "cruza_os", "cruza_ma", "mutacion_os", "mutacion_ma",
        "mejor", "peor", "promedio", "desviacion", "seleccionada",
    ]  # fmt: skip
    filas = []
    for rc in campana:
        cfg, est = rc.configuracion, rc.estadisticas
        filas.append(
            [
                cfg.nombre, cfg.seleccion, cfg.cruza_os, cfg.cruza_ma, cfg.mutacion_os,
                cfg.mutacion_ma, f"{est.mejor:.2f}", f"{est.peor:.2f}", f"{est.promedio:.2f}",
                f"{est.desviacion:.2f}", "si" if rc is seleccionada else "no",
            ]  # fmt: skip
        )
    with open(carpeta / "comparacion.csv", "w", newline="", encoding="utf-8") as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow(encabezados)
        escritor.writerows(filas)

    asignaciones, secuencias, total = tamano_espacio(escenario)
    cfg = seleccionada.configuracion
    mejores = tres_mejores(seleccionada.resultados)
    texto = (
        f"# {escenario.nombre}\n\n"
        f"- Operaciones (tipos): {escenario.num_operaciones}\n"
        f"- Máquinas: {escenario.num_maquinas}\n"
        f"- Trabajos: {escenario.num_trabajos}\n"
        f"- Operaciones a planificar (N): {escenario.total_operaciones}\n"
        f"- Espacio de búsqueda p^N * N!/prod(n_j!): {notacion_cientifica(asignaciones)} * "
        f"{notacion_cientifica(secuencias)} = {notacion_cientifica(total)}\n"
        f"- Parámetros: población {cfg.poblacion}, generaciones {cfg.generaciones}, "
        f"pc {cfg.pc}, pm {cfg.pm}, élites {cfg.elites}, torneo k = {cfg.torneo_k}\n"
        f"- Ejecuciones por configuración: {len(seleccionada.resultados)} "
        f"(semillas {seleccionada.resultados[0].semilla} a {seleccionada.resultados[-1].semilla})\n\n"
        "## Comparación de configuraciones\n\n"
        + tabla_markdown(encabezados, filas)
        + f"\nConfiguración seleccionada (menor promedio): **{cfg.nombre}**\n\n"
        "## Tres mejores ejecuciones de la configuración seleccionada\n\n"
        + tabla_markdown(
            ["lugar", "semilla", "makespan", "carga_maxima", "energia", "gantt"],
            [
                [
                    i,
                    r.semilla,
                    f"{r.makespan:.2f}",
                    f"{r.planificacion.carga_maxima:.2f}",
                    "n/d" if r.planificacion.energia is None else f"{r.planificacion.energia:.2f}",
                    f"gantt_top{i}.png",
                ]
                for i, r in enumerate(mejores, start=1)
            ],
        )
    )
    (carpeta / "comparacion.md").write_text(texto, encoding="utf-8")

    for i, r in enumerate(mejores, start=1):
        diagrama_gantt(
            r.planificacion,
            carpeta / f"gantt_top{i}.png",
            f"{escenario.nombre} · configuración {cfg.nombre} · lugar {i} · "
            f"semilla {r.semilla} · makespan {r.makespan:.2f} s",
        )
    mejor, peor, promedio = curvas_convergencia(seleccionada.resultados)
    grafica_convergencia(
        mejor,
        peor,
        promedio,
        carpeta / "convergencia.png",
        f"{escenario.nombre} · convergencia de la configuración {cfg.nombre} "
        f"({len(seleccionada.resultados)} ejecuciones)",
    )
    return seleccionada


def con_parametros(configuracion: Configuracion, **cambios) -> Configuracion:
    """Copia de la configuración con los parámetros no nulos sustituidos."""
    return replace(configuracion, **{k: v for k, v in cambios.items() if v is not None})
