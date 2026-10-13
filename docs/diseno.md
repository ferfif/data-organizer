# Diseño del algoritmo genético

Este documento reúne las decisiones de diseño y su justificación. Sirve como insumo para la sección "Diseño del algoritmo" del reporte.

## 1. Modelo del problema

Cada escenario define una tabla de tiempos operación × máquina y una lista de trabajos. Un trabajo es una secuencia ordenada de operaciones (`J1={O2,O4,O5}`). Las operaciones O1…Ok son **tipos**: lo que se planifica es cada aparición de un tipo dentro de un trabajo. Cualquier operación puede ejecutarse en cualquier máquina, con un tiempo distinto en cada una (job shop flexible).

| Escenario | Tipos de operación | Máquinas (p) | Trabajos | Operaciones a planificar (N) |
|---|---:|---:|---:|---:|
| 1 | 5 | 4 | 6 | 19 |
| 2 | 8 | 10 | 10 | 40 |
| 3 | 15 | 5 | 12 | 59 |

Una operación se identifica como `J<trabajo>-O<operación>`; por ejemplo, `J3-O2` es la operación O2 del trabajo J3. En los tres escenarios ningún trabajo repite un tipo de operación, así que la etiqueta es inequívoca. Si un escenario lo repitiera, el programa añade la repetición (`J3-O2#2`).

## 2. Codificación del individuo

El cromosoma tiene dos partes de longitud N:

- **MA (asignación de máquina).** La posición i corresponde a una operación fija (todas las de J1 en su orden, luego las de J2, …) y el valor es la máquina que la atiende. Es la codificación entera del enunciado.
- **OS (secuencia de operaciones).** Lista de identificadores de trabajo en la que el trabajo j aparece tantas veces como operaciones tiene. La k-ésima aparición de j representa la k-ésima operación de j. El orden de la lista es el orden en que las operaciones se encolan en sus máquinas.

Ejemplo con J1={O2,O4} y J2={O1}:

```text
MA = [2, 1, 3]     J1-O2 en M2, J1-O4 en M1, J2-O1 en M3
OS = [1, 2, 1]     se encola J1-O2, luego J2-O1, luego J1-O4
```

### Por qué esta codificación

- **Asignar máquinas no basta.** Dos planificaciones con la misma asignación pueden tener makespan distinto según el orden en que las operaciones entran a cada cola. OS es la parte que decide ese orden.
- **La precedencia se cumple por construcción.** Como la k-ésima aparición de un trabajo siempre es su k-ésima operación, ningún cromosoma puede ejecutar O(i+1) antes que O(i). No hace falta reparar ni penalizar.
- **Todo cromosoma es válido.** Cualquier valor de 1 a p en MA es una asignación legal, y cualquier reordenamiento de OS es una secuencia legal. Los operadores solo tienen que conservar cuántas veces aparece cada trabajo.
- **Frente a la codificación binaria** (matriz máquina × operación): ocupa p·N bits, exige exactamente un 1 por columna y casi cualquier cruza o mutación rompe esa condición. La entera es más compacta y no genera inválidos.

### Tamaño del espacio de búsqueda

MA admite p^N combinaciones. OS es una permutación con repetición: N! / ∏ n_j!, donde n_j es el número de operaciones del trabajo j.

|S| = p^N × N! / ∏_j (n_j!)

| Escenario | p^N | N! / ∏ n_j! | Total |
|---|---:|---:|---:|
| 1 | 4^19 = 2.75 × 10^11 | 2.93 × 10^11 | 8.06 × 10^22 |
| 2 | 10^40 | 1.96 × 10^33 | 1.96 × 10^73 |
| 3 | 5^59 = 1.73 × 10^41 | 4.08 × 10^54 | 7.08 × 10^95 |

El programa calcula el valor exacto con enteros y lo guarda en `parametros.json`. Es el tamaño del espacio de **genotipos**: varias secuencias OS producen la misma planificación (por ejemplo, al intercambiar dos operaciones vecinas de trabajos y máquinas distintas), de modo que el número de planificaciones diferentes es menor.

## 3. De cromosoma a planificación

El decodificador recorre OS de izquierda a derecha. Para cada operación:

```text
inicio = max( fin de la operación previa del mismo trabajo,
              instante en que su máquina queda libre,
              tiempo de llegada del trabajo )
fin    = inicio + tiempo de la tabla para esa operación en su máquina
```

La operación se coloca al final de la cola de su máquina. Una vez encolada no se mueve, no se interrumpe y no cambia de máquina (asignación fija). El decodificador no inserta operaciones en huecos que hayan quedado antes en la cola: respeta la disciplina de cola del enunciado, a cambio de dejar algunos tiempos muertos que un decodificador con inserción aprovecharía.

