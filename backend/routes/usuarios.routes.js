const express = require('express');
const router = express.Router();
const db = require('../db/database');
const { requireAuth, requireAdmin } = require('../middleware/auth.middleware');

// GET /api/users — solo admin
router.get('/', requireAdmin, (req, res) => {
  const users = db.prepare('SELECT id, name, username, email, image, rol, created_at, updated_at FROM users').all();
  res.json(users);
});

// GET /api/users/:id
router.get('/:id', requireAuth, (req, res) => {
  const user = db.prepare('SELECT id, name, username, email, image, rol, created_at, updated_at FROM users WHERE id = ?').get(req.params.id);
  if (!user) return res.status(404).json({ error: 'Usuario no encontrado.' });

  const currentUser = req.session.user;
  if (currentUser.rol !== 'admin' && currentUser.id !== user.id) {
    return res.status(403).json({ error: 'Acceso denegado.' });
  }

  res.json(user);
});

// POST /api/users
router.post('/', requireAdmin, (req, res) => {
  const { name, username, email, password, rol, image } = req.body;

  if (!name || !username || !email || !password) {
    return res.status(400).json({ error: 'Nombre, usuario, email y contraseña son requeridos.' });
  }

  const validRoles = ['admin', 'ofertante', 'demandante'];
  const userRol = rol && validRoles.includes(rol) ? rol : 'demandante';

  try {
    const result = db.prepare(
      'INSERT INTO users (name, username, email, password, rol, image) VALUES (?, ?, ?, ?, ?, ?)'
    ).run(name, username, email, password, userRol, image || 'default.jpg');

    const newUser = db.prepare('SELECT id, name, username, email, image, rol, created_at FROM users WHERE id = ?').get(Number(result.lastInsertRowid));
    res.status(201).json(newUser);
  } catch (err) {
    if (err.message.includes('UNIQUE')) {
      return res.status(409).json({ error: 'El nombre de usuario o email ya existe.' });
    }
    res.status(500).json({ error: 'Error al crear el usuario.' });
  }
});

// PUT /api/users/:id
router.put('/:id', requireAuth, (req, res) => {
  const currentUser = req.session.user;
  const targetId = parseInt(req.params.id);

  if (currentUser.rol !== 'admin' && currentUser.id !== targetId) {
    return res.status(403).json({ error: 'Acceso denegado.' });
  }

  const existing = db.prepare('SELECT * FROM users WHERE id = ?').get(targetId);
  if (!existing) return res.status(404).json({ error: 'Usuario no encontrado.' });

  const { name, username, email, password, rol, image } = req.body;
  const updatedName = name || existing.name;
  const updatedUsername = username || existing.username;
  const updatedEmail = email || existing.email;
  const updatedPassword = password || existing.password;
  const updatedImage = image || existing.image;
  const updatedRol = (currentUser.rol === 'admin' && rol) ? rol : existing.rol;

  try {
    db.prepare(
      'UPDATE users SET name=?, username=?, email=?, password=?, rol=?, image=?, updated_at=CURRENT_TIMESTAMP WHERE id=?'
    ).run(updatedName, updatedUsername, updatedEmail, updatedPassword, updatedRol, updatedImage, targetId);

    const updated = db.prepare('SELECT id, name, username, email, image, rol, created_at, updated_at FROM users WHERE id = ?').get(targetId);
    res.json(updated);
  } catch (err) {
    if (err.message.includes('UNIQUE')) {
      return res.status(409).json({ error: 'El nombre de usuario o email ya existe.' });
    }
    res.status(500).json({ error: 'Error al actualizar el usuario.' });
  }
});

// DELETE /api/users/:id — solo admin
router.delete('/:id', requireAdmin, (req, res) => {
  const targetId = parseInt(req.params.id);

  if (req.session.user.id === targetId) {
    return res.status(400).json({ error: 'No puedes eliminar tu propia cuenta.' });
  }

  const existing = db.prepare('SELECT id FROM users WHERE id = ?').get(targetId);
  if (!existing) return res.status(404).json({ error: 'Usuario no encontrado.' });

  db.prepare('DELETE FROM users WHERE id = ?').run(targetId);
  res.json({ message: 'Usuario eliminado correctamente.' });
});

module.exports = router;
