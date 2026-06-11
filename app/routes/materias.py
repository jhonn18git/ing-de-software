import json
from flask import Blueprint, request, session, jsonify
from app.database import get_db
from app.middleware import require_auth
from app.algoritmo import get_horario_clases

materias_bp = Blueprint('materias', __name__)

COLORES_DEFAULT = [
    '#e53e3e', '#dd6b20', '#d69e2e', '#38a169', '#3182ce',
    '#805ad5', '#d53f8c', '#00b5d8', '#2d3748', '#744210',
]


@materias_bp.route('/api/materias', methods=['GET'])
@require_auth
def get_materias():
    uid = session['user']['id']
    db  = get_db()
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
    Genera el horario de clases óptimo (armar_horario_clases) y sincroniza
    las materias del estudiante.  Preserva dificultad/horas/color de
    materias que el usuario ya tenía configuradas.
    """
    uid = session['user']['id']
    db  = get_db()

    perfil = db.execute(
        'SELECT carrera, semestre FROM perfil_academico WHERE usuario_id=?',
        (uid,)
    ).fetchone()
    if not perfil:
        db.close()
        return jsonify({'error': 'Configura tu perfil académico primero'}), 400

    carrera  = perfil['carrera']
    semestre = perfil['semestre']

    # ── 1. Obtener horario de clases fijo por carrera+semestre ───────────────
    horario_clases = get_horario_clases(carrera, semestre, db)

    if not horario_clases:
        db.close()
        return jsonify({
            'error': f"Sin materias disponibles para {carrera} semestre {semestre}."
        }), 400

    # ── 2. Guardar horario de clases en horario_clases_usuario ────────────────
    horario_json = json.dumps(horario_clases, ensure_ascii=False)
    exists = db.execute(
        'SELECT id FROM horario_clases_usuario WHERE usuario_id=?', (uid,)
    ).fetchone()
    if exists:
        db.execute(
            'UPDATE horario_clases_usuario SET horario_json=?, generado_at=CURRENT_TIMESTAMP WHERE usuario_id=?',
            (horario_json, uid)
        )
    else:
        db.execute(
            'INSERT INTO horario_clases_usuario (usuario_id, horario_json) VALUES (?,?)',
            (uid, horario_json)
        )

    # ── 3. Preservar config previa (dificultad, horas, color) ─────────────────
    existentes = {
        r['materia_codigo']: dict(r) for r in db.execute(
            'SELECT materia_codigo, dificultad, horas_semana, color FROM materias_estudiante WHERE usuario_id=?',
            (uid,)
        ).fetchall()
    }

    codigos_nuevos = {e['materia_codigo'] for e in horario_clases}

    # Eliminar materias que ya no están en el plan del semestre actual
    for viejo in list(existentes):
        if viejo not in codigos_nuevos:
            db.execute(
                'DELETE FROM materias_estudiante WHERE usuario_id=? AND materia_codigo=?',
                (uid, viejo)
            )

    # Insertar materias nuevas
    insertadas = 0
    for i, entry in enumerate(horario_clases):
        codigo = entry['materia_codigo']
        nombre = entry.get('materia_nombre') or codigo
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
    return jsonify({
        'insertadas':     insertadas,
        'materias':       [dict(r) for r in rows],
        'horario_clases': horario_clases,
    }), 200


@materias_bp.route('/api/materias/<int:mid>', methods=['PUT'])
@require_auth
def update_materia(mid):
    uid  = session['user']['id']
    data = request.get_json() or {}
    db   = get_db()

    row = db.execute(
        'SELECT * FROM materias_estudiante WHERE id=? AND usuario_id=?', (mid, uid)
    ).fetchone()
    if not row:
        db.close()
        return jsonify({'error': 'No encontrado'}), 404

    dificultad   = data.get('dificultad',   row['dificultad'])
    horas_semana = data.get('horas_semana', row['horas_semana'])
    color        = data.get('color',        row['color'])

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
    db  = get_db()
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
