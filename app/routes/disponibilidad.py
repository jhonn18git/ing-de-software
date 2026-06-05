from flask import Blueprint, request, session, jsonify
from app.database import get_db
from app.middleware import require_auth

disponibilidad_bp = Blueprint('disponibilidad', __name__)

DIAS = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo']


@disponibilidad_bp.route('', methods=['GET'])
@require_auth
def get_disponibilidad():
    user = session['user']
    conn = get_db()
    row = conn.execute(
        'SELECT * FROM disponibilidad WHERE usuario_id = ?', (user['id'],)
    ).fetchone()
    conn.close()
    if not row:
        return jsonify({d: 0 for d in DIAS})
    return jsonify(dict(row))


@disponibilidad_bp.route('', methods=['POST'])
@require_auth
def upsert_disponibilidad():
    user = session['user']
    data = request.get_json() or {}

    horas = {}
    for dia in DIAS:
        h = data.get(dia, 0)
        if not isinstance(h, int) or not (0 <= h <= 12):
            return jsonify({'error': f'Horas de {dia} deben ser un entero entre 0 y 12'}), 400
        horas[dia] = h

    conn = get_db()
    existe = conn.execute(
        'SELECT id FROM disponibilidad WHERE usuario_id = ?', (user['id'],)
    ).fetchone()

    if existe:
        conn.execute('''
            UPDATE disponibilidad
            SET lunes=?, martes=?, miercoles=?, jueves=?, viernes=?, sabado=?, domingo=?
            WHERE usuario_id=?
        ''', (horas['lunes'], horas['martes'], horas['miercoles'], horas['jueves'],
              horas['viernes'], horas['sabado'], horas['domingo'], user['id']))
    else:
        conn.execute('''
            INSERT INTO disponibilidad (usuario_id, lunes, martes, miercoles, jueves, viernes, sabado, domingo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user['id'], horas['lunes'], horas['martes'], horas['miercoles'], horas['jueves'],
              horas['viernes'], horas['sabado'], horas['domingo']))

    conn.commit()
    result = conn.execute(
        'SELECT * FROM disponibilidad WHERE usuario_id = ?', (user['id'],)
    ).fetchone()
    conn.close()
    return jsonify(dict(result))
