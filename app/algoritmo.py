from datetime import date

DIAS = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo']


def generar_horario(materias, disponibilidad, evaluaciones):
    """
    materias:      list[dict]  {id, nombre, dificultad, color}
    disponibilidad: dict       {lunes: int, ..., domingo: int}
    evaluaciones:  list[dict]  {materia_id, fecha: date}
    Returns: dict {dia: [{materia, materia_id, horas, color, dificultad}]}
    """
    hoy = date.today()
    total_horas = sum(disponibilidad.get(d, 0) for d in DIAS)

    if not materias or total_horas == 0:
        return {d: [] for d in DIAS}

    # Weight per materia = dificultad × urgency_factor
    pesos = {}
    for m in materias:
        factor = 1.0
        for ev in evaluaciones:
            if ev['materia_id'] == m['id']:
                restantes = (ev['fecha'] - hoy).days
                if 0 <= restantes <= 3:
                    factor = max(factor, 2.0)
                elif restantes <= 7:
                    factor = max(factor, 1.5)
        pesos[m['id']] = float(m['dificultad']) * factor

    total_peso = sum(pesos.values()) or 1.0

    # Raw hour allocation per materia
    horas_obj = {
        m['id']: total_horas * pesos[m['id']] / total_peso
        for m in materias
    }

    # Days ordered most-to-least available hours
    dias_ordenados = sorted(DIAS, key=lambda d: disponibilidad.get(d, 0), reverse=True)

    # Materias ordered by priority (highest weight first)
    materias_sorted = sorted(materias, key=lambda m: pesos[m['id']], reverse=True)

    horario = {d: [] for d in DIAS}
    pendiente = {m['id']: horas_obj[m['id']] for m in materias}

    for dia in dias_ordenados:
        cap = float(disponibilidad.get(dia, 0))
        if cap <= 0:
            continue

        for m in materias_sorted:
            if pendiente[m['id']] < 0.25 or cap < 0.25:
                continue

            # Cap at 3h per materia per day, round to nearest 0.5
            asignar = min(pendiente[m['id']], cap, 3.0)
            asignar = round(asignar * 2) / 2  # nearest 0.5h

            if asignar >= 0.5:
                horario[dia].append({
                    'materia': m['nombre'],
                    'materia_id': m['id'],
                    'horas': asignar,
                    'color': m.get('color', '#3182ce'),
                    'dificultad': m['dificultad'],
                })
                cap -= asignar
                pendiente[m['id']] -= asignar

    return horario
