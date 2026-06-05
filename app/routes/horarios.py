import json
from flask import Blueprint, session, jsonify
from app.database import get_db
from app.middleware import require_auth
from app.algoritmo import generar_horario
from app.carreras import get_carreras_buscar

horario_bp = Blueprint('horario', __name__)


@horario_bp.route('/api/horario', methods=['GET'])
@require_auth
def get_horario():
    uid = session['user']['id']
    db = get_db()
    row = db.execute(
        'SELECT horario_json, generado_at FROM horario_estudio WHERE usuario_id=?',
        (uid,)
    ).fetchone()
    db.close()
    if not row:
        return jsonify({'horario': None}), 200
    return jsonify({
        'horario':     json.loads(row['horario_json']),
        'generado_at': row['generado_at'],
    }), 200


@horario_bp.route('/api/horario/generar', methods=['POST'])
@require_auth
def generar():
    uid = session['user']['id']
    db = get_db()

    # Verificar que tiene materias
    count = db.execute(
        'SELECT COUNT(*) FROM materias_estudiante WHERE usuario_id=?', (uid,)
    ).fetchone()[0]
    if count == 0:
        db.close()
        return jsonify({'error': 'No tienes materias registradas. Sincroniza desde tu perfil.'}), 400

    horario = generar_horario(uid, db)
    horario_str = json.dumps(horario, ensure_ascii=False)

    existing = db.execute(
        'SELECT id FROM horario_estudio WHERE usuario_id=?', (uid,)
    ).fetchone()
    if existing:
        db.execute(
            'UPDATE horario_estudio SET horario_json=?, generado_at=CURRENT_TIMESTAMP WHERE usuario_id=?',
            (horario_str, uid)
        )
    else:
        db.execute(
            'INSERT INTO horario_estudio (usuario_id, horario_json) VALUES (?,?)',
            (uid, horario_str)
        )
    db.commit()

    row = db.execute(
        'SELECT generado_at FROM horario_estudio WHERE usuario_id=?', (uid,)
    ).fetchone()
    db.close()
    return jsonify({'horario': horario, 'generado_at': row['generado_at']}), 200


@horario_bp.route('/api/horario/clases', methods=['GET'])
@require_auth
def get_clases():
    """Devuelve las clases USFX del usuario según su perfil académico."""
    uid = session['user']['id']
    db = get_db()
    perfil = db.execute(
        'SELECT carrera, semestre, grupo FROM perfil_academico WHERE usuario_id=?',
        (uid,)
    ).fetchone()
    if not perfil:
        db.close()
        return jsonify({'clases': [], 'perfil': None}), 200

    carreras_buscar = get_carreras_buscar(perfil['carrera'])
    placeholders = ','.join('?' * len(carreras_buscar))

    rows = db.execute(
        f'''SELECT dia, hora_inicio, hora_fin, materia_codigo, materia_nombre, aula
           FROM horarios_usfx
           WHERE carrera IN ({placeholders}) AND semestre=? AND grupo=?
           ORDER BY dia, hora_inicio''',
        (*carreras_buscar, perfil['semestre'], perfil['grupo'])
    ).fetchall()
    db.close()
    return jsonify({'clases': [dict(r) for r in rows], 'perfil': dict(perfil)}), 200
