import json
from datetime import date, datetime, timedelta

DIAS = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado']
HORAS = [f'{h:02d}:00' for h in range(7, 22)]   # 07:00 … 21:00  (15 bloques de 1 h)


def _lunes_semana() -> str:
    hoy = date.today()
    lunes = hoy - timedelta(days=hoy.weekday())
    return str(lunes)


def generar_horario(usuario_id: int, db) -> dict:
    """
    Genera un horario de estudio semanal para el usuario.

    Pasos:
    1. Cargar perfil académico → carrera/semestre/grupo
    2. Cargar clases del usuario desde horarios_usfx
    3. Cargar materias_estudiante
    4. Cargar evaluaciones próximas (14 días)
    5. Construir grilla vacía lunes-sábado 07:00-21:00 (bloques de 1 h)
    6. Marcar bloques de CLASE en la grilla
    7. Calcular horas de estudio necesarias por materia (base + urgencia)
    8. Asignar bloques de ESTUDIO en slots libres
    9. Retornar estructura JSON
    """
    c = db.cursor()

    # ── 1. Perfil académico ────────────────────────────────────────────────
    perfil = c.execute(
        'SELECT carrera, semestre, grupo FROM perfil_academico WHERE usuario_id = ?',
        (usuario_id,)
    ).fetchone()

    # ── 2. Clases USFX ────────────────────────────────────────────────────
    clases = []
    if perfil:
        rows = c.execute(
            '''SELECT dia, hora_inicio, hora_fin, materia_codigo, materia_nombre, aula
               FROM horarios_usfx
               WHERE carrera = ? AND semestre = ? AND grupo = ?''',
            (perfil['carrera'], perfil['semestre'], perfil['grupo'])
        ).fetchall()
        clases = [dict(r) for r in rows]

    # ── 3. Materias del estudiante ────────────────────────────────────────
    materias = [
        dict(r) for r in c.execute(
            'SELECT * FROM materias_estudiante WHERE usuario_id = ?', (usuario_id,)
        ).fetchall()
    ]
    if not materias:
        return _horario_vacio()

    # ── 4. Evaluaciones próximas (14 días) ────────────────────────────────
    hoy = date.today()
    limite = hoy + timedelta(days=14)
    evals = [
        dict(r) for r in c.execute(
            '''SELECT materia_codigo, fecha FROM evaluaciones
               WHERE usuario_id = ? AND fecha BETWEEN ? AND ?
               ORDER BY fecha''',
            (usuario_id, str(hoy), str(limite))
        ).fetchall()
    ]

    # ── 5. Grilla vacía ───────────────────────────────────────────────────
    grilla: dict[str, dict[str, dict]] = {
        dia: {hora: {'hora': hora, 'tipo': 'libre'} for hora in HORAS}
        for dia in DIAS
    }

    # ── 6. Marcar clases ──────────────────────────────────────────────────
    for clase in clases:
        dia = clase['dia']
        if dia not in grilla:
            continue
        hi = clase['hora_inicio']
        hf = clase['hora_fin']
        if hi not in HORAS:
            continue
        for h in HORAS:
            if h >= hi and h < hf:
                grilla[dia][h] = {
                    'hora':   h,
                    'tipo':   'clase',
                    'codigo': clase['materia_codigo'],
                    'nombre': clase.get('materia_nombre') or clase['materia_codigo'],
                    'aula':   clase.get('aula') or '',
                }

    # ── 7. Horas de estudio por materia ───────────────────────────────────
    def urgencia(codigo: str) -> float:
        factor = 1.0
        for ev in evals:
            if ev['materia_codigo'] != codigo:
                continue
            try:
                dias_rest = (date.fromisoformat(ev['fecha']) - hoy).days
            except ValueError:
                continue
            if 0 <= dias_rest <= 3:
                factor = max(factor, 2.0)
            elif dias_rest <= 7:
                factor = max(factor, 1.5)
        return factor

    horas_obj = {m['materia_codigo']: m['horas_semana'] * urgencia(m['materia_codigo'])
                 for m in materias}

    materias_sorted = sorted(materias, key=lambda m: m['dificultad'], reverse=True)
    mat_map = {m['materia_codigo']: m for m in materias}
    pendiente = dict(horas_obj)

    # ── 8. Asignar bloques de estudio ────────────────────────────────────
    asignadas_dia: dict[str, dict[str, float]] = {d: {} for d in DIAS}

    for dia in DIAS:
        consec: dict[str, int] = {}

        for hora in HORAS:
            slot = grilla[dia][hora]
            if slot['tipo'] != 'libre':
                consec = {}
                continue

            elegida = None
            for m in materias_sorted:
                cod = m['materia_codigo']
                if pendiente.get(cod, 0) < 0.5:
                    continue
                if asignadas_dia[dia].get(cod, 0) >= 2:
                    continue
                if consec.get(cod, 0) >= 2:
                    continue
                elegida = m
                break

            if not elegida:
                continue

            cod = elegida['materia_codigo']
            grilla[dia][hora] = {
                'hora':   hora,
                'tipo':   'estudio',
                'codigo': cod,
                'nombre': elegida['materia_nombre'],
                'color':  elegida.get('color', '#3182ce'),
            }
            pendiente[cod] = max(0.0, pendiente[cod] - 1.0)
            asignadas_dia[dia][cod] = asignadas_dia[dia].get(cod, 0) + 1
            for other in list(consec):
                if other != cod:
                    consec[other] = 0
            consec[cod] = consec.get(cod, 0) + 1

    # ── 9. Armar respuesta ────────────────────────────────────────────────
    dias_json = {dia: list(grilla[dia].values()) for dia in DIAS}

    resumen: dict[str, dict] = {}
    for dia in DIAS:
        for slot in grilla[dia].values():
            if slot['tipo'] == 'estudio':
                cod = slot['codigo']
                if cod not in resumen:
                    resumen[cod] = {
                        'nombre':          slot.get('nombre', cod),
                        'horas_asignadas': 0,
                        'color':           slot.get('color', '#3182ce'),
                    }
                resumen[cod]['horas_asignadas'] += 1

    return {'semana': _lunes_semana(), 'dias': dias_json, 'resumen': resumen}


def _horario_vacio() -> dict:
    dias_json = {dia: [{'hora': h, 'tipo': 'libre'} for h in HORAS] for dia in DIAS}
    return {'semana': _lunes_semana(), 'dias': dias_json, 'resumen': {}}
