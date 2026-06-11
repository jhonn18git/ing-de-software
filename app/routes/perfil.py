from flask import Blueprint, jsonify, request, session
from app.database import get_db
from app.middleware import require_auth
from app.plan_estudios import PLAN_ESTUDIOS

perfil_bp = Blueprint('perfil', __name__)


@perfil_bp.route('/api/perfil', methods=['GET'])
@require_auth
def get_perfil():
    uid = session['user']['id']
    db  = get_db()
    row = db.execute(
        'SELECT carrera, semestre FROM perfil_academico WHERE usuario_id=?', (uid,)
    ).fetchone()
    db.close()
    if not row:
        return jsonify({'perfil': None}), 200
    return jsonify({'perfil': dict(row)}), 200


@perfil_bp.route('/api/perfil', methods=['POST'])
@require_auth
def save_perfil():
    uid  = session['user']['id']
    data = request.get_json() or {}

    carrera  = (data.get('carrera') or '').strip()
    semestre = data.get('semestre')

    if not carrera or semestre is None:
        return jsonify({'error': 'carrera y semestre son requeridos'}), 400

    try:
        semestre = int(semestre)
    except (ValueError, TypeError):
        return jsonify({'error': 'semestre debe ser un número'}), 400

    db = get_db()
    existing = db.execute(
        'SELECT id FROM perfil_academico WHERE usuario_id=?', (uid,)
    ).fetchone()

    if existing:
        db.execute(
            'UPDATE perfil_academico SET carrera=?, semestre=?, grupo=? WHERE usuario_id=?',
            (carrera, semestre, '', uid)
        )
    else:
        db.execute(
            'INSERT INTO perfil_academico (usuario_id, carrera, semestre, grupo) VALUES (?,?,?,?)',
            (uid, carrera, semestre, '')
        )
    db.commit()
    db.close()
    return jsonify({'ok': True}), 200


@perfil_bp.route('/api/perfil/carreras', methods=['GET'])
@require_auth
def get_carreras():
    return jsonify(sorted(PLAN_ESTUDIOS.keys())), 200


@perfil_bp.route('/api/perfil/semestres', methods=['GET'])
@require_auth
def get_semestres():
    carrera = request.args.get('carrera', '').strip()
    plan    = PLAN_ESTUDIOS.get(carrera, {})
    semestres = sorted(s for s, codigos in plan.items() if codigos)
    if not semestres:
        semestres = list(range(1, 11))
    return jsonify(semestres), 200
