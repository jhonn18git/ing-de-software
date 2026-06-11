import json
import time
import unicodedata
from datetime import date, timedelta

DIAS       = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado']
_BASE_HORAS = [f'{h:02d}:00' for h in range(7, 22)]  # 07:00 … 21:00 (1h slots)

# Mapa defensivo: cualquier variante de dia → forma canónica (sin tilde, minúscula)
_DIA_CANON = {}
for _d in DIAS:
    _nfd = unicodedata.normalize('NFD', _d)
    _plain = ''.join(c for c in _nfd if unicodedata.category(c) != 'Mn')
    _DIA_CANON[_d]         = _d
    _DIA_CANON[_d.upper()] = _d
    _DIA_CANON[_d.capitalize()] = _d
    _DIA_CANON[_plain]     = _d
    _DIA_CANON[_plain.upper()] = _d

# Casos con tilde que pueden llegar del CSV o de datos viejos
_DIA_CANON.update({
    'miércoles': 'miercoles', 'Miércoles': 'miercoles', 'MIÉRCOLES': 'miercoles',
    'sábado':    'sabado',    'Sábado':    'sabado',    'SÁBADO':    'sabado',
})


def _norm_dia(dia: str) -> str:
    """Normaliza variantes de día → canónica sin tilde y en minúsculas."""
    return _DIA_CANON.get(dia, dia.lower().strip())


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
            bloque_key = (_norm_dia(r['dia']), r['hora_inicio'])
            if bloque_key not in secciones[sec]['_seen']:
                secciones[sec]['_seen'].add(bloque_key)
                secciones[sec]['bloques'].append({
                    'dia':         _norm_dia(r['dia']),
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
# HORARIO DE CLASES FIJO POR CARRERA+SEMESTRE (sin backtracking)
# -----------------------------------------------------------------------

def get_horario_clases(carrera: str, semestre: int, db) -> list:
    """
    Returns fixed class schedule for carrera+semestre.
    Groups DB rows by materia_codigo, returns blocks as-is.
    For each materia: if GL* and GT* sections exist with same professor,
    pick FIRST GL (by day order) + matching GT.
    If only G-type or single-type sections: take all blocks for
    the section with the most matching professor blocks.
    """
    from app.carreras import get_carreras_buscar
    from collections import defaultdict

    carreras_buscar = get_carreras_buscar(carrera)
    placeholders = ','.join('?' * len(carreras_buscar))

    rows = db.execute(
        f'''SELECT materia_codigo, materia_nombre, seccion, profesor,
                   dia, hora_inicio, hora_fin, aula
            FROM horarios_usfx
            WHERE carrera IN ({placeholders}) AND semestre=?
            ORDER BY materia_codigo, dia, hora_inicio''',
        (*carreras_buscar, semestre)
    ).fetchall()

    if not rows:
        return []

    # Group by materia
    mat_secs = defaultdict(lambda: defaultdict(list))  # {codigo: {seccion: [blocks]}}
    mat_names = {}
    mat_profs = {}

    DAY_ORDER = {d: i for i, d in enumerate(DIAS)}

    for r in rows:
        cod = r['materia_codigo']
        sec = r['seccion']
        mat_names[cod] = r['materia_nombre'] or cod
        mat_profs.setdefault(cod, {})
        mat_profs[cod][sec] = r['profesor'] or ''
        mat_secs[cod][sec].append({
            'dia': _norm_dia(r['dia']),
            'hora_inicio': r['hora_inicio'],
            'hora_fin': r['hora_fin'],
            'aula': r['aula'] or '',
        })

    result = []

    for cod, secciones in mat_secs.items():
        gl_secs = {s: blks for s, blks in secciones.items()
                   if s.upper().startswith('GL')}
        gt_secs = {s: blks for s, blks in secciones.items()
                   if s.upper().startswith('GT')}
        g_secs  = {s: blks for s, blks in secciones.items()
                   if not s.upper().startswith('GL') and not s.upper().startswith('GT')}

        chosen_secs = {}

        if gl_secs and gt_secs:
            # Find GL+GT pairs with same professor; prefer lowest-numbered GL section
            paired = {}
            for sg in sorted(gl_secs.keys()):
                bg = gl_secs[sg]
                prof_g = mat_profs[cod].get(sg, '')
                for st in sorted(gt_secs.keys()):
                    prof_t = mat_profs[cod].get(st, '')
                    if prof_g and prof_t and prof_g.split('.')[0] == prof_t.split('.')[0]:
                        # Same professor - valid pair; first match wins (sorted order)
                        if sg not in paired:
                            paired[sg] = (sg, st)

            if paired:
                # Pick the pair with the lowest-numbered GL section
                best_gl = sorted(paired.keys())[0]
                best = paired[best_gl]
                chosen_secs[best[0]] = gl_secs[best[0]]
                chosen_secs[best[1]] = gt_secs[best[1]]
            else:
                # No same-prof pair, pick first GL + first GT by seccion name
                first_gl = sorted(gl_secs.keys())[0]
                first_gt = sorted(gt_secs.keys())[0]
                chosen_secs[first_gl] = gl_secs[first_gl]
                chosen_secs[first_gt] = gt_secs[first_gt]

        elif gl_secs:
            # Only GL sections: pick first by seccion name
            first_gl = sorted(gl_secs.keys())[0]
            chosen_secs[first_gl] = gl_secs[first_gl]

        elif g_secs and gt_secs:
            # G-type + GT-type: treat as teo/lab pair if same professor
            # (handles G1 + GT1 with same prof, like SIS256)
            paired_g = {}
            for sg in sorted(g_secs.keys()):
                prof_g = mat_profs[cod].get(sg, '')
                for st in sorted(gt_secs.keys()):
                    prof_t = mat_profs[cod].get(st, '')
                    if prof_g and prof_t and prof_g.split('.')[0] == prof_t.split('.')[0]:
                        if sg not in paired_g:
                            paired_g[sg] = (sg, st)

            if paired_g:
                best_g = sorted(paired_g.keys())[0]
                best = paired_g[best_g]
                chosen_secs[best[0]] = g_secs[best[0]]
                chosen_secs[best[1]] = gt_secs[best[1]]
            else:
                # No same-prof pair, pick first G + first GT
                first_g = sorted(g_secs.keys())[0]
                first_gt = sorted(gt_secs.keys())[0]
                chosen_secs[first_g] = g_secs[first_g]
                chosen_secs[first_gt] = gt_secs[first_gt]

        elif g_secs:
            # G-type sections only: group by seccion, pick the seccion that appears most days
            # (handles G1 appearing Tue+Wed for SIS315)
            for sec, blks in sorted(g_secs.items()):
                chosen_secs[sec] = blks
            # If multiple G secs, keep only those with same professor as most common
            if len(chosen_secs) > 1:
                # Find professor with most blocks
                prof_count = defaultdict(int)
                for sec, blks in chosen_secs.items():
                    prof_count[mat_profs[cod].get(sec, '')] += len(blks)
                top_prof = max(prof_count, key=prof_count.get)
                chosen_secs = {s: b for s, b in chosen_secs.items()
                               if mat_profs[cod].get(s, '') == top_prof}

        else:
            # GT only (rare) - pick first
            if gt_secs:
                first_gt = sorted(gt_secs.keys())[0]
                chosen_secs[first_gt] = gt_secs[first_gt]

        # Flatten chosen sections into blocks list
        all_blocks = []
        seen_keys = set()
        # Determine display seccion/seccion_lab
        sec_list = sorted(chosen_secs.keys())
        main_sec = sec_list[0] if sec_list else ''
        sec_lab  = sec_list[1] if len(sec_list) > 1 else ''

        for sec, blks in chosen_secs.items():
            for b in blks:
                key = (b['dia'], b['hora_inicio'])
                if key not in seen_keys:
                    seen_keys.add(key)
                    all_blocks.append(dict(b, bloque_sec=sec))

        result.append({
            'materia_codigo': cod,
            'materia_nombre': mat_names[cod],
            'seccion':     main_sec,
            'seccion_lab': sec_lab,
            'profesor':    mat_profs[cod].get(main_sec, ''),
            'bloques':     all_blocks,
        })

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
                    key = (_norm_dia(b['dia']), b['hora_inicio'])
                    if b.get('bloque_sec', sec) == sec_lab and sec_lab:
                        lab_slots.add(key)
                    else:
                        teo_slots.add(key)
                for bloque in entry.get('bloques', []):
                    key = (_norm_dia(bloque['dia']), bloque['hora_inicio'])
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
                        'dia':            _norm_dia(bloque['dia']),
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
                if asignadas_dia[dia].get(cod, 0) >= 1:  # max 1 slot/día → fuerza distribucion semanal
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
