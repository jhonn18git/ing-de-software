const express = require('express');
const router = express.Router();
const db = require('../db/database');

// POST /api/auth/login
router.post('/login', (req, res) => {
  const { username, password } = req.body;

  if (!username || !password) {
    return res.status(400).json({ error: 'Usuario y contraseña son requeridos.' });
  }

  const user = db.prepare('SELECT * FROM users WHERE username = ?').get(username);

  if (!user || user.password !== password) {
    return res.status(401).json({ error: 'Credenciales incorrectas.' });
  }

  const { password: _, ...safeUser } = user;
  req.session.user = safeUser;

  res.json({ message: 'Sesión iniciada correctamente.', user: safeUser });
});

// POST /api/auth/logout
router.post('/logout', (req, res) => {
  req.session.destroy((err) => {
    if (err) return res.status(500).json({ error: 'Error al cerrar sesión.' });
    res.clearCookie('connect.sid');
    res.json({ message: 'Sesión cerrada correctamente.' });
  });
});

// GET /api/auth/me
router.get('/me', (req, res) => {
  if (!req.session || !req.session.user) {
    return res.status(401).json({ error: 'No autenticado.' });
  }
  res.json({ user: req.session.user });
});

module.exports = router;