Cada operación espera por lo que termine más tarde: su operación previa o la máquina. Por eso en los diagramas de Gantt aparecen huecos.

## 4. Función objetivo

Se minimiza el **makespan como C_max**: el mayor tiempo de finalización entre todas las operaciones.

El enunciado escribe f₁ = min max_j Σ_i t_ij · x_ij, que es la **carga máxima por máquina** (suma de los tiempos asignados a la máquina más ocupada). Esa suma ignora las esperas por precedencia, así que siempre se cumple C_max ≥ carga máxima, y solo coinciden si la máquina más cargada nunca queda ociosa. Como el enunciado llama makespan a f₁ y además pide registrar el inicio y el fin de cada operación, se optimiza C_max, que es el tiempo real en que termina todo, y la carga máxima se **reporta junto a él** en cada corrida (`Carga máxima por máquina (f1)` en los reportes y `carga_maxima` en `resumen.csv`).

## 5. Supuestos sobre los datos

- **Consumo energético.** Los tres archivos incluyen una matriz de consumo que el enunciado no menciona. Se lee, se valida y se reporta el consumo total de cada planificación, pero no interviene en la aptitud: el enunciado define un solo objetivo.
- **Tiempos de llegada.** Los archivos no los traen, así que todos los trabajos llegan en t = 0 y el orden del archivo define la prioridad de llegada. Para cubrir la restricción de llegadas dinámicas, el lector acepta una sección opcional `#Llegadas` (`J4=6.5`) y el decodificador no inicia ninguna operación antes de la llegada de su trabajo.

## 6. Operadores

Cada operador actúa sobre una de las dos partes del cromosoma y conserva su validez.

### Selección

| Técnica | Funcionamiento | Motivo |
|---|---|---|
| Torneo (k = 3) | Se toman 3 individuos al azar y gana el de menor makespan | Presión de selección moderada y no depende de la escala de la aptitud |
| Ruleta | Probabilidad proporcional a (peor − makespan + ε) | Referencia clásica; la transformación es necesaria porque se minimiza |
| Ranking lineal | Probabilidad proporcional a la posición: el mejor pesa n y el peor 1 | Evita que un individuo muy superior domine la ruleta |

### Cruza

| Técnica | Parte | Funcionamiento |
|---|---|---|
| POX | OS | Se elige un subconjunto de trabajos. El hijo conserva en su lugar los genes de esos trabajos de un padre y rellena los espacios con los genes restantes del otro padre, en su orden |
| JBX | OS | Igual que POX, pero el segundo hijo conserva el subconjunto complementario |
| Uniforme | MA | Cada gen se toma de uno u otro padre con probabilidad 0.5 |
| Dos puntos | MA | Se intercambia el segmento entre dos puntos de corte |

POX y JBX heredan el orden relativo de las operaciones de cada trabajo y mantienen el número de apariciones de cada uno. Los cruces clásicos de permutaciones (PMX, OX) no sirven aquí porque OS tiene elementos repetidos. En MA cualquier mezcla es válida; la de dos puntos conserva juntas las asignaciones de un mismo trabajo, que son genes contiguos.

### Mutación

| Técnica | Parte | Funcionamiento |
|---|---|---|
| Intercambio | OS | Intercambia dos genes de trabajos distintos |
| Inserción | OS | Saca un gen y lo inserta en otra posición |
| Reasignación aleatoria | MA | Cambia una operación a otra máquina al azar |
| Balance de carga | MA | Toma una operación de la máquina más cargada y la pasa a la máquina donde (carga actual + tiempo de esa operación) es menor |

La mutación de balance de carga es el operador pedido para reducir el desbalance: descarga la máquina que más tiempo acumula y elige el destino considerando a la vez qué tan ocupada está la otra máquina y cuánto tarda ahí la operación.

### Configuraciones comparadas

| Config. | Selección | Cruza OS / MA | Mutación OS / MA |
|---|---|---|---|
| A | Torneo | POX / uniforme | Intercambio / aleatoria |
| B | Ruleta | JBX / dos puntos | Inserción / aleatoria |
| C | Ranking | POX / uniforme | Intercambio / balance de carga |
| D | Torneo | POX / dos puntos | Inserción / balance de carga |

## 7. Ciclo del algoritmo y parámetros

Modelo generacional con elitismo:

