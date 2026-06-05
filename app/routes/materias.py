from flask import Blueprint, request, session, jsonify
from app.database import get_db
from app.middleware import require_auth

materias_bp = Blueprint('materias', __name__)


@materias_bp.route('', methods=['GET'])
@require_auth
def list_materias():
    user = session['user']
    conn = get_db()
    rows = conn.execute(
        'SELECT * FROM materias WHERE usuario_id = ? ORDER BY nombre',
        (user['id'],)
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@materias_bp.route('', methods=['POST'])
@require_auth
def create_materia():
    user = session['user']
    data = request.get_json() or {}

    nombre = data.get('nombre', '').strip()
    dificultad = data.get('dificultad')
    color = data.get('color', '#3182ce').strip() or '#3182ce'

    if not nombre:
        return jsonify({'error': 'El nombre es obligatorio'}), 400
    if not isinstance(dificultad, int) or not (1 <= dificultad <= 5):
        return jsonify({'error': 'La dificultad debe ser un número entre 1 y 5'}), 400

    conn = get_db()
    cur = conn.execute(
        'INSERT INTO materias (nombre, dificultad, color, usuario_id) VALUES (?, ?, ?, ?)',
        (nombre, dificultad, color, user['id'])
    )
    conn.commit()
    row = conn.execute('SELECT * FROM materias WHERE id = ?', (cur.lastrowid,)).fetchone()
    conn.close()
    return jsonify(dict(row)), 201


@materias_bp.route('/<int:id>', methods=['PUT'])
@require_auth
def update_materia(id):
    user = session['user']
    conn = get_db()
    row = conn.execute('SELECT * FROM materias WHERE id = ?', (id,)).fetchone()

    if not row:
        conn.close()
        return jsonify({'error': 'Materia no encontrada'}), 404
    if dict(row)['usuario_id'] != user['id']:
        conn.close()
        return jsonify({'error': 'Acceso denegado'}), 403

    data = request.get_json() or {}
    m = dict(row)
    nombre = data.get('nombre', m['nombre']).strip()
    dificultad = data.get('dificultad', m['dificultad'])
    color = data.get('color', m['color']).strip() or m['color']

    if not nombre:
        conn.close()
        return jsonify({'error': 'El nombre es obligatorio'}), 400
    if not isinstance(dificultad, int) or not (1 <= dificultad <= 5):
        conn.close()
        return jsonify({'error': 'La dificultad debe ser entre 1 y 5'}), 400

    conn.execute(
        'UPDATE materias SET nombre=?, dificultad=?, color=? WHERE id=?',
        (nombre, dificultad, color, id)
    )
    conn.commit()
    updated = conn.execute('SELECT * FROM materias WHERE id = ?', (id,)).fetchone()
    conn.close()
    return jsonify(dict(updated))


@materias_bp.route('/<int:id>', methods=['DELETE'])
@require_auth
def delete_materia(id):
    user = session['user']
    conn = get_db()
    row = conn.execute('SELECT * FROM materias WHERE id = ?', (id,)).fetchone()

    if not row:
        conn.close()
        return jsonify({'error': 'Materia no encontrada'}), 404
    if dict(row)['usuario_id'] != user['id']:
        conn.close()
        return jsonify({'error': 'Acceso denegado'}), 403

    conn.execute('DELETE FROM materias WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Materia eliminada'})
