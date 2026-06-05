from flask import Blueprint, jsonify, request, session
from app.database import get_db
from app.middleware import require_auth

perfil_bp = Blueprint('perfil', __name__)


@perfil_bp.route('', methods=['GET'])
@require_auth
def get_perfil():
    uid = session['user']['id']
    db = get_db()
    row = db.execute(
        'SELECT carrera, semestre, grupo FROM perfil_academico WHERE usuario_id = ?', (uid,)
    ).fetchone()
    db.close()
    if not row:
        return jsonify({'perfil': None}), 200
    return jsonify({'perfil': dict(row)}), 200


@perfil_bp.route('', methods=['POST'])
@require_auth
def save_perfil():
    uid = session['user']['id']
    data = request.get_json() or {}
    carrera  = (data.get('carrera') or '').strip()
    semestre = data.get('semestre')
    grupo    = (data.get('grupo') or '').strip()

    if not carrera or semestre is None or not grupo:
        return jsonify({'error': 'carrera, semestre y grupo son requeridos'}), 400

    try:
        semestre = int(semestre)
    except (ValueError, TypeError):
        return jsonify({'error': 'semestre debe ser un número'}), 400

    db = get_db()
    existing = db.execute(
        'SELECT id FROM perfil_academico WHERE usuario_id = ?', (uid,)
    ).fetchone()

    if existing:
        db.execute(
            'UPDATE perfil_academico SET carrera=?, semestre=?, grupo=? WHERE usuario_id=?',
            (carrera, semestre, grupo, uid)
        )
    else:
        db.execute(
            'INSERT INTO perfil_academico (usuario_id, carrera, semestre, grupo) VALUES (?,?,?,?)',
            (uid, carrera, semestre, grupo)
        )
    db.commit()
    db.close()
    return jsonify({'ok': True}), 200


@perfil_bp.route('/carreras', methods=['GET'])
@require_auth
def get_carreras():
    db = get_db()
    rows = db.execute(
        'SELECT DISTINCT carrera FROM horarios_usfx ORDER BY carrera'
    ).fetchall()
    db.close()
    return jsonify([r['carrera'] for r in rows]), 200


@perfil_bp.route('/semestres', methods=['GET'])
@require_auth
def get_semestres():
    carrera = request.args.get('carrera', '')
    db = get_db()
    rows = db.execute(
        'SELECT DISTINCT semestre FROM horarios_usfx WHERE carrera=? ORDER BY semestre',
        (carrera,)
    ).fetchall()
    db.close()
    return jsonify([r['semestre'] for r in rows]), 200


@perfil_bp.route('/grupos', methods=['GET'])
@require_auth
def get_grupos():
    carrera  = request.args.get('carrera', '')
    semestre = request.args.get('semestre', '')
    db = get_db()
    rows = db.execute(
        '''SELECT DISTINCT grupo FROM horarios_usfx
           WHERE carrera=? AND semestre=? ORDER BY grupo''',
        (carrera, semestre)
    ).fetchall()
    db.close()
    return jsonify([r['grupo'] for r in rows]), 200
