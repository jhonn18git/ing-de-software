import json
import time
from datetime import date, timedelta

DIAS       = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado']
_BASE_HORAS = [f'{h:02d}:00' for h in range(7, 22)]  # 07:00 … 21:00 (1h slots)


def _hm(t: str) -> int:
    """Convert 'HH:MM' → total minutes since midnight."""
    h, m = t.split(':')
    return int(h) * 60 + int(m)


def _build_horas(clases: list) -> list:
    """1h grid + extra :30 rows only for classes that start at :30."""
    extra = {c['hora_inicio'] for c in clases if c['hora_inicio'].endswith(':30')}
    return sorted(set(_BASE_HORAS) | extra)


HORAS = _BASE_HORAS  # default (no classes loaded yet)


def _lunes_semana() -> str:
    hoy  = date.today()
    lunes = hoy - timedelta(days=hoy.weekday())
    return str(lunes)


def _es_seccion_lab(seccion: str) -> bool:
    s = seccion.upper()
    return s.startswith('GL') or s.startswith('GP')


# -----------------------------------------------------------------------
# ARMADO DE HORARIO DE CLASES (backtracking con teoria+laboratorio)
# -----------------------------------------------------------------------

def armar_horario_clases(carrera: str, semestre: int, db) -> list:
    """
    Elige secciones para cada materia del semestre sin conflictos horarios,
    minimizando huecos entre clases.

    Para materias que tienen secciones de teoria (G*, GT*) Y laboratorio
    (GL*, GP*), selecciona UNA seccion de cada tipo; los bloques de ambas
    se unen en el resultado.

    Retorna lista de:
      {materia_codigo, materia_nombre, seccion, seccion_lab, profesor,
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

    # --- Cargar secciones disponibles por materia, deduplicando bloques ------
    # Estrategia: priorizar la carrera propia del estudiante. Solo usar el
    # fallback multi-carrera si la materia no tiene secciones en su carrera propia.
    # Esto evita contaminacion cuando dos carreras comparten codigos de seccion
    # (p.ej. CIC y SIS ambas tienen GL1 para SIS420 pero en horarios distintos).
    materias_secciones: dict[str, dict] = {}

    for codigo in codigos:
        # Primero: solo carrera propia
        rows = db.execute(
            '''SELECT materia_nombre, seccion, profesor, dia, hora_inicio, hora_fin, aula
               FROM horarios_usfx
               WHERE carrera=? AND semestre=? AND materia_codigo=?
               ORDER BY seccion, dia, hora_inicio''',
            (carrera, semestre, codigo)
        ).fetchall()

        # Fallback: todas las carreras relacionadas si no hay datos propios
        if not rows:
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
                    '_seen':    set(),
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

        for sec_info in secciones.values():
            sec_info.pop('_seen', None)

        if secciones:
            materias_secciones[codigo] = secciones

    if not materias_secciones:
        return [{'materia_codigo': c, 'materia_nombre': c,
                 'seccion': '', 'seccion_lab': '', 'profesor': '', 'bloques': []} for c in codigos]

    # --- Clasificar secciones por tipo y construir opciones de eleccion -------
    # opciones_materia: {codigo: [opcion, ...]}
    # cada opcion = {seccion, seccion_lab, nombre, profesor, bloques}
    opciones_materia: dict[str, list] = {}

    for codigo, secciones in materias_secciones.items():
        teo = {s: i for s, i in secciones.items() if not _es_seccion_lab(s)}
        lab = {s: i for s, i in secciones.items() if _es_seccion_lab(s)}

        opciones: list = []

        if teo and lab:
            # Producto cruzado: el alumno necesita UNA de teoria Y UNA de lab
            for st, it in teo.items():
                for sl, il in lab.items():
                    # Tag each block with its source section for display logic
                    bloques = [dict(b, bloque_sec=st) for b in it['bloques']]
                    bloques += [dict(b, bloque_sec=sl) for b in il['bloques']]
                    opciones.append({
                        'seccion':     st,
                        'seccion_lab': sl,
                        'nombre':      it['nombre'],
                        'profesor':    it['profesor'],
                        'bloques':     bloques,
                    })
        elif teo:
            for st, it in teo.items():
                opciones.append({
                    'seccion':     st,
                    'seccion_lab': '',
                    'nombre':      it['nombre'],
                    'profesor':    it['profesor'],
                    'bloques':     it['bloques'],
                })
        else:
            for sl, il in lab.items():
                opciones.append({
                    'seccion':     '',
                    'seccion_lab': sl,
                    'nombre':      il['nombre'],
                    'profesor':    il['profesor'],
                    'bloques':     il['bloques'],
                })

        if opciones:
            opciones_materia[codigo] = opciones

    if not opciones_materia:
        return [{'materia_codigo': c, 'materia_nombre': c,
                 'seccion': '', 'seccion_lab': '', 'profesor': '', 'bloques': []} for c in codigos]

    # --- Backtracking ---------------------------------------------------------
    # Orden: menos opciones primero (poda mas agresiva)
    orden = sorted(opciones_materia.keys(), key=lambda c: len(opciones_materia[c]))

    best_score:      list = [None]
    best_asignacion: list = [None]
    deadline = time.time() + 4.0   # max 4 s (producto cruzado amplia espacio)

    def _conflicto(nuevos, existentes):
        for nb in nuevos:
            for eb in existentes:
                if nb['dia'] != eb['dia']:
                    continue
                if nb['hora_inicio'] < eb['hora_fin'] and nb['hora_fin'] > eb['hora_inicio']:
                    return True
        return False

    def _score(asignacion):
        by_day: dict[str, set] = {}
        for opcion in asignacion.values():
            for b in opcion['bloques']:
                hi = _hm(b['hora_inicio'])
                hf = _hm(b['hora_fin'])
                by_day.setdefault(b['dia'], set()).update(range(hi, hf, 30))

        total = 0
        for slots in by_day.values():
            if not slots:
                continue
            span = range(min(slots), max(slots) + 30, 30)
            huecos = sum(1 for s in span if s not in slots)
            total -= huecos
        total += (len(DIAS) - len(by_day)) * 4  # bonus por dias libres
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

        codigo  = orden[idx]
        opciones = opciones_materia[codigo]

        # Ordenar: menos dias distintos primero
        opciones_ord = sorted(opciones, key=lambda o: len({b['dia'] for b in o['bloques']}))

        for opcion in opciones_ord:
            if time.time() > deadline:
                break
            if _conflicto(opcion['bloques'], bloques_usados):
                continue
            asignacion[codigo] = opcion
            backtrack(idx + 1, asignacion, bloques_usados + opcion['bloques'])
            del asignacion[codigo]

    backtrack(0, {}, [])

    # --- Construir resultado --------------------------------------------------
    result = []
    asig = best_asignacion[0] or {}

    for codigo in codigos:
        if codigo in asig:
            op = asig[codigo]
            result.append({
                'materia_codigo': codigo,
                'materia_nombre': op.get('nombre', codigo),
                'seccion':        op.get('seccion', ''),
                'seccion_lab':    op.get('seccion_lab', ''),
                'profesor':       op.get('profesor', ''),
                'bloques':        op.get('bloques', []),
            })
        elif codigo in opciones_materia:
            # Fallback: primera opcion sin verificar conflictos
            op = opciones_materia[codigo][0]
            result.append({
                'materia_codigo': codigo,
                'materia_nombre': op['nombre'],
                'seccion':        op['seccion'],
                'seccion_lab':    op['seccion_lab'],
                'profesor':       op['profesor'],
                'bloques':        op['bloques'],
            })
        else:
            result.append({'materia_codigo': codigo, 'materia_nombre': codigo,
                           'seccion': '', 'seccion_lab': '', 'profesor': '', 'bloques': []})

    return result


# -----------------------------------------------------------------------
# GENERACION DE HORARIO DE ESTUDIO
# -----------------------------------------------------------------------

def generar_horario(usuario_id: int, db) -> dict:
    """
    Genera el horario semanal de estudio:
    1. Lee clases desde horario_clases_usuario (armado por armar_horario_clases)
    2. Carga materias_estudiante y evaluaciones proximas
    3. Marca slots de CLASE en la grilla
    4. Llena huecos con ESTUDIO proporcional a dificultad x urgencia
    """
    c = db.cursor()

    # 1. Clases del usuario (desde horario_clases_usuario)
    clases = []
    row = c.execute(
        'SELECT horario_json FROM horario_clases_usuario WHERE usuario_id=?',
        (usuario_id,)
    ).fetchone()
    if row:
        try:
            for entry in json.loads(row['horario_json']):
                sec     = entry.get('seccion', '')
                sec_lab = entry.get('seccion_lab', '')
                # Build a set of (dia, hora_inicio) for teo blocks and lab blocks
                teo_slots = set()
                lab_slots = set()
                for b in entry.get('bloques', []):
                    key = (b['dia'], b['hora_inicio'])
                    if b.get('bloque_sec', sec) == sec_lab and sec_lab:
                        lab_slots.add(key)
                    else:
                        teo_slots.add(key)
                for bloque in entry.get('bloques', []):
                    key = (bloque['dia'], bloque['hora_inicio'])
                    bs  = bloque.get('bloque_sec', sec)
                    # Show both secciones only when teo AND lab share this exact slot
                    if sec_lab and key in teo_slots and key in lab_slots:
                        disp_sec     = sec
                        disp_sec_lab = sec_lab
                    elif bs == sec_lab and sec_lab:
                        disp_sec     = sec_lab
                        disp_sec_lab = ''
                    else:
                        disp_sec     = sec
                        disp_sec_lab = ''
                    clases.append({
                        'dia':            bloque['dia'],
                        'hora_inicio':    bloque['hora_inicio'],
                        'hora_fin':       bloque['hora_fin'],
                        'materia_codigo': entry['materia_codigo'],
                        'materia_nombre': entry.get('materia_nombre', entry['materia_codigo']),
                        'aula':           bloque.get('aula', ''),
                        'seccion':        disp_sec,
                        'seccion_lab':    disp_sec_lab,
                        'profesor':       entry.get('profesor', ''),
                    })
        except Exception:
            pass

    # 2. Materias del estudiante
    materias = [dict(r) for r in c.execute(
        'SELECT * FROM materias_estudiante WHERE usuario_id=?', (usuario_id,)
    ).fetchall()]
    if not materias:
        return _horario_vacio()

    # 3. Evaluaciones proximas (14 dias)
    hoy    = date.today()
    limite = hoy + timedelta(days=14)
    evals  = [dict(r) for r in c.execute(
        '''SELECT materia_codigo, fecha FROM evaluaciones
           WHERE usuario_id=? AND fecha BETWEEN ? AND ?
           ORDER BY fecha''',
        (usuario_id, str(hoy), str(limite))
    ).fetchall()]

    # 4. Grilla: 1h base + filas :30 extra solo si hay clases que empiezan a :30
    horas_grilla = _build_horas(clases)
    grilla: dict[str, dict[str, dict]] = {
        dia: {hora: {'hora': hora, 'tipo': 'libre'} for hora in horas_grilla}
        for dia in DIAS
    }

    # 5. Marcar clases — bloque completo (p.ej. 07:00-09:00) pinta cada fila cubierta
    for clase in clases:
        dia = clase['dia']
        if dia not in grilla:
            continue
        hi = clase['hora_inicio']
        hf = clase['hora_fin']
        for h in horas_grilla:
            if hi <= h < hf:
                grilla[dia][h] = {
                    'hora':       h,
                    'tipo':       'clase',
                    'codigo':     clase['materia_codigo'],
                    'nombre':     clase['materia_nombre'],
                    'aula':       clase.get('aula', ''),
                    'seccion':    clase.get('seccion', ''),
                    'seccion_lab':clase.get('seccion_lab', ''),
                    'profesor':   clase.get('profesor', ''),
                }

    # 6. Horas de estudio por materia
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

    # 7. Asignar bloques de estudio (itera solo sobre la grilla dinámica)
    asignadas_dia: dict[str, dict[str, float]] = {d: {} for d in DIAS}

    for dia in DIAS:
        consec: dict[str, int] = {}
        for hora in horas_grilla:
            slot = grilla[dia][hora]
            if slot['tipo'] != 'libre':
                consec = {}
                continue

            elegida = None
            for m in materias_sorted:
                cod = m['materia_codigo']
                if pendiente.get(cod, 0) < 0.5:
                    continue
                if asignadas_dia[dia].get(cod, 0) >= 2:  # max 2 slots/día (~2h)
                    continue
                if consec.get(cod, 0) >= 2:              # max 2 slots consecutivos
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

    # 8. Armar respuesta
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
    dias_json = {dia: [{'hora': h, 'tipo': 'libre'} for h in _BASE_HORAS] for dia in DIAS}
    return {'semana': _lunes_semana(), 'dias': dias_json, 'resumen': {}}
