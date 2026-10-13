"""Reportes de texto: tiempos por máquina y tablas de resultados."""

from __future__ import annotations

from decimal import Decimal

from .planificacion import Planificacion


def reporte_maquinas(plan: Planificacion, encabezado: dict[str, object] | None = None) -> str:
    """Reporte por máquina de una planificación.

    Cada operación se identifica como ``J<trabajo>-O<operación>``.
    """
    esc = plan.escenario
    lineas = [f"Escenario: {esc.nombre}"]
    for clave, valor in (encabezado or {}).items():
        lineas.append(f"{clave}: {valor}")
    lineas.append(f"Makespan (C_max): {plan.makespan:.2f}")
    lineas.append(f"Carga máxima por máquina (f1): {plan.carga_maxima:.2f}")
    if plan.energia is None:
        lineas.append("Consumo energético total: no disponible")
    else:
        lineas.append(f"Consumo energético total: {plan.energia:.2f}")

    for m, cola in enumerate(plan.por_maquina()):
        lineas.append("")
        lineas.append(f"Máquina M{m + 1}")
        if not cola:
            lineas.append("  (sin operaciones)")
            lineas.append("  Tiempo total de proceso: 0.00 | Fin de la última operación: 0.00")
            continue
        lineas.append(f"  {'Operación':<12}{'T. inicial':>12}{'T. final':>12}{'Duración':>12}")
        for op in sorted(cola, key=lambda o: o.inicio):
            lineas.append(
                f"  {esc.etiqueta(op.gen):<12}{op.inicio:>12.2f}{op.fin:>12.2f}"
                f"{op.fin - op.inicio:>12.2f}"
            )
        lineas.append(
            f"  Tiempo total de proceso: {plan.cargas[m]:.2f} | "
            f"Fin de la última operación: {max(op.fin for op in cola):.2f}"
        )

    lineas.append("")
    lineas.append("Tiempo de finalización por trabajo")
    for trabajo, fin in zip(esc.trabajos, plan.fin_trabajos):
        lineas.append(f"  {trabajo.nombre}: {fin:.2f}")
    return "\n".join(lineas) + "\n"


def tabla_markdown(encabezados: list[str], filas: list[list[object]]) -> str:
    lineas = [
        "| " + " | ".join(encabezados) + " |",
        "|" + "|".join("---" for _ in encabezados) + "|",
    ]
    lineas += ["| " + " | ".join(str(c) for c in fila) + " |" for fila in filas]
    return "\n".join(lineas) + "\n"


def notacion_cientifica(valor: int) -> str:
    """Entero grande como ``a.bc x 10^n`` (Decimal evita el desbordamiento de float)."""
    if valor < 10**6:
        return str(valor)
    mantisa, exponente = f"{Decimal(valor):.2e}".lower().split("e")
    return f"{mantisa} x 10^{int(exponente)}"
