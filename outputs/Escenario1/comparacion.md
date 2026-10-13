# Escenario1

- Operaciones (tipos): 5
- Máquinas: 4
- Trabajos: 6
- Operaciones a planificar (N): 19
- Espacio de búsqueda p^N * N!/prod(n_j!): 2.75 x 10^11 * 2.93 x 10^11 = 8.06 x 10^22
- Parámetros: población 200, generaciones 500, pc 0.9, pm 0.4, élites 2, torneo k = 3
- Ejecuciones por configuración: 20 (semillas 1 a 20)

## Comparación de configuraciones

| configuracion | seleccion | cruza_os | cruza_ma | mutacion_os | mutacion_ma | mejor | peor | promedio | desviacion | seleccionada |
|---|---|---|---|---|---|---|---|---|---|---|
| A | torneo | pox | uniforme | intercambio | aleatoria | 21.10 | 22.30 | 21.57 | 0.29 | no |
| B | ruleta | jbx | dos_puntos | insercion | aleatoria | 20.90 | 22.30 | 21.63 | 0.32 | no |
| C | ranking | pox | uniforme | intercambio | balance | 20.60 | 21.70 | 21.19 | 0.36 | si |
| D | torneo | pox | dos_puntos | insercion | balance | 20.90 | 22.80 | 21.60 | 0.40 | no |

Configuración seleccionada (menor promedio): **C**

## Tres mejores ejecuciones de la configuración seleccionada

| lugar | semilla | makespan | carga_maxima | energia | gantt |
|---|---|---|---|---|---|
| 1 | 9 | 20.60 | 20.60 | 95.50 | gantt_top1.png |
| 2 | 13 | 20.60 | 20.60 | 95.50 | gantt_top2.png |
| 3 | 20 | 20.60 | 20.60 | 95.50 | gantt_top3.png |
