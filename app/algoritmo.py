import json
import time
from datetime import date, timedelta

DIAS  = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado']
HORAS = [f'{h:02d}:00' for h in range(7, 22)]   # 07:00 … 21:00


def _lunes_semana() -> str:
    hoy  = date.today()
    lunes = hoy - timedelta(days=hoy.weekday())
    return str(lunes)


# ─────────────────────────────────────────────────────────────────────────────
# ARMADO DE HORARIO DE CLASES (backtracking)
# ─────────────────────────────────────────────────────────────────────────────

def armar_horario_clases(carrera: str, semestre: int, db) -> list:
    """
    Elige una sección por cada materia del semestre (carrera+semestre) de forma
    que no haya conflictos de horario y se minimicen los huecos entre clases.

    Retorna lista de:
      {materia_codigo, materia_nombre, seccion, profesor,
       bloques: [{dia, hora_inicio, hora_fin, aula}]}
    """
    from app.plan_estudios import PLAN_ESTUDIOS
    from app.carreras import get_carreras_buscar

    codigos = list(PLAN_ESTUDIOS.get(carrera, {}).get(semestre, []))

    carreras_buscar = get_carreras_buscar(carrera)
    placeholders    = ','.join('?' * len(carreras_buscar))

    if not codigos:
        rows = db.execute(
            f'''SELECT DISTINCT materia_codigo FROM horarios_usfx
                WHERE carrera IN ({placeholders}) AND semestre=?
                ORDER BY materia_codigo''',
            (*carreras_buscar, semestre)
        ).fetchall()
        codigos = [r['materia_codigo'] for r in rows]

    if not codigos:
        return []

    # ── Cargar secciones disponibles por materia ──────────────────────────────
    materias_secciones: dict[str, dict] = {}

    for codigo in codigos:
        rows = db.execute(
            f'''SELECT materia_nombre, seccion, profesor, dia, hora_inicio, hora_fin, aula
                FROM horarios_usfx
                WHERE carrera IN ({placeholders}) AND semestre=? AND materia_codigo=?
                ORDER BY seccion, dia, hora_inicio''',
            (*carreras_buscar, semestre, codigo)
        ).fetchall()

        secciones: dict[str, dict] = {}
        for r in rows:
            sec = r['seccion']
            if sec not in secciones:
                secciones[sec] = {
                    'nombre':   r['materia_nombre'] or codigo,
                    'profesor': r['profesor'] or '',
                    'bloques':  [],
                    '_seen':    set(),   # para deduplicar bloques entre carreras
                }
            bloque_key = (r['dia'], r['hora_inicio'])
            if bloque_key not in secciones[sec]['_seen']:
                secciones[sec]['_seen'].add(bloque_key)
                secciones[sec]['bloques'].append({
                    'dia':         r['dia'],
                    'hora_inicio': r['hora_inicio'],
                    'hora_fin':    r['hora_fin'],
                    'aula':        r['aula'] or '',
                })

        # Quitar campo interno antes de pasar al backtracking
        for sec_info in secciones.values():
            sec_info.pop('_seen', None)

        if secciones:
            materias_secciones[codigo] = secciones

    if not materias_secciones:
        return [{'materia_codigo': c, 'materia_nombre': c,
                 'seccion': '', 'profesor': '', 'bloques': []} for c in codigos]

    # ── Backtracking ──────────────────────────────────────────────────────────
    # Ordenar materias: menor número de secciones primero (poda más rápida)
    orden = sorted(materias_secciones.keys(), key=lambda c: len(materias_secciones[c]))

    best_score:      list = [None]
    best_asignacion: list = [None]
    deadline = time.time() + 3.0   # máx 3 s de backtracking

    def _conflicto(nuevos, existentes):
        for nb in nuevos:
            for eb in existentes:
                if nb['dia'] != eb['dia']:
                    continue
                if nb['hora_inicio'] < eb['hora_fin'] and nb['hora_fin'] > nb['hora_inicio']:
                    if nb['hora_inicio'] < eb['hora_fin'] and nb['hora_fin'] > eb['hora_inicio']:
                        return True
        return False

    def _score(asignacion):
        by_day: dict[str, set] = {}
        for sec_info in asignacion.values():
            for b in sec_info['bloques']:
                hi = int(b['hora_inicio'][:2])
                hf = int(b['hora_fin'][:2])
                by_day.setdefault(b['dia'], set()).update(range(hi, hf))

        total = 0
        for horas in by_day.values():
            if not horas:
                continue
            span = range(min(horas), max(horas) + 1)
            huecos = sum(1 for h in span if h not in horas)
            total -= huecos
        total += (len(DIAS) - len(by_day)) * 2   # bonus por días libres
        return total

    def backtrack(idx, asignacion, bloques_usados):
        if time.time() > deadline:
            return
        if idx == len(orden):
            s = _score(asignacion)
            if best_score[0] is None or s > best_score[0]:
                best_score[0] = s
                best_asignacion[0] = {k: dict(v) for k, v in asignacion.items()}
            return

        codigo   = orden[idx]
        secciones = materias_secciones[codigo]

        # Ordenar secciones: las que tienen menos días de clase primero
        secciones_ord = sorted(
            secciones.items(),
            key=lambda kv: len({b['dia'] for b in kv[1]['bloques']})
        )

        for sec, info in secciones_ord:
            if time.time() > deadline:
                break
            if _conflicto(info['bloques'], bloques_usados):
                continue
            asignacion[codigo] = info | {'seccion': sec}
            backtrack(idx + 1, asignacion, bloques_usados + info['bloques'])
            del asignacion[codigo]

    backtrack(0, {}, [])

    # ── Construir resultado ───────────────────────────────────────────────────
    result = []
    asig = best_asignacion[0] or {}

    for codigo in codigos:
        if codigo in asig:
            info = asig[codigo]
            result.append({
                'materia_codigo': codigo,
                'materia_nombre': info.get('nombre', codigo),
                'seccion':        info.get('seccion', ''),
                'profesor':       info.get('profesor', ''),
                'bloques':        info.get('bloques', []),
            })
        elif codigo in materias_secciones:
            # Fallback: primera sección sin verificar conflictos
            sec, info = next(iter(materias_secciones[codigo].items()))
            result.append({
                'materia_codigo': codigo,
                'materia_nombre': info['nombre'],
                'seccion':        sec,
                'profesor':       info['profesor'],
                'bloques':        info['bloques'],
            })
        else:
            result.append({'materia_codigo': codigo, 'materia_nombre': codigo,
                           'seccion': '', 'profesor': '', 'bloques': []})

    return result


