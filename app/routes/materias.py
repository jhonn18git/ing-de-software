from flask import Blueprint, request, session, jsonify
from app.database import get_db
from app.middleware import require_auth
from app.carreras import get_carreras_buscar
from app.plan_estudios import PLAN_ESTUDIOS

materias_bp = Blueprint('materias', __name__)

COLORES_DEFAULT = [
    '#e53e3e', '#dd6b20', '#d69e2e', '#38a169', '#3182ce',
    '#805ad5', '#d53f8c', '#00b5d8', '#2d3748', '#744210',
]


@materias_bp.route('/api/materias', methods=['GET'])
@require_auth
def get_materias():
    uid = session['user']['id']
    db = get_db()
    rows = db.execute(
        'SELECT * FROM materias_estudiante WHERE usuario_id=? ORDER BY materia_nombre',
        (uid,)
    ).fetchall()
    db.close()
    return jsonify([dict(r) for r in rows]), 200


@materias_bp.route('/api/materias/sync', methods=['POST'])
@require_auth
def sync_materias():
    """
    Re-sincroniza las materias del estudiante desde horarios_usfx filtradas
    por el plan de estudios oficial (PLAN_ESTUDIOS). Preserva dificultad/horas/color
    de materias que el usuario ya tenía configuradas.
    """
    uid = session['user']['id']
    db = get_db()

    perfil = db.execute(
        'SELECT carrera, semestre, grupo FROM perfil_academico WHERE usuario_id=?',
        (uid,)
    ).fetchone()
    if not perfil:
        db.close()
        return jsonify({'error': 'Configura tu perfil académico primero'}), 400

    carrera  = perfil['carrera']
    semestre = perfil['semestre']
    grupo    = perfil['grupo']

    # --- 1. Buscar materias en horarios_usfx (con carreras relacionadas) ---
    carreras_buscar = get_carreras_buscar(carrera)
    placeholders    = ','.join('?' * len(carreras_buscar))

    usfx = db.execute(
        f'''SELECT DISTINCT materia_codigo, materia_nombre
            FROM horarios_usfx
            WHERE carrera IN ({placeholders}) AND semestre=? AND grupo=?
            ORDER BY materia_codigo''',
        (*carreras_buscar, semestre, grupo)
    ).fetchall()

    if not usfx:
        usfx = db.execute(
            f'''SELECT DISTINCT materia_codigo, materia_nombre
                FROM horarios_usfx
                WHERE carrera IN ({placeholders}) AND semestre=?
                ORDER BY materia_codigo''',
            (*carreras_buscar, semestre)
        ).fetchall()

    if not usfx:
        db.close()
        return jsonify({
            'error': (
                f"Sin materias para carrera='{carrera}' "
                f"semestre={semestre} grupo='{grupo}'. "
                f"Verifica tu perfil académico."
            )
        }), 400

    # --- 2. Filtrar por plan de estudios oficial ---
    codigos_plan = set(PLAN_ESTUDIOS.get(carrera, {}).get(semestre, []))
    if codigos_plan:
        usfx_filtrado = [r for r in usfx if r['materia_codigo'] in codigos_plan]
        # Si el filtro deja todo vacío (datos de horarios_usfx incompletos), usar sin filtro
        if usfx_filtrado:
            usfx = usfx_filtrado
            print(f"DEBUG sync - plan aplicado: {len(usfx)} materias para {carrera} sem {semestre}")
        else:
            print(f"DEBUG sync - plan vacío tras filtro, usando sin filtro ({len(usfx)} materias)")
    else:
        print(f"DEBUG sync - sin plan para '{carrera}' sem {semestre}, sin filtro")

    # --- 3. Preservar configuración previa (dificultad, horas, color) ---
    existentes = {
        r['materia_codigo']: dict(r) for r in db.execute(
            'SELECT materia_codigo, dificultad, horas_semana, color FROM materias_estudiante WHERE usuario_id=?',
            (uid,)
        ).fetchall()
    }

    # Reemplazar todas las materias: borrar las que ya no corresponden al semestre actual
    codigos_nuevos = {r['materia_codigo'] for r in usfx}
    for codigo_viejo in list(existentes.keys()):
        if codigo_viejo not in codigos_nuevos:
            db.execute(
                'DELETE FROM materias_estudiante WHERE usuario_id=? AND materia_codigo=?',
                (uid, codigo_viejo)
            )

    # --- 4. Insertar materias nuevas, preservando config de las ya existentes ---
    insertadas = 0
    for i, row in enumerate(usfx):
        codigo = row['materia_codigo']
        nombre = row['materia_nombre'] or codigo

        if codigo in existentes:
            continue

        color = COLORES_DEFAULT[i % len(COLORES_DEFAULT)]
        db.execute(
            '''INSERT OR IGNORE INTO materias_estudiante
               (usuario_id, materia_codigo, materia_nombre, dificultad, horas_semana, color)
               VALUES (?, ?, ?, 3, 2, ?)''',
            (uid, codigo, nombre, color)
        )
        insertadas += 1

    db.commit()

    rows = db.execute(
        'SELECT * FROM materias_estudiante WHERE usuario_id=? ORDER BY materia_nombre',
        (uid,)
    ).fetchall()
    db.close()
    return jsonify({'insertadas': insertadas, 'materias': [dict(r) for r in rows]}), 200


@materias_bp.route('/api/materias/<int:mid>', methods=['PUT'])
@require_auth
def update_materia(mid):
    uid = session['user']['id']
    data = request.get_json() or {}

    m = None
    db = get_db()
    row = db.execute(
        'SELECT * FROM materias_estudiante WHERE id=? AND usuario_id=?', (mid, uid)
    ).fetchone()
    if not row:
        db.close()
        return jsonify({'error': 'No encontrado'}), 404

    dificultad  = data.get('dificultad', row['dificultad'])
    horas_semana = data.get('horas_semana', row['horas_semana'])
    color       = data.get('color', row['color'])

    try:
        dificultad   = int(dificultad)
        horas_semana = int(horas_semana)
    except (ValueError, TypeError):
        db.close()
        return jsonify({'error': 'Valores inválidos'}), 400

    if not (1 <= dificultad <= 5):
        db.close()
        return jsonify({'error': 'dificultad debe ser 1-5'}), 400
    if not (1 <= horas_semana <= 20):
        db.close()
        return jsonify({'error': 'horas_semana debe ser 1-20'}), 400

    db.execute(
        'UPDATE materias_estudiante SET dificultad=?, horas_semana=?, color=? WHERE id=?',
        (dificultad, horas_semana, color, mid)
    )
    db.commit()
    updated = db.execute('SELECT * FROM materias_estudiante WHERE id=?', (mid,)).fetchone()
    db.close()
    return jsonify(dict(updated)), 200


@materias_bp.route('/api/materias/<int:mid>', methods=['DELETE'])
@require_auth
def delete_materia(mid):
    uid = session['user']['id']
    db = get_db()
    row = db.execute(
        'SELECT id FROM materias_estudiante WHERE id=? AND usuario_id=?', (mid, uid)
    ).fetchone()
    if not row:
        db.close()
        return jsonify({'error': 'No encontrado'}), 404

    db.execute('DELETE FROM materias_estudiante WHERE id=?', (mid,))
    db.commit()
    db.close()
    return jsonify({'ok': True}), 200
