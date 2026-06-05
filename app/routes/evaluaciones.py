from datetime import date
from flask import Blueprint, request, session, jsonify
from app.database import get_db
from app.middleware import require_auth

evaluaciones_bp = Blueprint('evaluaciones', __name__)


@evaluaciones_bp.route('', methods=['GET'])
@require_auth
def get_evaluaciones():
    uid = session['user']['id']
    db = get_db()
    rows = db.execute(
        '''SELECT * FROM evaluaciones
           WHERE usuario_id=? ORDER BY fecha ASC''',
        (uid,)
    ).fetchall()
    db.close()
    return jsonify([dict(r) for r in rows]), 200


@evaluaciones_bp.route('', methods=['POST'])
@require_auth
def create_evaluacion():
    uid = session['user']['id']
    data = request.get_json() or {}

    materia_codigo = (data.get('materia_codigo') or '').strip()
    materia_nombre = (data.get('materia_nombre') or '').strip()
    titulo         = (data.get('titulo') or '').strip()
    fecha          = (data.get('fecha') or '').strip()
    tipo           = (data.get('tipo') or 'examen').strip()

    if not all([materia_codigo, materia_nombre, titulo, fecha]):
        return jsonify({'error': 'materia_codigo, materia_nombre, titulo y fecha son requeridos'}), 400
    if tipo not in ('examen', 'trabajo', 'practica', 'otro'):
        return jsonify({'error': 'tipo inválido'}), 400
    try:
        date.fromisoformat(fecha)
    except ValueError:
        return jsonify({'error': 'fecha inválida (YYYY-MM-DD)'}), 400

    db = get_db()
    cur = db.execute(
        '''INSERT INTO evaluaciones (usuario_id, materia_codigo, materia_nombre, titulo, fecha, tipo)
           VALUES (?,?,?,?,?,?)''',
        (uid, materia_codigo, materia_nombre, titulo, fecha, tipo)
    )
    db.commit()
    row = db.execute('SELECT * FROM evaluaciones WHERE id=?', (cur.lastrowid,)).fetchone()
    db.close()
    return jsonify(dict(row)), 201


@evaluaciones_bp.route('/<int:eid>', methods=['PUT'])
@require_auth
def update_evaluacion(eid):
    uid = session['user']['id']
    db = get_db()
    row = db.execute(
        'SELECT * FROM evaluaciones WHERE id=? AND usuario_id=?', (eid, uid)
    ).fetchone()
    if not row:
        db.close()
        return jsonify({'error': 'No encontrado'}), 404

    data           = request.get_json() or {}
    materia_codigo = (data.get('materia_codigo') or row['materia_codigo']).strip()
    materia_nombre = (data.get('materia_nombre') or row['materia_nombre']).strip()
    titulo         = (data.get('titulo') or row['titulo']).strip()
    fecha          = (data.get('fecha') or row['fecha']).strip()
    tipo           = (data.get('tipo') or row['tipo']).strip()

    if tipo not in ('examen', 'trabajo', 'practica', 'otro'):
        db.close()
        return jsonify({'error': 'tipo inválido'}), 400
    try:
        date.fromisoformat(fecha)
    except ValueError:
        db.close()
        return jsonify({'error': 'fecha inválida (YYYY-MM-DD)'}), 400

    db.execute(
        '''UPDATE evaluaciones
           SET materia_codigo=?, materia_nombre=?, titulo=?, fecha=?, tipo=?
           WHERE id=?''',
        (materia_codigo, materia_nombre, titulo, fecha, tipo, eid)
    )
    db.commit()
    updated = db.execute('SELECT * FROM evaluaciones WHERE id=?', (eid,)).fetchone()
    db.close()
    return jsonify(dict(updated)), 200


@evaluaciones_bp.route('/<int:eid>', methods=['DELETE'])
@require_auth
def delete_evaluacion(eid):
    uid = session['user']['id']
    db = get_db()
    row = db.execute(
        'SELECT id FROM evaluaciones WHERE id=? AND usuario_id=?', (eid, uid)
    ).fetchone()
    if not row:
        db.close()
        return jsonify({'error': 'No encontrado'}), 404

    db.execute('DELETE FROM evaluaciones WHERE id=?', (eid,))
    db.commit()
    db.close()
    return jsonify({'ok': True}), 200
