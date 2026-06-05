from flask import Blueprint, request, session, jsonify
from app.database import get_db

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({'error': 'Usuario y contraseña requeridos'}), 400

    conn = get_db()
    user = conn.execute(
        'SELECT * FROM users WHERE username = ? AND password = ?',
        (username, password)
    ).fetchone()
    conn.close()

    if not user:
        return jsonify({'error': 'Credenciales inválidas'}), 401

    session['user'] = dict(user)
    return jsonify({'message': 'Login exitoso', 'user': dict(user)})


@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Sesión cerrada'})


@auth_bp.route('/me', methods=['GET'])
def me():
    if 'user' not in session:
        return jsonify({'error': 'No autenticado'}), 401
    return jsonify({'user': session['user']})
