"""Línea de comandos: ``python -m planificador RUTA [opciones]``."""

from __future__ import annotations

import argparse
import shutil
import sys
import time
from pathlib import Path

from . import operadores as ops
from .escenario import ErrorEscenario, cargar_escenario
from .experimento import CONFIGURACIONES, con_parametros, ejecutar_campana, guardar_campana
from .genetico import ErrorConfiguracion, ejecutar, tamano_espacio
from .reportes import notacion_cientifica, reporte_maquinas

ERROR_ESCENARIO = 1
ERROR_CONFIGURACION = 2


def _analizador() -> argparse.ArgumentParser:
    analizador = argparse.ArgumentParser(
        prog="planificador",
        description="Algoritmo genético para planificación de tareas (minimiza el makespan).",
    )
    analizador.add_argument("ruta", help="archivo de escenario o carpeta con escenarios .txt")
    analizador.add_argument(
        "--unica", action="store_true", help="hace una sola corrida y muestra su reporte"
    )
    analizador.add_argument("--semilla", type=int, default=1, help="semilla de la corrida única")
    analizador.add_argument(
        "--config",
        nargs="+",
        metavar="NOMBRE",
        help=f"configuraciones a ejecutar (por defecto todas: {' '.join(CONFIGURACIONES)})",
    )
    analizador.add_argument(
        "--corridas", type=int, default=20, help="ejecuciones por configuración (semillas 1..n)"
    )
    analizador.add_argument("--salida", default="outputs", help="directorio de salida")
    analizador.add_argument(
        "--sobrescribir",
        action="store_true",
        help="reemplaza los resultados previos del escenario en el directorio de salida",
    )

    parametros = analizador.add_argument_group("parámetros del algoritmo")
    parametros.add_argument("--poblacion", type=int)
    parametros.add_argument("--generaciones", type=int)
    parametros.add_argument("--pc", type=float, help="probabilidad de cruza")
    parametros.add_argument("--pm", type=float, help="probabilidad de mutación")
    parametros.add_argument("--elites", type=int)
    parametros.add_argument("--torneo-k", type=int, dest="torneo_k")

    tecnicas = analizador.add_argument_group(
        "técnicas (al indicar alguna se ejecuta una sola configuración 'personalizada')"
    )
    tecnicas.add_argument("--seleccion", help=", ".join(ops.SELECCIONES))
    tecnicas.add_argument("--cruza-os", dest="cruza_os", help=", ".join(ops.CRUZAS_OS))
    tecnicas.add_argument("--cruza-ma", dest="cruza_ma", help=", ".join(ops.CRUZAS_MA))
    tecnicas.add_argument("--mutacion-os", dest="mutacion_os", help=", ".join(ops.MUTACIONES_OS))
    tecnicas.add_argument("--mutacion-ma", dest="mutacion_ma", help=", ".join(ops.MUTACIONES_MA))
    return analizador


def _configuraciones(args: argparse.Namespace) -> list:
    parametros = {
        k: getattr(args, k)
        for k in ("poblacion", "generaciones", "pc", "pm", "elites", "torneo_k")
    }
    tecnicas = {
        k: getattr(args, k)
        for k in ("seleccion", "cruza_os", "cruza_ma", "mutacion_os", "mutacion_ma")
    }
    if any(v is not None for v in tecnicas.values()):
        if args.config and len(args.config) > 1:
            raise ErrorConfiguracion(
                "al indicar técnicas solo se admite una configuración base en --config"
            )
        base = _buscar_configuracion(args.config[0] if args.config else "A")
        elegidas = [con_parametros(base, nombre="personalizada", **tecnicas)]
    else:
        elegidas = [_buscar_configuracion(n) for n in (args.config or CONFIGURACIONES)]
    elegidas = [con_parametros(cfg, **parametros) for cfg in elegidas]
    for cfg in elegidas:
        cfg.validar()
    return elegidas


def _buscar_configuracion(nombre: str):
    if nombre not in CONFIGURACIONES:
        raise ErrorConfiguracion(
            f"configuración desconocida: '{nombre}'. Disponibles: {', '.join(CONFIGURACIONES)}"
        )
    return CONFIGURACIONES[nombre]


def _rutas_escenarios(ruta: Path) -> list[Path]:
    if ruta.is_dir():
        archivos = sorted(ruta.glob("*.txt"))
        if not archivos:
            raise ErrorEscenario(f"la carpeta {ruta} no contiene escenarios .txt")
        return archivos
    return [ruta]


def _describir(escenario) -> str:
    asignaciones, secuencias, total = tamano_espacio(escenario)
    return (
        f"{escenario.nombre}: {escenario.num_operaciones} operaciones, "
        f"{escenario.num_maquinas} máquinas, {escenario.num_trabajos} trabajos, "
        f"N = {escenario.total_operaciones} operaciones a planificar\n"
        f"  Espacio de búsqueda p^N * N!/prod(n_j!) = {notacion_cientifica(asignaciones)} * "
        f"{notacion_cientifica(secuencias)} = {notacion_cientifica(total)}"
    )


def main(argumentos: list[str] | None = None) -> int:
    args = _analizador().parse_args(argumentos)
    try:
        configuraciones = _configuraciones(args)
        if args.corridas < 1:
            raise ErrorConfiguracion(f"corridas debe ser al menos 1 (se indicó {args.corridas})")
        escenarios = [cargar_escenario(r) for r in _rutas_escenarios(Path(args.ruta))]
    except ErrorEscenario as error:
        print(f"Error en el escenario: {error}", file=sys.stderr)
        return ERROR_ESCENARIO
    except ErrorConfiguracion as error:
        print(f"Error de configuración: {error}", file=sys.stderr)
        return ERROR_CONFIGURACION

    if args.unica:
        cfg = configuraciones[0]
        for escenario in escenarios:
            print(_describir(escenario))
            resultado = ejecutar(escenario, cfg, args.semilla)
            encabezado = {"Configuración": cfg.nombre, "Semilla": args.semilla}
            print()
            print(reporte_maquinas(resultado.planificacion, encabezado))
        return 0

    salida = Path(args.salida)
    ocupadas = [
        salida / e.nombre
        for e in escenarios
        if (salida / e.nombre).is_dir() and any((salida / e.nombre).iterdir())
    ]
    if ocupadas and not args.sobrescribir:
        print(
            "Error de configuración: ya existen resultados en "
            + ", ".join(str(c) for c in ocupadas)
            + ". Use --sobrescribir para reemplazarlos o --salida para otro directorio.",
            file=sys.stderr,
        )
        return ERROR_CONFIGURACION
    for carpeta in ocupadas:
        print(f"Aviso: se reemplazan los resultados previos de {carpeta}")
        shutil.rmtree(carpeta)

    semillas = tuple(range(1, args.corridas + 1))
    for escenario in escenarios:
        print(_describir(escenario))
        inicio = time.perf_counter()

        def informar(rc) -> None:
            est = rc.estadisticas
            print(
                f"  Configuración {rc.configuracion.nombre:<14} mejor {est.mejor:7.2f}   "
                f"peor {est.peor:7.2f}   promedio {est.promedio:7.2f}   "
                f"desv. {est.desviacion:5.2f}   ({time.perf_counter() - inicio:.0f} s)"
            )

        campana = ejecutar_campana(escenario, configuraciones, semillas, informar)
        seleccionada = guardar_campana(escenario, campana, salida / escenario.nombre)
        print(
            f"  Seleccionada: {seleccionada.configuracion.nombre}. "
            f"Resultados en {salida / escenario.nombre}\n"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
