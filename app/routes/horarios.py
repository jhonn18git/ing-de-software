import json
from flask import Blueprint, session, jsonify
from app.database import get_db
from app.middleware import require_auth
from app.algoritmo import generar_horario

horario_bp = Blueprint('horario', __name__)


@horario_bp.route('/api/horario', methods=['GET'])
@require_auth
def get_horario():
    uid = session['user']['id']
    db  = get_db()
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
    db  = get_db()

    count = db.execute(
        'SELECT COUNT(*) FROM materias_estudiante WHERE usuario_id=?', (uid,)
    ).fetchone()[0]
    if count == 0:
        db.close()
        return jsonify({'error': 'No tienes materias registradas. Sincroniza desde tu perfil.'}), 400

    horario     = generar_horario(uid, db)
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
    """Devuelve el horario de clases armado del usuario (desde horario_clases_usuario)."""
    uid = session['user']['id']
    db  = get_db()
    row = db.execute(
        'SELECT horario_json, generado_at FROM horario_clases_usuario WHERE usuario_id=?',
        (uid,)
    ).fetchone()
    perfil = db.execute(
        'SELECT carrera, semestre FROM perfil_academico WHERE usuario_id=?', (uid,)
    ).fetchone()
    db.close()

    if not row:
        return jsonify({'clases': [], 'perfil': dict(perfil) if perfil else None}), 200

    try:
        clases = json.loads(row['horario_json'])
    except Exception:
        clases = []

    return jsonify({
        'clases':      clases,
        'perfil':      dict(perfil) if perfil else None,
        'generado_at': row['generado_at'],
    }), 200
