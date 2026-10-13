# Escenario2

- Operaciones (tipos): 8
- Máquinas: 10
- Trabajos: 10
- Operaciones a planificar (N): 40
- Espacio de búsqueda p^N * N!/prod(n_j!): 1.00 x 10^40 * 1.96 x 10^33 = 1.96 x 10^73
- Parámetros: población 200, generaciones 500, pc 0.9, pm 0.4, élites 2, torneo k = 3
- Ejecuciones por configuración: 20 (semillas 1 a 20)

## Comparación de configuraciones

| configuracion | seleccion | cruza_os | cruza_ma | mutacion_os | mutacion_ma | mejor | peor | promedio | desviacion | seleccionada |
|---|---|---|---|---|---|---|---|---|---|---|
| A | torneo | pox | uniforme | intercambio | aleatoria | 20.70 | 21.40 | 20.79 | 0.21 | no |
| B | ruleta | jbx | dos_puntos | insercion | aleatoria | 20.70 | 22.30 | 20.94 | 0.38 | no |
| C | ranking | pox | uniforme | intercambio | balance | 20.70 | 20.80 | 20.70 | 0.02 | no |
| D | torneo | pox | dos_puntos | insercion | balance | 20.70 | 20.70 | 20.70 | 0.00 | si |

Configuración seleccionada (menor promedio): **D**

## Tres mejores ejecuciones de la configuración seleccionada

| lugar | semilla | makespan | carga_maxima | energia | gantt |
|---|---|---|---|---|---|
| 1 | 1 | 20.70 | 17.40 | 137.80 | gantt_top1.png |
| 2 | 2 | 20.70 | 14.00 | 132.10 | gantt_top2.png |
| 3 | 3 | 20.70 | 15.00 | 125.30 | gantt_top3.png |
