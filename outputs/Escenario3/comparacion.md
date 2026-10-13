# Escenario3

- Operaciones (tipos): 15
- Máquinas: 5
- Trabajos: 12
- Operaciones a planificar (N): 59
- Espacio de búsqueda p^N * N!/prod(n_j!): 1.73 x 10^41 * 4.08 x 10^54 = 7.08 x 10^95
- Parámetros: población 200, generaciones 500, pc 0.9, pm 0.4, élites 2, torneo k = 3
- Ejecuciones por configuración: 20 (semillas 1 a 20)

## Comparación de configuraciones

| configuracion | seleccion | cruza_os | cruza_ma | mutacion_os | mutacion_ma | mejor | peor | promedio | desviacion | seleccionada |
|---|---|---|---|---|---|---|---|---|---|---|
| A | torneo | pox | uniforme | intercambio | aleatoria | 31.30 | 33.80 | 32.36 | 0.68 | no |
| B | ruleta | jbx | dos_puntos | insercion | aleatoria | 33.20 | 37.30 | 34.86 | 1.17 | no |
| C | ranking | pox | uniforme | intercambio | balance | 31.10 | 33.60 | 32.30 | 0.69 | no |
| D | torneo | pox | dos_puntos | insercion | balance | 31.10 | 33.30 | 32.28 | 0.55 | si |

Configuración seleccionada (menor promedio): **D**

## Tres mejores ejecuciones de la configuración seleccionada

| lugar | semilla | makespan | carga_maxima | energia | gantt |
|---|---|---|---|---|---|
| 1 | 20 | 31.10 | 30.90 | 480.30 | gantt_top1.png |
| 2 | 18 | 31.50 | 31.50 | 478.60 | gantt_top2.png |
| 3 | 1 | 31.90 | 31.70 | 473.80 | gantt_top3.png |