1. **Población inicial.** 80 % aleatoria y 20 % sembrada asignando cada operación a su máquina más rápida. El primer individuo sembrado encola los trabajos por orden de llegada; los demás usan un orden aleatorio, para no llenar la población de copias.
2. **Evaluación.** Se decodifica cada individuo y su aptitud es el makespan.
3. **Elitismo.** Los 2 mejores pasan sin cambios, por lo que el mejor makespan nunca empeora.
4. **Reproducción.** Se seleccionan dos padres; con probabilidad pc se cruzan OS y MA, y si no, se copian.
5. **Mutación.** Cada hijo muta su OS con probabilidad pm y, de forma independiente, su MA con probabilidad pm.
6. Se repite desde el paso 2 hasta completar las generaciones.

El criterio de paro es un número fijo de generaciones, para que las curvas de convergencia de las 20 corridas tengan la misma longitud y puedan promediarse.

| Parámetro | Valor |
|---|---|
| Tamaño de población | 200 |
| Generaciones | 500 |
| Probabilidad de cruza (pc) | 0.9 |
| Probabilidad de mutación (pm) | 0.4 |
| Élites | 2 |
| Tamaño del torneo | 3 |

### Cómo se eligieron

Se hicieron corridas piloto con 8 semillas por configuración sobre los escenarios 1 y 3. Makespan promedio de las configuraciones A / B / C / D:

| Población | Generaciones | pm | Escenario 1 | Escenario 3 |
|---:|---:|---:|---|---|
| 100 | 300 | 0.2 | 22.35 / 22.43 / 21.94 / 22.11 | 33.26 / 33.66 / 32.86 / 33.07 |
| 100 | 300 | 0.4 | 21.60 / 22.11 / 21.25 / 21.76 | 33.27 / 35.64 / 32.49 / 32.44 |
| 200 | 300 | 0.4 | 21.51 / 21.70 / 21.26 / 21.65 | 32.65 / 35.35 / 32.41 / 32.61 |
| 200 | 500 | 0.4 | 21.50 / 21.53 / 21.15 / 21.62 | 32.45 / 34.84 / 32.26 / 32.50 |
| 200 | 500 | 0.6 | 21.54 / 21.91 / 20.99 / 20.94 | 32.51 / 35.85 / 33.31 / 31.99 |

- Subir pm de 0.2 a 0.4 mejoró casi todas las configuraciones: con pm bajo la población se estanca pronto.
- Con pm = 0.6 los resultados se vuelven irregulares (mejora D, empeoran B y C en el escenario 3), por lo que se dejó 0.4.
- Duplicar la población y alargar a 500 generaciones dio mejoras pequeñas pero consistentes, con un costo de 1 a 2.5 segundos por corrida.
- Variar pc a 0.8 con 4 élites no cambió los resultados de forma apreciable; se conservaron 0.9 y 2.

## 8. Experimentos

- **Ejecuciones.** 20 por escenario y por configuración.
- **Semillas.** 1 a 20, las mismas para las cuatro configuraciones, de modo que la comparación sea pareada. Cada corrida usa su propio generador (`random.Random(semilla)`), así que repetirla con el mismo escenario, configuración y semilla da exactamente el mismo resultado.
- **Configuración seleccionada.** La de menor makespan promedio en las 20 ejecuciones; si hay empate, la de mejor valor.
- **Tres mejores ejecuciones.** Las tres corridas de menor makespan final de la configuración seleccionada; si hay empate, primero la de semilla menor. De cada una se genera un diagrama de Gantt.
- **Convergencia.** Cada corrida guarda, por generación, el mejor makespan encontrado hasta ese momento (incluida la población inicial). La gráfica muestra tres curvas: la de la corrida con mejor makespan final (empate: semilla menor), la de la corrida con el peor (empate: semilla mayor), y el **promedio aritmético de las 20 curvas generación a generación**.
- **Estadística.** Mejor, peor, promedio y desviación estándar muestral del makespan final.

## 9. Resultados

Makespan final en segundos, 20 ejecuciones por celda (semillas 1 a 20). Los archivos completos están en `outputs/`.

### Escenario 1

| Config. | Mejor | Peor | Promedio | Desv. est. |
|---|---:|---:|---:|---:|
| A | 21.10 | 22.30 | 21.57 | 0.29 |
| B | 20.90 | 22.30 | 21.63 | 0.32 |
| **C** | **20.60** | **21.70** | **21.19** | 0.36 |
| D | 20.90 | 22.80 | 21.60 | 0.40 |

Seleccionada: **C**. Tres mejores ejecuciones: semillas 9, 13 y 20, las tres con makespan 20.60.

### Escenario 2

| Config. | Mejor | Peor | Promedio | Desv. est. |
|---|---:|---:|---:|---:|
| A | 20.70 | 21.40 | 20.79 | 0.21 |
| B | 20.70 | 22.30 | 20.94 | 0.38 |
| C | 20.70 | 20.80 | 20.70 | 0.02 |
| **D** | **20.70** | **20.70** | **20.70** | 0.00 |

