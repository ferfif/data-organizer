# data-organizer

Algoritmo genético para el problema de planificación de tareas (*job shop* flexible): asigna las operaciones de cada trabajo a las máquinas y decide su orden para minimizar el **makespan**.

El diseño, la codificación y la justificación de operadores y parámetros están en [`docs/diseno.md`](docs/diseno.md).

## Instalación

Requiere Python 3.10 o superior.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

`pip install -e .` instala el paquete `planificador` y su única dependencia, `matplotlib` (también listada en `requirements.txt`).

## Uso

Campaña completa sobre los tres escenarios (4 configuraciones × 20 semillas cada uno; tarda unos minutos):

```powershell
python -m planificador scenes
```

Si `outputs/` ya tiene resultados de un escenario, el programa se detiene. Use `--sobrescribir` para reemplazarlos o `--salida otra_carpeta` para conservarlos.

Una sola corrida, con el reporte por máquina en consola:

```powershell
python -m planificador scenes/Escenario1.txt --unica --semilla 7
```

Opciones principales (`python -m planificador --help` las lista todas):

| Opción | Efecto |
|---|---|
| `--config A C` | Ejecuta solo esas configuraciones (por defecto A, B, C y D) |
| `--corridas N` | Ejecuciones por configuración, con semillas 1 a N (por defecto 20) |
| `--poblacion`, `--generaciones`, `--pc`, `--pm`, `--elites`, `--torneo-k` | Parámetros del algoritmo |
| `--seleccion`, `--cruza-os`, `--cruza-ma`, `--mutacion-os`, `--mutacion-ma` | Define una configuración `personalizada` |
| `--salida DIR` | Directorio de salida (por defecto `outputs`) |

Técnicas disponibles:

- Selección: `torneo`, `ruleta`, `ranking`
- Cruza de la secuencia: `pox`, `jbx`; de la asignación: `uniforme`, `dos_puntos`
- Mutación de la secuencia: `intercambio`, `insercion`; de la asignación: `aleatoria`, `balance`

## Formato de los escenarios

Archivo de texto con secciones encabezadas por `#`. Cada fila de una matriz es una operación y cada columna una máquina.

```text
#tiempos por máquina
3.5	6.7	2.5	8.2
5.5	4.2	7.6	9
#consumo energético por máquina
1.2	4.7	3.5	4.2
7.5	1.5	6.6	3.5
#Trabajos
J1={O2,O1}
J2={O1}
#Llegadas
J2=6.5
```

Las secciones de consumo y de llegadas son opcionales; sin llegadas, todos los trabajos llegan en t = 0.

## Salidas

```text
outputs/<Escenario>/
  comparacion.md / comparacion.csv   tabla comparativa de configuraciones y la seleccionada
  convergencia.png                   curvas mejor, peor y promedio de la configuración seleccionada
  gantt_top1.png .. gantt_top3.png   Gantt de las tres mejores ejecuciones
  <configuración>/
    parametros.json                  parámetros, semillas y tamaño del espacio de búsqueda
    resumen.csv                      semilla, makespan, carga máxima y energía de cada ejecución
    estadisticas.txt                 mejor, peor, promedio y desviación estándar
    convergencia.csv                 mejor makespan por generación de cada ejecución
    corrida_<semilla>.txt            reporte de tiempos por máquina
```

En los reportes, `J3-O2` es la operación O2 del trabajo J3.

## Pruebas

```powershell
python -m unittest discover -s tests
```