# ─────────────────────────────────────────────────────────────────────────────
# GENERACIÓN DE HORARIO DE ESTUDIO
# ─────────────────────────────────────────────────────────────────────────────

def generar_horario(usuario_id: int, db) -> dict:
    """
    Genera el horario semanal de estudio:
    1. Lee clases desde horario_clases_usuario (armado por armar_horario_clases)
    2. Carga materias_estudiante y evaluaciones próximas
    3. Marca slots de CLASE en la grilla
    4. Llena huecos con ESTUDIO proporcional a dificultad×urgencia
    """
    c = db.cursor()

    # ── 1. Clases del usuario (desde horario_clases_usuario) ──────────────────
    clases = []
    row = c.execute(
        'SELECT horario_json FROM horario_clases_usuario WHERE usuario_id=?',
        (usuario_id,)
    ).fetchone()
    if row:
        try:
            for entry in json.loads(row['horario_json']):
                for bloque in entry.get('bloques', []):
                    clases.append({
                        'dia':            bloque['dia'],
                        'hora_inicio':    bloque['hora_inicio'],
                        'hora_fin':       bloque['hora_fin'],
                        'materia_codigo': entry['materia_codigo'],
                        'materia_nombre': entry.get('materia_nombre', entry['materia_codigo']),
                        'aula':           bloque.get('aula', ''),
                        'seccion':        entry.get('seccion', ''),
                        'profesor':       entry.get('profesor', ''),
                    })
        except Exception:
            pass

    # ── 2. Materias del estudiante ────────────────────────────────────────────
    materias = [dict(r) for r in c.execute(
        'SELECT * FROM materias_estudiante WHERE usuario_id=?', (usuario_id,)
    ).fetchall()]
    if not materias:
        return _horario_vacio()

    # ── 3. Evaluaciones próximas (14 días) ────────────────────────────────────
    hoy    = date.today()
    limite = hoy + timedelta(days=14)
    evals  = [dict(r) for r in c.execute(
        '''SELECT materia_codigo, fecha FROM evaluaciones
           WHERE usuario_id=? AND fecha BETWEEN ? AND ?
           ORDER BY fecha''',
        (usuario_id, str(hoy), str(limite))
    ).fetchall()]

    # ── 4. Grilla vacía ───────────────────────────────────────────────────────
    grilla: dict[str, dict[str, dict]] = {
        dia: {hora: {'hora': hora, 'tipo': 'libre'} for hora in HORAS}
        for dia in DIAS
    }

    # ── 5. Marcar clases ──────────────────────────────────────────────────────
    for clase in clases:
        dia = clase['dia']
        if dia not in grilla:
            continue
        hi = clase['hora_inicio']
        hf = clase['hora_fin']
        if hi not in HORAS:
            continue
        for h in HORAS:
            if hi <= h < hf:
                grilla[dia][h] = {
                    'hora':    h,
                    'tipo':    'clase',
                    'codigo':  clase['materia_codigo'],
                    'nombre':  clase['materia_nombre'],
                    'aula':    clase.get('aula', ''),
                    'seccion': clase.get('seccion', ''),
                    'profesor':clase.get('profesor', ''),
                }

    # ── 6. Horas de estudio por materia ───────────────────────────────────────
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
    pendiente       = dict(horas_obj)

    # ── 7. Asignar bloques de estudio ────────────────────────────────────────
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

    # ── 8. Armar respuesta ────────────────────────────────────────────────────
    dias_json = {dia: list(grilla[dia].values()) for dia in DIAS}

    resumen: dict[str, dict] = {}
    for dia in DIAS:
        for slot in grilla[dia].values():
            if slot['tipo'] == 'estudio':
                cod = slot['codigo']
                if cod not in resumen:
                    resumen[cod] = {'nombre': slot.get('nombre', cod),
                                    'horas_asignadas': 0,
                                    'color': slot.get('color', '#3182ce')}
                resumen[cod]['horas_asignadas'] += 1

    return {'semana': _lunes_semana(), 'dias': dias_json, 'resumen': resumen}


def _horario_vacio() -> dict:
    dias_json = {dia: [{'hora': h, 'tipo': 'libre'} for h in HORAS] for dia in DIAS}
    return {'semana': _lunes_semana(), 'dias': dias_json, 'resumen': {}}
