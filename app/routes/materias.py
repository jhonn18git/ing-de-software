from flask import Blueprint, request, session, jsonify
from app.database import get_db
from app.middleware import require_auth
from app.carreras import get_carreras_buscar

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
    Importa las materias del estudiante desde horarios_usfx
    según su perfil académico (carrera/semestre/grupo).
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

    print(f"DEBUG sync - perfil: carrera='{perfil['carrera']}' semestre={perfil['semestre']} grupo='{perfil['grupo']}'")

    total_usfx = db.execute("SELECT COUNT(*) FROM horarios_usfx").fetchone()[0]
    print(f"DEBUG sync - total en horarios_usfx: {total_usfx}")

    carreras_buscar = get_carreras_buscar(perfil['carrera'])
    placeholders = ','.join('?' * len(carreras_buscar))

    usfx = db.execute(
        f'''SELECT DISTINCT materia_codigo, materia_nombre
           FROM horarios_usfx
           WHERE carrera IN ({placeholders}) AND semestre=? AND grupo=?
           ORDER BY materia_codigo''',
        (*carreras_buscar, perfil['semestre'], perfil['grupo'])
    ).fetchall()
    print(f"DEBUG sync - carreras={carreras_buscar} materias={[r['materia_codigo'] for r in usfx]}")

    if not usfx:
        # Fallback sin grupo: el nombre del grupo puede no coincidir exactamente
        usfx = db.execute(
            f'''SELECT DISTINCT materia_codigo, materia_nombre
               FROM horarios_usfx
               WHERE carrera IN ({placeholders}) AND semestre=?
               ORDER BY materia_codigo''',
            (*carreras_buscar, perfil['semestre'])
        ).fetchall()
        print(f"DEBUG sync (sin grupo) - materias={[r['materia_codigo'] for r in usfx]}")

    if not usfx:
        db.close()
        return jsonify({
            'error': (
                f"Sin materias para carrera='{perfil['carrera']}' "
                f"(buscado en: {carreras_buscar}) "
                f"semestre={perfil['semestre']} grupo='{perfil['grupo']}'. "
                f"Total en DB: {total_usfx}"
            )
        }), 400

    # Obtener colores existentes del usuario para no perder configuración
    existentes = {
        r['materia_codigo']: dict(r) for r in db.execute(
            'SELECT materia_codigo, dificultad, horas_semana, color FROM materias_estudiante WHERE usuario_id=?',
            (uid,)
        ).fetchall()
    }

    insertadas = 0
    for i, row in enumerate(usfx):
        codigo = row['materia_codigo']
        nombre = row['materia_nombre'] or codigo
        color  = COLORES_DEFAULT[i % len(COLORES_DEFAULT)]

        if codigo in existentes:
            # No sobreescribir configuración existente
            continue

        db.execute(
            '''INSERT OR IGNORE INTO materias_estudiante
               (usuario_id, materia_codigo, materia_nombre, dificultad, horas_semana, color)
               VALUES (?, ?, ?, 3, 2, ?)''',
            (uid, codigo, nombre, color)
        )
        insertadas += 1

    db.commit()

    # Retornar lista actualizada
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
