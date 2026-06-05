import json
from datetime import date
from flask import Blueprint, session, jsonify
from app.database import get_db
from app.middleware import require_auth
from app.algoritmo import generar_horario

horarios_bp = Blueprint('horarios', __name__)

DIAS = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo']


@horarios_bp.route('/generar', methods=['POST'])
@require_auth
def generar():
    user = session['user']
    conn = get_db()

    materias = [dict(r) for r in conn.execute(
        'SELECT * FROM materias WHERE usuario_id = ?', (user['id'],)
    ).fetchall()]

    if not materias:
        conn.close()
        return jsonify({'error': 'No tienes materias registradas. Agrega materias primero.'}), 400

    disp_row = conn.execute(
        'SELECT * FROM disponibilidad WHERE usuario_id = ?', (user['id'],)
    ).fetchone()

    if not disp_row:
        conn.close()
        return jsonify({'error': 'No has configurado tu disponibilidad. Configúrala primero.'}), 400

    disp = dict(disp_row)
    if sum(disp.get(d, 0) for d in DIAS) == 0:
        conn.close()
        return jsonify({'error': 'Tu disponibilidad semanal es 0 horas.'}), 400

    hoy = date.today().isoformat()
    ev_rows = conn.execute(
        'SELECT materia_id, fecha FROM evaluaciones WHERE usuario_id = ? AND fecha >= ? ORDER BY fecha',
        (user['id'], hoy)
    ).fetchall()

    evaluaciones = [
        {'materia_id': r['materia_id'], 'fecha': date.fromisoformat(r['fecha'])}
        for r in ev_rows
    ]

    horario = generar_horario(materias, disp, evaluaciones)
    horario_json = json.dumps(horario, ensure_ascii=False)

    existe = conn.execute(
        'SELECT id FROM horarios WHERE usuario_id = ?', (user['id'],)
    ).fetchone()

    if existe:
        conn.execute(
            'UPDATE horarios SET horario_json=?, generado_at=CURRENT_TIMESTAMP WHERE usuario_id=?',
            (horario_json, user['id'])
        )
    else:
        conn.execute(
            'INSERT INTO horarios (usuario_id, horario_json) VALUES (?, ?)',
            (user['id'], horario_json)
        )

    conn.commit()
    conn.close()
    return jsonify({'horario': horario, 'message': 'Horario generado correctamente'})


@horarios_bp.route('', methods=['GET'])
@require_auth
def get_horario():
    user = session['user']
    conn = get_db()
    row = conn.execute(
        'SELECT * FROM horarios WHERE usuario_id = ?', (user['id'],)
    ).fetchone()
    conn.close()

    if not row:
        return jsonify({'horario': None, 'generado_at': None})

    h = dict(row)
    return jsonify({'horario': json.loads(h['horario_json']), 'generado_at': h['generado_at']})
