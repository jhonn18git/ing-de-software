import traceback
from flask import Blueprint, jsonify, request, session
from app.database import get_db, DB_PATH
from app.middleware import require_auth
from app.carreras import get_carreras_buscar

perfil_bp = Blueprint('perfil', __name__)


@perfil_bp.route('/api/perfil', methods=['GET'])
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


@perfil_bp.route('/api/perfil', methods=['POST'])
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


@perfil_bp.route('/api/perfil/carreras', methods=['GET'])
@require_auth
def get_carreras():
    db = get_db()
    rows = db.execute(
        'SELECT DISTINCT carrera FROM horarios_usfx ORDER BY carrera'
    ).fetchall()
    db.close()
    return jsonify([r['carrera'] for r in rows]), 200


@perfil_bp.route('/api/perfil/semestres', methods=['GET'])
@require_auth
def get_semestres():
    try:
        carrera = request.args.get('carrera', '').strip()
        carreras_buscar = get_carreras_buscar(carrera)
        placeholders = ','.join('?' * len(carreras_buscar))

        conn = get_db()
        rows = conn.execute(
            f"SELECT DISTINCT semestre FROM horarios_usfx WHERE carrera IN ({placeholders}) ORDER BY semestre ASC",
            tuple(carreras_buscar)
        ).fetchall()
        conn.close()

        semestres = [r[0] for r in rows]
        print(f"DEBUG semestres - carrera='{carrera}' buscado en={carreras_buscar} encontrados={semestres}")
        if not semestres:
            semestres = list(range(1, 11))
        return jsonify(semestres), 200
    except Exception as e:
        print(f"ERROR en /semestres: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@perfil_bp.route('/api/perfil/grupos', methods=['GET'])
@require_auth
def get_grupos():
    try:
        carrera  = request.args.get('carrera', '').strip()
        semestre = request.args.get('semestre', '').strip()
        carreras_buscar = get_carreras_buscar(carrera)
        placeholders = ','.join('?' * len(carreras_buscar))

        conn = get_db()
        rows = conn.execute(
            f'''SELECT DISTINCT grupo FROM horarios_usfx
               WHERE carrera IN ({placeholders}) AND semestre=? ORDER BY grupo''',
            (*carreras_buscar, semestre)
        ).fetchall()
        conn.close()

        grupos = [r[0] for r in rows]
        print(f"DEBUG grupos - carrera='{carrera}' sem={semestre} buscado en={carreras_buscar} grupos={grupos}")

        if not grupos:
            grupos = ['A', 'B', 'C', 'NUEVOS A', 'NUEVOS B']
            print("DEBUG grupos - usando fallback genérico")

        return jsonify(grupos), 200
    except Exception as e:
        print(f"ERROR en /grupos: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
