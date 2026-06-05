from flask import Blueprint, request, session, jsonify
from app.database import get_db
from app.middleware import require_auth
from datetime import date

evaluaciones_bp = Blueprint('evaluaciones', __name__)

TIPOS = ('examen', 'trabajo', 'practica', 'otro')

EV_QUERY = '''
    SELECT e.*, m.nombre AS materia_nombre, m.color AS materia_color
    FROM evaluaciones e
    LEFT JOIN materias m ON e.materia_id = m.id
'''


@evaluaciones_bp.route('', methods=['GET'])
@require_auth
def list_evaluaciones():
    user = session['user']
    conn = get_db()
    rows = conn.execute(
        EV_QUERY + ' WHERE e.usuario_id = ? ORDER BY e.fecha ASC',
        (user['id'],)
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@evaluaciones_bp.route('', methods=['POST'])
@require_auth
def create_evaluacion():
    user = session['user']
    data = request.get_json() or {}

    titulo = data.get('titulo', '').strip()
    materia_id = data.get('materia_id')
    fecha = data.get('fecha', '').strip()
    tipo = data.get('tipo', 'examen')

    if not all([titulo, materia_id, fecha]):
        return jsonify({'error': 'Título, materia y fecha son obligatorios'}), 400
    if tipo not in TIPOS:
        return jsonify({'error': f'Tipo inválido. Use: {", ".join(TIPOS)}'}), 400
    try:
        date.fromisoformat(fecha)
    except ValueError:
        return jsonify({'error': 'Formato de fecha inválido (use YYYY-MM-DD)'}), 400

    conn = get_db()
    materia = conn.execute(
        'SELECT id FROM materias WHERE id = ? AND usuario_id = ?', (materia_id, user['id'])
    ).fetchone()
    if not materia:
        conn.close()
        return jsonify({'error': 'Materia no encontrada o no te pertenece'}), 404

    cur = conn.execute(
        'INSERT INTO evaluaciones (titulo, materia_id, usuario_id, fecha, tipo) VALUES (?, ?, ?, ?, ?)',
        (titulo, materia_id, user['id'], fecha, tipo)
    )
    conn.commit()
    row = conn.execute(EV_QUERY + ' WHERE e.id = ?', (cur.lastrowid,)).fetchone()
    conn.close()
    return jsonify(dict(row)), 201


@evaluaciones_bp.route('/<int:id>', methods=['PUT'])
@require_auth
def update_evaluacion(id):
    user = session['user']
    conn = get_db()
    ev = conn.execute('SELECT * FROM evaluaciones WHERE id = ?', (id,)).fetchone()

    if not ev:
        conn.close()
        return jsonify({'error': 'Evaluación no encontrada'}), 404
    if dict(ev)['usuario_id'] != user['id']:
        conn.close()
        return jsonify({'error': 'Acceso denegado'}), 403

    data = request.get_json() or {}
    e = dict(ev)
    titulo = data.get('titulo', e['titulo']).strip()
    materia_id = data.get('materia_id', e['materia_id'])
    fecha = data.get('fecha', e['fecha'])
    tipo = data.get('tipo', e['tipo'])

    if not titulo:
        conn.close()
        return jsonify({'error': 'El título es obligatorio'}), 400
    if tipo not in TIPOS:
        conn.close()
        return jsonify({'error': 'Tipo inválido'}), 400
    try:
        date.fromisoformat(str(fecha))
    except ValueError:
        conn.close()
        return jsonify({'error': 'Formato de fecha inválido'}), 400

    conn.execute(
        'UPDATE evaluaciones SET titulo=?, materia_id=?, fecha=?, tipo=? WHERE id=?',
        (titulo, materia_id, fecha, tipo, id)
    )
    conn.commit()
    row = conn.execute(EV_QUERY + ' WHERE e.id = ?', (id,)).fetchone()
    conn.close()
    return jsonify(dict(row))


@evaluaciones_bp.route('/<int:id>', methods=['DELETE'])
@require_auth
def delete_evaluacion(id):
    user = session['user']
    conn = get_db()
    ev = conn.execute('SELECT * FROM evaluaciones WHERE id = ?', (id,)).fetchone()

    if not ev:
        conn.close()
        return jsonify({'error': 'Evaluación no encontrada'}), 404
    if dict(ev)['usuario_id'] != user['id']:
        conn.close()
        return jsonify({'error': 'Acceso denegado'}), 403

    conn.execute('DELETE FROM evaluaciones WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Evaluación eliminada'})
