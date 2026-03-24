# Figure 5 Recovery

Fecha: 2026-03-24

Esta carpeta concentra el plan de recuperacion del flujo `SHARC -> CVA6 -> Spike -> Figure 5`.

Objetivo:

- volver al estado que ya funciono,
- recuperar un flujo reproducible,
- dejar fuera de `SHARCBRIDGE` todo lo que no sea estrictamente necesario para el flujo productivo.

Documentos base:

- `CURRENT_STATE.md`: diagnostico actual y evidencias observadas.
- `PLAN.md`: plan por tareas, con test y gate por tarea.

Reglas de trabajo:

- `sharc_original/` no se toca.
- `SHARCBRIDGE/` no recibe experimentos ni utilidades temporales nuevas.
- `SHARCBRIDGE_CVA6/` solo recibe cambios minimos si son necesarios para que el flujo funcione.
- Toda sonda, log, replay, diff, reporte y script auxiliar vive en esta carpeta.
- Si una tarea falla dos veces por drift del entorno, se activa el camino de reinstalacion controlada en lugar de seguir parcheando.

Estructura prevista:

- `logs/`: logs crudos de ejecucion y probes.
- `results/`: reportes markdown/json/txt de cada gate.
- `scripts/`: probes y tests auxiliares de recuperacion.

