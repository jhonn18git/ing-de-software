from flask import Blueprint, request, session, jsonify
from app.database import get_db
from app.middleware import require_auth, require_admin

usuarios_bp = Blueprint('usuarios', __name__)

SAFE_FIELDS = 'id, name, username, email, image, rol, created_at, updated_at'


@usuarios_bp.route('/api/usuarios', methods=['GET'])
@require_admin
def list_users():
    conn = get_db()
    users = conn.execute(f'SELECT {SAFE_FIELDS} FROM users').fetchall()
    conn.close()
    return jsonify([dict(u) for u in users])


@usuarios_bp.route('/api/usuarios/<int:id>', methods=['GET'])
@require_auth
def get_user(id):
    current = session['user']
    if current['rol'] != 'admin' and current['id'] != id:
        return jsonify({'error': 'Acceso denegado'}), 403

    conn = get_db()
    user = conn.execute(f'SELECT {SAFE_FIELDS} FROM users WHERE id = ?', (id,)).fetchone()
    conn.close()

    if not user:
        return jsonify({'error': 'Usuario no encontrado'}), 404
    return jsonify(dict(user))


@usuarios_bp.route('/api/usuarios', methods=['POST'])
@require_admin
def create_user():
    data     = request.get_json() or {}
    name     = data.get('name', '').strip()
    username = data.get('username', '').strip()
    email    = data.get('email', '').strip()
    password = data.get('password', '')

    if not all([name, username, email, password]):
        return jsonify({'error': 'Todos los campos son obligatorios'}), 400

    conn = get_db()
    try:
        cursor = conn.execute(
            'INSERT INTO users (name, username, email, password, rol) VALUES (?, ?, ?, ?, ?)',
            (name, username, email, password, 'estudiante')
        )
        conn.commit()
        user = conn.execute(f'SELECT {SAFE_FIELDS} FROM users WHERE id = ?', (cursor.lastrowid,)).fetchone()
        conn.close()
        return jsonify(dict(user)), 201
    except Exception as e:
        conn.close()
        if 'UNIQUE' in str(e):
            return jsonify({'error': 'Username o email ya en uso'}), 409
        return jsonify({'error': str(e)}), 500


@usuarios_bp.route('/api/usuarios/<int:id>', methods=['PUT'])
@require_auth
def update_user(id):
    current = session['user']
    if current['rol'] != 'admin' and current['id'] != id:
        return jsonify({'error': 'Acceso denegado'}), 403

    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (id,)).fetchone()
    if not user:
        conn.close()
        return jsonify({'error': 'Usuario no encontrado'}), 404

    data     = request.get_json() or {}
    u        = dict(user)
    name     = data.get('name',     u['name'])
    username = data.get('username', u['username'])
    email    = data.get('email',    u['email'])
    password = data.get('password') or u['password']

    if not all([name, username, email]):
        conn.close()
        return jsonify({'error': 'Nombre, usuario y email son obligatorios'}), 400

    try:
        conn.execute(
            'UPDATE users SET name=?, username=?, email=?, password=?, updated_at=CURRENT_TIMESTAMP WHERE id=?',
            (name, username, email, password, id)
        )
        conn.commit()
        updated      = conn.execute(f'SELECT {SAFE_FIELDS} FROM users WHERE id = ?', (id,)).fetchone()
        conn.close()
        updated_dict = dict(updated)

        if id == current['id']:
            session['user'] = updated_dict

        return jsonify(updated_dict)
    except Exception as e:
        conn.close()
        if 'UNIQUE' in str(e):
            return jsonify({'error': 'Username o email ya en uso'}), 409
        return jsonify({'error': str(e)}), 500


@usuarios_bp.route('/api/usuarios/<int:id>', methods=['DELETE'])
@require_admin
def delete_user(id):
    current = session['user']
    if current['id'] == id:
        return jsonify({'error': 'No puedes eliminar tu propia cuenta'}), 400

    conn = get_db()
    user = conn.execute('SELECT id FROM users WHERE id = ?', (id,)).fetchone()
    if not user:
        conn.close()
        return jsonify({'error': 'Usuario no encontrado'}), 404

    conn.execute('DELETE FROM users WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Usuario eliminado'})
