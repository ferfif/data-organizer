"""Lectura y validación de escenarios desde archivos de texto.

Formato (secciones encabezadas por una línea que empieza con ``#``):

    #tiempos ...      matriz operación x máquina
    #consumo ...      matriz operación x máquina (opcional)
    #trabajos         líneas  J1={O2,O4,O5}
    #llegadas         líneas  J4=6.5 (opcional)
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

# El orden importa: se revisa cada palabra clave contra el encabezado normalizado.
_SECCIONES = ("llegada", "trabajo", "consumo", "tiempo")
_RE_TRABAJO = re.compile(r"^J(\d+)\s*=\s*\{(.*)\}$", re.IGNORECASE)
_RE_OPERACION = re.compile(r"^O(\d+)$", re.IGNORECASE)
_RE_LLEGADA = re.compile(r"^J(\d+)\s*=\s*(\S+)$", re.IGNORECASE)


class ErrorEscenario(ValueError):
    """El archivo de escenario no existe o está mal formado."""


@dataclass(frozen=True)
class Trabajo:
    numero: int  # el número que aparece en el archivo (J3 -> 3)
    operaciones: tuple[int, ...]  # tipos de operación, base 0, en orden de ejecución
    llegada: float = 0.0

    @property
    def nombre(self) -> str:
        return f"J{self.numero}"


@dataclass
class Escenario:
    nombre: str
    tiempos: list[list[float]]  # tiempos[operación][máquina]
    consumo: list[list[float]] | None
    trabajos: list[Trabajo]

    # Derivados: un "gen" es una operación a planificar (trabajo, posición),
    # numerada en orden fijo: todas las de J1, luego las de J2, ...
    inicio_trabajo: list[int] = field(init=False)
    tipo_gen: list[int] = field(init=False)
    trabajo_gen: list[int] = field(init=False)
    tiempos_gen: list[list[float]] = field(init=False)
    llegadas: list[float] = field(init=False)

    def __post_init__(self) -> None:
        self.inicio_trabajo = []
        self.tipo_gen = []
        self.trabajo_gen = []
        for j, trabajo in enumerate(self.trabajos):
            self.inicio_trabajo.append(len(self.tipo_gen))
            self.tipo_gen.extend(trabajo.operaciones)
            self.trabajo_gen.extend([j] * len(trabajo.operaciones))
        self.tiempos_gen = [self.tiempos[tipo] for tipo in self.tipo_gen]
        self.llegadas = [t.llegada for t in self.trabajos]

    @property
    def num_operaciones(self) -> int:
        return len(self.tiempos)

    @property
    def num_maquinas(self) -> int:
        return len(self.tiempos[0])

    @property
    def num_trabajos(self) -> int:
        return len(self.trabajos)

    @property
    def total_operaciones(self) -> int:
        return len(self.tipo_gen)

    def etiqueta(self, gen: int) -> str:
        """Identificador ``J<trabajo>-O<operación>`` de una operación a planificar."""
        trabajo = self.trabajos[self.trabajo_gen[gen]]
        tipo = self.tipo_gen[gen]
        texto = f"{trabajo.nombre}-O{tipo + 1}"
        if trabajo.operaciones.count(tipo) > 1:
            posicion = gen - self.inicio_trabajo[self.trabajo_gen[gen]]
            repeticion = trabajo.operaciones[: posicion + 1].count(tipo)
            texto += f"#{repeticion}"
        return texto


def _normalizar(texto: str) -> str:
    sin_acentos = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in sin_acentos if not unicodedata.combining(c)).lower()


def _leer_texto(ruta: Path) -> str:
    datos = ruta.read_bytes()
    try:
        return datos.decode("utf-8-sig")
    except UnicodeDecodeError:
        return datos.decode("latin-1")


def _fila_numerica(linea: str, seccion: str, num_fila: int, error) -> list[float]:
    valores = []
    for texto in linea.split():
        try:
            valores.append(float(texto))
        except ValueError:
            raise error(
                f"valor no numérico '{texto}' en la sección de {seccion}, fila {num_fila}"
            ) from None
    return valores


def _validar_matriz(matriz: list[list[float]], seccion: str, error) -> None:
    columnas = len(matriz[0])
    for i, fila in enumerate(matriz, start=1):
        if len(fila) != columnas:
            raise error(
                f"la fila {i} de la sección de {seccion} tiene {len(fila)} columnas "
                f"y se esperaban {columnas}"
            )


def cargar_escenario(ruta: str | Path) -> Escenario:
    ruta = Path(ruta)
    if not ruta.is_file():
        raise ErrorEscenario(f"no se encontró el archivo de escenario: {ruta}")

    def error(causa: str) -> ErrorEscenario:
        return ErrorEscenario(f"{ruta}: {causa}")

    lineas: dict[str, list[str]] = {}
    actual: str | None = None
    for cruda in _leer_texto(ruta).splitlines():
        linea = cruda.strip()
        if not linea:
            continue
        if linea.startswith("#"):
            encabezado = _normalizar(linea)
            actual = next((s for s in _SECCIONES if s in encabezado), None)
            if actual is None:
                raise error(f"encabezado de sección no reconocido: '{linea}'")
            if actual in lineas:
                raise error(f"la sección '{linea}' está repetida")
            lineas[actual] = []
        elif actual is None:
            raise error(f"hay datos antes del primer encabezado de sección: '{linea}'")
        else:
            lineas[actual].append(linea)

    if not lineas.get("tiempo"):
        raise error("falta la sección de tiempos o está vacía")
    if not lineas.get("trabajo"):
        raise error("falta la sección de trabajos o está vacía")

    tiempos = [
        _fila_numerica(l, "tiempos", i, error) for i, l in enumerate(lineas["tiempo"], 1)
    ]
    _validar_matriz(tiempos, "tiempos", error)
    for i, fila in enumerate(tiempos, start=1):
        for m, valor in enumerate(fila, start=1):
            if not valor > 0:
                raise error(f"tiempo no positivo ({valor}) para O{i} en M{m}")

    consumo = None
    if lineas.get("consumo"):
        consumo = [
            _fila_numerica(l, "consumo", i, error)
            for i, l in enumerate(lineas["consumo"], 1)
        ]
        _validar_matriz(consumo, "consumo", error)
        if len(consumo) != len(tiempos) or len(consumo[0]) != len(tiempos[0]):
            raise error(
                f"la matriz de consumo es de {len(consumo)}x{len(consumo[0])} y la de "
                f"tiempos de {len(tiempos)}x{len(tiempos[0])}"
            )
        for i, fila in enumerate(consumo, start=1):
            for m, valor in enumerate(fila, start=1):
                if valor < 0:
                    raise error(f"consumo negativo ({valor}) para O{i} en M{m}")

    secuencias: dict[int, tuple[int, ...]] = {}
    for linea in lineas["trabajo"]:
        coincidencia = _RE_TRABAJO.match(linea)
        if coincidencia is None:
            raise error(f"línea de trabajo mal formada: '{linea}'")
        numero = int(coincidencia.group(1))
        if numero in secuencias:
            raise error(f"el trabajo J{numero} está repetido")
        operaciones = []
        for texto in (t.strip() for t in coincidencia.group(2).split(",")):
            if not texto:
                continue
            op = _RE_OPERACION.match(texto)
            if op is None:
                raise error(f"operación mal formada '{texto}' en el trabajo J{numero}")
            indice = int(op.group(1))
            if not 1 <= indice <= len(tiempos):
                raise error(
                    f"el trabajo J{numero} referencia la operación desconocida O{indice} "
                    f"(el escenario tiene {len(tiempos)} operaciones)"
                )
            operaciones.append(indice - 1)
        if not operaciones:
            raise error(f"el trabajo J{numero} no tiene operaciones")
        secuencias[numero] = tuple(operaciones)

    llegadas: dict[int, float] = {}
    for linea in lineas.get("llegada", []):
        coincidencia = _RE_LLEGADA.match(linea)
        if coincidencia is None:
            raise error(f"línea de llegada mal formada: '{linea}'")
        numero = int(coincidencia.group(1))
        if numero not in secuencias:
            raise error(f"la llegada referencia el trabajo desconocido J{numero}")
        try:
            valor = float(coincidencia.group(2))
        except ValueError:
            raise error(f"tiempo de llegada no numérico para J{numero}") from None
        if valor < 0:
            raise error(f"tiempo de llegada negativo ({valor}) para J{numero}")
        llegadas[numero] = valor

    trabajos = [
        Trabajo(numero, operaciones, llegadas.get(numero, 0.0))
        for numero, operaciones in secuencias.items()
    ]
    return Escenario(ruta.stem, tiempos, consumo, trabajos)