Seleccionada: **D**. Las 20 ejecuciones llegan a 20.70, así que las tres mejores son las semillas 1, 2 y 3 por el criterio de desempate.

El valor 20.70 es el **óptimo** de este escenario: el trabajo J3 tiene 8 operaciones consecutivas y, aun dándole a cada una su máquina más rápida, tarda 2.9 + 2.8 + 2.1 + 2.5 + 2.1 + 2.9 + 2.8 + 2.6 = 20.7 s. Ninguna planificación puede terminar antes.

### Escenario 3

| Config. | Mejor | Peor | Promedio | Desv. est. |
|---|---:|---:|---:|---:|
| A | 31.30 | 33.80 | 32.36 | 0.68 |
| B | 33.20 | 37.30 | 34.86 | 1.17 |
| C | 31.10 | 33.60 | 32.30 | 0.69 |
| **D** | **31.10** | **33.30** | **32.28** | 0.55 |

Seleccionada: **D**. Tres mejores ejecuciones: semilla 20 (31.10), semilla 18 (31.50) y semilla 1 (31.90).

### Observaciones

- La configuración seleccionada usa la **mutación de balance de carga** en los tres escenarios (C en el 1, D en el 2 y el 3). La ventaja no es uniforme: en el escenario 1, D queda ligeramente detrás de A (21.60 frente a 21.57), y en el escenario 3 la diferencia de C y D sobre A (32.30 y 32.28 frente a 32.36) queda dentro de la dispersión entre corridas.
- La configuración B (ruleta, JBX, inserción) es la peor en los escenarios 2 y 3, con una diferencia clara en el 3 (34.86 de promedio). No se aisló qué operador de B causa la diferencia, porque las configuraciones cambian varios operadores a la vez.
- En el escenario 2 hay 10 máquinas para 10 trabajos y el problema resulta fácil: el límite lo pone el trabajo más largo, no la competencia por máquinas.
- En las curvas de convergencia, la mayor parte de la mejora ocurre en las primeras 50 a 100 generaciones.

## 10. Verificación

- **Pruebas automáticas** (`python -m unittest discover -s tests`, 57 pruebas): lector y validaciones, un caso del Escenario 1 calculado a mano (makespan 43.0), factibilidad de 1000 individuos aleatorios por escenario, validez de 1000 aplicaciones de cada operador de cruza y mutación, elitismo, reproducibilidad por semilla, campaña y línea de comandos.
- **Revisión de las salidas**: los 240 reportes de `outputs/` se releyeron con un script independiente del decodificador y se comprobó en cada uno que están todas las operaciones, que las duraciones coinciden con la tabla del escenario, que no hay traslapes en ninguna máquina y que se respeta la precedencia de cada trabajo. No se encontró ninguna violación.

## 11. Criterios de aceptación del enunciado

| Criterio | Evidencia |
|---|---|
| Los escenarios se cargan desde archivos de texto | `src/planificador/escenario.py`; `tests/test_escenario.py` |
| Representación del cromosoma documentada y justificada | Sección 2 |
| Tamaño del espacio de búsqueda y cómo se calcula | Sección 2; `parametros.json` de cada configuración |
| Cada operación se asigna a una sola máquina | Sección 2; verificador de factibilidad |
| Se preserva el orden de las operaciones de cada trabajo | Secciones 2 y 3; sección 10 |
| Tiempos tomados de la tabla operación-máquina | Sección 3; sección 10 |
| Tiempo inicial y final de cada operación | `outputs/<Escenario>/<config>/corrida_<semilla>.txt` |
| Makespan según la interpretación documentada | Sección 4 |
| Operadores de selección, cruza y mutación | Sección 6; `src/planificador/operadores.py` |
| Comparación de configuraciones | Sección 9; `outputs/<Escenario>/comparacion.md` |
| Reporte por máquina | `corrida_<semilla>.txt` |
| Gantt de las tres mejores ejecuciones | `outputs/<Escenario>/gantt_top1.png` a `gantt_top3.png` |
| 20 ejecuciones por escenario con semillas distintas | Sección 8; `resumen.csv` |
| Mejor, peor y promedio | Sección 9; `estadisticas.txt` |
| Gráfica de convergencia mejor, peor y promedio | `outputs/<Escenario>/convergencia.png` |
| Archivos de salida de todas las pruebas | `outputs/` |
| Código fuente | `src/`, `tests/` |
| Reporte con la estructura solicitada | **Pendiente**: portada, introducción y conclusiones individuales corresponden al equipo; este documento cubre la sección de diseño y las tablas de resultados |
