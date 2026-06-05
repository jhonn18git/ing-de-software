from functools import wraps
from flask import session, jsonify


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return jsonify({'error': 'No autenticado'}), 401
        return f(*args, **kwargs)
    return decorated


def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return jsonify({'error': 'No autenticado'}), 401
        if session['user']['rol'] != 'admin':
            return jsonify({'error': 'Acceso restringido a administradores'}), 403
        return f(*args, **kwargs)
    return decorated


def require_ofertante(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return jsonify({'error': 'No autenticado'}), 401
        if session['user']['rol'] not in ['admin', 'ofertante']:
            return jsonify({'error': 'Acceso restringido a ofertantes'}), 403
        return f(*args, **kwargs)
    return decorated
