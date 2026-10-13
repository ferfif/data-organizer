"""Diagrama de Gantt y gráfica de convergencia (PNG, sin ventana)."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

from .planificacion import Planificacion  # noqa: E402

# Paleta categórica de orden fijo (el color sigue al trabajo, no a su posición).
COLORES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
SUPERFICIE = "#fcfcfb"
TINTA = "#0b0b0b"
TINTA_SECUNDARIA = "#52514e"
TINTA_TENUE = "#898781"
REJILLA = "#e1e0d9"
EJE = "#c3c2b7"

plt.rcParams.update(
    {
        "font.family": ["Segoe UI", "DejaVu Sans"],
        "figure.facecolor": SUPERFICIE,
        "axes.facecolor": SUPERFICIE,
        "savefig.facecolor": SUPERFICIE,
        "text.color": TINTA,
        "axes.labelcolor": TINTA_SECUNDARIA,
        "axes.edgecolor": EJE,
        "xtick.color": TINTA_TENUE,
        "ytick.color": TINTA_TENUE,
        "xtick.labelcolor": TINTA_SECUNDARIA,
        "ytick.labelcolor": TINTA_SECUNDARIA,
        "hatch.linewidth": 0.8,
    }
)


def _estilo_trabajo(indice: int) -> tuple[str, str | None]:
    """Color y trama del trabajo. A partir del noveno se repite el color con trama."""
    return COLORES[indice % len(COLORES)], ("////" if indice >= len(COLORES) else None)


def _tinta_sobre(color: str) -> str:
    r, g, b = (int(color[i : i + 2], 16) / 255 for i in (1, 3, 5))
    luminancia = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return TINTA if luminancia > 0.38 else "#ffffff"


def _limpiar_ejes(ax) -> None:
    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.tick_params(length=0)


def diagrama_gantt(plan: Planificacion, ruta: str | Path, titulo: str) -> None:
    esc = plan.escenario
    p = esc.num_maquinas
    ancho = min(22.0, max(11.0, plan.makespan * 0.42))
    fig, ax = plt.subplots(figsize=(ancho, 1.6 + 0.62 * p))

    for op in plan.operaciones:
        color, trama = _estilo_trabajo(op.trabajo)
        ax.barh(
            op.maquina,
            op.fin - op.inicio,
            left=op.inicio,
            height=0.68,
            color=color,
            edgecolor=SUPERFICIE,
            linewidth=1.5,
            hatch=trama,
        )
        trabajo, operacion = esc.etiqueta(op.gen).split("-")
        ax.text(
            (op.inicio + op.fin) / 2,
            op.maquina,
            f"{trabajo}\n{operacion}",
            ha="center",
            va="center",
            fontsize=7,
            linespacing=0.95,
            color=_tinta_sobre(color),
            bbox={"facecolor": color, "edgecolor": "none", "pad": 0.6} if trama else None,
        )

    ax.axvline(plan.makespan, color=TINTA_SECUNDARIA, linewidth=1, linestyle=(0, (4, 3)))
    ax.text(
        plan.makespan,
        -0.62,
        f"makespan {plan.makespan:.2f}",
        ha="right",
        va="bottom",
        fontsize=8,
        color=TINTA_SECUNDARIA,
    )

    ax.set_yticks(range(p), [f"M{m + 1}" for m in range(p)])
    ax.set_ylim(p - 0.4, -0.75)
    ax.set_xlim(0, plan.makespan * 1.01)
    ax.set_xlabel("Tiempo (s)")
    ax.xaxis.grid(True, color=REJILLA, linewidth=0.8)
    ax.set_axisbelow(True)
    _limpiar_ejes(ax)
    ax.set_title(titulo, loc="left", fontsize=11, fontweight="bold", pad=10)

    leyenda = []
    for j, trabajo in enumerate(esc.trabajos):
        color, trama = _estilo_trabajo(j)
        leyenda.append(
            Patch(facecolor=color, edgecolor=SUPERFICIE, hatch=trama, label=trabajo.nombre)
        )
    ax.legend(
        handles=leyenda,
        title="Trabajo",
        loc="upper left",
        bbox_to_anchor=(1.005, 1.0),
        frameon=False,
        fontsize=8,
        title_fontsize=8,
    )
    fig.savefig(ruta, dpi=150, bbox_inches="tight")
    plt.close(fig)


def grafica_convergencia(
    mejor: list[float],
    peor: list[float],
    promedio: list[float],
    ruta: str | Path,
    titulo: str,
) -> None:
    fig, ax = plt.subplots(figsize=(9.5, 5.2))
    generaciones = range(len(promedio))
    series = (
        ("Peor ejecución", peor, COLORES[1]),
        ("Promedio de las ejecuciones", promedio, COLORES[2]),
        ("Mejor ejecución", mejor, COLORES[0]),
    )
    for nombre, valores, color in series:
        ax.plot(generaciones, valores, color=color, linewidth=2, label=nombre)

    # Etiquetas directas con el valor final, separadas si quedan encimadas.
    finales = sorted(((valores[-1], color) for _, valores, color in series), reverse=True)
    alto = ax.get_ylim()[1] - ax.get_ylim()[0]
    separacion = alto * 0.045
    posiciones = []
    for valor, _ in finales:
        if posiciones and f"{valor:.2f}" == f"{finales[len(posiciones) - 1][0]:.2f}":
            y = posiciones[-1]
        else:
            y = valor if not posiciones else min(valor, posiciones[-1] - separacion)
        posiciones.append(y)
    rotulados = set()
    for (valor, color), y in zip(finales, posiciones):
        ax.plot([len(promedio) - 1], [valor], marker="o", markersize=5, color=color)
        if f"{valor:.2f}" in rotulados:  # curvas que terminan en el mismo valor
            continue
        rotulados.add(f"{valor:.2f}")
        ax.annotate(
            f"{valor:.2f}",
            xy=(len(promedio) - 1, y),
            xytext=(8, 0),
            textcoords="offset points",
            va="center",
            fontsize=9,
            color=TINTA,
            annotation_clip=False,
        )

    ax.set_xlabel("Generación")
    ax.set_ylabel("Mejor makespan encontrado (s)")
    ax.set_xlim(0, len(promedio) - 1)
    ax.yaxis.grid(True, color=REJILLA, linewidth=0.8)
    ax.set_axisbelow(True)
    _limpiar_ejes(ax)
    ax.set_title(titulo, loc="left", fontsize=11, fontweight="bold", pad=10)
    ax.legend(loc="upper right", frameon=False, fontsize=9)
    fig.savefig(ruta, dpi=150, bbox_inches="tight")
    plt.close(fig)
