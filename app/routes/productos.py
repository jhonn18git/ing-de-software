from flask import Blueprint, request, session, jsonify
from app.database import get_db
from app.middleware import require_auth, require_admin, require_ofertante

productos_bp = Blueprint('productos', __name__)

PRODUCT_QUERY = '''
    SELECT p.*, u.name AS ofertante_name
    FROM products p
    LEFT JOIN users u ON p.ofertante_id = u.id
'''


def _valid_price(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0


@productos_bp.route('', methods=['GET'])
@require_auth
def list_products():
    user = session['user']
    conn = get_db()

    if user['rol'] == 'admin':
        products = conn.execute(PRODUCT_QUERY).fetchall()
    elif user['rol'] == 'ofertante':
        products = conn.execute(
            PRODUCT_QUERY + ' WHERE p.ofertante_id = ?', (user['id'],)
        ).fetchall()
    else:
        products = conn.execute(
            PRODUCT_QUERY + " WHERE p.status = 'aprobado'"
        ).fetchall()

    conn.close()
    return jsonify([dict(p) for p in products])


@productos_bp.route('/pendientes', methods=['GET'])
@require_admin
def list_pending():
    conn = get_db()
    products = conn.execute(
        PRODUCT_QUERY + " WHERE p.status = 'pendiente'"
    ).fetchall()
    conn.close()
    return jsonify([dict(p) for p in products])


@productos_bp.route('/<int:id>', methods=['GET'])
@require_auth
def get_product(id):
    user = session['user']
    conn = get_db()
    product = conn.execute(PRODUCT_QUERY + ' WHERE p.id = ?', (id,)).fetchone()
    conn.close()

    if not product:
        return jsonify({'error': 'Producto no encontrado'}), 404

    p = dict(product)
    if user['rol'] == 'demandante' and p['status'] != 'aprobado':
        return jsonify({'error': 'Acceso denegado'}), 403
    if user['rol'] == 'ofertante' and p['ofertante_id'] != user['id']:
        return jsonify({'error': 'Acceso denegado'}), 403

    return jsonify(p)


@productos_bp.route('', methods=['POST'])
@require_ofertante
def create_product():
    user = session['user']
    data = request.get_json() or {}

    title = data.get('title', '').strip()
    description = data.get('description', '').strip()
    price = data.get('price')
    category = data.get('category', '').strip()

    if not all([title, description, category]):
        return jsonify({'error': 'Todos los campos son obligatorios'}), 400
    if not _valid_price(price):
        return jsonify({'error': 'El precio debe ser un número mayor o igual a 0'}), 400

    conn = get_db()
    cursor = conn.execute(
        'INSERT INTO products (title, description, price, category, ofertante_id) VALUES (?, ?, ?, ?, ?)',
        (title, description, price, category, user['id'])
    )
    conn.commit()
    product = conn.execute(PRODUCT_QUERY + ' WHERE p.id = ?', (cursor.lastrowid,)).fetchone()
    conn.close()
    return jsonify(dict(product)), 201


@productos_bp.route('/<int:id>', methods=['PUT'])
@require_auth
def update_product(id):
    user = session['user']
    conn = get_db()
    product = conn.execute('SELECT * FROM products WHERE id = ?', (id,)).fetchone()

    if not product:
        conn.close()
        return jsonify({'error': 'Producto no encontrado'}), 404

    p = dict(product)
    if user['rol'] == 'demandante':
        conn.close()
        return jsonify({'error': 'Acceso denegado'}), 403
    if user['rol'] == 'ofertante' and p['ofertante_id'] != user['id']:
        conn.close()
        return jsonify({'error': 'Acceso denegado'}), 403

    data = request.get_json() or {}
    title = data.get('title', p['title'])
    description = data.get('description', p['description'])
    price = data.get('price', p['price'])
    category = data.get('category', p['category'])

    if not _valid_price(price):
        conn.close()
        return jsonify({'error': 'El precio debe ser un número mayor o igual a 0'}), 400

    conn.execute(
        "UPDATE products SET title=?, description=?, price=?, category=?, status='pendiente', updated_at=CURRENT_TIMESTAMP WHERE id=?",
        (title, description, price, category, id)
    )
    conn.commit()
    updated = conn.execute(PRODUCT_QUERY + ' WHERE p.id = ?', (id,)).fetchone()
    conn.close()
    return jsonify(dict(updated))


@productos_bp.route('/<int:id>', methods=['DELETE'])
@require_auth
def delete_product(id):
    user = session['user']
    conn = get_db()
    product = conn.execute('SELECT * FROM products WHERE id = ?', (id,)).fetchone()

    if not product:
        conn.close()
        return jsonify({'error': 'Producto no encontrado'}), 404

    p = dict(product)
    if user['rol'] == 'demandante':
        conn.close()
        return jsonify({'error': 'Acceso denegado'}), 403
    if user['rol'] == 'ofertante' and p['ofertante_id'] != user['id']:
        conn.close()
        return jsonify({'error': 'Acceso denegado'}), 403

    conn.execute('DELETE FROM products WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Producto eliminado'})


@productos_bp.route('/<int:id>/status', methods=['PATCH'])
@require_admin
def change_status(id):
    data = request.get_json() or {}
    status = data.get('status')

    if status not in ['aprobado', 'rechazado', 'pendiente']:
        return jsonify({'error': 'Estado inválido. Use: aprobado, rechazado o pendiente'}), 400

    conn = get_db()
    product = conn.execute('SELECT id FROM products WHERE id = ?', (id,)).fetchone()
    if not product:
        conn.close()
        return jsonify({'error': 'Producto no encontrado'}), 404

    conn.execute(
        'UPDATE products SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?',
        (status, id)
    )
    conn.commit()
    conn.close()
    return jsonify({'message': f'Producto {status} correctamente'})
