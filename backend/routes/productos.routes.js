const express = require('express');
const router = express.Router();
const db = require('../db/database');
const { requireAuth, requireAdmin, requireOfertante } = require('../middleware/auth.middleware');

// GET /api/products
router.get('/', requireAuth, (req, res) => {
  const { rol, id } = req.session.user;

  let products;
  if (rol === 'admin') {
    products = db.prepare(`
      SELECT p.*, u.name as ofertante_name, u.username as ofertante_username
      FROM products p
      JOIN users u ON p.ofertante_id = u.id
      ORDER BY p.created_at DESC
    `).all();
  } else if (rol === 'ofertante') {
    // SPEC: HU-02 - Ofertante solo ve sus propios productos
    products = db.prepare(`
      SELECT p.*, u.name as ofertante_name, u.username as ofertante_username
      FROM products p
      JOIN users u ON p.ofertante_id = u.id
      WHERE p.ofertante_id = ?
      ORDER BY p.created_at DESC
    `).all(id);
  } else {
    // SPEC: Demandante solo ve productos aprobados
    products = db.prepare(`
      SELECT p.*, u.name as ofertante_name, u.username as ofertante_username
      FROM products p
      JOIN users u ON p.ofertante_id = u.id
      WHERE p.status = 'aprobado'
      ORDER BY p.created_at DESC
    `).all();
  }

  res.json(products);
});

// GET /api/products/pending — solo admin
router.get('/pending', requireAdmin, (req, res) => {
  // SPEC: HU-03 - Admin ve todos los productos en estado pendiente
  const products = db.prepare(`
    SELECT p.*, u.name as ofertante_name, u.username as ofertante_username
    FROM products p
    JOIN users u ON p.ofertante_id = u.id
    WHERE p.status = 'pendiente'
    ORDER BY p.created_at DESC
  `).all();
  res.json(products);
});

// GET /api/products/:id
router.get('/:id', requireAuth, (req, res) => {
  const product = db.prepare(`
    SELECT p.*, u.name as ofertante_name
    FROM products p
    JOIN users u ON p.ofertante_id = u.id
    WHERE p.id = ?
  `).get(req.params.id);

  if (!product) return res.status(404).json({ error: 'Producto no encontrado.' });

  const { rol, id } = req.session.user;
  if (rol === 'demandante' && product.status !== 'aprobado') {
    return res.status(403).json({ error: 'Acceso denegado.' });
  }
  if (rol === 'ofertante' && product.ofertante_id !== id) {
    return res.status(403).json({ error: 'Acceso denegado.' });
  }

  res.json(product);
});

// POST /api/products
router.post('/', requireOfertante, (req, res) => {
  const { title, description, price, category } = req.body;

  // SPEC: HU-01 - Rechazo si faltan campos obligatorios
  if (!title || !description || price === undefined || !category) {
    return res.status(400).json({ error: 'Título, descripción, precio y categoría son requeridos.' });
  }
  if (isNaN(parseFloat(price)) || parseFloat(price) < 0) {
    return res.status(400).json({ error: 'El precio debe ser un número positivo.' });
  }

  // SPEC: HU-01 - Registro exitoso de producto con estado pendiente
  const result = db.prepare(
    'INSERT INTO products (title, description, price, category, status, ofertante_id) VALUES (?, ?, ?, ?, ?, ?)'
  ).run(title, description.trim(), parseFloat(price), category.trim(), 'pendiente', req.session.user.id);

  const newProduct = db.prepare('SELECT * FROM products WHERE id = ?').get(Number(result.lastInsertRowid));
  res.status(201).json(newProduct);
});

// PUT /api/products/:id
router.put('/:id', requireOfertante, (req, res) => {
  const productId = parseInt(req.params.id);
  const { rol, id: userId } = req.session.user;

  const existing = db.prepare('SELECT * FROM products WHERE id = ?').get(productId);
  if (!existing) return res.status(404).json({ error: 'Producto no encontrado.' });

  if (rol !== 'admin' && existing.ofertante_id !== userId) {
    return res.status(403).json({ error: 'No puedes editar productos de otro ofertante.' });
  }

  const { title, description, price, category } = req.body;
  const updatedTitle = title || existing.title;
  const updatedDesc = description || existing.description;
  const updatedPrice = price !== undefined ? parseFloat(price) : existing.price;
  const updatedCategory = category || existing.category;

  // SPEC: HU-02 - Edición de producto vuelve estado a pendiente
  db.prepare(
    'UPDATE products SET title=?, description=?, price=?, category=?, status=\'pendiente\', updated_at=CURRENT_TIMESTAMP WHERE id=?'
  ).run(updatedTitle, updatedDesc, updatedPrice, updatedCategory, productId);

  const updated = db.prepare('SELECT * FROM products WHERE id = ?').get(productId);
  res.json(updated);
});

// DELETE /api/products/:id
router.delete('/:id', requireAuth, (req, res) => {
  const productId = parseInt(req.params.id);
  const { rol, id: userId } = req.session.user;

  const existing = db.prepare('SELECT * FROM products WHERE id = ?').get(productId);
  if (!existing) return res.status(404).json({ error: 'Producto no encontrado.' });

  if (rol !== 'admin' && existing.ofertante_id !== userId) {
    return res.status(403).json({ error: 'No puedes eliminar productos de otro ofertante.' });
  }

  db.prepare('DELETE FROM products WHERE id = ?').run(productId);
  res.json({ message: 'Producto eliminado correctamente.' });
});

// PATCH /api/products/:id/status — solo admin
router.patch('/:id/status', requireAdmin, (req, res) => {
  const productId = parseInt(req.params.id);
  const { status } = req.body;

  const validStatuses = ['aprobado', 'rechazado', 'pendiente'];
  if (!validStatuses.includes(status)) {
    return res.status(400).json({ error: 'Estado inválido. Usa: aprobado, rechazado o pendiente.' });
  }

  const existing = db.prepare('SELECT * FROM products WHERE id = ?').get(productId);
  if (!existing) return res.status(404).json({ error: 'Producto no encontrado.' });

  // SPEC: HU-03 - Admin no puede aprobar producto ya aprobado (idempotencia)
  if (existing.status === status) {
    return res.status(200).json({ message: `El producto ya está en estado '${status}'.`, product: existing });
  }

  // SPEC: HU-03 - Admin puede aprobar producto pendiente
  db.prepare(
    'UPDATE products SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?'
  ).run(status, productId);

  const updated = db.prepare('SELECT * FROM products WHERE id = ?').get(productId);
  res.json(updated);
});

module.exports = router;
